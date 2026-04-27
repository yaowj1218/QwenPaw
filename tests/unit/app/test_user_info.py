# -*- coding: utf-8 -*-
"""Tests for USER_INFO.md synchronization helpers."""

from qwenpaw.app.user_info import (
    USER_INFO_FILENAME,
    format_user_info_markdown,
    merge_user_info_markdown,
    write_user_info_md,
)


def _payload() -> dict:
    return {
        "username": "alice",
        "auth_enabled": True,
        "registered": True,
        "timezone": "Asia/Hong_Kong",
        "agent_language": "zh",
        "active_agent": "default",
        "updated_at": "2026-04-27T12:00:00+00:00",
        "agents": [
            {
                "id": "default",
                "name": "Default",
                "workspace_dir": "/tmp/default",
                "enabled": True,
                "language": "zh",
            },
        ],
    }


def test_merge_user_info_markdown_preserves_manual_notes():
    existing = "# USER_INFO\n\n## 手动记录\n\n- 喜欢简洁回答\n"
    generated = format_user_info_markdown(_payload())

    merged = merge_user_info_markdown(existing, generated)

    assert "## 自动同步信息" in merged
    assert "alice" in merged
    assert "## 手动记录" in merged
    assert "喜欢简洁回答" in merged


def test_write_user_info_md_updates_auto_block_only(tmp_path):
    user_info = tmp_path / USER_INFO_FILENAME
    user_info.write_text(
        "<!-- user-info:auto:start -->\nold\n"
        "<!-- user-info:auto:end -->\n\n## 手动记录\nkeep\n",
        encoding="utf-8",
    )

    write_user_info_md(tmp_path, _payload())

    content = user_info.read_text(encoding="utf-8")
    assert "old" not in content
    assert "alice" in content
    assert "## 手动记录\nkeep" in content
