# -*- coding: utf-8 -*-
"""Periodic user-info synchronization service."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from ...constant import EnvVarLoader
from .sync import sync_user_info_once

logger = logging.getLogger(__name__)

USER_INFO_SYNC_INTERVAL_SECONDS = EnvVarLoader.get_int(
    "QWENPAW_USER_INFO_SYNC_INTERVAL_SECONDS",
    10,
    min_value=10,
)
USER_INFO_SYNC_JOB_ID = "user_info_sync"


class UserInfoSyncService:
    """Owns the periodic USER_INFO.md synchronization lifecycle."""

    def __init__(self, interval_seconds: int = USER_INFO_SYNC_INTERVAL_SECONDS):
        self._interval_seconds = interval_seconds
        self._scheduler = AsyncIOScheduler()
        self._lock = asyncio.Lock()

    @property
    def running(self) -> bool:
        """Whether the underlying scheduler is running."""
        return self._scheduler.running

    def start(self) -> None:
        """Start periodic synchronization."""
        self._scheduler.add_job(
            self.sync_job,
            trigger=IntervalTrigger(seconds=self._interval_seconds),
            id=USER_INFO_SYNC_JOB_ID,
            max_instances=1,
            coalesce=True,
            replace_existing=True,
            next_run_time=datetime.now(timezone.utc),
        )
        self._scheduler.start()

    def stop(self) -> None:
        """Stop periodic synchronization."""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)

    async def sync_job(self) -> None:
        """Run one non-overlapping user-info synchronization job."""
        if self._lock.locked():
            logger.info("user_info: previous sync still running, skipping")
            return

        async with self._lock:
            try:
                await sync_user_info_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.warning("user_info: sync failed", exc_info=True)


def start_user_info_sync_scheduler() -> AsyncIOScheduler:
    """Start periodic synchronization of USER_INFO.md.

    Kept as a compatibility wrapper for older callers. New code should use
    UserInfoSyncService so lifecycle ownership is explicit.
    """
    service = UserInfoSyncService()
    service.start()
    return service._scheduler  # pylint: disable=protected-access
