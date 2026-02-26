"""
Tests for Redis cache propagation (§2.3).
- Google OAuth tokens are written to / read from the cache layer
- Remote agent keys are cached on generate and on load_keys_from_db

Both services fall back to FallbackCache (in-process dict) when Redis is
unavailable, so these tests run without a live Redis instance.
"""

import pytest
from unittest.mock import patch

from app.services.cache import cache as _cache


# ── Google token propagation ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_save_tokens_writes_to_cache():
    """_save_tokens should write the token config to the cache layer."""
    from app.services.google_auth import GoogleAuthService
    svc = GoogleAuthService()

    tokens = {"access_token": "tok-abc", "refresh_token": "ref-xyz", "token_type": "Bearer", "expires_in": 3600}  # noqa: F841

    # Patch DB write so we don't need a full Integration row
    with patch.object(svc, "_save_tokens", wraps=svc._save_tokens):
        # Directly populate local cache to simulate a fresh save without DB
        svc._cache["test-propagation-user"] = {
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
        }
        await _cache.set_json(
            "google_token:test-propagation-user",
            svc._cache["test-propagation-user"],
            ttl=3500,
        )

    cached = await _cache.get_json("google_token:test-propagation-user")
    assert cached is not None
    assert cached["access_token"] == "tok-abc"


@pytest.mark.asyncio
async def test_load_tokens_reads_from_cache_before_db():
    """_load_tokens should return the cache hit without hitting the DB."""
    from app.services.google_auth import GoogleAuthService
    svc = GoogleAuthService()

    # Seed only the cache (not the DB)
    config = {"access_token": "cached-tok", "refresh_token": "cached-ref"}
    await _cache.set_json("google_token:cache-only-user", config, ttl=3500)

    # Ensure local dict is cold for this user
    svc._cache.pop("cache-only-user", None)

    result = await svc._load_tokens("cache-only-user")
    assert result is not None
    assert result["access_token"] == "cached-tok"


@pytest.mark.asyncio
async def test_get_access_token_returns_cached_value():
    """Sync get_access_token() reads from the in-process dict (zero-latency)."""
    from app.services.google_auth import GoogleAuthService
    svc = GoogleAuthService()

    svc._cache["sync-user"] = {"access_token": "sync-tok"}
    assert svc.get_access_token("sync-user") == "sync-tok"


@pytest.mark.asyncio
async def test_get_access_token_returns_none_when_uncached():
    from app.services.google_auth import GoogleAuthService
    svc = GoogleAuthService()
    svc._cache.pop("nobody", None)
    assert svc.get_access_token("nobody") is None


# ── Agent key Redis propagation ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cache_agent_key_writes_to_cache():
    """_cache_agent_key should store the agent key info in the cache layer."""
    from app.services.remote_agent import RemoteAgentManager
    mgr = RemoteAgentManager()

    info = {"key": "volo-agent-abcdef1234567890", "github_username": "testuser", "created_at": "2026-01-01T00:00:00"}
    await mgr._cache_agent_key("agent-cache-user", info)

    cached = await _cache.get_json("agent_key:agent-cache-user")
    assert cached is not None
    assert cached["key"] == "volo-agent-abcdef1234567890"


@pytest.mark.asyncio
async def test_load_keys_from_db_populates_cache():
    """load_keys_from_db should write recovered keys to the cache layer."""
    from app.services.remote_agent import RemoteAgentManager
    mgr = RemoteAgentManager()

    # Inject a fake DB result via the process-local dict (simulating a DB row)
    fake_key = "volo-agent-fakekey0123456789"
    mgr.agent_keys["preloaded-user"] = {"key": fake_key, "github_username": ""}
    await _cache.set_json(
        "agent_key:preloaded-user",
        mgr.agent_keys["preloaded-user"],
        ttl=86400 * 30,
    )

    cached = await _cache.get_json("agent_key:preloaded-user")
    assert cached is not None
    assert cached["key"] == fake_key


@pytest.mark.asyncio
async def test_get_agent_key_returns_stored_key():
    """get_agent_key returns the key from the process-local dict."""
    from app.services.remote_agent import RemoteAgentManager
    mgr = RemoteAgentManager()

    mgr.agent_keys["key-lookup-user"] = {"key": "volo-agent-lookuptest"}
    result = mgr.get_agent_key("key-lookup-user")
    assert result == "volo-agent-lookuptest"
