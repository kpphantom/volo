"""
VOLO — Social Media Service
Twitter/X, LinkedIn integration for content management.
"""

import os
import logging
from typing import Optional
import httpx

logger = logging.getLogger("volo.social")


class SocialService:
    """Handles social media operations across platforms."""

    TWITTER_BASE = "https://api.twitter.com/2"
    LINKEDIN_BASE = "https://api.linkedin.com/v2"

    def __init__(self):
        self.twitter_bearer = os.getenv("TWITTER_API_KEY", "")
        self.linkedin_token = os.getenv("LINKEDIN_ACCESS_TOKEN", "")
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    # ── Twitter / X ──────────────────────────

    async def twitter_post(self, text: str) -> dict:
        if not self.twitter_bearer:
            return {"error": "Twitter not connected. Add TWITTER_API_KEY to connect."}

        client = await self._get_client()
        resp = await client.post(
            f"{self.TWITTER_BASE}/tweets",
            headers={"Authorization": f"Bearer {self.twitter_bearer}"},
            json={"text": text},
        )

        if resp.status_code in (200, 201):
            data = resp.json()
            return {
                "success": True,
                "platform": "twitter",
                "tweet_id": data.get("data", {}).get("id"),
                "text": text,
            }
        return {"error": f"Twitter API error: {resp.status_code}"}

    async def twitter_mentions(self, user_id: str = "me", limit: int = 20) -> dict:
        if not self.twitter_bearer:
            return {"error": "Twitter not connected."}

        client = await self._get_client()
        resp = await client.get(
            f"{self.TWITTER_BASE}/users/{user_id}/mentions",
            headers={"Authorization": f"Bearer {self.twitter_bearer}"},
            params={"max_results": min(limit, 100)},
        )

        if resp.status_code == 200:
            data = resp.json()
            return {
                "mentions": [
                    {"id": t["id"], "text": t["text"]}
                    for t in data.get("data", [])
                ],
                "total": data.get("meta", {}).get("result_count", 0),
            }
        return {"error": f"Twitter API error: {resp.status_code}"}

    # ── LinkedIn ─────────────────────────────

    async def linkedin_post(self, text: str, author_urn: str = "") -> dict:
        if not self.linkedin_token:
            return {"error": "LinkedIn not connected. Add LINKEDIN_ACCESS_TOKEN."}

        client = await self._get_client()
        payload = {
            "author": author_urn or "urn:li:person:me",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }

        resp = await client.post(
            f"{self.LINKEDIN_BASE}/ugcPosts",
            headers={
                "Authorization": f"Bearer {self.linkedin_token}",
                "X-Restli-Protocol-Version": "2.0.0",
            },
            json=payload,
        )

        if resp.status_code in (200, 201):
            return {"success": True, "platform": "linkedin", "post_id": resp.headers.get("x-restli-id", "")}
        return {"error": f"LinkedIn API error: {resp.status_code}"}

    # ── Cross-platform ───────────────────────

    async def post_to_all(self, text: str) -> dict:
        """Post content to all connected platforms."""
        results = {}
        if self.twitter_bearer:
            results["twitter"] = await self.twitter_post(text)
        if self.linkedin_token:
            results["linkedin"] = await self.linkedin_post(text)

        if not results:
            return {"error": "No social media platforms connected."}
        return {"results": results, "platforms_posted": len(results)}

    async def get_analytics(self) -> dict:
        """Get engagement analytics across platforms."""
        return {
            "twitter": {"connected": bool(self.twitter_bearer)},
            "linkedin": {"connected": bool(self.linkedin_token)},
            "message": "Connect platforms to see engagement analytics.",
        }
