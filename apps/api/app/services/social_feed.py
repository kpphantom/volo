"""
VOLO — Unified Social Feed Service
Aggregates content from Twitter/X, Instagram, LinkedIn, TikTok, Reddit, Facebook.

Each platform is a SocialAdapter subclass. SocialFeedService registers
adapters and provides the unified feed + connection-status used by routes.
"""

import os
import logging
import httpx
from datetime import datetime, timezone

from app.services.social_oauth import social_oauth
from app.services.base_platform import SocialAdapter

logger = logging.getLogger("volo.social_feed")


# ── Per-platform adapters ─────────────────────────────────────────────────────

class TwitterAdapter(SocialAdapter):
    def __init__(self, app_token: str):
        self._app_token = app_token

    @property
    def platform_id(self) -> str: return "twitter"
    @property
    def name(self) -> str: return "Twitter / X"
    @property
    def is_configured(self) -> bool: return bool(self._app_token)
    @property
    def icon(self) -> str: return "twitter"
    @property
    def color(self) -> str: return "#1DA1F2"

    async def get_feed(self, limit: int = 20, user_id: str | None = None) -> list[dict]:
        # Home timeline requires OAuth 2.0 user context — app-only token won't work.
        user_token = None
        if user_id:
            user_token = await social_oauth.get_access_token(user_id, "twitter")
        if not user_token:
            return self._wrap_demo(self._demo_data())

        async with httpx.AsyncClient() as client:
            token = user_token
            tl_params = {
                "max_results": limit,
                "tweet.fields": "created_at,public_metrics,author_id",
                "expansions": "author_id",
                "user.fields": "name,username,profile_image_url",
            }
            resp = await client.get(
                "https://api.twitter.com/2/users/me/timelines/reverse_chronological",
                headers={"Authorization": f"Bearer {token}"},
                params=tl_params,
            )

            # Refresh expired token (2-hour lifetime) and retry once
            if resp.status_code == 401 and user_id:
                refreshed = await social_oauth.twitter_refresh(user_id)
                if refreshed:
                    token = refreshed
                    resp = await client.get(
                        "https://api.twitter.com/2/users/me/timelines/reverse_chronological",
                        headers={"Authorization": f"Bearer {token}"},
                        params=tl_params,
                    )

            if resp.status_code == 200:
                data = resp.json()
                users = {u["id"]: u for u in data.get("includes", {}).get("users", [])}
                posts = []
                for tweet in data.get("data", []):
                    author = users.get(tweet.get("author_id", ""), {})
                    metrics = tweet.get("public_metrics", {})
                    posts.append({
                        "platform": "twitter",
                        "id": tweet["id"],
                        "author": author.get("name", "Unknown"),
                        "username": f"@{author.get('username', '')}",
                        "avatar": author.get("profile_image_url", ""),
                        "content": tweet.get("text", ""),
                        "timestamp": tweet.get("created_at", ""),
                        "likes": metrics.get("like_count", 0),
                        "comments": metrics.get("reply_count", 0),
                        "shares": metrics.get("retweet_count", 0),
                        "media": [],
                        "url": f"https://x.com/{author.get('username', '')}/status/{tweet['id']}",
                    })
                return posts

            logger.warning(
                "Twitter home timeline unavailable (HTTP %d); trying user tweets fallback",
                resp.status_code,
            )

            # Fallback: user's own tweets — broader API tier availability
            me_resp = await client.get(
                "https://api.twitter.com/2/users/me",
                headers={"Authorization": f"Bearer {token}"},
                params={"user.fields": "id,name,username,profile_image_url"},
            )
            if me_resp.status_code != 200:
                logger.warning("Twitter /users/me failed: HTTP %d", me_resp.status_code)
                return []

            me = me_resp.json().get("data", {})
            uid = me.get("id")
            if not uid:
                return []

            tweets_resp = await client.get(
                f"https://api.twitter.com/2/users/{uid}/tweets",
                headers={"Authorization": f"Bearer {token}"},
                params={"max_results": limit, "tweet.fields": "created_at,public_metrics"},
            )
            if tweets_resp.status_code == 200:
                posts = []
                for tweet in tweets_resp.json().get("data", []):
                    metrics = tweet.get("public_metrics", {})
                    posts.append({
                        "platform": "twitter",
                        "id": tweet["id"],
                        "author": me.get("name", "You"),
                        "username": f"@{me.get('username', '')}",
                        "avatar": me.get("profile_image_url", ""),
                        "content": tweet.get("text", ""),
                        "timestamp": tweet.get("created_at", ""),
                        "likes": metrics.get("like_count", 0),
                        "comments": metrics.get("reply_count", 0),
                        "shares": metrics.get("retweet_count", 0),
                        "media": [],
                        "url": f"https://x.com/{me.get('username', '')}/status/{tweet['id']}",
                    })
                return posts

            logger.warning("Twitter user tweets fallback also failed: HTTP %d", tweets_resp.status_code)
        return []

    def _demo_data(self) -> list[dict]:
        return [
            {"author": "Elon Musk", "username": "@elonmusk", "content": "The future is closer than you think 🚀", "likes": 42000, "comments": 8500, "shares": 12000},
            {"author": "Naval", "username": "@naval", "content": "Specific knowledge is found by pursuing your genuine curiosity and passion.", "likes": 15000, "comments": 2100, "shares": 5400},
            {"author": "Sam Altman", "username": "@sama", "content": "AI will be the most transformative technology in human history.", "likes": 28000, "comments": 6200, "shares": 9100},
        ]


class InstagramAdapter(SocialAdapter):
    def __init__(self, app_token: str):
        self._app_token = app_token

    @property
    def platform_id(self) -> str: return "instagram"
    @property
    def name(self) -> str: return "Instagram"
    @property
    def is_configured(self) -> bool: return bool(self._app_token)
    @property
    def icon(self) -> str: return "instagram"
    @property
    def color(self) -> str: return "#E4405F"

    async def _get_token(self, user_id: str | None) -> str:
        if user_id:
            t = await social_oauth.get_access_token(user_id, "instagram")
            if t:
                return t
        return self._app_token

    async def get_feed(self, limit: int = 20, user_id: str | None = None) -> list[dict]:
        token = await self._get_token(user_id)
        if not token:
            return self._wrap_demo(self._demo_data())
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://graph.instagram.com/me/media",
                params={
                    "fields": "id,caption,media_type,media_url,thumbnail_url,timestamp,like_count,comments_count,permalink",
                    "access_token": token,
                    "limit": limit,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                return [
                    {
                        "platform": "instagram",
                        "id": post["id"],
                        "author": "You", "username": "@me", "avatar": "",
                        "content": post.get("caption", ""),
                        "timestamp": post.get("timestamp", ""),
                        "likes": post.get("like_count", 0),
                        "comments": post.get("comments_count", 0),
                        "shares": 0,
                        "media": [{"url": post.get("media_url", ""), "type": post.get("media_type", "IMAGE")}],
                        "url": post.get("permalink", ""),
                    }
                    for post in data.get("data", [])
                ]
        return []

    def _demo_data(self) -> list[dict]:
        return [
            {"author": "National Geographic", "username": "@natgeo", "content": "The Northern Lights paint the sky in vivid colors over Iceland 🌌", "likes": 890000, "comments": 4200, "shares": 0},
            {"author": "NASA", "username": "@nasa", "content": "A stunning view of Earth from the ISS 🌍", "likes": 1200000, "comments": 8900, "shares": 0},
        ]


class LinkedInAdapter(SocialAdapter):
    def __init__(self, app_token: str):
        self._app_token = app_token

    @property
    def platform_id(self) -> str: return "linkedin"
    @property
    def name(self) -> str: return "LinkedIn"
    @property
    def is_configured(self) -> bool: return bool(self._app_token)
    @property
    def icon(self) -> str: return "linkedin"
    @property
    def color(self) -> str: return "#0A66C2"

    async def get_feed(self, limit: int = 20, user_id: str | None = None) -> list[dict]:
        # LinkedIn API requires approved Marketing Developer Platform access
        return self._wrap_demo(self._demo_data())

    def _demo_data(self) -> list[dict]:
        return [
            {"author": "Satya Nadella", "username": "Satya Nadella", "content": "Excited to share that we're pushing the boundaries of what AI can do for every organization. The era of the AI copilot is here.", "likes": 45000, "comments": 3200, "shares": 8900},
            {"author": "Reid Hoffman", "username": "Reid Hoffman", "content": "The best founders I know are constantly learning. They read voraciously, ask questions relentlessly.", "likes": 12000, "comments": 890, "shares": 2100},
        ]


class RedditAdapter(SocialAdapter):
    def __init__(self, client_id: str, client_secret: str):
        self._client_id = client_id
        self._client_secret = client_secret

    @property
    def platform_id(self) -> str: return "reddit"
    @property
    def name(self) -> str: return "Reddit"
    @property
    def is_configured(self) -> bool: return bool(self._client_id)
    @property
    def icon(self) -> str: return "message-circle"
    @property
    def color(self) -> str: return "#FF4500"

    async def get_feed(self, limit: int = 20, user_id: str | None = None) -> list[dict]:
        subs = ["technology", "programming", "worldnews"]
        sub_str = "+".join(subs)
        headers = {"User-Agent": "Volo/1.0"}

        if self._client_id:
            try:
                async with httpx.AsyncClient() as client:
                    auth_resp = await client.post(
                        "https://www.reddit.com/api/v1/access_token",
                        auth=(self._client_id, self._client_secret),
                        data={"grant_type": "client_credentials"},
                        headers=headers,
                    )
                    if auth_resp.status_code == 200:
                        token = auth_resp.json().get("access_token")
                        headers["Authorization"] = f"Bearer {token}"
            except Exception:
                pass

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"https://www.reddit.com/r/{sub_str}/hot.json",
                    params={"limit": limit},
                    headers=headers,
                    timeout=10.0,
                )
                if resp.status_code == 200:
                    posts = []
                    for child in resp.json().get("data", {}).get("children", []):
                        post = child.get("data", {})
                        posts.append({
                            "platform": "reddit",
                            "id": post.get("id", ""),
                            "author": post.get("author", ""),
                            "username": f"u/{post.get('author', '')}",
                            "avatar": "",
                            "content": post.get("title", ""),
                            "body": post.get("selftext", "")[:500],
                            "timestamp": datetime.fromtimestamp(post.get("created_utc", 0), tz=timezone.utc).isoformat(),
                            "likes": post.get("ups", 0),
                            "comments": post.get("num_comments", 0),
                            "shares": 0,
                            "subreddit": post.get("subreddit", ""),
                            "media": [{"url": post["url"], "type": "link"}] if post.get("url") else [],
                            "url": f"https://reddit.com{post.get('permalink', '')}",
                        })
                    return posts
        except Exception:
            pass
        return self._wrap_demo(self._demo_data())

    def _demo_data(self) -> list[dict]:
        return [
            {"author": "tech_enthusiast", "username": "u/tech_enthusiast", "content": "Just built my first AI agent that manages my entire digital life", "subreddit": "programming", "likes": 4200, "comments": 380, "shares": 0},
            {"author": "curious_dev", "username": "u/curious_dev", "content": "What's your favorite developer tool of 2026?", "subreddit": "technology", "likes": 1800, "comments": 650, "shares": 0},
        ]


class TikTokAdapter(SocialAdapter):
    def __init__(self, app_token: str):
        self._app_token = app_token

    @property
    def platform_id(self) -> str: return "tiktok"
    @property
    def name(self) -> str: return "TikTok"
    @property
    def is_configured(self) -> bool: return bool(self._app_token)
    @property
    def icon(self) -> str: return "music"
    @property
    def color(self) -> str: return "#000000"

    async def _get_token(self, user_id: str | None) -> str:
        if user_id:
            t = await social_oauth.get_access_token(user_id, "tiktok")
            if t:
                return t
        return self._app_token

    async def get_feed(self, limit: int = 20, user_id: str | None = None) -> list[dict]:
        token = await self._get_token(user_id)
        if not token:
            return self._wrap_demo(self._demo_data())
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://open.tiktokapis.com/v2/video/list/",
                json={"max_count": limit},
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            )
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                posts = []
                for video in data.get("videos", []):
                    posts.append({
                        "platform": "tiktok",
                        "id": video.get("id", ""),
                        "author": "You", "username": "", "avatar": "",
                        "content": video.get("title", ""),
                        "timestamp": datetime.fromtimestamp(video.get("create_time", 0), tz=timezone.utc).isoformat() if video.get("create_time") else "",
                        "likes": video.get("like_count", 0),
                        "comments": video.get("comment_count", 0),
                        "shares": video.get("share_count", 0),
                        "media": [{"url": video.get("cover_image_url", ""), "type": "video"}],
                        "url": video.get("share_url", ""),
                    })
                return posts
        return self._wrap_demo(self._demo_data())

    def _demo_data(self) -> list[dict]:
        return [
            {"author": "CodeWithMe", "username": "@codewithme", "content": "POV: Your AI assistant just automated your entire morning routine 🤖✨ #tech #ai #productivity", "likes": 120000, "comments": 5400, "shares": 28000},
        ]


class FacebookAdapter(SocialAdapter):
    def __init__(self, app_token: str):
        self._app_token = app_token

    @property
    def platform_id(self) -> str: return "facebook"
    @property
    def name(self) -> str: return "Facebook"
    @property
    def is_configured(self) -> bool: return bool(self._app_token)
    @property
    def icon(self) -> str: return "facebook"
    @property
    def color(self) -> str: return "#1877F2"

    async def _get_token(self, user_id: str | None) -> str:
        if user_id:
            t = await social_oauth.get_access_token(user_id, "facebook")
            if t:
                return t
        return self._app_token

    async def get_feed(self, limit: int = 20, user_id: str | None = None) -> list[dict]:
        token = await self._get_token(user_id)
        if not token:
            return self._wrap_demo(self._demo_data())
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://graph.facebook.com/v18.0/me/feed",
                params={
                    "fields": "id,message,created_time,likes.summary(true),comments.summary(true),full_picture,permalink_url",
                    "access_token": token,
                    "limit": limit,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                return [
                    {
                        "platform": "facebook",
                        "id": post["id"],
                        "author": "You", "username": "", "avatar": "",
                        "content": post.get("message", ""),
                        "timestamp": post.get("created_time", ""),
                        "likes": post.get("likes", {}).get("summary", {}).get("total_count", 0),
                        "comments": post.get("comments", {}).get("summary", {}).get("total_count", 0),
                        "shares": 0,
                        "media": [{"url": post["full_picture"], "type": "image"}] if post.get("full_picture") else [],
                        "url": post.get("permalink_url", ""),
                    }
                    for post in data.get("data", [])
                ]
        return []

    def _demo_data(self) -> list[dict]:
        return [
            {"author": "Mark Zuckerberg", "username": "Mark Zuckerberg", "content": "Excited about the future of mixed reality and the ways it will bring people together.", "likes": 180000, "comments": 12000, "shares": 25000},
        ]


# ── Aggregator ────────────────────────────────────────────────────────────────

class SocialFeedService:
    """Unified social feed aggregator — iterates over registered SocialAdapters."""

    def __init__(self):
        self._adapters: list[SocialAdapter] = [
            TwitterAdapter(app_token=os.getenv("TWITTER_BEARER_TOKEN", "")),
            InstagramAdapter(app_token=os.getenv("INSTAGRAM_TOKEN", "")),
            LinkedInAdapter(app_token=os.getenv("LINKEDIN_TOKEN", "")),
            RedditAdapter(
                client_id=os.getenv("REDDIT_CLIENT_ID", ""),
                client_secret=os.getenv("REDDIT_CLIENT_SECRET", ""),
            ),
            TikTokAdapter(app_token=os.getenv("TIKTOK_TOKEN", "")),
            FacebookAdapter(app_token=os.getenv("FACEBOOK_TOKEN", "")),
        ]
        self._by_id: dict[str, SocialAdapter] = {a.platform_id: a for a in self._adapters}

    async def get_unified_feed(self, platforms: list[str] | None = None, user_id: str | None = None) -> list[dict]:
        target = platforms or [a.platform_id for a in self._adapters]
        all_posts: list[dict] = []
        for pid in target:
            adapter = self._by_id.get(pid)
            if adapter:
                posts = await adapter.get_feed(user_id=user_id)
                all_posts.extend(posts)
        all_posts.sort(key=lambda p: p.get("timestamp", ""), reverse=True)
        return all_posts

    async def get_connected_platforms(self, user_id: str | None = None) -> list[dict]:
        user_status: dict[str, dict] = {}
        if user_id:
            user_status = await social_oauth.get_connection_status(user_id)
        return [
            a.to_status_dict(user_connected=user_status.get(a.platform_id, {}).get("connected", False))
            for a in self._adapters
        ]

    # ── Per-platform delegation (backwards-compat for existing route handlers) ─

    async def twitter_timeline(self, limit: int = 20, user_id: str | None = None) -> list[dict]:
        return await self._by_id["twitter"].get_feed(limit, user_id)

    async def instagram_feed(self, limit: int = 20, user_id: str | None = None) -> list[dict]:
        return await self._by_id["instagram"].get_feed(limit, user_id)

    async def linkedin_feed(self, limit: int = 20, user_id: str | None = None) -> list[dict]:
        return await self._by_id["linkedin"].get_feed(limit, user_id)

    async def reddit_feed(self, subreddits: list[str] | None = None, limit: int = 20, user_id: str | None = None) -> list[dict]:
        return await self._by_id["reddit"].get_feed(limit, user_id)

    async def tiktok_feed(self, limit: int = 20, user_id: str | None = None) -> list[dict]:
        return await self._by_id["tiktok"].get_feed(limit, user_id)

    async def facebook_feed(self, limit: int = 20, user_id: str | None = None) -> list[dict]:
        return await self._by_id["facebook"].get_feed(limit, user_id)
