# -*- coding: utf-8 -*-
"""Workspace synchronization for USER_INFO.md."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from ...config import load_config
from .markdown import USER_INFO_FILENAME, write_user_info_md
from .provider import fetch_user_info_payload

logger = logging.getLogger(__name__)


async def sync_user_info_once() -> None:
    """Fetch user-info and update USER_INFO.md in workspaces."""
    payload = (await fetch_user_info_payload()).model_dump(mode="json")

    config = load_config()
    for agent_ref in config.agents.profiles.values():
        if not getattr(agent_ref, "enabled", True):
            continue
        try:
            write_user_info_md(
                Path(agent_ref.workspace_dir).expanduser(),
                payload,
            )
        except OSError:
            logger.warning(
                "user_info: failed to write %s in %s",
                USER_INFO_FILENAME,
                agent_ref.workspace_dir,
                exc_info=True,
            )


async def sync_user_info_job() -> None:
    """Run one user-info synchronization job and keep scheduler alive."""
    try:
        await sync_user_info_once()
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.warning("user_info: sync failed", exc_info=True)
