# -*- coding: utf-8 -*-
"""Common-info payload providers."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Literal

import httpx

from ...constant import EnvVarLoader
from .models import CommonInfoFile, CommonInfoResponse

logger = logging.getLogger(__name__)

COMMON_INFO_SOURCE_ENV = "QWENPAW_COMMON_INFO_SOURCE"
COMMON_INFO_API_URL_ENV = "QWENPAW_COMMON_INFO_API_URL"
COMMON_INFO_API_TOKEN_ENV = "QWENPAW_COMMON_INFO_API_TOKEN"
COMMON_INFO_API_TIMEOUT_SECONDS = EnvVarLoader.get_float(
    "QWENPAW_COMMON_INFO_API_TIMEOUT_SECONDS",
    10.0,
    min_value=0.1,
)


def build_common_info_payload() -> CommonInfoResponse:
    """Build a development/mock common-info response."""
    return CommonInfoResponse(
        updated_at=datetime.now(timezone.utc).isoformat(),
        files=[
            CommonInfoFile(
                filename="agreements.md",
                title="约定",
                content="- 暂无自动同步约定。",
            ),
            CommonInfoFile(
                filename="rules.md",
                title="规则",
                content="- 暂无自动同步规则。",
            ),
            CommonInfoFile(
                filename="common_sense.md",
                title="常识",
                content="- 暂无自动同步常识。",
            ),
        ],
    )


def get_common_info_source() -> Literal["mock", "remote"]:
    """Resolve the active common-info data source."""
    source = EnvVarLoader.get_str(COMMON_INFO_SOURCE_ENV, "auto").strip().lower()
    if source in {"mock", "local", "dev", "development"}:
        return "mock"
    if source in {"remote", "third-party", "third_party"}:
        return "remote"
    if source and source != "auto":
        logger.warning(
            "common_info: unknown source %r, falling back to auto",
            source,
        )

    api_url = EnvVarLoader.get_str(COMMON_INFO_API_URL_ENV, "").strip()
    return "remote" if api_url else "mock"


async def fetch_common_info_payload() -> CommonInfoResponse:
    """Fetch common-info from the configured source."""
    if get_common_info_source() == "mock":
        return build_common_info_payload()
    return await fetch_remote_common_info_payload()


async def fetch_remote_common_info_payload() -> CommonInfoResponse:
    """Fetch common-info from the third-party provider."""
    api_url = EnvVarLoader.get_str(COMMON_INFO_API_URL_ENV, "").strip()
    if not api_url:
        raise RuntimeError(
            f"{COMMON_INFO_API_URL_ENV} is required when "
            f"{COMMON_INFO_SOURCE_ENV}=remote",
        )

    token = EnvVarLoader.get_str(COMMON_INFO_API_TOKEN_ENV, "").strip()
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient(
        timeout=COMMON_INFO_API_TIMEOUT_SECONDS,
        trust_env=False,
    ) as client:
        response = await client.get(api_url, headers=headers)
        response.raise_for_status()
        return CommonInfoResponse.model_validate(response.json())
