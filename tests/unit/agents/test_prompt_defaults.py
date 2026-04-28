# -*- coding: utf-8 -*-
"""Tests for system prompt default file behavior."""

from qwenpaw.agents.prompt import PromptBuilder
from qwenpaw.agents.prompt_defaults import DEFAULT_SYSTEM_PROMPT_FILES


def test_default_system_prompt_files_include_user_info_not_common_info():
    assert "USER_INFO.md" in DEFAULT_SYSTEM_PROMPT_FILES
    assert "COMMON_INFO.md" not in DEFAULT_SYSTEM_PROMPT_FILES


def test_prompt_builder_always_loads_user_info_with_legacy_file_list(tmp_path):
    (tmp_path / "AGENTS.md").write_text("agent rules", encoding="utf-8")
    (tmp_path / "USER_INFO.md").write_text("user details", encoding="utf-8")
    (tmp_path / "COMMON_INFO.md").write_text("common index", encoding="utf-8")

    prompt = PromptBuilder(
        tmp_path,
        enabled_files=["AGENTS.md", "SOUL.md", "PROFILE.md"],
        language="en",
    ).build()

    assert "# USER_INFO.md" in prompt
    assert "user details" in prompt
    assert "common index" not in prompt
    assert "read `COMMON_INFO.md`" in prompt


def test_prompt_builder_adds_common_info_guidance_in_chinese(tmp_path):
    (tmp_path / "AGENTS.md").write_text("agent rules", encoding="utf-8")

    prompt = PromptBuilder(tmp_path, language="zh").build()

    assert "`COMMON_INFO.md` 是公共信息索引" in prompt
    assert "common_info/" in prompt
