# -*- coding: utf-8 -*-
"""COMMON_INFO.md rendering and update helpers."""
from __future__ import annotations

from pathlib import Path
from typing import Any

COMMON_INFO_FILENAME = "COMMON_INFO.md"
COMMON_INFO_DIRNAME = "common_info"

_AUTO_START = "<!-- common-info:auto:start -->"
_AUTO_END = "<!-- common-info:auto:end -->"


def format_common_info_index_markdown(payload: dict[str, Any]) -> str:
    """Render the auto-generated COMMON_INFO.md index section."""
    files = payload.get("files") or []
    rows = [
        "| 文件 | 分类 |",
        "| --- | --- |",
    ]
    for item in files:
        filename = _normalize_md_filename(item.get("filename", ""))
        title = item.get("title") or filename.replace(".md", "")
        rows.append(
            f"| `{COMMON_INFO_DIRNAME}/{_md_cell(filename)}` | "
            f"{_md_cell(title)} |",
        )

    return "\n".join(
        [
            _AUTO_START,
            "<!-- 本区块由后台 common-info 同步服务自动更新，请勿手动编辑。 -->",
            "",
            "## 公共信息索引",
            "",
            f"- **更新时间：** {payload.get('updated_at', '')}",
            "",
            *rows,
            _AUTO_END,
            "",
        ],
    )


def format_common_info_file_markdown(item: dict[str, Any]) -> str:
    """Render one auto-generated common-info child file section."""
    filename = _normalize_md_filename(item.get("filename", ""))
    title = item.get("title") or filename.replace(".md", "")
    content = str(item.get("content") or "").strip()

    return "\n".join(
        [
            _AUTO_START,
            "<!-- 本区块由后台 common-info 同步服务自动更新，请勿手动编辑。 -->",
            "",
            f"# {title}",
            "",
            content,
            _AUTO_END,
            "",
        ],
    )


def merge_common_info_markdown(existing: str, generated: str) -> str:
    """Replace or prepend the auto-generated block in a common-info file."""
    start_idx = existing.find(_AUTO_START)
    end_idx = existing.find(_AUTO_END)
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        end_idx += len(_AUTO_END)
        merged = existing[:start_idx] + generated.strip() + existing[end_idx:]
        return merged.strip() + "\n"

    if existing.strip():
        return generated.strip() + "\n\n" + existing.strip() + "\n"
    return generated.strip() + "\n"


def write_common_info_files(
    workspace_dir: Path,
    payload: dict[str, Any],
) -> None:
    """Write COMMON_INFO.md and common_info/*.md into one workspace."""
    workspace_dir.mkdir(parents=True, exist_ok=True)
    common_info_dir = workspace_dir / COMMON_INFO_DIRNAME
    common_info_dir.mkdir(parents=True, exist_ok=True)

    index_path = workspace_dir / COMMON_INFO_FILENAME
    _write_merged(index_path, format_common_info_index_markdown(payload))

    for item in payload.get("files") or []:
        filename = _normalize_md_filename(item.get("filename", ""))
        if not filename:
            continue
        _write_merged(
            common_info_dir / filename,
            format_common_info_file_markdown(item),
        )


def _write_merged(path: Path, generated: str) -> None:
    existing = ""
    if path.exists():
        existing = path.read_text(encoding="utf-8")
    path.write_text(
        merge_common_info_markdown(existing, generated),
        encoding="utf-8",
    )


def _normalize_md_filename(value: object) -> str:
    filename = Path(str(value or "").strip().replace("\\", "/")).name
    if not filename:
        return ""
    if not filename.endswith(".md"):
        filename += ".md"
    return filename


def _md_cell(value: object) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ").strip()
