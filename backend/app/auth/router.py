from __future__ import annotations
from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.dependencies import get_db, get_current_user
from app.auth.schemas import UserCreate, UserLogin, UserResponse, Token
from app.auth import service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Register a new user account."""
    return await service.register_user(db, user_in)


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Authenticate with email and password and receive a JWT token."""
    return await service.authenticate_user(db, credentials)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserResponse = Depends(get_current_user)):
    """Retrieve profile of currently authenticated user."""
    return current_user
