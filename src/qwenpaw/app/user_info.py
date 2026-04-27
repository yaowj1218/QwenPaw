# -*- coding: utf-8 -*-
"""User-info API payload and workspace synchronization helpers."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI
from pydantic import BaseModel, Field

from ..config import load_config
from ..config.config import load_agent_config
from ..constant import EnvVarLoader

logger = logging.getLogger(__name__)

USER_INFO_FILENAME = "USER_INFO.md"
USER_INFO_ENDPOINT = "/api/user-info"
USER_INFO_SYNC_INTERVAL_SECONDS = EnvVarLoader.get_int(
    "QWENPAW_USER_INFO_SYNC_INTERVAL_SECONDS",
    300,
    min_value=30,
)

_AUTO_START = "<!-- user-info:auto:start -->"
_AUTO_END = "<!-- user-info:auto:end -->"


class UserInfoAgent(BaseModel):
    """Agent summary included in the user-info payload."""

    id: str
    name: str = ""
    description: str = ""
    workspace_dir: str
    enabled: bool = True
    language: str = ""


class UserInfoResponse(BaseModel):
    """Non-sensitive information about the current user environment."""

    username: str = ""
    auth_enabled: bool
    registered: bool
    timezone: str
    agent_language: str
    active_agent: str
    agents: list[UserInfoAgent] = Field(default_factory=list)
    updated_at: str


def build_user_info_payload(username: str = "") -> UserInfoResponse:
    """Build the user-info response from local configuration."""
    from .auth import has_registered_users, is_auth_enabled

    config = load_config()
    agents: list[UserInfoAgent] = []

    for agent_id, agent_ref in config.agents.profiles.items():
        name = ""
        description = ""
        language = ""
        try:
            agent_config = load_agent_config(agent_id)
            name = agent_config.name
            description = agent_config.description or ""
            language = agent_config.language or ""
        except Exception:
            logger.debug(
                "user_info: failed to load agent config for %s",
                agent_id,
                exc_info=True,
            )

        agents.append(
            UserInfoAgent(
                id=agent_id,
                name=name,
                description=description,
                workspace_dir=agent_ref.workspace_dir,
                enabled=getattr(agent_ref, "enabled", True),
                language=language,
            ),
        )

    return UserInfoResponse(
        username=username,
        auth_enabled=is_auth_enabled(),
        registered=has_registered_users(),
        timezone=config.user_timezone,
        agent_language=config.agents.language,
        active_agent=config.agents.active_agent or "default",
        agents=agents,
        updated_at=datetime.now(timezone.utc).isoformat(),
    )


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
            "<!-- 本区块由后台从 /api/user-info 自动同步，请勿手动编辑。 -->",
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


async def sync_user_info_once(app: FastAPI) -> None:
    """Request the user-info API and update USER_INFO.md in workspaces."""
    transport = httpx.ASGITransport(
        app=app,
        client=("127.0.0.1", 0),
    )
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://127.0.0.1",
    ) as client:
        response = await client.get(USER_INFO_ENDPOINT)
        response.raise_for_status()
        payload = response.json()

    config = load_config()
    for agent_ref in config.agents.profiles.values():
        if not getattr(agent_ref, "enabled", True):
            continue
        try:
            write_user_info_md(Path(agent_ref.workspace_dir).expanduser(), payload)
        except OSError:
            logger.warning(
                "user_info: failed to write %s in %s",
                USER_INFO_FILENAME,
                agent_ref.workspace_dir,
                exc_info=True,
            )


def start_user_info_sync_task(app: FastAPI) -> asyncio.Task:
    """Start periodic synchronization of USER_INFO.md."""

    async def _loop() -> None:
        while True:
            try:
                await sync_user_info_once(app)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.warning("user_info: sync failed", exc_info=True)

            await asyncio.sleep(USER_INFO_SYNC_INTERVAL_SECONDS)

    return asyncio.create_task(_loop(), name="user_info_sync")


def _md_cell(value: object) -> str:
    return _md_inline(value).replace("|", "\\|").replace("\n", " ")


def _md_inline(value: object) -> str:
    return str(value or "").replace("\n", " ").strip()
