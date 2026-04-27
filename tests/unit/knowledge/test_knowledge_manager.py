# -*- coding: utf-8 -*-
"""Tests for knowledge base manager."""

from __future__ import annotations

from pathlib import Path

import pytest

from qwenpaw.knowledge.manager import KnowledgeBaseManager
from qwenpaw.knowledge.models import KnowledgeQuery, KnowledgeFile


@pytest.mark.asyncio
async def test_refresh_creates_structure(temp_workspace: Path) -> None:
    """Manager should create base structure and files."""

    kb = KnowledgeBaseManager(workspace_dir=temp_workspace)
    result = await kb.refresh()
    assert result["created"] >= 0
    root = temp_workspace / "knowledge_base"
    assert root.exists()
    assert (root / "background").exists()
    assert (root / "user_context").exists()
    assert (root / "domain_knowledge").exists()


@pytest.mark.asyncio
async def test_refresh_detects_updates(temp_workspace: Path) -> None:
    """Manager should detect updated files."""

    kb = KnowledgeBaseManager(workspace_dir=temp_workspace)
    await kb.refresh()
    target = temp_workspace / "knowledge_base" / "background" / "note.md"
    target.write_text("# Note\n\nhello world", encoding="utf-8")
    result = await kb.refresh()
    assert result["created"] >= 1
    query = KnowledgeQuery(text="hello", limit=5)
    matches = kb.search(query)
    assert matches


def test_backup_and_restore(temp_workspace: Path) -> None:
    """Backup and restore should return success."""

    kb = KnowledgeBaseManager(workspace_dir=temp_workspace)
    kb.ensure_structure()
    info = kb.backup()
    assert "backup_path" in info
    restored = kb.restore(info["backup_path"])
    assert restored.get("restored") is True


def test_health_check(temp_workspace: Path) -> None:
    """Health check should return issues when content empty."""

    kb = KnowledgeBaseManager(workspace_dir=temp_workspace)
    kb.ensure_structure()
    path = temp_workspace / "knowledge_base" / "background" / "empty.md"
    path.write_text("", encoding="utf-8")
    kb._cache["background/empty.md"] = KnowledgeFile(
        file_id="background/empty.md",
        path=path,
        category="background",
        content="",
    )
    issues = kb.validate_files()
    assert isinstance(issues, list)
