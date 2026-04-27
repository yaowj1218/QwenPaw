# -*- coding: utf-8 -*-
"""Simple knowledge file selector."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .models import KnowledgeSearchResult
from .utils import tokenize


@dataclass
class SelectionResult:
    """Selection result with reason."""

    selected: list[KnowledgeSearchResult]
    reason: str


class KnowledgeSelector:
    """Select relevant knowledge files by token overlap."""

    def select(
        self,
        results: Iterable[KnowledgeSearchResult],
        query: str,
        limit: int = 5,
    ) -> SelectionResult:
        """Select relevant items from results.

        Args:
            results: Candidate results.
            query: Query text.
            limit: Maximum items.

        Returns:
            SelectionResult: Selected results and reason.
        """

        tokens = set(tokenize(query))
        scored = []
        for item in results:
            text_tokens = set(tokenize(item.content))
            overlap = len(tokens.intersection(text_tokens))
            scored.append((item, overlap))
        scored.sort(key=lambda pair: pair[1], reverse=True)
        selected = [item for item, _score in scored[:limit]]
        return SelectionResult(selected=selected, reason="token_overlap")
