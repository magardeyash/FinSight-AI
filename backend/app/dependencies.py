from __future__ import annotations
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.database import get_database
from app.auth.utils import decode_access_token
from app.auth.schemas import UserResponse
from app.utils.exceptions import UnauthorizedError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_db() -> AsyncIOMotorDatabase:
    return get_database()


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> UserResponse:
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise UnauthorizedError("Invalid or expired authentication token.")

    user_id = payload["sub"]
    user_doc = await db.users.find_one({"_id": user_id})
    if not user_doc:
        raise UnauthorizedError("User does not exist.")

    return UserResponse(
        id=user_doc["_id"],
        email=user_doc["email"],
        full_name=user_doc.get("full_name"),
        created_at=user_doc["created_at"],
    )
