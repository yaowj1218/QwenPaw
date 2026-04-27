# -*- coding: utf-8 -*-
"""Knowledge file health checks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass
class HealthIssue:
    """Health issue record.

    Args:
        file_id: File identifier.
        issue: Issue code.
        detail: Optional detail.
    """

    file_id: str
    issue: str
    detail: str = ""


class KnowledgeHealthChecker:
    """Health checker for knowledge files."""

    def check_paths(self, files: Iterable[tuple[str, Path]]) -> list[HealthIssue]:
        """Check file paths for existence.

        Args:
            files: Iterable of (file_id, path).

        Returns:
            list[HealthIssue]: Issues list.
        """

        issues = []
        for file_id, path in files:
            if not path.exists():
                issues.append(
                    HealthIssue(file_id=file_id, issue="missing_file"),
                )
        return issues
