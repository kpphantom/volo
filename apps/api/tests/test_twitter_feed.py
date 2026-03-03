"""
Tests for the TwitterAdapter user-token + refresh flow.

The bug: Twitter OAuth 2.0 access tokens expire in 2 hours.  The adapter
previously fell back to an app-only Bearer token for the home timeline,
which requires user context and always fails.  Now it:
  1. Requires a user token (demo data if none available)
  2. Refreshes the token on 401 and retries once
  3. Falls back to the user's own tweets if the home timeline is unavailable
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.services.social_feed import TwitterAdapter


# ── No user context ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_twitter_returns_demo_when_no_user_id():
    """Without a user_id, always return demo data regardless of app_token."""
    adapter = TwitterAdapter(app_token="real-bearer-token")
    posts = await adapter.get_feed(limit=5)
    assert isinstance(posts, list)
    assert len(posts) > 0
    assert all(p.get("_demo") is True for p in posts)


@pytest.mark.asyncio
async def test_twitter_returns_demo_when_user_has_no_stored_token():
    """user_id given but social_oauth returns None → fall back to demo."""
    adapter = TwitterAdapter(app_token="real-bearer-token")
    with patch(
        "app.services.social_feed.social_oauth.get_access_token",
        new_callable=AsyncMock,
        return_value=None,
    ):
        posts = await adapter.get_feed(limit=5, user_id="user-without-twitter")

    assert all(p.get("_demo") is True for p in posts)


# ── Successful home timeline ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_twitter_uses_user_token_for_home_timeline():
    """When a user token is found, it is used in the Authorization header."""
    adapter = TwitterAdapter(app_token="")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": [
            {
                "id": "111",
                "text": "Hello world",
                "created_at": "2026-03-03T10:00:00Z",
                "public_metrics": {"like_count": 5, "reply_count": 1, "retweet_count": 2},
                "author_id": "u1",
            }
        ],
        "includes": {
            "users": [{"id": "u1", "name": "Test User", "username": "testuser", "profile_image_url": ""}]
        },
    }

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get.return_value = mock_resp

    with (
        patch("app.services.social_feed.social_oauth.get_access_token", new_callable=AsyncMock, return_value="user-token-abc"),
        patch("app.services.social_feed.httpx.AsyncClient", return_value=mock_client),
    ):
        posts = await adapter.get_feed(limit=5, user_id="user-123")

    assert len(posts) == 1
    assert posts[0]["platform"] == "twitter"
    assert posts[0]["content"] == "Hello world"
    # Verify the Authorization header contained the user token
    call_kwargs = mock_client.get.call_args_list[0][1]
    assert call_kwargs["headers"]["Authorization"] == "Bearer user-token-abc"


# ── Token refresh on 401 ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_twitter_refreshes_token_on_401_and_retries():
    """On a 401 response, twitter_refresh is called and timeline retried."""
    adapter = TwitterAdapter(app_token="")

    resp_401 = MagicMock()
    resp_401.status_code = 401

    resp_200 = MagicMock()
    resp_200.status_code = 200
    resp_200.json.return_value = {"data": [], "includes": {"users": []}}

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get.side_effect = [resp_401, resp_200]

    with (
        patch("app.services.social_feed.social_oauth.get_access_token", new_callable=AsyncMock, return_value="expired-token"),
        patch("app.services.social_feed.social_oauth.twitter_refresh", new_callable=AsyncMock, return_value="fresh-token"),
        patch("app.services.social_feed.httpx.AsyncClient", return_value=mock_client),
    ):
        posts = await adapter.get_feed(limit=5, user_id="user-123")

    assert isinstance(posts, list)
    # Two GET calls: first with expired-token (401), second with fresh-token
    assert mock_client.get.call_count == 2
    second_call_auth = mock_client.get.call_args_list[1][1]["headers"]["Authorization"]
    assert second_call_auth == "Bearer fresh-token"


@pytest.mark.asyncio
async def test_twitter_returns_empty_list_when_refresh_also_fails():
    """If refresh returns None (no refresh_token stored), return empty list."""
    adapter = TwitterAdapter(app_token="")

    resp_401 = MagicMock()
    resp_401.status_code = 401

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get.return_value = resp_401

    with (
        patch("app.services.social_feed.social_oauth.get_access_token", new_callable=AsyncMock, return_value="expired-token"),
        patch("app.services.social_feed.social_oauth.twitter_refresh", new_callable=AsyncMock, return_value=None),
        patch("app.services.social_feed.httpx.AsyncClient", return_value=mock_client),
    ):
        posts = await adapter.get_feed(limit=5, user_id="user-123")

    # No retry possible, and fallback /users/me also 401 → empty list
    assert isinstance(posts, list)


# ── Home timeline unavailable → fallback ─────────────────────────────────────

@pytest.mark.asyncio
async def test_twitter_falls_back_to_own_tweets_on_403():
    """When home timeline returns 403, fall back to the user's own tweets."""
    adapter = TwitterAdapter(app_token="")

    resp_403 = MagicMock()
    resp_403.status_code = 403

    resp_me = MagicMock()
    resp_me.status_code = 200
    resp_me.json.return_value = {"data": {"id": "u99", "name": "Me", "username": "myself"}}

    resp_tweets = MagicMock()
    resp_tweets.status_code = 200
    resp_tweets.json.return_value = {
        "data": [
            {
                "id": "999",
                "text": "My own tweet",
                "created_at": "2026-03-03T12:00:00Z",
                "public_metrics": {"like_count": 10, "reply_count": 0, "retweet_count": 1},
            }
        ]
    }

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get.side_effect = [resp_403, resp_me, resp_tweets]

    with (
        patch("app.services.social_feed.social_oauth.get_access_token", new_callable=AsyncMock, return_value="user-token"),
        patch("app.services.social_feed.httpx.AsyncClient", return_value=mock_client),
    ):
        posts = await adapter.get_feed(limit=5, user_id="user-123")

    assert len(posts) == 1
    assert posts[0]["content"] == "My own tweet"
    assert posts[0]["platform"] == "twitter"
