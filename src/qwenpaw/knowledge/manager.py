# -*- coding: utf-8 -*-
"""Workspace knowledge base manager."""

from __future__ import annotations

import asyncio
import json
import logging
import zipfile
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .config import KnowledgeBaseConfig, KnowledgeCategoryConfig
from .index import InvertedIndex
from .models import (
    KnowledgeFile,
    KnowledgeQuery,
    KnowledgeSearchResult,
    KnowledgeUpdateEvent,
)
from .graph import KnowledgeGraph
from .graph_builder import KnowledgeGraphBuilder
from .selector import KnowledgeSelector
from .health import KnowledgeHealthChecker
from .parsers import BaseParser
from .registry import KnowledgeSourceRegistry, ParserRegistry
from .sources import BaseKnowledgeSource, KnowledgeFileEntry
from .defaults import init_default_kb_structure
from .utils import (
    build_excerpt,
    compress_text,
    compute_checksum,
    decompress_text,
    diff_summary,
    ensure_dir,
    load_json,
    now_iso,
    save_json,
)

logger = logging.getLogger(__name__)


class KnowledgeBaseManager:
    """Manage workspace knowledge base files, cache, and search."""

    def __init__(
        self,
        workspace_dir: Path,
        config: KnowledgeBaseConfig | None = None,
    ):
        """Initialize the knowledge base manager.

        Args:
            workspace_dir: Workspace directory path.
            config: Optional knowledge base config.
        """

        self.workspace_dir = Path(workspace_dir)
        self.config = config or self._default_config()
        self.root_dir = self.workspace_dir / self.config.root_dir
        self._cache: dict[str, KnowledgeFile] = {}
        self._index = InvertedIndex()
        self._update_events: list[KnowledgeUpdateEvent] = []
        self._lock = asyncio.Lock()
        self._last_scan_at: datetime | None = None
        self._state_dir = self.root_dir / ".state"
        self._version_path = self._state_dir / "versions.json"
        self._index_path = self._state_dir / "index.json"
        self._config_path = self.root_dir / "knowledge_config.json"
        self._compressed_store: dict[str, str] = {}
        self._events_path = self._state_dir / "events.jsonl"
        self._refresh_task: asyncio.Task | None = None
        self._stop_refresh = asyncio.Event()
        self._session_categories: dict[str, list[str]] = {}
        self._graph = KnowledgeGraph()
        self._graph_builder = KnowledgeGraphBuilder()
        self._selector = KnowledgeSelector()
        self._health_checker = KnowledgeHealthChecker()

    def _default_config(self) -> KnowledgeBaseConfig:
        """Return default knowledge base config.

        Returns:
            KnowledgeBaseConfig: Default config.
        """

        return KnowledgeBaseConfig(
            categories=[
                KnowledgeCategoryConfig(
                    name="background",
                    description="Organization and business background",
                ),
                KnowledgeCategoryConfig(
                    name="user_context",
                    description="User profile and context",
                ),
                KnowledgeCategoryConfig(
                    name="domain_knowledge",
                    description="Domain knowledge",
                ),
            ],
        )

    def ensure_structure(self) -> None:
        """Ensure knowledge base folder structure exists.

        Returns:
            None: Directories are created if missing.
        """

        ensure_dir(self.root_dir)
        self._load_config_file()
        for category in self.config.categories:
            if not category.enabled:
                continue
            ensure_dir(self.root_dir / category.name)
        init_default_kb_structure(self.root_dir)
        ensure_dir(self._state_dir)
        if not self._config_path.exists():
            save_json(self._config_path, self._config_to_dict())

    def _load_config_file(self) -> None:
        """Load configuration from file if present.

        Returns:
            None: Config is updated in memory.
        """

        if not self._config_path.exists():
            return
        data = load_json(self._config_path, default=None)
        if not isinstance(data, dict):
            return
        self.config.root_dir = data.get("root_dir", self.config.root_dir)
        self.config.refresh_minutes = int(
            data.get("refresh_minutes", self.config.refresh_minutes),
        )
        self.config.max_excerpt_chars = int(
            data.get("max_excerpt_chars", self.config.max_excerpt_chars),
        )
        self.config.cache_ttl_seconds = int(
            data.get("cache_ttl_seconds", self.config.cache_ttl_seconds),
        )
        self.config.source_type = data.get("source_type", self.config.source_type)
        categories = []
        for raw in data.get("categories", []):
            if not isinstance(raw, dict) or not raw.get("name"):
                continue
            categories.append(
                KnowledgeCategoryConfig(
                    name=raw.get("name"),
                    description=raw.get("description", ""),
                    enabled=bool(raw.get("enabled", True)),
                    file_glob=raw.get("file_glob", "**/*.md"),
                ),
            )
        if categories:
            self.config.categories = categories

    def _config_to_dict(self) -> dict:
        """Serialize config to dict.

        Returns:
            dict: Serialized config.
        """

        return {
            "root_dir": self.config.root_dir,
            "refresh_minutes": self.config.refresh_minutes,
            "max_excerpt_chars": self.config.max_excerpt_chars,
            "cache_ttl_seconds": self.config.cache_ttl_seconds,
            "source_type": self.config.source_type,
            "categories": [asdict(cat) for cat in self.config.categories],
        }

    async def start(self) -> None:
        """Start knowledge manager and schedule refresh task.

        Returns:
            None: Manager is started.
        """

        self.ensure_structure()
        self.load_state()
        await self.refresh()
        self._stop_refresh.clear()
        if self._refresh_task is None or self._refresh_task.done():
            self._refresh_task = asyncio.create_task(self._run_refresh_loop())

    async def close(self) -> bool:
        """Stop background refresh tasks and persist state.

        Returns:
            bool: True if closed cleanly.
        """

        self._stop_refresh.set()
        if self._refresh_task is not None:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except Exception:
                pass
        self.save_state()
        return True

    async def _run_refresh_loop(self) -> None:
        """Run periodic refresh loop in background.

        Returns:
            None: Loop exits when stop event is set.
        """

        interval = max(int(self.config.refresh_minutes * 60), 60)
        while not self._stop_refresh.is_set():
            try:
                await asyncio.wait_for(self._stop_refresh.wait(), timeout=interval)
            except asyncio.TimeoutError:
                await self.refresh()

    def load_state(self) -> None:
        """Load cached versions and index state.

        Returns:
            None: State loaded if available.
        """

        self.ensure_structure()
        versions = load_json(self._version_path, default={}) or {}
        for file_id, payload in versions.items():
            try:
                path = Path(payload["path"])
                self._cache[file_id] = KnowledgeFile(
                    file_id=file_id,
                    path=path,
                    category=payload.get("category", ""),
                    tags=payload.get("tags", []),
                    last_modified=payload.get("last_modified", 0.0),
                    content=payload.get("content", ""),
                    checksum=payload.get("checksum", ""),
                    updated_at=(
                        datetime.fromisoformat(payload["updated_at"])
                        if payload.get("updated_at")
                        else None
                    ),
                    version=payload.get("version", 0),
                )
            except Exception as exc:
                logger.warning("Failed to load knowledge version %s: %s", file_id, exc)
        index_state = load_json(self._index_path, default=None)
        if index_state:
            self._index.load_state(index_state)

    def save_state(self) -> None:
        """Persist versions and index state to disk.

        Returns:
            None: State saved to disk.
        """

        self.ensure_structure()
        payload = {}
        for file_id, item in self._cache.items():
            payload[file_id] = {
                "path": str(item.path),
                "category": item.category,
                "tags": item.tags,
                "last_modified": item.last_modified,
                "content": item.content,
                "checksum": item.checksum,
                "updated_at": item.updated_at.isoformat() if item.updated_at else None,
                "version": item.version,
            }
        save_json(self._version_path, payload)
        save_json(self._index_path, self._index.dump_state())
        save_json(self._config_path, self._config_to_dict())

    def _create_source(self) -> BaseKnowledgeSource:
        """Create knowledge source based on registry.

        Returns:
            BaseKnowledgeSource: Knowledge source instance.
        """

        source_cls = KnowledgeSourceRegistry.get(self.config.source_type)
        if source_cls is None:
            raise RuntimeError(
                f"Knowledge source '{self.config.source_type}' is not registered",
            )
        categories = [
            {
                "name": cat.name,
                "file_glob": cat.file_glob,
            }
            for cat in self.config.categories
            if cat.enabled
        ]
        return source_cls(self.root_dir, categories=categories)

    def _get_parser(self, suffix: str) -> BaseParser | None:
        """Get parser for a file suffix.

        Args:
            suffix: File suffix (e.g. .md).

        Returns:
            BaseParser | None: Parser instance if found.
        """

        for key in ParserRegistry.list_registered():
            parser_cls = ParserRegistry.get(key)
            if not parser_cls:
                continue
            parser = parser_cls()
            if suffix.lower() in parser.file_types:
                return parser
        return None

    def scan(self) -> list[KnowledgeFileEntry]:
        """Scan all knowledge files from sources.

        Returns:
            list[KnowledgeFileEntry]: Scanned entries.
        """

        source = self._create_source()
        entries = list(source.scan())
        return entries

    async def refresh(self) -> dict:
        """Refresh the knowledge cache and index incrementally.

        Returns:
            dict: Refresh summary.
        """

        async with self._lock:
            self.ensure_structure()
            self.load_state()
            entries = self.scan()
            current_ids = {entry.file_id for entry in entries}
            cached_ids = set(self._cache.keys())

            removed_ids = cached_ids - current_ids
            for file_id in removed_ids:
                self._index.remove_document(file_id)
                self._cache.pop(file_id, None)
                self._record_event(file_id, "deleted", {})

            changed = 0
            created = 0
            for entry in entries:
                updated = await self._process_entry(entry)
                if updated == "created":
                    created += 1
                elif updated == "updated":
                    changed += 1

            self._last_scan_at = datetime.now()
            self.save_state()
            return {
                "created": created,
                "updated": changed,
                "removed": len(removed_ids),
                "last_scan_at": self._last_scan_at.isoformat(),
            }

    async def _process_entry(self, entry: KnowledgeFileEntry) -> str | None:
        """Process a single knowledge file entry.

        Args:
            entry: Knowledge file entry.

        Returns:
            str | None: "created", "updated" or None.
        """

        path = entry.path
        if not path.exists():
            return None
        stat = path.stat()
        cached = self._cache.get(entry.file_id)
        if cached and cached.last_modified >= stat.st_mtime:
            return None
        parser = self._get_parser(path.suffix)
        if parser is None:
            logger.warning("No parser for %s, skipping", path)
            return None
        try:
            content = path.read_text(encoding="utf-8")
        except Exception as exc:
            logger.warning("Failed to read knowledge file %s: %s", path, exc)
            return None
        meta, body = parser.parse(path, content)
        checksum = compute_checksum(body)
        if cached and cached.checksum == checksum:
            cached.last_modified = stat.st_mtime
            cached.updated_at = datetime.now()
            return None
        change_summary = diff_summary(cached.content if cached else "", body)
        if cached is None:
            cached = KnowledgeFile(
                file_id=entry.file_id,
                path=path,
                category=entry.category,
                tags=entry.tags,
            )
            self._cache[entry.file_id] = cached
        cached.content = build_excerpt(body, self.config.max_excerpt_chars)
        cached.checksum = checksum
        cached.last_modified = stat.st_mtime
        cached.updated_at = datetime.now()
        cached.version += 1
        self._index.add_document(entry.file_id, body)
        self._compressed_store[entry.file_id] = compress_text(body)
        self._graph.add_node(entry.file_id, "file", {"category": entry.category})
        self._graph_builder.build(self._graph)
        self._record_event(
            entry.file_id,
            "created" if cached.version == 1 else "updated",
            {
                "checksum": checksum,
                "summary": change_summary,
                "updated_at": cached.updated_at.isoformat(),
            },
        )
        return "created" if cached.version == 1 else "updated"

    def _record_event(self, file_id: str, change_type: str, detail: dict) -> None:
        """Record a knowledge update event.

        Args:
            file_id: File identifier.
            change_type: Change type.
            detail: Detail dictionary.

        Returns:
            None: Event stored in memory.
        """

        self._update_events.append(
            KnowledgeUpdateEvent(
                file_id=file_id,
                timestamp=datetime.now(),
                change_type=change_type,
                detail=detail,
            ),
        )
        self._append_event_log(file_id, change_type, detail)

    def _append_event_log(
        self,
        file_id: str,
        change_type: str,
        detail: dict,
    ) -> None:
        """Append an update event to the on-disk log.

        Args:
            file_id: File identifier.
            change_type: Change type.
            detail: Detail dictionary.

        Returns:
            None: Event is appended to log.
        """

        try:
            self._events_path.write_text(
                "",
                encoding="utf-8",
            ) if not self._events_path.exists() else None
            payload = {
                "file_id": file_id,
                "timestamp": now_iso(),
                "change_type": change_type,
                "detail": detail,
            }
            with self._events_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except Exception as exc:
            logger.warning("Failed to append knowledge event log: %s", exc)

    def get_update_events(self, limit: int = 100) -> list[dict]:
        """Return recent update events.

        Args:
            limit: Maximum number of events.

        Returns:
            list[dict]: Event list.
        """

        events = self._update_events[-limit:]
        return [
            {
                "file_id": e.file_id,
                "timestamp": e.timestamp.isoformat(),
                "change_type": e.change_type,
                "detail": e.detail,
            }
            for e in events
        ]

    def search(self, query: KnowledgeQuery) -> list[KnowledgeSearchResult]:
        """Search knowledge files by query text.

        Args:
            query: Knowledge query.

        Returns:
            list[KnowledgeSearchResult]: Search results.
        """

        matches = self._index.search(query.text, limit=query.limit)
        results: list[KnowledgeSearchResult] = []
        for file_id, score in matches:
            item = self._cache.get(file_id)
            if item is None:
                continue
            if query.categories and item.category not in query.categories:
                continue
            if query.tags:
                if not set(query.tags).intersection(set(item.tags)):
                    continue
            excerpt = build_excerpt(item.content, self.config.max_excerpt_chars)
            results.append(
                KnowledgeSearchResult(
                    file_id=file_id,
                    score=score,
                    content=excerpt,
                    metadata={
                        "category": item.category,
                        "tags": item.tags,
                        "version": item.version,
                    },
                ),
            )
        return results

    def list_files(self) -> list[dict]:
        """List cached knowledge files.

        Returns:
            list[dict]: File summaries.
        """

        return [
            {
                "file_id": file_id,
                "category": item.category,
                "tags": item.tags,
                "version": item.version,
                "updated_at": item.updated_at.isoformat()
                if item.updated_at
                else None,
            }
            for file_id, item in self._cache.items()
        ]

    def resolve_context(
        self,
        query: KnowledgeQuery,
        explicit_categories: list[str] | None = None,
    ) -> list[KnowledgeSearchResult]:
        """Resolve context based on query and explicit categories.

        Args:
            query: Knowledge query.
            explicit_categories: Categories explicitly requested by user.

        Returns:
            list[KnowledgeSearchResult]: Selected knowledge results.
        """

        if explicit_categories:
            query.categories = explicit_categories
        return self.search(query)

    def set_session_categories(self, session_id: str, categories: list[str]) -> None:
        """Set preferred categories for a session.

        Args:
            session_id: Session identifier.
            categories: Category list.

        Returns:
            None: Session preferences updated.
        """

        self._session_categories[session_id] = categories

    def get_session_categories(self, session_id: str) -> list[str]:
        """Get preferred categories for a session.

        Args:
            session_id: Session identifier.

        Returns:
            list[str]: Category list.
        """

        return self._session_categories.get(session_id, [])

    def validate_files(self) -> list[dict]:
        """Validate knowledge files for health checking.

        Returns:
            list[dict]: Validation issues.
        """

        issues = []
        for file_id, item in self._cache.items():
            if not item.content.strip():
                issues.append(
                    {
                        "file_id": file_id,
                        "issue": "empty_content",
                    },
                )
        path_issues = self._health_checker.check_paths(
            [(file_id, item.path) for file_id, item in self._cache.items()],
        )
        for issue in path_issues:
            issues.append(
                {
                    "file_id": issue.file_id,
                    "issue": issue.issue,
                    "detail": issue.detail,
                },
            )
        return issues

    def get_file_content(self, file_id: str) -> str:
        """Get full content for a knowledge file.

        Args:
            file_id: File identifier.

        Returns:
            str: Full file content or empty string.
        """

        compressed = self._compressed_store.get(file_id)
        if not compressed:
            return ""
        try:
            return decompress_text(compressed)
        except Exception as exc:
            logger.warning("Failed to decompress knowledge content: %s", exc)
            return ""

    def backup(self) -> dict:
        """Backup knowledge files metadata and state.

        Returns:
            dict: Backup info.
        """

        backup_dir = self.root_dir / "backup"
        ensure_dir(backup_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_path = backup_dir / f"kb_backup_{timestamp}.zip"
        meta_path = backup_dir / f"kb_backup_{timestamp}.json"

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in self.root_dir.rglob("*"):
                rel = path.relative_to(self.root_dir)
                if rel.parts and rel.parts[0] in {"backup", ".state"}:
                    continue
                if path.is_file():
                    zf.write(path, rel.as_posix())

        payload = {
            "timestamp": now_iso(),
            "zip_path": str(zip_path),
            "files": self.list_files(),
            "events": self.get_update_events(limit=200),
        }
        save_json(meta_path, payload)
        return {"backup_path": str(zip_path), "meta_path": str(meta_path)}

    def restore(self, backup_path: str) -> dict:
        """Restore state from backup metadata.

        Args:
            backup_path: Backup JSON path.

        Returns:
            dict: Restore status.
        """

        path = Path(backup_path)
        if not path.exists():
            return {"restored": False, "reason": "missing_backup"}
        if path.suffix == ".json":
            data = load_json(path, default=None)
            if not data:
                return {"restored": False, "reason": "invalid_backup"}
            zip_path = data.get("zip_path")
            if zip_path:
                return self.restore(str(zip_path))
            return {"restored": True, "timestamp": data.get("timestamp")}
        if path.suffix == ".zip":
            with zipfile.ZipFile(path, "r") as zf:
                zf.extractall(self.root_dir)
            return {"restored": True, "timestamp": now_iso()}
        return {"restored": False, "reason": "unsupported_backup"}

    def build_knowledge_prompt(
        self,
        query_text: str,
        session_id: str,
        categories: list[str] | None = None,
        limit: int = 5,
    ) -> str:
        """Build a prompt section from knowledge search results.

        Args:
            query_text: Query text from conversation.
            session_id: Session identifier.
            categories: Optional category filter.
            limit: Maximum number of results.

        Returns:
            str: Formatted knowledge prompt section.
        """

        pinned = self.get_session_categories(session_id)
        query = KnowledgeQuery(
            text=query_text,
            categories=categories or pinned or None,
            limit=limit,
        )
        results = self.search(query)
        selection = self._selector.select(results, query_text, limit=limit)
        results = selection.selected
        if not results:
            return ""
        lines = ["# KNOWLEDGE_CONTEXT", ""]
        for item in results:
            lines.append(f"## {item.file_id} (score={item.score:.2f})")
            lines.append(item.content.strip())
            lines.append("")
        return "\n".join(lines).strip()
