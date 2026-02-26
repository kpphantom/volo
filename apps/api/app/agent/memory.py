"""
VOLO — Memory Manager
Persistent memory storage in PostgreSQL.
The agent never forgets — memories survive restarts.
"""

import json
from typing import Optional
from datetime import datetime
from sqlalchemy import select

from app.database import async_session, Memory
from app.services.cache import cache


class MemoryManager:
    """Manages the agent's long-term memory backed by PostgreSQL."""

    async def store(
        self,
        user_id: str = "dev-user",
        category: str = "fact",
        content: str = "",
        source: str = "conversation",
        confidence: float = 1.0,
    ) -> dict:
        """Store a new memory."""
        async with async_session() as session:
            mem = Memory(
                user_id=user_id,
                category=category,
                content=content,
                source=source,
                confidence=confidence,
            )
            session.add(mem)
            await session.commit()
            await session.refresh(mem)

            return {
                "id": mem.id,
                "user_id": mem.user_id,
                "category": mem.category,
                "content": mem.content,
                "source": mem.source,
                "confidence": mem.confidence,
                "created_at": mem.created_at.isoformat() if mem.created_at else None,
                "last_accessed_at": mem.last_accessed_at.isoformat() if mem.last_accessed_at else None,
            }

    async def search(
        self,
        query: str,
        user_id: str = "dev-user",
        category: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict]:
        """Search memories by keyword match. (pgvector semantic search can be added later.)"""
        cache_key = f"memsearch:{user_id}:{category or ''}:{limit}:{query}"
        cached = await cache.get(cache_key)
        if cached is not None:
            try:
                return json.loads(cached)
            except Exception:
                pass

        async with async_session() as session:
            q = select(Memory).where(
                Memory.user_id == user_id,
                Memory.content.ilike(f"%{query}%"),
            )
            if category:
                q = q.where(Memory.category == category)
            q = q.limit(limit)

            result = await session.execute(q)
            memories = result.scalars().all()

            # Batch-update last_accessed_at in a single commit
            now = datetime.utcnow()
            for m in memories:
                m.last_accessed_at = now
            if memories:
                await session.commit()

            rows = [
                {
                    "id": m.id,
                    "user_id": m.user_id,
                    "category": m.category,
                    "content": m.content,
                    "source": m.source,
                    "confidence": m.confidence,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                    "last_accessed_at": m.last_accessed_at.isoformat() if m.last_accessed_at else None,
                }
                for m in memories
            ]

        await cache.set(cache_key, json.dumps(rows), ttl=60)
        return rows

    async def get_all(
        self,
        user_id: str = "dev-user",
        category: Optional[str] = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[dict]:
        """Get memories for a user with pagination (default page size 200)."""
        async with async_session() as session:
            q = (
                select(Memory)
                .where(Memory.user_id == user_id)
                .order_by(Memory.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            if category:
                q = q.where(Memory.category == category)

            result = await session.execute(q)
            return [
                {
                    "id": m.id,
                    "user_id": m.user_id,
                    "category": m.category,
                    "content": m.content,
                    "source": m.source,
                    "confidence": m.confidence,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                    "last_accessed_at": m.last_accessed_at.isoformat() if m.last_accessed_at else None,
                }
                for m in result.scalars().all()
            ]

    async def delete(self, memory_id: str) -> bool:
        """Delete a specific memory."""
        async with async_session() as session:
            result = await session.execute(
                select(Memory).where(Memory.id == memory_id)
            )
            mem = result.scalar_one_or_none()
            if mem:
                await session.delete(mem)
                await session.commit()
                return True
        return False

    async def clear_all(self, user_id: str = "dev-user") -> int:
        """Clear all memories for a user. Returns count deleted."""
        from sqlalchemy import delete as sa_delete, func

        async with async_session() as session:
            count_q = select(func.count()).select_from(
                select(Memory).where(Memory.user_id == user_id).subquery()
            )
            count = (await session.execute(count_q)).scalar() or 0

            await session.execute(
                sa_delete(Memory).where(Memory.user_id == user_id)
            )
            await session.commit()
            return count
