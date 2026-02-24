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
async def test_me_dev_fallback(client: AsyncClient):
    """Test /me endpoint with dev fallback (no auth)."""
    response = await client.get("/api/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert "email" in data
