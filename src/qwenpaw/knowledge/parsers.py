# -*- coding: utf-8 -*-
"""Parsers for knowledge files."""

from __future__ import annotations

import logging
from pathlib import Path

from .registry import ParserRegistry
from .utils import extract_frontmatter

logger = logging.getLogger(__name__)


class BaseParser:
    """Base parser interface for knowledge files."""

    file_types: tuple[str, ...] = ()

    def parse(self, path: Path, content: str) -> tuple[dict, str]:
        """Parse file content into metadata and body text.

        Args:
            path: File path.
            content: Raw file content.

        Returns:
            tuple[dict, str]: (metadata, body text).
        """

        raise NotImplementedError


@ParserRegistry.register("markdown")
class MarkdownParser(BaseParser):
    """Markdown parser with frontmatter extraction."""

    file_types = (".md",)

    def parse(self, path: Path, content: str) -> tuple[dict, str]:
        """Parse markdown content.

        Args:
            path: File path.
            content: Markdown content.

        Returns:
            tuple[dict, str]: (metadata, body text).
        """

        meta, body = extract_frontmatter(content)
        meta["filename"] = path.name
        return meta, body.strip()
