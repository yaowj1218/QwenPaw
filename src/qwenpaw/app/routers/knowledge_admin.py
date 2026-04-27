# -*- coding: utf-8 -*-
"""Knowledge admin endpoints for backup and restore."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ...knowledge import KnowledgeBaseManager
from ..agent_context import get_agent_for_request

router = APIRouter(prefix="/knowledge-admin", tags=["knowledge-admin"])


class BackupRequest(BaseModel):
    """Request to restore a backup."""

    backup_path: str = Field(..., description="Backup file path")


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


@router.post("/backup")
async def backup(request: Request) -> dict:
    """Trigger backup of knowledge base metadata."""

    kb = await _get_kb(request)
    return kb.backup()


@router.post("/restore")
async def restore(request: Request, body: BackupRequest) -> dict:
    """Restore knowledge base metadata from backup."""

    kb = await _get_kb(request)
    result = kb.restore(body.backup_path)
    if result.get("restored"):
        await kb.refresh()
    return result
