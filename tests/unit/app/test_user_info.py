# -*- coding: utf-8 -*-
"""Tests for USER_INFO.md synchronization helpers."""

import httpx
import pytest

from qwenpaw.app.user_info import (
    USER_INFO_FILENAME,
    UserInfoResponse,
    fetch_user_info_payload,
    format_user_info_markdown,
    get_user_info_source,
    merge_user_info_markdown,
    write_user_info_md,
)
from qwenpaw.app.user_info import provider as user_info_provider


def _payload() -> dict:
    return {
        "username": "alice",
        "auth_enabled": True,
        "registered": True,
        "timezone": "Asia/Hong_Kong",
        "agent_language": "zh",
        "active_agent": "default",
        "updated_at": "2026-04-27T12:00:00+00:00",
        "agents": [
            {
                "id": "default",
                "name": "Default",
                "workspace_dir": "/tmp/default",
                "enabled": True,
                "language": "zh",
            },
        ],
    }


def test_merge_user_info_markdown_preserves_manual_notes():
    existing = "# USER_INFO\n\n## 手动记录\n\n- 喜欢简洁回答\n"
    generated = format_user_info_markdown(_payload())

    merged = merge_user_info_markdown(existing, generated)

    assert "## 自动同步信息" in merged
    assert "alice" in merged
    assert "## 手动记录" in merged
    assert "喜欢简洁回答" in merged


def test_write_user_info_md_updates_auto_block_only(tmp_path):
    user_info = tmp_path / USER_INFO_FILENAME
    user_info.write_text(
        "<!-- user-info:auto:start -->\nold\n"
        "<!-- user-info:auto:end -->\n\n## 手动记录\nkeep\n",
        encoding="utf-8",
    )

    write_user_info_md(tmp_path, _payload())

    content = user_info.read_text(encoding="utf-8")
    assert "old" not in content
    assert "alice" in content
    assert "## 手动记录\nkeep" in content


@pytest.mark.asyncio
async def test_fetch_user_info_payload_defaults_to_mock(monkeypatch):
    monkeypatch.delenv("QWENPAW_USER_INFO_SOURCE", raising=False)
    monkeypatch.delenv("QWENPAW_USER_INFO_API_URL", raising=False)

    expected = UserInfoResponse.model_validate(_payload())
    monkeypatch.setattr(
        user_info_provider,
        "build_user_info_payload",
        lambda username="": expected.model_copy(update={"username": username}),
    )

    payload = await fetch_user_info_payload(username="dev-user")

    assert get_user_info_source() == "mock"
    assert payload.username == "dev-user"


@pytest.mark.asyncio
async def test_fetch_user_info_payload_remote_calls_third_party(
    monkeypatch,
):
    monkeypatch.setenv("QWENPAW_USER_INFO_SOURCE", "remote")
    monkeypatch.setenv("QWENPAW_USER_INFO_API_URL", "https://example.test/me")
    monkeypatch.setenv("QWENPAW_USER_INFO_API_TOKEN", "secret-token")

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
        user_info_provider.httpx,
        "AsyncClient",
        FakeAsyncClient,
    )

    payload = await fetch_user_info_payload()

    assert payload.username == "alice"
    assert calls == [
        (
            "https://example.test/me",
            {"Authorization": "Bearer secret-token"},
            {"timeout": 10.0, "trust_env": False},
        ),
    ]
