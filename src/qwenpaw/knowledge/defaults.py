# -*- coding: utf-8 -*-
"""Default knowledge base files and structure."""

from __future__ import annotations

from pathlib import Path

from .utils import ensure_dir


def init_default_kb_structure(root_dir: Path) -> None:
    """Initialize default knowledge base files.

    Args:
        root_dir: Knowledge base root directory.

    Returns:
        None: Files and directories created if missing.
    """

    ensure_dir(root_dir / "background")
    ensure_dir(root_dir / "user_context")
    ensure_dir(root_dir / "domain_knowledge")

    background = root_dir / "background" / "org_background.md"
    if not background.exists():
        background.write_text(
            "# Organization Background\n\n- Business owner:\n- System owner:\n- Core systems:\n",
            encoding="utf-8",
        )

    user_context = root_dir / "user_context" / "user_profile_template.md"
    if not user_context.exists():
        user_context.write_text(
            "# User Profile Template\n\n- Name:\n- Employee ID:\n- Department:\n- Role:\n- Manager:\n- Projects:\n",
            encoding="utf-8",
        )

    domain_knowledge = root_dir / "domain_knowledge" / "domain_knowledge.md"
    if not domain_knowledge.exists():
        domain_knowledge.write_text(
            "# Domain Knowledge\n\n- Terms:\n- Processes:\n- FAQs:\n",
            encoding="utf-8",
        )
