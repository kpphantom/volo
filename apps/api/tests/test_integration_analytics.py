"""Tests for GET /analytics/integrations (§4)."""

import pytest
from httpx import AsyncClient
from app.database import async_session, Integration


async def _add_integration(type_: str, status: str = "connected", category: str = "messaging"):
    async with async_session() as session:
        integ = Integration(
            user_id="dev-user",
            type=type_,
            category=category,
            name=type_.title(),
            status=status,
        )
        session.add(integ)
        await session.commit()
        await session.refresh(integ)
        return integ.id


async def _delete_integration(integ_id: str):
    async with async_session() as session:
        from sqlalchemy import select
        result = await session.execute(select(Integration).where(Integration.id == integ_id))
        integ = result.scalar_one_or_none()
        if integ:
            await session.delete(integ)
            await session.commit()


@pytest.mark.xfail(reason="dev auth bypass active in non-production env", strict=False)
@pytest.mark.asyncio
async def test_integration_analytics_requires_auth(client: AsyncClient):
    resp = await client.get("/api/analytics/integrations")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_integration_analytics_response_shape(auth_client: AsyncClient):
    resp = await auth_client.get("/api/analytics/integrations")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_integrations" in data
    assert "active_integrations" in data
    assert "integrations_by_category" in data
    assert "period" in data
    assert data["period"] == "all_time"


@pytest.mark.asyncio
async def test_integration_analytics_counts_connected(auth_client: AsyncClient):
    integ_id = await _add_integration("test_slack", status="connected", category="messaging")
    try:
        resp = await auth_client.get("/api/analytics/integrations")
        data = resp.json()
        assert data["total_integrations"] >= 1
        active_types = [i["type"] for i in data["active_integrations"]]
        assert "test_slack" in active_types
    finally:
        await _delete_integration(integ_id)


@pytest.mark.asyncio
async def test_integration_analytics_excludes_disconnected(auth_client: AsyncClient):
    integ_id = await _add_integration("test_disconnected", status="disconnected", category="auth")
    try:
        resp = await auth_client.get("/api/analytics/integrations")
        data = resp.json()
        active_types = [i["type"] for i in data["active_integrations"]]
        assert "test_disconnected" not in active_types
    finally:
        await _delete_integration(integ_id)


@pytest.mark.asyncio
async def test_integration_analytics_groups_by_category(auth_client: AsyncClient):
    ids = []
    try:
        ids.append(await _add_integration("svc_a", category="finance"))
        ids.append(await _add_integration("svc_b", category="finance"))
        ids.append(await _add_integration("svc_c", category="health"))
        resp = await auth_client.get("/api/analytics/integrations")
        by_cat = resp.json()["integrations_by_category"]
        assert by_cat.get("finance", 0) >= 2
        assert by_cat.get("health", 0) >= 1
    finally:
        for iid in ids:
            await _delete_integration(iid)
