"""
VOLO — Platform Adapter Base Classes

Defines the contracts for messaging (MessagingAdapter) and social feed
(SocialAdapter) platform integrations.

Benefits over the old flat-method design:
- New platforms are a single self-contained class, no touching the aggregator
- get_connected_platforms() is auto-populated from registered adapters
- get_all_messages() / get_unified_feed() iterate over adapters uniformly
- Each adapter owns its demo data and connection-status metadata
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone


class MessagingAdapter(ABC):
    """Contract for a messaging platform (Telegram, Slack, etc.)."""

    @property
    @abstractmethod
    def platform_id(self) -> str:
        """Stable lowercase identifier used as the 'platform' field in messages."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable platform name."""

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """True when the adapter has valid credentials / API tokens."""

    @property
    def icon(self) -> str:
        return "message-circle"

    @property
    def color(self) -> str:
        return "#000000"

    @abstractmethod
    async def get_messages(self, limit: int = 50) -> list[dict]:
        """Return messages from this platform. Falls back to demo data when unconfigured."""

    async def send_message(self, to: str, text: str, **kwargs) -> dict:
        """Send a message. Override per platform; default returns not-supported."""
        return {"status": "not_supported", "platform": self.platform_id}

    @abstractmethod
    def _demo_data(self) -> list[dict]:
        """Platform-specific demo messages for the unconfigured state."""

    def _wrap_demo(self, entries: list[dict]) -> list[dict]:
        """Add common envelope fields to raw demo entries."""
        now = datetime.now(timezone.utc).isoformat()
        return [
            {
                "platform": self.platform_id,
                "id": f"demo-{self.platform_id}-{i}",
                "from": e["from"],
                "from_username": e.get("from_username", ""),
                "avatar": None,
                "content": e["content"],
                "timestamp": now,
                "chat_id": e.get("from_username", ""),
                "chat_title": e["from"],
                "read": i > 0,
                "type": "text",
                "_demo": True,
            }
            for i, e in enumerate(entries)
        ]

    def to_status_dict(self) -> dict:
        return {
            "id": self.platform_id,
            "name": self.name,
            "connected": self.is_configured,
            "icon": self.icon,
            "color": self.color,
        }


class SocialAdapter(ABC):
    """Contract for a social feed platform (Twitter, Instagram, etc.)."""

    @property
    @abstractmethod
    def platform_id(self) -> str:
        """Stable lowercase identifier."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable platform name."""

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """True when the adapter has app-level credentials (user-level may still be None)."""

    @property
    def icon(self) -> str:
        return "globe"

    @property
    def color(self) -> str:
        return "#000000"

    @abstractmethod
    async def get_feed(self, limit: int = 20, user_id: str | None = None) -> list[dict]:
        """Return posts from this platform. Falls back to demo data when unconfigured."""

    @abstractmethod
    def _demo_data(self) -> list[dict]:
        """Platform-specific demo posts for the unconfigured state."""

    def _wrap_demo(self, entries: list[dict]) -> list[dict]:
        """Add common envelope fields to raw demo entries."""
        now = datetime.now(timezone.utc).isoformat()
        return [
            {
                "platform": self.platform_id,
                "id": f"demo-{self.platform_id}-{i}",
                "author": e["author"],
                "username": e["username"],
                "avatar": "",
                "content": e["content"],
                "timestamp": now,
                "likes": e.get("likes", 0),
                "comments": e.get("comments", 0),
                "shares": e.get("shares", 0),
                "subreddit": e.get("subreddit", ""),
                "media": [],
                "url": "",
                "_demo": True,
            }
            for i, e in enumerate(entries)
        ]

    def to_status_dict(self, user_connected: bool = False) -> dict:
        return {
            "id": self.platform_id,
            "name": self.name,
            "connected": user_connected or self.is_configured,
            "icon": self.icon,
            "color": self.color,
        }
