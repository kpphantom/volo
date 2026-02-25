"""Tests for standing orders endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_standing_orders(auth_client: AsyncClient):
    """Authenticated user can list standing orders."""
    response = await auth_client.get("/api/standing-orders")
    assert response.status_code == 200
    data = response.json()
    assert "standing_orders" in data


@pytest.mark.asyncio
async def test_create_standing_order(auth_client: AsyncClient):
    """Authenticated user can create a standing order."""
    response = await auth_client.post(
        "/api/standing-orders",
        json={
            "name": "Daily standup brief",
            "description": "Send Slack standup every morning",
            "trigger_type": "cron",
            "trigger_config": {"cron": "0 9 * * 1-5"},
            "actions": [{"type": "send_message", "platform": "slack", "text": "Standup time!"}],
            "enabled": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Daily standup brief"
    assert "id" in data


@pytest.mark.asyncio
async def test_update_standing_order(auth_client: AsyncClient):
    """Authenticated user can update a standing order."""
    create_resp = await auth_client.post(
        "/api/standing-orders",
        json={
            "name": "To update",
            "trigger_type": "event",
            "trigger_config": {},
            "actions": [],
        },
    )
    order_id = create_resp.json()["id"]

    update_resp = await auth_client.patch(
        f"/api/standing-orders/{order_id}",
        json={"enabled": False},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["enabled"] is False


@pytest.mark.asyncio
async def test_delete_standing_order(auth_client: AsyncClient):
    """Authenticated user can delete a standing order."""
    create_resp = await auth_client.post(
        "/api/standing-orders",
        json={
            "name": "To delete",
            "trigger_type": "event",
            "trigger_config": {},
            "actions": [],
        },
    )
    order_id = create_resp.json()["id"]

    delete_resp = await auth_client.delete(f"/api/standing-orders/{order_id}")
    assert delete_resp.status_code == 200
    assert delete_resp.json()["deleted"] is True
