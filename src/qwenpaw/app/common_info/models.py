# -*- coding: utf-8 -*-
"""Common-info response models."""
from __future__ import annotations

from pydantic import BaseModel, Field


class CommonInfoFile(BaseModel):
    """One common-info markdown file to sync into a workspace."""

    filename: str
    title: str = ""
    content: str = ""


class CommonInfoResponse(BaseModel):
    """Structured common information shared with all agent workspaces."""

    updated_at: str
    files: list[CommonInfoFile] = Field(default_factory=list)
