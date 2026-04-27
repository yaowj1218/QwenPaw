# -*- coding: utf-8 -*-
"""Utility helpers for knowledge base processing."""

from __future__ import annotations

import base64
import difflib
import hashlib
import json
import logging
import re
import zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

logger = logging.getLogger(__name__)

_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_\u4e00-\u9fa5]+")


def now_iso() -> str:
    """Return the current UTC timestamp in ISO 8601 format.

    Returns:
        str: ISO 8601 timestamp string.
    """

    return datetime.now(timezone.utc).isoformat()


def ensure_dir(path: Path) -> None:
    """Ensure the directory exists.

    Args:
        path: Directory path to create.

    Returns:
        None: Directory is created if missing.
    """

    path.mkdir(parents=True, exist_ok=True)


def compute_checksum(text: str) -> str:
    """Compute SHA256 checksum for the given text.

    Args:
        text: Text content to hash.

    Returns:
        str: SHA256 hex digest.
    """

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def tokenize(text: str) -> list[str]:
    """Tokenize text into a list of terms for indexing.

    Args:
        text: Input text.

    Returns:
        list[str]: Token list.
    """

    return [token.lower() for token in _TOKEN_PATTERN.findall(text)]


def diff_summary(old: str, new: str) -> dict:
    """Summarize line-level diff changes between two texts.

    Args:
        old: Old text content.
        new: New text content.

    Returns:
        dict: Summary dict with added_lines, removed_lines, changed.
    """

    old_lines = old.splitlines()
    new_lines = new.splitlines()
    diff = difflib.ndiff(old_lines, new_lines)
    added = sum(1 for line in diff if line.startswith("+ "))
    diff = difflib.ndiff(old_lines, new_lines)
    removed = sum(1 for line in diff if line.startswith("- "))
    return {
        "added_lines": added,
        "removed_lines": removed,
        "changed": added + removed > 0,
    }


def compress_text(text: str) -> str:
    """Compress text to base64-encoded zlib bytes.

    Args:
        text: Text content to compress.

    Returns:
        str: Base64-encoded compressed bytes.
    """

    compressed = zlib.compress(text.encode("utf-8"))
    return base64.b64encode(compressed).decode("ascii")


def decompress_text(data: str) -> str:
    """Decompress base64-encoded zlib text data.

    Args:
        data: Base64-encoded compressed text.

    Returns:
        str: Decompressed text content.
    """

    raw = base64.b64decode(data.encode("ascii"))
    return zlib.decompress(raw).decode("utf-8")


def load_json(path: Path, default: dict | list | None = None):
    """Load JSON data from file with fallback.

    Args:
        path: JSON file path.
        default: Default value when file is missing or invalid.

    Returns:
        dict | list | None: Parsed JSON or default.
    """

    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to read json %s: %s", path, exc)
        return default


def save_json(path: Path, data: dict | list) -> None:
    """Save JSON data to file with UTF-8 encoding.

    Args:
        path: JSON file path.
        data: Data to serialize.

    Returns:
        None: Data is written to disk.
    """

    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def extract_frontmatter(text: str) -> tuple[dict, str]:
    """Extract YAML-like frontmatter from markdown text.

    Args:
        text: Markdown content.

    Returns:
        tuple[dict, str]: (frontmatter dict, body text).
    """

    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    raw = parts[1].strip()
    body = parts[2].strip()
    meta: dict = {}
    for line in raw.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip()
    return meta, body


def limit_text(text: str, max_chars: int) -> str:
    """Limit text length to a maximum number of characters.

    Args:
        text: Input text.
        max_chars: Maximum character length.

    Returns:
        str: Truncated text with ellipsis if needed.
    """

    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


def build_excerpt(text: str, max_chars: int = 800) -> str:
    """Build a short excerpt for prompt injection.

    Args:
        text: Full text content.
        max_chars: Maximum characters to keep.

    Returns:
        str: Excerpt text.
    """

    return limit_text(text.strip(), max_chars)


def normalize_categories(raw: Iterable[str] | None) -> list[str]:
    """Normalize category names to lowercase list.

    Args:
        raw: Raw category names.

    Returns:
        list[str]: Normalized category list.
    """

    if not raw:
        return []
    return [str(item).strip().lower() for item in raw if str(item).strip()]
