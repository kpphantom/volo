"""
Tests for the platform adapter pattern (§3.2).
- MessagingAdapter / SocialAdapter base class behaviour
- Adapters instantiated with empty credentials → unconfigured → demo data returned
- Aggregator services collect all adapters uniformly
"""

import pytest
from app.services.messaging import (
    MessagingService,
    TelegramAdapter,
    WhatsAppAdapter,
    DiscordAdapter,
    SlackAdapter,
)
from app.services.social_feed import (
    SocialFeedService,
    TwitterAdapter,
    InstagramAdapter,
    RedditAdapter,
)


# ── MessagingAdapter base behaviour ──────────────────────────────────────────

def test_messaging_adapter_is_not_configured_without_credentials():
    """Empty credentials → is_configured is False for all token-based adapters."""
    assert TelegramAdapter(token="").is_configured is False
    assert WhatsAppAdapter(token="", phone_id="").is_configured is False
    assert DiscordAdapter(token="").is_configured is False
    assert SlackAdapter(token="").is_configured is False


@pytest.mark.asyncio
async def test_messaging_adapter_returns_demo_data_when_unconfigured():
    adapter = TelegramAdapter(token="")
    messages = await adapter.get_messages(limit=5)
    assert isinstance(messages, list)
    assert len(messages) > 0
    assert all(m.get("_demo") is True for m in messages)


def test_messaging_demo_wrap_adds_envelope_fields():
    adapter = TelegramAdapter(token="")
    wrapped = adapter._wrap_demo(adapter._demo_data())
    for item in wrapped:
        assert item["platform"] == adapter.platform_id
        assert item["id"].startswith(f"demo-{adapter.platform_id}-")
        assert "timestamp" in item
        assert item["_demo"] is True


def test_messaging_to_status_dict_shape():
    adapter = TelegramAdapter(token="")
    status = adapter.to_status_dict()
    assert status["id"] == adapter.platform_id
    assert status["name"] == adapter.name
    assert "connected" in status
    assert status["connected"] is False


def test_messaging_to_status_dict_connected_when_configured():
    """A non-empty token should make to_status_dict report connected=True."""
    adapter = TelegramAdapter(token="real-bot-token")
    assert adapter.to_status_dict()["connected"] is True


# ── MessagingService aggregator ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_messaging_service_get_all_messages_returns_list():
    svc = MessagingService()
    messages = await svc.get_all_messages()
    assert isinstance(messages, list)


@pytest.mark.asyncio
async def test_messaging_service_messages_have_platform_field():
    svc = MessagingService()
    messages = await svc.get_all_messages()
    for msg in messages:
        assert "platform" in msg


def test_messaging_service_get_connected_platforms_lists_all():
    svc = MessagingService()
    platforms = svc.get_connected_platforms()
    ids = {p["id"] for p in platforms}
    assert "telegram" in ids
    assert "discord" in ids
    assert "slack" in ids


def test_messaging_service_connected_platforms_have_required_keys():
    svc = MessagingService()
    for p in svc.get_connected_platforms():
        assert "id" in p
        assert "name" in p
        assert "connected" in p


# ── SocialAdapter base behaviour ──────────────────────────────────────────────

def test_social_adapter_is_not_configured_without_credentials():
    assert TwitterAdapter(app_token="").is_configured is False
    assert InstagramAdapter(app_token="").is_configured is False
    assert RedditAdapter(client_id="", client_secret="").is_configured is False


@pytest.mark.asyncio
async def test_social_adapter_returns_demo_data_when_unconfigured():
    adapter = TwitterAdapter(app_token="")
    posts = await adapter.get_feed(limit=5)
    assert isinstance(posts, list)
    assert len(posts) > 0
    assert all(p.get("_demo") is True for p in posts)


def test_social_demo_wrap_adds_envelope_fields():
    adapter = TwitterAdapter(app_token="")
    wrapped = adapter._wrap_demo(adapter._demo_data())
    for item in wrapped:
        assert item["platform"] == adapter.platform_id
        assert item["id"].startswith(f"demo-{adapter.platform_id}-")
        assert "timestamp" in item
        assert item["_demo"] is True


def test_social_to_status_dict_shape():
    adapter = TwitterAdapter(app_token="")
    status = adapter.to_status_dict(user_connected=False)
    assert status["id"] == adapter.platform_id
    assert "connected" in status
    assert status["connected"] is False


def test_social_to_status_dict_user_connected_overrides():
    adapter = TwitterAdapter(app_token="")
    assert adapter.to_status_dict(user_connected=True)["connected"] is True


# ── SocialFeedService aggregator ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_social_feed_service_get_unified_feed_returns_list():
    svc = SocialFeedService()
    posts = await svc.get_unified_feed()
    assert isinstance(posts, list)


@pytest.mark.asyncio
async def test_social_feed_service_posts_have_platform_field():
    svc = SocialFeedService()
    posts = await svc.get_unified_feed()
    for post in posts:
        assert "platform" in post


@pytest.mark.asyncio
async def test_social_feed_service_connected_platforms_returns_list():
    svc = SocialFeedService()
    platforms = await svc.get_connected_platforms()
    assert isinstance(platforms, list)
    ids = {p["id"] for p in platforms}
    assert "twitter" in ids
    assert "instagram" in ids
    assert "reddit" in ids
