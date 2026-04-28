# -*- coding: utf-8 -*-
"""Shared defaults for agent system prompt construction."""

DEFAULT_SYSTEM_PROMPT_FILES = [
    "AGENTS.md",
    "SOUL.md",
    "PROFILE.md",
    "USER_INFO.md",
]

COMMON_INFO_GUIDANCE = {
    "zh": (
        "# COMMON_INFO.md\n\n"
        "`COMMON_INFO.md` 是公共信息索引，不会默认展开全部内容。"
        "当用户问题涉及公共规则、项目背景、业务约定、资源信息、"
        "团队规范，或你判断当前上下文缺少共享背景时，主动查看"
        "`COMMON_INFO.md`，再按索引读取 `common_info/` 目录下"
        "相关 Markdown 文件。只加载与当前任务相关的文件。"
    ),
    "en": (
        "# COMMON_INFO.md\n\n"
        "`COMMON_INFO.md` is an index for shared information and is not "
        "expanded by default. When the user's request involves shared rules, "
        "project background, business agreements, resource information, team "
        "norms, or when you judge that shared context is missing, proactively "
        "read `COMMON_INFO.md`, then use its index to open relevant Markdown "
        "files under `common_info/`. Load only files relevant to the task."
    ),
    "ru": (
        "# COMMON_INFO.md\n\n"
        "`COMMON_INFO.md` is an index for shared information and is not "
        "expanded by default. When the user's request involves shared rules, "
        "project background, business agreements, resource information, team "
        "norms, or when you judge that shared context is missing, proactively "
        "read `COMMON_INFO.md`, then use its index to open relevant Markdown "
        "files under `common_info/`. Load only files relevant to the task."
    ),
}


def get_common_info_guidance(language: str) -> str:
    """Return the common-info lookup guidance for a language."""
    return COMMON_INFO_GUIDANCE.get(language, COMMON_INFO_GUIDANCE["en"])
