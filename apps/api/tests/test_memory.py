"""Tests for memory endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
@pytest.mark.xfail(reason="Dev bypass still active — see §1.2")
async def test_memory_requires_auth(client: AsyncClient):
    """GET /api/memory returns 401 without auth."""
    client.headers.pop("Authorization", None)
    response = await client.get("/api/memory")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_memories(auth_client: AsyncClient):
    """Authenticated user can list memories."""
    response = await auth_client.get("/api/memory")
    assert response.status_code == 200
    data = response.json()
    assert "memories" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_create_memory(auth_client: AsyncClient):
    """Authenticated user can create a memory."""
    response = await auth_client.post(
        "/api/memory",
        json={"category": "fact", "content": "I prefer dark mode", "source": "manual"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "memory" in data


@pytest.mark.asyncio
async def test_delete_memory(auth_client: AsyncClient):
    """Authenticated user can delete a memory."""
    # Create first
    create_resp = await auth_client.post(
        "/api/memory",
        json={"category": "fact", "content": "Temp memory to delete", "source": "test"},
    )
    assert create_resp.status_code == 200
    memory_id = create_resp.json()["memory"]["id"]

    # Delete
    delete_resp = await auth_client.delete(f"/api/memory/{memory_id}")
    assert delete_resp.status_code == 200
    assert delete_resp.json()["success"] is True
