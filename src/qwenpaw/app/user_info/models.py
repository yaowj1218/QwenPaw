# -*- coding: utf-8 -*-
"""User-info response models."""
from __future__ import annotations

from pydantic import BaseModel, Field


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
