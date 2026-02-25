"""Tests for authenticator (TOTP vault) endpoints."""

import pytest
from httpx import AsyncClient


# A known-valid Base32 TOTP secret for testing
TEST_SECRET = "JBSWY3DPEHPK3PXP"


@pytest.mark.asyncio
async def test_add_account(auth_client: AsyncClient):
    """Authenticated user can add a TOTP account."""
    response = await auth_client.post(
        "/api/authenticator/add",
        json={
            "service": "test-service-123",
            "secret": TEST_SECRET,
            "label": "Test Account",
            "issuer": "TestIssuer",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "service" in data or "success" in data


@pytest.mark.asyncio
async def test_list_accounts(auth_client: AsyncClient):
    """Authenticated user can list TOTP accounts."""
    response = await auth_client.get("/api/authenticator/accounts")
    assert response.status_code == 200
    data = response.json()
    assert "accounts" in data


@pytest.mark.asyncio
async def test_get_codes(auth_client: AsyncClient):
    """Authenticated user can retrieve current TOTP codes."""
    response = await auth_client.get("/api/authenticator/codes")
    assert response.status_code == 200
    data = response.json()
    assert "codes" in data


@pytest.mark.asyncio
async def test_get_code_for_service(auth_client: AsyncClient):
    """Authenticated user can get a code for a specific service."""
    # Add account first
    await auth_client.post(
        "/api/authenticator/add",
        json={
            "service": "test-totp-service",
            "secret": TEST_SECRET,
            "label": "Test TOTP",
        },
    )

    response = await auth_client.get("/api/authenticator/code/test-totp-service")
    assert response.status_code == 200
    data = response.json()
    assert "code" in data
    assert len(data["code"]) == 6


@pytest.mark.asyncio
async def test_get_code_not_found(auth_client: AsyncClient):
    """Getting a code for an unknown service returns 404."""
    response = await auth_client.get("/api/authenticator/code/nonexistent-xyz-9999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_account(auth_client: AsyncClient):
    """Authenticated user can remove a TOTP account."""
    # Add first
    await auth_client.post(
        "/api/authenticator/add",
        json={
            "service": "service-to-delete",
            "secret": TEST_SECRET,
            "label": "Delete Me",
        },
    )

    # Delete
    delete_resp = await auth_client.delete("/api/authenticator/service-to-delete")
    assert delete_resp.status_code == 200
    assert delete_resp.json()["success"] is True
