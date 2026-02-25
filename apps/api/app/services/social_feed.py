"""
VOLO — Unified Social Feed Service
Aggregates content from Twitter/X, Instagram, LinkedIn, TikTok, Reddit, Facebook.
Uses per-user OAuth tokens when available, falls back to app-level tokens or demo data.
"""

import os
import httpx
from datetime import datetime, timezone

from app.services.social_oauth import social_oauth


class SocialFeedService:
    """Unified social feed aggregator across all platforms."""

    def __init__(self):
        # App-level fallback tokens (from env)
        self.twitter_token = os.getenv("TWITTER_BEARER_TOKEN", "")
        self.instagram_token = os.getenv("INSTAGRAM_TOKEN", "")
        self.linkedin_token = os.getenv("LINKEDIN_TOKEN", "")
        self.reddit_client_id = os.getenv("REDDIT_CLIENT_ID", "")
        self.reddit_client_secret = os.getenv("REDDIT_CLIENT_SECRET", "")
        self.tiktok_token = os.getenv("TIKTOK_TOKEN", "")
        self.facebook_token = os.getenv("FACEBOOK_TOKEN", "")

    async def _get_token(self, user_id: str | None, platform: str, fallback: str) -> str:
        """Get user-specific token or fall back to app-level token."""
        if user_id:
            user_token = await social_oauth.get_access_token(user_id, platform)
            if user_token:
                return user_token
        return fallback

    # ── Twitter/X ───────────────────────────────────────────────────────

    async def twitter_timeline(self, limit: int = 20, user_id: str | None = None) -> list[dict]:
        """Get home timeline from Twitter/X."""
        token = await self._get_token(user_id, "twitter", self.twitter_token)
        if not token:
            return self._demo_posts("twitter")

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.twitter.com/2/users/me/timelines/reverse_chronological",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "max_results": limit,
                    "tweet.fields": "created_at,public_metrics,author_id",
                    "expansions": "author_id",
                    "user.fields": "name,username,profile_image_url",
                },
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
        return []

    # ── Instagram ───────────────────────────────────────────────────────

    async def instagram_feed(self, limit: int = 20, user_id: str | None = None) -> list[dict]:
        """Get Instagram feed."""
        token = await self._get_token(user_id, "instagram", self.instagram_token)
        if not token:
            return self._demo_posts("instagram")

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
                        "author": "You",
                        "username": "@me",
                        "avatar": "",
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

    # ── LinkedIn ────────────────────────────────────────────────────────

    async def linkedin_feed(self, limit: int = 20, user_id: str | None = None) -> list[dict]:
        """Get LinkedIn feed."""
        token = await self._get_token(user_id, "linkedin", self.linkedin_token)
        if not token:
            return self._demo_posts("linkedin")
        # LinkedIn API is restrictive — requires approved marketing developer platform
        return self._demo_posts("linkedin")

    # ── Reddit ──────────────────────────────────────────────────────────

    async def reddit_feed(self, subreddits: list[str] | None = None, limit: int = 20, user_id: str | None = None) -> list[dict]:
        """Get Reddit front page or specific subreddit posts."""
        subs = subreddits or ["technology", "programming", "worldnews"]
        sub_str = "+".join(subs)

        headers = {"User-Agent": "Volo/1.0"}

        # Try authenticated if we have creds
        if self.reddit_client_id:
            try:
                async with httpx.AsyncClient() as client:
                    auth_resp = await client.post(
                        "https://www.reddit.com/api/v1/access_token",
                        auth=(self.reddit_client_id, self.reddit_client_secret),
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
                    data = resp.json()
                    posts = []
                    for child in data.get("data", {}).get("children", []):
                        post = child.get("data", {})
                        posts.append({
                            "platform": "reddit",
                            "id": post.get("id", ""),
                            "author": post.get("author", ""),
                            "username": f"u/{post.get('author', '')}",
                            "avatar": "",
                            "content": post.get("title", ""),
                            "body": post.get("selftext", "")[:500],
                            "timestamp": datetime.fromtimestamp(
                                post.get("created_utc", 0), tz=timezone.utc
                            ).isoformat(),
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
        return self._demo_posts("reddit")

    # ── TikTok ──────────────────────────────────────────────────────────

    async def tiktok_feed(self, limit: int = 20, user_id: str | None = None) -> list[dict]:
        """Get TikTok feed."""
        token = await self._get_token(user_id, "tiktok", self.tiktok_token)
        if not token:
            return self._demo_posts("tiktok")

        # TikTok API: fetch user's posted videos
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://open.tiktokapis.com/v2/video/list/",
                json={"max_count": limit},
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                posts = []
                for video in data.get("videos", []):
                    posts.append({
                        "platform": "tiktok",
                        "id": video.get("id", ""),
                        "author": "You",
                        "username": "",
                        "avatar": "",
                        "content": video.get("title", ""),
                        "timestamp": datetime.fromtimestamp(
                            video.get("create_time", 0), tz=timezone.utc
                        ).isoformat() if video.get("create_time") else "",
                        "likes": video.get("like_count", 0),
                        "comments": video.get("comment_count", 0),
                        "shares": video.get("share_count", 0),
                        "media": [{"url": video.get("cover_image_url", ""), "type": "video"}],
                        "url": video.get("share_url", ""),
                    })
                return posts
        return self._demo_posts("tiktok")

    # ── Facebook ────────────────────────────────────────────────────────

    async def facebook_feed(self, limit: int = 20, user_id: str | None = None) -> list[dict]:
        """Get Facebook feed."""
        token = await self._get_token(user_id, "facebook", self.facebook_token)
        if not token:
            return self._demo_posts("facebook")

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
                        "author": "You",
                        "username": "",
                        "avatar": "",
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

    # ── Unified Feed ────────────────────────────────────────────────────

    async def get_unified_feed(self, platforms: list[str] | None = None, user_id: str | None = None) -> list[dict]:
        """Get posts from all platforms, merged and sorted."""
        target = platforms or ["twitter", "instagram", "linkedin", "reddit", "tiktok", "facebook"]
        all_posts: list[dict] = []

        fetchers = {
            "twitter": lambda: self.twitter_timeline(user_id=user_id),
            "instagram": lambda: self.instagram_feed(user_id=user_id),
            "linkedin": lambda: self.linkedin_feed(user_id=user_id),
            "reddit": lambda: self.reddit_feed(user_id=user_id),
            "tiktok": lambda: self.tiktok_feed(user_id=user_id),
            "facebook": lambda: self.facebook_feed(user_id=user_id),
        }

        for platform in target:
            if platform in fetchers:
                posts = await fetchers[platform]()
                all_posts.extend(posts)

        all_posts.sort(key=lambda p: p.get("timestamp", ""), reverse=True)
        return all_posts

    async def get_connected_platforms(self, user_id: str | None = None) -> list[dict]:
        """Return which social platforms are connected."""
        # Check user-specific connections
        user_status = {}
        if user_id:
            user_status = await social_oauth.get_connection_status(user_id)

        return [
            {"id": "twitter", "name": "Twitter / X", "connected": user_status.get("twitter", {}).get("connected", False) or bool(self.twitter_token), "icon": "twitter", "color": "#1DA1F2"},
            {"id": "instagram", "name": "Instagram", "connected": user_status.get("instagram", {}).get("connected", False) or bool(self.instagram_token), "icon": "instagram", "color": "#E4405F"},
            {"id": "linkedin", "name": "LinkedIn", "connected": user_status.get("linkedin", {}).get("connected", False) or bool(self.linkedin_token), "icon": "linkedin", "color": "#0A66C2"},
            {"id": "reddit", "name": "Reddit", "connected": user_status.get("reddit", {}).get("connected", False) or bool(self.reddit_client_id), "icon": "message-circle", "color": "#FF4500"},
            {"id": "tiktok", "name": "TikTok", "connected": user_status.get("tiktok", {}).get("connected", False) or bool(self.tiktok_token), "icon": "music", "color": "#000000"},
            {"id": "facebook", "name": "Facebook", "connected": user_status.get("facebook", {}).get("connected", False) or bool(self.facebook_token), "icon": "facebook", "color": "#1877F2"},
        ]

    # ── Demo Data ───────────────────────────────────────────────────────

    def _demo_posts(self, platform: str) -> list[dict]:
        now = datetime.now(timezone.utc).isoformat()
        demos: dict[str, list[dict]] = {
            "twitter": [
                {"author": "Elon Musk", "username": "@elonmusk", "content": "The future is closer than you think 🚀", "likes": 42000, "comments": 8500, "shares": 12000},
                {"author": "Naval", "username": "@naval", "content": "Specific knowledge is found by pursuing your genuine curiosity and passion.", "likes": 15000, "comments": 2100, "shares": 5400},
                {"author": "Sam Altman", "username": "@sama", "content": "AI will be the most transformative technology in human history.", "likes": 28000, "comments": 6200, "shares": 9100},
            ],
            "instagram": [
                {"author": "National Geographic", "username": "@natgeo", "content": "The Northern Lights paint the sky in vivid colors over Iceland 🌌", "likes": 890000, "comments": 4200, "shares": 0},
                {"author": "NASA", "username": "@nasa", "content": "A stunning view of Earth from the ISS 🌍", "likes": 1200000, "comments": 8900, "shares": 0},
            ],
            "linkedin": [
                {"author": "Satya Nadella", "username": "Satya Nadella", "content": "Excited to share that we're pushing the boundaries of what AI can do for every organization. The era of the AI copilot is here.", "likes": 45000, "comments": 3200, "shares": 8900},
                {"author": "Reid Hoffman", "username": "Reid Hoffman", "content": "The best founders I know are constantly learning. They read voraciously, ask questions relentlessly.", "likes": 12000, "comments": 890, "shares": 2100},
            ],
            "reddit": [
                {"author": "tech_enthusiast", "username": "u/tech_enthusiast", "content": "Just built my first AI agent that manages my entire digital life", "subreddit": "programming", "likes": 4200, "comments": 380, "shares": 0},
                {"author": "curious_dev", "username": "u/curious_dev", "content": "What's your favorite developer tool of 2026?", "subreddit": "technology", "likes": 1800, "comments": 650, "shares": 0},
            ],
            "tiktok": [
                {"author": "CodeWithMe", "username": "@codewithme", "content": "POV: Your AI assistant just automated your entire morning routine 🤖✨ #tech #ai #productivity", "likes": 120000, "comments": 5400, "shares": 28000},
            ],
            "facebook": [
                {"author": "Mark Zuckerberg", "username": "Mark Zuckerberg", "content": "Excited about the future of mixed reality and the ways it will bring people together.", "likes": 180000, "comments": 12000, "shares": 25000},
            ],
        }

        return [
            {
                "platform": platform,
                "id": f"demo-{platform}-{i}",
                "author": post["author"],
                "username": post["username"],
                "avatar": "",
                "content": post["content"],
                "timestamp": now,
                "likes": post.get("likes", 0),
                "comments": post.get("comments", 0),
                "shares": post.get("shares", 0),
                "subreddit": post.get("subreddit", ""),
                "media": [],
                "url": "",
                "_demo": True,
            }
            for i, post in enumerate(demos.get(platform, []))
        ]
