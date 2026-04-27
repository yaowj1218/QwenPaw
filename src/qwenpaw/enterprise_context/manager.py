# -*- coding: utf-8 -*-
"""Fetch enterprise context sources and render them into markdown files."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from qwenpaw.app.crons.heartbeat import (
    is_cron_expression,
    parse_heartbeat_cron,
    parse_heartbeat_every,
)
from qwenpaw.config.config import ContextConfig, ContextSourceConfig
from qwenpaw.config.config import load_agent_config

logger = logging.getLogger(__name__)

_SECTION_TITLES = {
    "user_info": "User Info",
    "common_knowledge": "Common Knowledge",
}


class EnterpriseContextManager:
    """Maintains generated context markdown for one agent workspace."""

    def __init__(
        self,
        *,
        workspace_dir: str | Path,
        agent_id: str,
        config: ContextConfig | None = None,
        timezone_name: str = "UTC",
    ):
        self.workspace_dir = Path(workspace_dir)
        self.agent_id = agent_id
        self.config = config or ContextConfig()
        self._scheduler = AsyncIOScheduler(timezone=timezone_name)
        self._started = False
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """Start refresh scheduling and optionally refresh immediately."""
        if self._started:
            return
        self._started = True

        if not self.config.enabled:
            return

        if self.config.refresh_on_start:
            try:
                await self.refresh()
            except Exception:  # pylint: disable=broad-except
                logger.exception(
                    "enterprise context refresh_on_start failed: agent=%s",
                    self.agent_id,
                )

        if self.config.refresh_every:
            trigger = self._build_trigger(self.config.refresh_every)
            self._scheduler.start()
            self._scheduler.add_job(
                self._scheduled_refresh,
                trigger=trigger,
                id="enterprise_context_refresh",
                replace_existing=True,
            )
            logger.info(
                "Enterprise context refresh scheduled: agent=%s every=%s",
                self.agent_id,
                self.config.refresh_every,
            )

    async def close(self) -> None:
        """Stop scheduled refreshes."""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
        self._started = False

    async def reload_config(self) -> None:
        """Reload configuration from agent.json and reschedule."""
        self.config = load_agent_config(self.agent_id).context
        await self.close()
        await self.start()

    async def refresh(self) -> Path | None:
        """Fetch all configured sources and rewrite generated markdown.

        Returns the generated prompt file path, or None when disabled.
        """
        if not self.config.enabled:
            return None

        async with self._lock:
            sections: dict[str, list[str]] = {
                "user_info": [],
                "common_knowledge": [],
            }

            for source in self.config.sources:
                if not source.enabled:
                    continue
                try:
                    value = await self._fetch_source(source)
                    sections[source.kind].append(
                        self._render_source(source, value),
                    )
                except Exception as exc:  # pylint: disable=broad-except
                    logger.warning(
                        "Failed to refresh enterprise context source: "
                        "agent=%s source=%s error=%r",
                        self.agent_id,
                        source.name or source.url,
                        exc,
                    )
                    sections[source.kind].append(
                        self._render_source_error(source, exc),
                    )

            output_dir = self.workspace_dir / self.config.output_dir
            output_dir.mkdir(parents=True, exist_ok=True)

            user_info = self._render_section("user_info", sections)
            common_knowledge = self._render_section(
                "common_knowledge",
                sections,
            )
            self._write_text(output_dir / "user_info.md", user_info)
            self._write_text(
                output_dir / "common_knowledge.md",
                common_knowledge,
            )

            prompt_path = self.workspace_dir / self.config.prompt_file
            self._write_text(
                prompt_path,
                self._render_prompt_file(user_info, common_knowledge),
            )
            logger.info(
                "Enterprise context refreshed: agent=%s file=%s",
                self.agent_id,
                prompt_path,
            )
            return prompt_path

    async def _scheduled_refresh(self) -> None:
        try:
            await self.refresh()
        except asyncio.CancelledError:
            raise
        except Exception:  # pylint: disable=broad-except
            logger.exception(
                "scheduled enterprise context refresh failed: agent=%s",
                self.agent_id,
            )

    def _build_trigger(self, schedule: str) -> CronTrigger | IntervalTrigger:
        if is_cron_expression(schedule):
            minute, hour, day, month, day_of_week = parse_heartbeat_cron(
                schedule,
            )
            return CronTrigger(
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week,
            )
        return IntervalTrigger(seconds=parse_heartbeat_every(schedule))

    async def _fetch_source(self, source: ContextSourceConfig) -> Any:
        if not source.url:
            return {}

        timeout = httpx.Timeout(source.timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout) as client:
            if source.method == "POST":
                response = await client.post(
                    source.url,
                    headers=source.headers,
                    params=source.params,
                    json=source.body or None,
                )
            else:
                response = await client.get(
                    source.url,
                    headers=source.headers,
                    params=source.params,
                )
            response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            value = response.json()
        else:
            try:
                value = response.json()
            except ValueError:
                value = response.text

        if source.json_path:
            value = self._extract_json_path(value, source.json_path)
        return value

    def _extract_json_path(self, value: Any, path: str) -> Any:
        current = value
        for part in path.split("."):
            if not part:
                continue
            if isinstance(current, dict):
                current = current[part]
            elif isinstance(current, list):
                current = current[int(part)]
            else:
                raise KeyError(path)
        return current

    def _render_source(self, source: ContextSourceConfig, value: Any) -> str:
        title = source.name or source.url or source.kind
        rendered = self._render_value(value)
        return f"## {title}\n\n{rendered}".strip()

    def _render_source_error(
        self,
        source: ContextSourceConfig,
        exc: Exception,
    ) -> str:
        title = source.name or source.url or source.kind
        return f"## {title}\n\n> Refresh failed: `{type(exc).__name__}`"

    def _render_value(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, list):
            if not value:
                return ""
            return "\n".join(f"- {self._inline(item)}" for item in value)
        if isinstance(value, dict):
            lines = []
            for key, item in value.items():
                lines.append(f"- **{key}**: {self._inline(item)}")
            return "\n".join(lines)
        return str(value)

    def _inline(self, value: Any) -> str:
        if isinstance(value, (dict, list)):
            return "`" + json.dumps(value, ensure_ascii=False) + "`"
        return str(value)

    def _render_section(
        self,
        kind: str,
        sections: dict[str, list[str]],
    ) -> str:
        title = _SECTION_TITLES[kind]
        body = "\n\n".join(part for part in sections[kind] if part).strip()
        if not body:
            body = "_No context sources produced content._"
        return f"# {title}\n\n{body}\n"

    def _render_prompt_file(
        self,
        user_info: str,
        common_knowledge: str,
    ) -> str:
        generated_at = datetime.now(timezone.utc).isoformat()
        return (
            "# Enterprise Context\n\n"
            "This file is generated from enterprise context sources. "
            "Use it as current company/user background when relevant.\n\n"
            f"_Generated at: {generated_at}_\n\n"
            f"{user_info.strip()}\n\n{common_knowledge.strip()}\n"
        )

    def _write_text(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(path)
