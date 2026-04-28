# -*- coding: utf-8 -*-
"""Workspace synchronization for COMMON_INFO.md and common_info/*.md."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from ...config import load_config
from .markdown import COMMON_INFO_FILENAME, write_common_info_files
from .provider import fetch_common_info_payload

logger = logging.getLogger(__name__)


async def sync_common_info_once() -> None:
    """Fetch common-info and update enabled agent workspaces."""
    payload = (await fetch_common_info_payload()).model_dump(mode="json")

    config = load_config()
    for agent_ref in config.agents.profiles.values():
        if not getattr(agent_ref, "enabled", True):
            continue
        try:
            write_common_info_files(
                Path(agent_ref.workspace_dir).expanduser(),
                payload,
            )
        except OSError:
            logger.warning(
                "common_info: failed to write %s in %s",
                COMMON_INFO_FILENAME,
                agent_ref.workspace_dir,
                exc_info=True,
            )


async def sync_common_info_job() -> None:
    """Run one common-info synchronization job and keep scheduler alive."""
    try:
        await sync_common_info_once()
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.warning("common_info: sync failed", exc_info=True)
