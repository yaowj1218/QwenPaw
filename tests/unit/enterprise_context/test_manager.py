# -*- coding: utf-8 -*-
"""Tests for enterprise context markdown generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from qwenpaw.config.config import ContextConfig, ContextSourceConfig
from qwenpaw.enterprise_context import EnterpriseContextManager


@pytest.mark.asyncio
async def test_refresh_writes_context_markdown(
    temp_workspace: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Refresh should render both context sections and the prompt file."""

    config = ContextConfig(
        enabled=True,
        sources=[
            ContextSourceConfig(
                name="Profile",
                kind="user_info",
                url="https://internal.test/profile",
            ),
            ContextSourceConfig(
                name="Rules",
                kind="common_knowledge",
                url="https://internal.test/rules",
            ),
        ],
    )
    manager = EnterpriseContextManager(
        workspace_dir=temp_workspace,
        agent_id="default",
        config=config,
    )

    async def fake_fetch(source: ContextSourceConfig) -> Any:
        if source.kind == "user_info":
            return {"name": "Alice", "team": "Platform"}
        return ["Use internal GitLab", "Create design docs for large changes"]

    monkeypatch.setattr(manager, "_fetch_source", fake_fetch)

    prompt_path = await manager.refresh()

    assert prompt_path == temp_workspace / "CONTEXT.md"
    prompt = prompt_path.read_text(encoding="utf-8")
    assert "# Enterprise Context" in prompt
    assert "**name**: Alice" in prompt
    assert "Use internal GitLab" in prompt
    assert (temp_workspace / "context" / "user_info.md").exists()
    assert (temp_workspace / "context" / "common_knowledge.md").exists()


def test_json_path_extracts_nested_values(temp_workspace: Path) -> None:
    """json_path supports dict keys and list indexes."""

    manager = EnterpriseContextManager(
        workspace_dir=temp_workspace,
        agent_id="default",
    )

    value = {"data": {"items": [{"name": "first"}, {"name": "second"}]}}

    assert manager._extract_json_path(value, "data.items.1.name") == "second"
