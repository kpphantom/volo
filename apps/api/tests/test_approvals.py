"""Tests for approvals endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_approvals(auth_client: AsyncClient):
    """Authenticated user can list approvals."""
    response = await auth_client.get("/api/approvals")
    assert response.status_code == 200
    data = response.json()
    assert "approvals" in data


@pytest.mark.asyncio
async def test_create_approval(auth_client: AsyncClient):
    """Authenticated user can create an approval request."""
    response = await auth_client.post(
        "/api/approvals",
        json={
            "action": "delete_file",
            "description": "Delete /tmp/report.csv",
            "tool_name": "delete_file",
            "parameters": {"path": "/tmp/report.csv"},
            "tier": "approve",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["action"] == "delete_file"
    assert data["status"] == "pending"
    assert "id" in data


@pytest.mark.asyncio
async def test_approve(auth_client: AsyncClient):
    """Authenticated user can approve a pending request."""
    create_resp = await auth_client.post(
        "/api/approvals",
        json={"action": "test_action", "tier": "approve"},
    )
    approval_id = create_resp.json()["id"]

    approve_resp = await auth_client.post(f"/api/approvals/{approval_id}/approve")
    assert approve_resp.status_code == 200
    assert approve_resp.json()["approved"] is True
    assert approve_resp.json()["approval"]["status"] == "approved"


@pytest.mark.asyncio
async def test_deny(auth_client: AsyncClient):
    """Authenticated user can deny a pending request."""
    create_resp = await auth_client.post(
        "/api/approvals",
        json={"action": "risky_action", "tier": "approve"},
    )
    approval_id = create_resp.json()["id"]

    deny_resp = await auth_client.post(
        f"/api/approvals/{approval_id}/deny",
        params={"reason": "Not authorized"},
    )
    assert deny_resp.status_code == 200
    assert deny_resp.json()["denied"] is True
    assert deny_resp.json()["approval"]["status"] == "denied"


@pytest.mark.asyncio
async def test_list_pending(auth_client: AsyncClient):
    """Authenticated user can list pending approvals."""
    response = await auth_client.get("/api/approvals/pending")
    assert response.status_code == 200
    data = response.json()
    assert "approvals" in data
    # All returned items must be pending
    for a in data["approvals"]:
        assert a["status"] == "pending"
