# -*- coding: utf-8 -*-
"""Knowledge base configuration models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class KnowledgeCategoryConfig:
    """Configuration for a knowledge category.

    Args:
        name: Category name.
        description: Description for human usage.
        enabled: Whether category is enabled.
        file_glob: File pattern for this category.
    """

    name: str
    description: str = ""
    enabled: bool = True
    file_glob: str = "**/*.md"


@dataclass
class KnowledgeBaseConfig:
    """Configuration for knowledge base manager.

    Args:
        root_dir: Root directory name under workspace.
        categories: Category config list.
        refresh_minutes: Periodic refresh interval.
        max_excerpt_chars: Maximum excerpt length per file.
        cache_ttl_seconds: Cache TTL in seconds.
        source_type: Knowledge source type from registry.
    """

    root_dir: str = "knowledge_base"
    categories: list[KnowledgeCategoryConfig] = field(default_factory=list)
    refresh_minutes: int = 30
    max_excerpt_chars: int = 1200
    cache_ttl_seconds: int = 1800
    source_type: str = "file"
