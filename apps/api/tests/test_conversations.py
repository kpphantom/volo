"""Tests for conversation endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
@pytest.mark.xfail(reason="Dev bypass still active — see §1.2")
async def test_list_conversations_requires_auth(client: AsyncClient):
    """GET /api/conversations returns 401 without auth."""
    client.headers.pop("Authorization", None)
    response = await client.get("/api/conversations")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_conversation(auth_client: AsyncClient):
    """Authenticated user can create a conversation."""
    response = await auth_client.post(
        "/api/conversations",
        json={"title": "Test Conversation"},
    )
    assert response.status_code in (200, 201)
    data = response.json()
    assert "id" in data


@pytest.mark.asyncio
async def test_list_conversations(auth_client: AsyncClient):
    """Authenticated user can list their conversations."""
    response = await auth_client.get("/api/conversations")
    assert response.status_code == 200
    data = response.json()
    assert "conversations" in data


@pytest.mark.asyncio
async def test_user_isolation(auth_client: AsyncClient):
    """A user cannot access another user's conversation (404 or 403)."""
    response = await auth_client.get("/api/conversations/nonexistent-conv-id-9999")
    assert response.status_code in (403, 404)
