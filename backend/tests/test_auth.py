from __future__ import annotations
import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_user_registration_and_login(async_client: AsyncClient):
    unique_email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    password = "StrongPassword987!"

    # 1. Register
    reg_res = await async_client.post(
        "/api/v1/auth/register",
        json={"email": unique_email, "password": password, "full_name": "Alice Developer"},
    )
    assert reg_res.status_code == 201
    data = reg_res.json()
    assert "access_token" in data
    assert data["user"]["email"] == unique_email
    assert data["user"]["full_name"] == "Alice Developer"

    # 2. Duplicate registration must fail with 409
    dup_res = await async_client.post(
        "/api/v1/auth/register",
        json={"email": unique_email, "password": password},
    )
    assert dup_res.status_code == 409

    # 3. Successful login
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": unique_email, "password": password},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    assert token is not None

    # 4. Failed login with invalid password
    bad_login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": unique_email, "password": "WrongPassword!"},
    )
    assert bad_login.status_code == 401

    # 5. Access protected /me endpoint
    me_res = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    assert me_res.json()["email"] == unique_email


@pytest.mark.asyncio
async def test_protected_route_without_token(async_client: AsyncClient):
    res = await async_client.get("/api/v1/auth/me")
    assert res.status_code == 401
