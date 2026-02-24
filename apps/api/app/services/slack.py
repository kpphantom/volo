"""
VOLO — Slack Service
Slack bot integration for messaging, channel management, and notifications.
"""

import os
import logging
from typing import Optional
import httpx

logger = logging.getLogger("volo.slack")


class SlackService:
    """Handles Slack API operations."""

    BASE_URL = "https://slack.com/api"

    def __init__(self):
        self.bot_token = os.getenv("SLACK_BOT_TOKEN", "")
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    @property
    def headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.bot_token}",
            "Content-Type": "application/json; charset=utf-8",
        }

    def _check_auth(self) -> Optional[dict]:
        if not self.bot_token:
            return {
                "error": "Slack not connected.",
                "message": "Add SLACK_BOT_TOKEN to connect Slack.",
            }
        return None

    async def list_channels(self, limit: int = 50) -> dict:
        err = self._check_auth()
        if err:
            return err

        client = await self._get_client()
        resp = await client.get(
            f"{self.BASE_URL}/conversations.list",
            headers=self.headers,
            params={"limit": limit, "types": "public_channel,private_channel"},
        )
        data = resp.json()
        if not data.get("ok"):
            return {"error": data.get("error", "Unknown Slack error")}

        return {
            "channels": [
                {
                    "id": ch["id"],
                    "name": ch["name"],
                    "is_private": ch.get("is_private", False),
                    "num_members": ch.get("num_members", 0),
                    "topic": ch.get("topic", {}).get("value", ""),
                }
                for ch in data.get("channels", [])
            ]
        }

    async def send_message(
        self,
        channel: str,
        text: str,
        thread_ts: Optional[str] = None,
    ) -> dict:
        err = self._check_auth()
        if err:
            return err

        client = await self._get_client()
        payload = {"channel": channel, "text": text}
        if thread_ts:
            payload["thread_ts"] = thread_ts

        resp = await client.post(
            f"{self.BASE_URL}/chat.postMessage",
            headers=self.headers,
            json=payload,
        )
        data = resp.json()
        if not data.get("ok"):
            return {"error": data.get("error", "Failed to send message")}

        return {
            "success": True,
            "channel": channel,
            "ts": data.get("ts"),
            "message": data.get("message", {}).get("text", ""),
        }

    async def get_thread(self, channel: str, thread_ts: str) -> dict:
        err = self._check_auth()
        if err:
            return err

        client = await self._get_client()
        resp = await client.get(
            f"{self.BASE_URL}/conversations.replies",
            headers=self.headers,
            params={"channel": channel, "ts": thread_ts},
        )
        data = resp.json()
        if not data.get("ok"):
            return {"error": data.get("error", "Failed to get thread")}

        return {
            "messages": [
                {
                    "user": m.get("user", ""),
                    "text": m.get("text", ""),
                    "ts": m.get("ts", ""),
                }
                for m in data.get("messages", [])
            ]
        }

    async def search_messages(self, query: str, count: int = 20) -> dict:
        err = self._check_auth()
        if err:
            return err

        client = await self._get_client()
        resp = await client.get(
            f"{self.BASE_URL}/search.messages",
            headers=self.headers,
            params={"query": query, "count": count},
        )
        data = resp.json()
        if not data.get("ok"):
            return {"error": data.get("error", "Search failed")}

        matches = data.get("messages", {}).get("matches", [])
        return {
            "results": [
                {
                    "text": m.get("text", ""),
                    "user": m.get("username", ""),
                    "channel": m.get("channel", {}).get("name", ""),
                    "ts": m.get("ts", ""),
                    "permalink": m.get("permalink", ""),
                }
                for m in matches
            ],
            "total": data.get("messages", {}).get("total", 0),
        }
