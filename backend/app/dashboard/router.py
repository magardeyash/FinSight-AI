from __future__ import annotations
from typing import Any
from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.dependencies import get_db, get_current_user
from app.auth.schemas import UserResponse
from app.dashboard import service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats")
async def get_stats(
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve aggregate statistics and status distribution for current user."""
    return await service.get_dashboard_stats(db, current_user.id)


@router.get("/recent-activity")
async def get_recent_activity(
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list[dict[str, Any]]:
    """Retrieve recent processing and review activities for current user."""
    return await service.get_recent_activity(db, current_user.id)
