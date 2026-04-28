# -*- coding: utf-8 -*-
"""Tests for COMMON_INFO.md synchronization helpers."""

import httpx
import pytest

from qwenpaw.app.common_info import (
    COMMON_INFO_DIRNAME,
    COMMON_INFO_FILENAME,
    CommonInfoResponse,
    fetch_common_info_payload,
    format_common_info_index_markdown,
    get_common_info_source,
    merge_common_info_markdown,
    write_common_info_files,
)
from qwenpaw.app.common_info import provider as common_info_provider


def _payload() -> dict:
    return {
        "updated_at": "2026-04-28T12:00:00+00:00",
        "files": [
            {
                "filename": "agreements.md",
                "title": "约定",
                "content": "- 统一用中文回答",
            },
            {
                "filename": "rules.md",
                "title": "规则",
                "content": "- 不泄露敏感信息",
            },
        ],
    }


def test_merge_common_info_markdown_preserves_manual_notes():
    existing = "# COMMON_INFO\n\n## 手动记录\n\n- keep\n"
    generated = format_common_info_index_markdown(_payload())

    merged = merge_common_info_markdown(existing, generated)

    assert "公共信息索引" in merged
    assert "agreements.md" in merged
    assert "## 手动记录" in merged
    assert "- keep" in merged


def test_write_common_info_files_updates_index_and_children(tmp_path):
    index = tmp_path / COMMON_INFO_FILENAME
    index.write_text(
        "<!-- common-info:auto:start -->\nold\n"
        "<!-- common-info:auto:end -->\n\n## 手动记录\nkeep\n",
        encoding="utf-8",
    )

    write_common_info_files(tmp_path, _payload())

    index_content = index.read_text(encoding="utf-8")
    child = tmp_path / COMMON_INFO_DIRNAME / "agreements.md"
    assert "old" not in index_content
    assert "agreements.md" in index_content
    assert "## 手动记录\nkeep" in index_content
    assert child.exists()
    assert "统一用中文回答" in child.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_fetch_common_info_payload_defaults_to_mock(monkeypatch):
    monkeypatch.delenv("QWENPAW_COMMON_INFO_SOURCE", raising=False)
    monkeypatch.delenv("QWENPAW_COMMON_INFO_API_URL", raising=False)

    expected = CommonInfoResponse.model_validate(_payload())
    monkeypatch.setattr(
        common_info_provider,
        "build_common_info_payload",
        lambda: expected,
    )

    payload = await fetch_common_info_payload()

    assert get_common_info_source() == "mock"
    assert payload.files[0].filename == "agreements.md"


@pytest.mark.asyncio
async def test_fetch_common_info_payload_remote_calls_third_party(
    monkeypatch,
):
    monkeypatch.setenv("QWENPAW_COMMON_INFO_SOURCE", "remote")
    monkeypatch.setenv("QWENPAW_COMMON_INFO_API_URL", "https://example.test/info")
    monkeypatch.setenv("QWENPAW_COMMON_INFO_API_TOKEN", "secret-token")

    calls = []

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            self.kwargs = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, url, headers=None):
            calls.append((url, headers, self.kwargs))
            request = httpx.Request("GET", url)
            return httpx.Response(200, json=_payload(), request=request)

    monkeypatch.setattr(
        common_info_provider.httpx,
        "AsyncClient",
        FakeAsyncClient,
    )

    payload = await fetch_common_info_payload()

    assert payload.files[1].title == "规则"
    assert calls == [
        (
            "https://example.test/info",
            {"Authorization": "Bearer secret-token"},
            {"timeout": 10.0, "trust_env": False},
        ),
    ]
