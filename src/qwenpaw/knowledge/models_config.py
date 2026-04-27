# -*- coding: utf-8 -*-
"""Pydantic models for knowledge API requests."""

from __future__ import annotations

from pydantic import BaseModel, Field


class KnowledgeQueryRequest(BaseModel):
    """Request for knowledge search.

    Args:
        query: Query text.
        categories: Optional category filters.
        tags: Optional tag filters.
        limit: Maximum results.
    """

    query: str = Field(..., description="Query text")
    categories: list[str] | None = Field(default=None)
    tags: list[str] | None = Field(default=None)
    limit: int = Field(default=5, ge=1, le=20)


class KnowledgeCategoryRequest(BaseModel):
    """Request to set session categories.

    Args:
        session_id: Session identifier.
        categories: Categories to pin.
    """

    session_id: str = Field(..., description="Session ID")
    categories: list[str] = Field(default_factory=list)


class KnowledgeFileWriteRequest(BaseModel):
    """Request to write knowledge file content.

    Args:
        path: Relative file path under knowledge_base.
        content: File content to write.
    """

    path: str = Field(..., description="Relative file path")
    content: str = Field(..., description="File content")
