# -*- coding: utf-8 -*-
"""Data models for knowledge base entities."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class KnowledgeFile:
    """Knowledge file metadata and cached content.

    Args:
        file_id: Unique file identifier (relative path).
        path: Absolute path to the file.
        category: Category name (e.g. background, user_context).
        tags: Optional tags derived from path or config.
        last_modified: Last modification timestamp.
        content: Parsed text content for prompt usage.
        checksum: Content checksum for change detection.
        updated_at: Last time the file metadata was refreshed.
        version: Incremental version number for this file.
    """

    file_id: str
    path: Path
    category: str
    tags: list[str] = field(default_factory=list)
    last_modified: float = 0.0
    content: str = ""
    checksum: str = ""
    updated_at: datetime | None = None
    version: int = 0


@dataclass
class KnowledgeUpdateEvent:
    """Record a knowledge file update event.

    Args:
        file_id: File identifier.
        timestamp: Event timestamp.
        change_type: Change type (created/updated/deleted).
        detail: Extra update detail for auditing.
    """

    file_id: str
    timestamp: datetime
    change_type: str
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class KnowledgeQuery:
    """Query payload for knowledge retrieval.

    Args:
        text: Query text.
        categories: Optional list of categories to constrain search.
        tags: Optional tags to constrain search.
        limit: Maximum number of files to return.
    """

    text: str
    categories: list[str] | None = None
    tags: list[str] | None = None
    limit: int = 5


@dataclass
class KnowledgeSearchResult:
    """Knowledge search result for prompt injection.

    Args:
        file_id: File identifier.
        score: Relevance score (0-1).
        content: Selected content snippet.
        metadata: Additional metadata.
    """

    file_id: str
    score: float
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
