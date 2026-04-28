# -*- coding: utf-8 -*-
"""USER_INFO.md rendering and update helpers."""
from __future__ import annotations

from pathlib import Path
from typing import Any

USER_INFO_FILENAME = "USER_INFO.md"

_AUTO_START = "<!-- user-info:auto:start -->"
_AUTO_END = "<!-- user-info:auto:end -->"


def format_user_info_markdown(payload: dict[str, Any]) -> str:
    """Render an auto-generated USER_INFO.md section."""
    agents = payload.get("agents") or []
    agent_rows = [
        "| ID | 名称 | 状态 | 语言 | Workspace |",
        "| --- | --- | --- | --- | --- |",
    ]
    for agent in agents:
        enabled = "启用" if agent.get("enabled", True) else "停用"
        agent_rows.append(
            "| {id} | {name} | {enabled} | {language} | {workspace} |".format(
                id=_md_cell(agent.get("id", "")),
                name=_md_cell(agent.get("name", "")),
                enabled=enabled,
                language=_md_cell(agent.get("language", "")),
                workspace=_md_cell(agent.get("workspace_dir", "")),
            ),
        )

    username = payload.get("username") or "未设置"
    auth_enabled = "开启" if payload.get("auth_enabled") else "关闭"
    registered = "是" if payload.get("registered") else "否"

    return "\n".join(
        [
            _AUTO_START,
            "<!-- 本区块由后台 user-info 同步服务自动更新，请勿手动编辑。 -->",
            "",
            "## 自动同步信息",
            "",
            f"- **更新时间：** {payload.get('updated_at', '')}",
            f"- **用户名：** {_md_inline(username)}",
            f"- **认证：** {auth_enabled}",
            f"- **已注册用户：** {registered}",
            f"- **时区：** {_md_inline(payload.get('timezone', ''))}",
            f"- **Agent 语言：** {_md_inline(payload.get('agent_language', ''))}",
            f"- **当前 Agent：** {_md_inline(payload.get('active_agent', ''))}",
            "",
            "### Agent Workspaces",
            "",
            *agent_rows,
            _AUTO_END,
            "",
        ],
    )


def merge_user_info_markdown(existing: str, generated: str) -> str:
    """Replace or prepend the auto-generated block in USER_INFO.md."""
    start_idx = existing.find(_AUTO_START)
    end_idx = existing.find(_AUTO_END)
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        end_idx += len(_AUTO_END)
        merged = existing[:start_idx] + generated.strip() + existing[end_idx:]
        return merged.strip() + "\n"

    if existing.strip():
        return generated.strip() + "\n\n" + existing.strip() + "\n"
    return generated.strip() + "\n"


def write_user_info_md(workspace_dir: Path, payload: dict[str, Any]) -> None:
    """Write the synchronized USER_INFO.md block into one workspace."""
    workspace_dir.mkdir(parents=True, exist_ok=True)
    user_info_path = workspace_dir / USER_INFO_FILENAME
    existing = ""
    if user_info_path.exists():
        existing = user_info_path.read_text(encoding="utf-8")

    generated = format_user_info_markdown(payload)
    user_info_path.write_text(
        merge_user_info_markdown(existing, generated),
        encoding="utf-8",
    )


def _md_cell(value: object) -> str:
    return _md_inline(value).replace("|", "\\|").replace("\n", " ")


def _md_inline(value: object) -> str:
    return str(value or "").replace("\n", " ").strip()
