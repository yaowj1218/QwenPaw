# -*- coding: utf-8 -*-
"""Knowledge source implementations."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .registry import KnowledgeSourceRegistry
from .utils import ensure_dir

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeFileEntry:
    """Knowledge file entry for scan results.

    Args:
        file_id: Unique identifier.
        path: Absolute file path.
        category: Category name.
        tags: Optional tags.
    """

    file_id: str
    path: Path
    category: str
    tags: list[str]


class BaseKnowledgeSource:
    """Base class for knowledge sources."""

    def __init__(self, root_dir: Path, categories: Iterable[dict] | None = None):
        """Initialize with root directory.

        Args:
            root_dir: Knowledge root directory.
            categories: Optional category configs.
        """

        self.root_dir = root_dir
        self._categories = list(categories or [])

    def scan(self) -> Iterable[KnowledgeFileEntry]:
        """Scan and return knowledge file entries.

        Returns:
            Iterable[KnowledgeFileEntry]: Scanned entries.
        """

        raise NotImplementedError


@KnowledgeSourceRegistry.register("file")
class FileKnowledgeSource(BaseKnowledgeSource):
    """File-based knowledge source (Markdown)."""

    def scan(self) -> Iterable[KnowledgeFileEntry]:
        """Scan file-based knowledge entries under root directory.

        Returns:
            Iterable[KnowledgeFileEntry]: Scanned entries.
        """

        ensure_dir(self.root_dir)
        categories = (
            self._categories
            if self._categories
            else [
                {"name": path.name, "file_glob": "**/*.md"}
                for path in self.root_dir.iterdir()
                if path.is_dir()
            ]
        )
        for cat in categories:
            name = cat.get("name")
            if not name:
                continue
            category_dir = self.root_dir / name
            if not category_dir.is_dir():
                continue
            category = category_dir.name
            file_glob = cat.get("file_glob", "**/*.md")
            for path in sorted(category_dir.glob(file_glob)):
                if not path.is_file():
                    continue
                rel_path = path.relative_to(self.root_dir).as_posix()
                tags = [category]
                if path.parent != category_dir:
                    tags.append(path.parent.name)
                yield KnowledgeFileEntry(
                    file_id=rel_path,
                    path=path,
                    category=category,
                    tags=tags,
                )
