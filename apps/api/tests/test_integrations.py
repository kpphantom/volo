"""Tests for integrations endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_integrations(auth_client: AsyncClient):
    """Authenticated user can list integrations."""
    response = await auth_client.get("/api/integrations")
    assert response.status_code == 200
    data = response.json()
    assert "available" in data
    assert "connected" in data


@pytest.mark.asyncio
async def test_connect_integration(auth_client: AsyncClient):
    """Authenticated user can connect an integration."""
    response = await auth_client.post(
        "/api/integrations/connect",
        json={
            "type": "github",
            "credentials": {"access_token": "test-token-abc"},
            "config": {},
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["integration"]["status"] == "connected"


@pytest.mark.asyncio
async def test_connect_invalid_integration(auth_client: AsyncClient):
    """Connecting an unknown integration type returns 400."""
    response = await auth_client.post(
        "/api/integrations/connect",
        json={
            "type": "nonexistent_service",
            "credentials": {"token": "x"},
        },
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_delete_integration(auth_client: AsyncClient):
    """Authenticated user can disconnect an integration."""
    # Connect first
    connect_resp = await auth_client.post(
        "/api/integrations/connect",
        json={
            "type": "alpaca",
            "credentials": {"api_key": "k", "secret_key": "s"},
        },
    )
    assert connect_resp.status_code == 200

    # Find the integration id
    list_resp = await auth_client.get("/api/integrations")
    connected = list_resp.json()["connected"]
    alpaca = next((i for i in connected if i["type"] == "alpaca"), None)
    assert alpaca is not None

    # Delete
    delete_resp = await auth_client.delete(f"/api/integrations/{alpaca['id']}")
    assert delete_resp.status_code == 200
    assert delete_resp.json()["success"] is True
