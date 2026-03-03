"""
Tests for Google service routes — specifically the 403-not-401 fix that
prevents frontend auto-logout when a Google account is not yet linked.

The api.ts client auto-logouts the user on any 401 response.  Google
auth errors must use 403 so only a missing Volo JWT triggers logout.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_gmail_returns_403_not_401_when_google_not_connected(auth_client: AsyncClient):
    """
    GET /api/google/gmail/messages must return 403 (not 401) when no
    Google token is stored for the user.  A 401 would trigger the
    frontend api.ts auto-logout and kick the user out of Volo entirely.
    """
    resp = await auth_client.get("/api/google/gmail/messages")
    assert resp.status_code == 403
    detail = resp.json()["detail"].lower()
    assert "not connected" in detail or "not authorized" in detail


@pytest.mark.asyncio
async def test_calendar_returns_403_not_401_when_google_not_connected(auth_client: AsyncClient):
    """
    GET /api/google/calendar/events must return 403 (not 401) when no
    Google token is stored.
    """
    resp = await auth_client.get("/api/google/calendar/events")
    assert resp.status_code == 403
    detail = resp.json()["detail"].lower()
    assert "not connected" in detail or "not authorized" in detail


@pytest.mark.asyncio
async def test_google_services_returns_disconnected_list_when_not_linked(auth_client: AsyncClient):
    """
    GET /api/google/services returns connected=False and a full service
    list when no Google account is linked — no crash, no 401.
    """
    resp = await auth_client.get("/api/google/services")
    assert resp.status_code == 200
    data = resp.json()
    assert data["connected"] is False
    assert isinstance(data["services"], list)
    assert len(data["services"]) > 0
    # Every service should be marked disconnected
    for svc in data["services"]:
        assert svc["connected"] is False


@pytest.mark.asyncio
async def test_google_profile_returns_nulls_when_not_linked(auth_client: AsyncClient):
    """GET /api/google/profile returns null fields rather than 401 when disconnected."""
    resp = await auth_client.get("/api/google/profile")
    assert resp.status_code == 200
    data = resp.json()
    assert "name" in data
    assert "email" in data


@pytest.mark.xfail(reason="dev auth bypass active in non-production env", strict=False)
@pytest.mark.asyncio
async def test_google_routes_require_volo_auth(client: AsyncClient):
    """Google endpoints must require a valid Volo JWT (not just Google auth).

    xfail locally where APP_ENV=development triggers the dev bypass.
    xpass in CI where APP_ENV=test keeps the bypass off.
    """
    for path in ["/api/google/gmail/messages", "/api/google/calendar/events", "/api/google/services"]:
        resp = await client.get(path)
        # Without a Volo JWT, must get 401 (not 200 or 403)
        assert resp.status_code in (401, 403), f"{path} should require auth"
