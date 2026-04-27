# -*- coding: utf-8 -*-
"""Knowledge base API (mock and management endpoints)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ...knowledge import KnowledgeBaseManager
from ...knowledge.models import KnowledgeQuery
from ...knowledge.models_config import (
    KnowledgeQueryRequest,
    KnowledgeCategoryRequest,
    KnowledgeFileWriteRequest,
)
from ..agent_context import get_agent_for_request

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


async def _get_kb(request: Request) -> KnowledgeBaseManager:
    """Get knowledge base manager for the active agent.

    Args:
        request: FastAPI request.

    Returns:
        KnowledgeBaseManager: Knowledge manager instance.
    """

    workspace = await get_agent_for_request(request)
    kb = getattr(workspace, "knowledge_manager", None)
    if kb is None:
        raise HTTPException(status_code=500, detail="Knowledge manager not ready")
    return kb


@router.post("/refresh")
async def refresh_kb(request: Request) -> dict:
    """Manual refresh knowledge base."""

    kb = await _get_kb(request)
    return await kb.refresh()


@router.get("/files")
async def list_files(request: Request) -> list[dict]:
    """List cached knowledge files."""

    kb = await _get_kb(request)
    return kb.list_files()


@router.get("/events")
async def list_events(request: Request) -> list[dict]:
    """List recent knowledge update events."""

    kb = await _get_kb(request)
    return kb.get_update_events()


@router.get("/health")
async def health_check(request: Request) -> dict:
    """Check knowledge file health."""

    kb = await _get_kb(request)
    return {"issues": kb.validate_files()}


@router.post("/search")
async def search(request: Request, body: KnowledgeQueryRequest) -> list[dict]:
    """Search knowledge base."""

    kb = await _get_kb(request)
    query = KnowledgeQuery(
        text=body.query,
        categories=body.categories,
        tags=body.tags,
        limit=body.limit,
    )
    results = kb.search(query)
    return [
        {
            "file_id": item.file_id,
            "score": item.score,
            "content": item.content,
            "metadata": item.metadata,
        }
        for item in results
    ]


@router.post("/categories")
async def set_session_categories(
    request: Request,
    body: KnowledgeCategoryRequest,
) -> dict:
    """Set session category filters."""

    kb = await _get_kb(request)
    kb.set_session_categories(body.session_id, body.categories)
    return {"updated": True}


@router.post("/write")
async def write_knowledge_file(
    request: Request,
    body: KnowledgeFileWriteRequest,
) -> dict:
    """Write a knowledge file to the workspace knowledge_base."""

    kb = await _get_kb(request)
    rel_path = body.path.strip().lstrip("/")
    if not rel_path:
        raise HTTPException(status_code=400, detail="Invalid path")
    target = kb.root_dir / rel_path
    if not str(target.resolve()).startswith(str(kb.root_dir.resolve())):
        raise HTTPException(status_code=400, detail="Invalid path")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body.content, encoding="utf-8")
    await kb.refresh()
    return {"written": True, "path": rel_path}


@router.post("/mock/user")
async def mock_user() -> dict:
    """Mock API: user profile."""

    return {
        "user_id": "U12345",
        "name": "Zhang San",
        "employee_id": "E10086",
        "department": "研发中心",
        "role": "后端工程师",
        "manager": "Li Si",
        "projects": ["Project A", "Project B"],
    }


@router.post("/mock/team")
async def mock_team() -> dict:
    """Mock API: team info."""

    return {
        "team_id": "T9988",
        "team_name": "平台研发组",
        "leader": "Wang Wu",
        "members": ["Zhang San", "Zhao Liu", "Qian Qi"],
    }


@router.post("/mock/project")
async def mock_project() -> dict:
    """Mock API: project info."""

    return {
        "project_id": "P2026",
        "name": "Knowledge Hub",
        "owner": "Wang Wu",
        "systems": ["System A", "System B"],
    }
