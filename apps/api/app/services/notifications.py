"""
VOLO — Notification Service
Persistent notification storage in PostgreSQL.
"""

import logging
from datetime import datetime
from typing import Optional
from sqlalchemy import select, func

from app.database import async_session, Notification

logger = logging.getLogger("volo.notifications")


class NotificationService:
    """Manages notifications with DB persistence."""

    async def create(
        self,
        user_id: str,
        type: str,
        title: str,
        body: str = "",
        data: dict = None,
    ) -> dict:
        async with async_session() as session:
            notif = Notification(
                user_id=user_id,
                type=type,
                title=title,
                body=body or "",
                data=data or {},
            )
            session.add(notif)
            await session.commit()
            await session.refresh(notif)

            return self._to_dict(notif)

    async def list_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        limit: int = 50,
    ) -> list[dict]:
        async with async_session() as session:
            q = select(Notification).where(Notification.user_id == user_id)
            if unread_only:
                q = q.where(Notification.read == False)
            q = q.order_by(Notification.created_at.desc()).limit(limit)

            result = await session.execute(q)
            return [self._to_dict(n) for n in result.scalars().all()]

    async def mark_read(self, notification_id: str) -> bool:
        async with async_session() as session:
            result = await session.execute(
                select(Notification).where(Notification.id == notification_id)
            )
            n = result.scalar_one_or_none()
            if n:
                n.read = True
                await session.commit()
                return True
        return False

    async def mark_all_read(self, user_id: str) -> int:
        async with async_session() as session:
            result = await session.execute(
                select(Notification).where(
                    Notification.user_id == user_id,
                    Notification.read == False,
                )
            )
            notifications = result.scalars().all()
            count = 0
            for n in notifications:
                n.read = True
                count += 1
            await session.commit()
            return count

    async def delete(self, notification_id: str) -> bool:
        async with async_session() as session:
            result = await session.execute(
                select(Notification).where(Notification.id == notification_id)
            )
            n = result.scalar_one_or_none()
            if n:
                await session.delete(n)
                await session.commit()
                return True
        return False

    async def get_unread_count(self, user_id: str) -> int:
        async with async_session() as session:
            result = await session.execute(
                select(func.count()).select_from(
                    select(Notification).where(
                        Notification.user_id == user_id,
                        Notification.read == False,
                    ).subquery()
                )
            )
            return result.scalar() or 0

    @staticmethod
    def _to_dict(n) -> dict:
        return {
            "id": n.id,
            "user_id": n.user_id,
            "type": n.type,
            "title": n.title,
            "body": n.body,
            "data": n.data,
            "read": n.read,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }


# Singleton
notifications = NotificationService()
