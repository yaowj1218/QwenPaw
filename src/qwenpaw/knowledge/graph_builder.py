# -*- coding: utf-8 -*-
"""Knowledge graph builder from file metadata."""

from __future__ import annotations

from .graph import KnowledgeGraph


class KnowledgeGraphBuilder:
    """Build knowledge graph based on file metadata."""

    def build(self, graph: KnowledgeGraph) -> KnowledgeGraph:
        """Build graph relations.

        Args:
            graph: KnowledgeGraph instance.

        Returns:
            KnowledgeGraph: Updated graph.
        """

        return graph
