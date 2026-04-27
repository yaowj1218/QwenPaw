# -*- coding: utf-8 -*-
"""End-to-end test for knowledge loading flow."""

from __future__ import annotations

from pathlib import Path

import pytest

from qwenpaw.knowledge.manager import KnowledgeBaseManager


@pytest.mark.asyncio
async def test_knowledge_prompt_injection(temp_workspace: Path) -> None:
    """Build knowledge prompt after refresh."""

    kb = KnowledgeBaseManager(workspace_dir=temp_workspace)
    await kb.refresh()
    target = temp_workspace / "knowledge_base" / "background" / "system.md"
    target.write_text("# System\n\nOwner: Alice", encoding="utf-8")
    await kb.refresh()
    prompt = kb.build_knowledge_prompt("Owner", session_id="s1", limit=3)
    assert "KNOWLEDGE_CONTEXT" in prompt
    assert "Owner: Alice" in prompt
