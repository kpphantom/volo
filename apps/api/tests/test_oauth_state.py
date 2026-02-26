"""Tests for shared OAuth state helpers (§3.1 — services/oauth.py)."""

import pytest
from app.services.oauth import store_oauth_state, pop_oauth_state


@pytest.mark.asyncio
async def test_store_returns_non_empty_state():
    state = await store_oauth_state("google")
    assert isinstance(state, str)
    assert len(state) > 20


@pytest.mark.asyncio
async def test_pop_returns_correct_provider():
    state = await store_oauth_state("github")
    payload = await pop_oauth_state(state, "github")
    assert payload["provider"] == "github"


@pytest.mark.asyncio
async def test_pop_is_one_time_use():
    """State is deleted after first pop — second pop raises ValueError."""
    state = await store_oauth_state("google")
    await pop_oauth_state(state, "google")
    with pytest.raises(ValueError, match="Invalid or expired"):
        await pop_oauth_state(state, "google")


@pytest.mark.asyncio
async def test_pop_missing_state_raises():
    with pytest.raises(ValueError, match="Invalid or expired"):
        await pop_oauth_state("nonexistent-state-xyz", "google")


@pytest.mark.asyncio
async def test_pop_provider_mismatch_raises():
    state = await store_oauth_state("google")
    with pytest.raises(ValueError, match="provider mismatch"):
        await pop_oauth_state(state, "github")


@pytest.mark.asyncio
async def test_extra_payload_preserved():
    state = await store_oauth_state("twitter", extra={"redirect": "/dashboard"})
    payload = await pop_oauth_state(state, "twitter")
    assert payload["redirect"] == "/dashboard"


@pytest.mark.asyncio
async def test_key_prefix_isolation():
    """Same state string under different prefixes should not collide."""
    state = await store_oauth_state("google", key_prefix="oauth_state")
    # This should raise because social_state prefix has no such key
    with pytest.raises(ValueError):
        await pop_oauth_state(state, "google", key_prefix="social_state")
    # Original prefix still works
    payload = await pop_oauth_state(state, "google", key_prefix="oauth_state")
    assert payload["provider"] == "google"
