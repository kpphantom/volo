"""Tests for NotificationService — direct DB-backed tests."""

import pytest

from app.services.notifications import notifications


@pytest.mark.asyncio
async def test_create_notification(create_tables):
    """Create a notification and verify the returned dict."""
    result = await notifications.create(
        user_id="dev-user",
        type="info",
        title="Test Notification",
        body="Test body",
        data={"source": "unit-test"},
    )
    assert "id" in result
    assert result["title"] == "Test Notification"
    assert result["body"] == "Test body"
    assert result["read"] is False
    assert result["type"] == "info"
    assert result["user_id"] == "dev-user"


@pytest.mark.asyncio
async def test_list_notifications_returns_list(create_tables):
    await notifications.create(user_id="dev-user", type="info", title="Listed")
    result = await notifications.list_notifications("dev-user")
    assert isinstance(result, list)
    assert len(result) >= 1


@pytest.mark.asyncio
async def test_list_notifications_unread_only(create_tables):
    """Unread-only filter returns only unread items."""
    notif = await notifications.create(user_id="dev-user", type="info", title="Unread Test")
    unread = await notifications.list_notifications("dev-user", unread_only=True)
    ids = [n["id"] for n in unread]
    assert notif["id"] in ids


@pytest.mark.asyncio
async def test_get_unread_count(create_tables):
    initial = await notifications.get_unread_count("dev-user")
    await notifications.create(user_id="dev-user", type="info", title="Count Me")
    after = await notifications.get_unread_count("dev-user")
    assert after == initial + 1


@pytest.mark.asyncio
async def test_mark_read(create_tables):
    notif = await notifications.create(user_id="dev-user", type="info", title="Mark Read")
    assert notif["read"] is False

    success = await notifications.mark_read(notif["id"])
    assert success is True

    # Should no longer appear in unread_only list
    unread = await notifications.list_notifications("dev-user", unread_only=True)
    assert notif["id"] not in [n["id"] for n in unread]


@pytest.mark.asyncio
async def test_mark_all_read(create_tables):
    await notifications.create(user_id="dev-user", type="info", title="Bulk 1")
    await notifications.create(user_id="dev-user", type="info", title="Bulk 2")

    count = await notifications.mark_all_read("dev-user")
    assert count >= 0  # may be 0 if previously marked read in same session

    remaining = await notifications.get_unread_count("dev-user")
    assert remaining == 0


@pytest.mark.asyncio
async def test_delete_notification(create_tables):
    notif = await notifications.create(user_id="dev-user", type="info", title="Delete Me")

    result = await notifications.delete(notif["id"])
    assert result is True

    # Verify it's gone
    all_notifs = await notifications.list_notifications("dev-user")
    assert notif["id"] not in [n["id"] for n in all_notifs]


@pytest.mark.asyncio
async def test_delete_nonexistent_returns_false(create_tables):
    result = await notifications.delete("does-not-exist-id")
    assert result is False


@pytest.mark.asyncio
async def test_mark_read_nonexistent_returns_false(create_tables):
    result = await notifications.mark_read("does-not-exist-id")
    assert result is False
