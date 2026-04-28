# -*- coding: utf-8 -*-
"""User information API."""
from __future__ import annotations

from fastapi import APIRouter, Request

from ..auth import get_registered_username
from ..user_info import UserInfoResponse, fetch_user_info_payload

router = APIRouter(prefix="/user-info", tags=["user-info"])


@router.get("", response_model=UserInfoResponse)
async def get_user_info(request: Request) -> UserInfoResponse:
    """Return non-sensitive user and workspace information."""
    username = getattr(request.state, "user", "") or get_registered_username()
    return await fetch_user_info_payload(username=username)
