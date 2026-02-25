"""Tests for auth endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register(client: AsyncClient):
    """Test user registration."""
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "test@example.com",
            "password": "securepass123",
            "name": "Test User",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_login(client: AsyncClient):
    """Test login after registration."""
    # Register first
    await client.post(
        "/api/auth/register",
        json={
            "email": "login_test@example.com",
            "password": "securepass123",
            "name": "Login Test",
        },
    )

    # Login
    response = await client.post(
        "/api/auth/login",
        json={
            "email": "login_test@example.com",
            "password": "securepass123",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    """Test login with wrong password."""
    # Register first
    await client.post(
        "/api/auth/register",
        json={
            "email": "wrong_pw@example.com",
            "password": "securepass123",
            "name": "Wrong PW",
        },
    )

    response = await client.post(
        "/api/auth/login",
        json={
            "email": "wrong_pw@example.com",
            "password": "wrongpassword",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_with_valid_jwt(auth_client: AsyncClient):
    """Test /me endpoint with a valid JWT."""
    response = await auth_client.get("/api/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert "email" in data


@pytest.mark.asyncio
@pytest.mark.xfail(reason="Dev bypass still active — see §1.2")
async def test_me_no_token(client: AsyncClient):
    """Test /me without token returns 401 (fails while dev bypass is active)."""
    client.headers.pop("Authorization", None)
    response = await client.get("/api/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_token_rejected(client: AsyncClient):
    """Test that a malformed JWT returns 401."""
    client.headers["Authorization"] = "Bearer this.is.garbage"
    response = await client.get("/api/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_token_expiry(client: AsyncClient):
    """Test that an expired token is rejected."""
    from datetime import timedelta
    from app.auth import create_access_token
    expired_token = create_access_token(
        "dev-user", "volo-default", "owner",
        expires_delta=timedelta(seconds=-1),
    )
    client.headers["Authorization"] = f"Bearer {expired_token}"
    response = await client.get("/api/auth/me")
    assert response.status_code == 401
