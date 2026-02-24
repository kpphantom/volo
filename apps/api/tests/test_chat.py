"""Tests for chat and conversation endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_conversations_list(client: AsyncClient):
    """Test listing conversations."""
    response = await client.get("/api/conversations")
    assert response.status_code == 200
    data = response.json()
    assert "conversations" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_conversation_create(client: AsyncClient):
    """Test creating a conversation."""
    response = await client.post(
        "/api/conversations",
        json={"title": "Test Conversation"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Conversation"
    assert "id" in data


@pytest.mark.asyncio
async def test_conversation_get(client: AsyncClient):
    """Test getting a conversation."""
    # Create first
    create = await client.post(
        "/api/conversations",
        json={"title": "Get Test"},
    )
    conv_id = create.json()["id"]

    response = await client.get(f"/api/conversations/{conv_id}")
    assert response.status_code == 200
    assert response.json()["title"] == "Get Test"


@pytest.mark.asyncio
async def test_conversation_delete(client: AsyncClient):
    """Test deleting a conversation."""
    create = await client.post(
        "/api/conversations",
        json={"title": "Delete Me"},
    )
    conv_id = create.json()["id"]

    response = await client.delete(f"/api/conversations/{conv_id}")
    assert response.status_code == 200
    assert response.json()["deleted"] is True


@pytest.mark.asyncio
async def test_conversation_not_found(client: AsyncClient):
    """Test getting a non-existent conversation."""
    response = await client.get("/api/conversations/non-existent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_public_api_status(client: AsyncClient):
    """Test public API status."""
    response = await client.get("/api/v1/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"


@pytest.mark.asyncio
async def test_public_api_tools(client: AsyncClient):
    """Test listing tools via public API."""
    response = await client.get("/api/v1/tools")
    assert response.status_code == 200
    data = response.json()
    assert "tools" in data
    assert data["total"] > 0
