from __future__ import annotations
import uuid
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.auth.schemas import UserCreate, UserLogin, UserResponse, Token
from app.auth.utils import hash_password, verify_password, create_access_token
from app.utils.exceptions import ConflictError, UnauthorizedError, NotFoundError


async def register_user(db: AsyncIOMotorDatabase, user_in: UserCreate) -> Token:
    existing = await db.users.find_one({"email": user_in.email.lower()})
    if existing:
        raise ConflictError("An account with this email already exists.")

    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    user_doc = {
        "_id": user_id,
        "email": user_in.email.lower(),
        "password_hash": hash_password(user_in.password),
        "full_name": user_in.full_name or "",
        "created_at": now,
        "updated_at": now,
    }
    await db.users.insert_one(user_doc)

    user_res = UserResponse(
        id=user_id,
        email=user_doc["email"],
        full_name=user_doc["full_name"],
        created_at=user_doc["created_at"],
    )
    token = create_access_token({"sub": user_id, "email": user_doc["email"]})
    return Token(access_token=token, token_type="bearer", user=user_res)


async def authenticate_user(db: AsyncIOMotorDatabase, credentials: UserLogin) -> Token:
    user_doc = await db.users.find_one({"email": credentials.email.lower()})
    if not user_doc or not verify_password(credentials.password, user_doc["password_hash"]):
        raise UnauthorizedError("Invalid email or password.")

    user_res = UserResponse(
        id=user_doc["_id"],
        email=user_doc["email"],
        full_name=user_doc.get("full_name"),
        created_at=user_doc["created_at"],
    )
    token = create_access_token({"sub": user_doc["_id"], "email": user_doc["email"]})
    return Token(access_token=token, token_type="bearer", user=user_res)


async def get_user_by_id(db: AsyncIOMotorDatabase, user_id: str) -> UserResponse:
    user_doc = await db.users.find_one({"_id": user_id})
    if not user_doc:
        raise NotFoundError("User not found.")
    return UserResponse(
        id=user_doc["_id"],
        email=user_doc["email"],
        full_name=user_doc.get("full_name"),
        created_at=user_doc["created_at"],
    )
