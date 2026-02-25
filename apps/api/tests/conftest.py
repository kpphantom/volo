"""
VOLO — Test Configuration
Pytest fixtures for API testing.
"""

import pytest
import pytest_asyncio
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport

# Set test env vars before importing app
import os
os.environ["TESTING"] = "1"
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
os.environ.setdefault("JWT_SECRET", "test-secret-do-not-use-in-prod")
os.environ.setdefault("APP_SECRET_KEY", "test-app-secret-do-not-use-in-prod")
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["OPENAI_API_KEY"] = ""

from main import app
from app.auth import create_access_token
from app.database import engine, Base


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for all tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    """Create all tables and seed required data before the test session."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Seed the default tenant + dev-user that many routes depend on
    from app.database import async_session as _session, Tenant, User
    from sqlalchemy import select as _select
    async with _session() as session:
        if not (await session.execute(_select(Tenant).where(Tenant.id == "volo-default"))).scalar_one_or_none():
            session.add(Tenant(id="volo-default", name="Volo", slug="volo", plan="pro"))
            await session.flush()
        if not (await session.execute(_select(User).where(User.id == "dev-user"))).scalar_one_or_none():
            session.add(User(id="dev-user", tenant_id="volo-default", email="dev@volo.ai", name="Developer", role="owner"))
        await session.commit()
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client for testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_client(client: AsyncClient) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client with a valid JWT for 'dev-user'."""
    token = create_access_token("dev-user", "volo-default", "owner")
    client.headers["Authorization"] = f"Bearer {token}"
    yield client


@pytest.fixture
def api_headers():
    """Standard API headers."""
    return {
        "Content-Type": "application/json",
    }
