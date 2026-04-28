# -*- coding: utf-8 -*-
"""User-info payload providers."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Literal

import httpx

from ...config import load_config
from ...config.config import load_agent_config
from ...constant import EnvVarLoader
from .models import UserInfoAgent, UserInfoResponse

logger = logging.getLogger(__name__)

USER_INFO_SOURCE_ENV = "QWENPAW_USER_INFO_SOURCE"
USER_INFO_API_URL_ENV = "QWENPAW_USER_INFO_API_URL"
USER_INFO_API_TOKEN_ENV = "QWENPAW_USER_INFO_API_TOKEN"
USER_INFO_API_TIMEOUT_SECONDS = EnvVarLoader.get_float(
    "QWENPAW_USER_INFO_API_TIMEOUT_SECONDS",
    10.0,
    min_value=0.1,
)


def build_user_info_payload(username: str = "") -> UserInfoResponse:
    """Build a development/mock user-info response from local configuration."""
    from ..auth import has_registered_users, is_auth_enabled

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


def get_user_info_source() -> Literal["mock", "remote"]:
    """Resolve the active user-info data source.

    ``auto`` keeps local development frictionless: a configured third-party
    URL enables remote mode, otherwise development mock data is returned.
    """
    source = EnvVarLoader.get_str(USER_INFO_SOURCE_ENV, "auto").strip().lower()
    if source in {"mock", "local", "dev", "development"}:
        return "mock"
    if source in {"remote", "third-party", "third_party"}:
        return "remote"
    if source and source != "auto":
        logger.warning(
            "user_info: unknown source %r, falling back to auto",
            source,
        )

    api_url = EnvVarLoader.get_str(USER_INFO_API_URL_ENV, "").strip()
    return "remote" if api_url else "mock"


async def fetch_user_info_payload(username: str = "") -> UserInfoResponse:
    """Fetch user-info from the configured source."""
    if get_user_info_source() == "mock":
        return build_user_info_payload(username=username or "dev-user")
    return await fetch_remote_user_info_payload()


async def fetch_remote_user_info_payload() -> UserInfoResponse:
    """Fetch user-info from the third-party provider."""
    api_url = EnvVarLoader.get_str(USER_INFO_API_URL_ENV, "").strip()
    if not api_url:
        raise RuntimeError(
            f"{USER_INFO_API_URL_ENV} is required when "
            f"{USER_INFO_SOURCE_ENV}=remote",
        )

    token = EnvVarLoader.get_str(USER_INFO_API_TOKEN_ENV, "").strip()
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient(
        timeout=USER_INFO_API_TIMEOUT_SECONDS,
        trust_env=False,
    ) as client:
        response = await client.get(api_url, headers=headers)
        response.raise_for_status()
        return UserInfoResponse.model_validate(response.json())
