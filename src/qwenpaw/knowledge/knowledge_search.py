# -*- coding: utf-8 -*-
"""Knowledge search tool for agent usage."""

from __future__ import annotations

from typing import Any

from agentscope.message import TextBlock
from agentscope_runtime.engine.schemas.tool import ToolResponse

from .manager import KnowledgeBaseManager
from .models import KnowledgeQuery


class KnowledgeSearchTool:
    """Tool wrapper for knowledge search."""

    def __init__(self, manager: KnowledgeBaseManager):
        """Initialize tool with knowledge manager.

        Args:
            manager: Knowledge base manager instance.
        """

        self._manager = manager

    async def knowledge_search(
        self,
        query: str,
        max_results: int = 5,
        categories: list[str] | None = None,
    ) -> ToolResponse:
        """Search knowledge base content.

        Args:
            query: Search query.
            max_results: Maximum results.
            categories: Optional category filters.

        Returns:
            ToolResponse: Search results content.
        """

        result = self._manager.search(
            KnowledgeQuery(text=query, categories=categories, limit=max_results),
        )
        lines = []
        for item in result:
            lines.append(f"{item.file_id} (score={item.score:.2f})")
            lines.append(item.content)
            lines.append("")
        text = "\n".join(lines).strip()
        return ToolResponse(content=[TextBlock(type="text", text=text)])
