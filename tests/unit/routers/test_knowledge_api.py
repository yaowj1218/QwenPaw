# -*- coding: utf-8 -*-
"""Tests for knowledge API endpoints."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

try:
    import qwenpaw.app.routers.knowledge as knowledge_router
    from qwenpaw.app.routers.knowledge import router
except ModuleNotFoundError as exc:
    pytest.skip(
        f"router dependency missing: {exc}",
        allow_module_level=True,
    )
from qwenpaw.knowledge.manager import KnowledgeBaseManager


class DummyWorkspace:
    """Workspace stub for knowledge API tests."""

    def __init__(self, kb: KnowledgeBaseManager):
        """Initialize with knowledge manager."""

        self.knowledge_manager = kb


@pytest.fixture
def knowledge_manager(temp_workspace: Path) -> KnowledgeBaseManager:
    """Create a knowledge manager for API tests."""

    kb = KnowledgeBaseManager(workspace_dir=temp_workspace)
    kb.ensure_structure()
    return kb


@pytest.fixture
def api_client(
    knowledge_manager: KnowledgeBaseManager,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncClient:
    """Create API client with knowledge router."""

    app = FastAPI()
    app.include_router(router, prefix="/api")

    async def _override(_request):
        return DummyWorkspace(knowledge_manager)

    monkeypatch.setattr(knowledge_router, "get_agent_for_request", _override)
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_search_endpoint(api_client: AsyncClient) -> None:
    """Search endpoint should return results."""

    async with api_client:
        response = await api_client.post(
            "/api/knowledge/search",
            json={"query": "background"},
        )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_refresh_endpoint(api_client: AsyncClient) -> None:
    """Refresh endpoint should succeed."""

    async with api_client:
        response = await api_client.post("/api/knowledge/refresh")
    assert response.status_code == 200
    body = response.json()
    assert "created" in body
