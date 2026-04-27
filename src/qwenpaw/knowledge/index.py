# -*- coding: utf-8 -*-
"""Inverted index for knowledge search."""

from __future__ import annotations

import logging
from collections import defaultdict

from .utils import tokenize

logger = logging.getLogger(__name__)


class InvertedIndex:
    """Inverted index for keyword-based search."""

    def __init__(self):
        """Initialize empty index."""

        self._index: dict[str, dict[str, int]] = defaultdict(dict)
        self._doc_tokens: dict[str, list[str]] = {}

    def add_document(self, doc_id: str, text: str) -> None:
        """Add or update a document in the index.

        Args:
            doc_id: Document identifier.
            text: Document text.

        Returns:
            None: Index is updated.
        """

        self.remove_document(doc_id)
        tokens = tokenize(text)
        self._doc_tokens[doc_id] = tokens
        for token in tokens:
            self._index[token][doc_id] = self._index[token].get(doc_id, 0) + 1

    def remove_document(self, doc_id: str) -> None:
        """Remove a document from the index.

        Args:
            doc_id: Document identifier.

        Returns:
            None: Index is updated.
        """

        tokens = self._doc_tokens.pop(doc_id, [])
        for token in tokens:
            doc_map = self._index.get(token)
            if not doc_map:
                continue
            doc_map.pop(doc_id, None)
            if not doc_map:
                self._index.pop(token, None)

    def search(self, query: str, limit: int = 5) -> list[tuple[str, float]]:
        """Search documents using token overlap scoring.

        Args:
            query: Query text.
            limit: Maximum results.

        Returns:
            list[tuple[str, float]]: List of (doc_id, score).
        """

        tokens = tokenize(query)
        if not tokens:
            return []
        scores: dict[str, float] = defaultdict(float)
        for token in tokens:
            for doc_id, count in self._index.get(token, {}).items():
                scores[doc_id] += float(count)
        if not scores:
            return []
        max_score = max(scores.values()) or 1.0
        normalized = [(doc_id, score / max_score) for doc_id, score in scores.items()]
        normalized.sort(key=lambda item: item[1], reverse=True)
        return normalized[:limit]

    def dump_state(self) -> dict:
        """Dump index state for persistence.

        Returns:
            dict: Serialized index state.
        """

        return {
            "index": {k: v for k, v in self._index.items()},
            "doc_tokens": self._doc_tokens,
        }

    def load_state(self, state: dict) -> None:
        """Load index state from persistence.

        Args:
            state: Serialized index state.

        Returns:
            None: Index state loaded.
        """

        self._index = defaultdict(dict, state.get("index", {}))
        self._doc_tokens = state.get("doc_tokens", {})
