"""
VOLO — Notification Service
In-app notifications, push notifications, email alerts.
"""

import uuid
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger("volo.notifications")


class NotificationService:
    """Manages notifications across channels."""

    def __init__(self):
        # In-memory store (DB in production)
        self._notifications: list[dict] = []

    async def create(
        self,
        user_id: str,
        type: str,
        title: str,
        body: str = "",
        data: dict = None,
    ) -> dict:
        notification = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "type": type,
            "title": title,
            "body": body,
            "data": data or {},
            "read": False,
            "created_at": datetime.utcnow().isoformat(),
        }
        self._notifications.append(notification)
        return notification

    async def list_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        limit: int = 50,
    ) -> list[dict]:
        results = [n for n in self._notifications if n["user_id"] == user_id]
        if unread_only:
            results = [n for n in results if not n["read"]]
        return list(reversed(results))[:limit]

    async def mark_read(self, notification_id: str) -> bool:
        for n in self._notifications:
            if n["id"] == notification_id:
                n["read"] = True
                return True
        return False

    async def mark_all_read(self, user_id: str) -> int:
        count = 0
        for n in self._notifications:
            if n["user_id"] == user_id and not n["read"]:
                n["read"] = True
                count += 1
        return count

    async def delete(self, notification_id: str) -> bool:
        before = len(self._notifications)
        self._notifications = [n for n in self._notifications if n["id"] != notification_id]
        return len(self._notifications) < before

    async def get_unread_count(self, user_id: str) -> int:
        return sum(
            1 for n in self._notifications
            if n["user_id"] == user_id and not n["read"]
        )


# Singleton
notifications = NotificationService()
