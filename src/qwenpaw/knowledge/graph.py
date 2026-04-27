# -*- coding: utf-8 -*-
"""Simple in-memory knowledge graph."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class KnowledgeNode:
    """Knowledge graph node.

    Args:
        node_id: Node identifier.
        node_type: Node type.
        attrs: Node attributes.
    """

    node_id: str
    node_type: str
    attrs: dict = field(default_factory=dict)


@dataclass
class KnowledgeEdge:
    """Knowledge graph edge.

    Args:
        source: Source node id.
        target: Target node id.
        relation: Relation label.
        attrs: Edge attributes.
    """

    source: str
    target: str
    relation: str
    attrs: dict = field(default_factory=dict)


class KnowledgeGraph:
    """Lightweight knowledge graph for file relations."""

    def __init__(self):
        """Initialize knowledge graph."""

        self.nodes: dict[str, KnowledgeNode] = {}
        self.edges: list[KnowledgeEdge] = []

    def add_node(self, node_id: str, node_type: str, attrs: dict | None = None) -> None:
        """Add a node to graph.

        Args:
            node_id: Node identifier.
            node_type: Node type.
            attrs: Node attributes.

        Returns:
            None: Node is added.
        """

        self.nodes[node_id] = KnowledgeNode(
            node_id=node_id,
            node_type=node_type,
            attrs=attrs or {},
        )

    def add_edge(
        self,
        source: str,
        target: str,
        relation: str,
        attrs: dict | None = None,
    ) -> None:
        """Add an edge to graph.

        Args:
            source: Source node id.
            target: Target node id.
            relation: Relation label.
            attrs: Edge attributes.

        Returns:
            None: Edge is added.
        """

        self.edges.append(
            KnowledgeEdge(
                source=source,
                target=target,
                relation=relation,
                attrs=attrs or {},
            ),
        )
