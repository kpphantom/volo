"""Tests for POST /standing-orders/{id}/run (§4)."""

import pytest
from httpx import AsyncClient


async def _create_order(auth_client: AsyncClient, actions: list) -> str:
    resp = await auth_client.post(
        "/api/standing-orders",
        json={
            "name": "Run test order",
            "trigger_type": "event",
            "trigger_config": {},
            "actions": actions,
        },
    )
    assert resp.status_code == 200
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_run_empty_actions_returns_executed(auth_client: AsyncClient):
    order_id = await _create_order(auth_client, [])
    resp = await auth_client.post(f"/api/standing-orders/{order_id}/run")
    assert resp.status_code == 200
    data = resp.json()
    assert data["executed"] is True
    assert data["action_results"] == []


@pytest.mark.asyncio
async def test_run_sets_last_run_at(auth_client: AsyncClient):
    order_id = await _create_order(auth_client, [])
    resp = await auth_client.post(f"/api/standing-orders/{order_id}/run")
    assert resp.json()["order"]["last_run_at"] is not None


@pytest.mark.asyncio
async def test_run_unknown_action_type_acknowledged(auth_client: AsyncClient):
    order_id = await _create_order(auth_client, [{"type": "future_feature"}])
    resp = await auth_client.post(f"/api/standing-orders/{order_id}/run")
    assert resp.status_code == 200
    results = resp.json()["action_results"]
    assert len(results) == 1
    assert results[0]["status"] == "acknowledged"
    assert results[0]["type"] == "future_feature"


@pytest.mark.asyncio
async def test_run_notification_action_executed(auth_client: AsyncClient):
    action = {
        "type": "notification",
        "level": "info",
        "title": "Daily Brief",
        "message": "Your standing order ran.",
    }
    order_id = await _create_order(auth_client, [action])
    resp = await auth_client.post(f"/api/standing-orders/{order_id}/run")
    assert resp.status_code == 200
    results = resp.json()["action_results"]
    assert results[0]["type"] == "notification"
    assert results[0]["status"] == "executed"


@pytest.mark.asyncio
async def test_run_message_action_queued(auth_client: AsyncClient):
    action = {"type": "message", "content": "Summarise my emails"}
    order_id = await _create_order(auth_client, [action])
    resp = await auth_client.post(f"/api/standing-orders/{order_id}/run")
    assert resp.status_code == 200
    results = resp.json()["action_results"]
    assert results[0]["type"] == "message"
    assert results[0]["status"] == "queued"


@pytest.mark.asyncio
async def test_run_chat_action_queued(auth_client: AsyncClient):
    """'chat' is an alias for 'message'."""
    action = {"type": "chat", "content": "Check GitHub PRs"}
    order_id = await _create_order(auth_client, [action])
    resp = await auth_client.post(f"/api/standing-orders/{order_id}/run")
    results = resp.json()["action_results"]
    assert results[0]["status"] == "queued"


@pytest.mark.asyncio
async def test_run_webhook_missing_url_returns_error(auth_client: AsyncClient):
    action = {"type": "webhook", "payload": {"hello": "world"}}
    order_id = await _create_order(auth_client, [action])
    resp = await auth_client.post(f"/api/standing-orders/{order_id}/run")
    results = resp.json()["action_results"]
    assert results[0]["status"] == "error"
    assert "missing url" in results[0]["error"]


@pytest.mark.asyncio
async def test_run_multiple_actions_all_have_results(auth_client: AsyncClient):
    actions = [
        {"type": "notification", "title": "Done", "level": "info", "message": ""},
        {"type": "message", "content": "Hello"},
        {"type": "unknown_x"},
    ]
    order_id = await _create_order(auth_client, actions)
    resp = await auth_client.post(f"/api/standing-orders/{order_id}/run")
    results = resp.json()["action_results"]
    assert len(results) == 3
    statuses = {r["status"] for r in results}
    assert "executed" in statuses
    assert "queued" in statuses
    assert "acknowledged" in statuses


@pytest.mark.asyncio
async def test_run_nonexistent_order_returns_404(auth_client: AsyncClient):
    resp = await auth_client.post("/api/standing-orders/does-not-exist/run")
    assert resp.status_code == 404
