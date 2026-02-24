"""
VOLO — Redis Cache Service
Provides caching, pub/sub, and session management.
Falls back gracefully when Redis is unavailable.
"""

import json
import logging
from typing import Optional, Any

from app.config import settings

logger = logging.getLogger("volo.cache")


class CacheService:
    """
    Redis-backed cache with graceful fallback to in-memory.
    """

    def __init__(self):
        self._redis = None
        self._connected = False
        self._fallback: dict[str, Any] = {}

    async def connect(self):
        """Try to connect to Redis."""
        try:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            await self._redis.ping()
            self._connected = True
            logger.info("✅ Redis connected")
        except Exception as e:
            logger.warning(f"⚠️  Redis unavailable, using in-memory fallback: {e}")
            self._connected = False

    async def close(self):
        if self._redis:
            await self._redis.close()

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def get(self, key: str) -> Optional[str]:
        if self._connected:
            try:
                return await self._redis.get(key)
            except Exception:
                pass
        return self._fallback.get(key)

    async def set(self, key: str, value: str, ttl: int = 3600) -> bool:
        if self._connected:
            try:
                await self._redis.set(key, value, ex=ttl)
                return True
            except Exception:
                pass
        self._fallback[key] = value
        return True

    async def delete(self, key: str) -> bool:
        if self._connected:
            try:
                await self._redis.delete(key)
                return True
            except Exception:
                pass
        self._fallback.pop(key, None)
        return True

    async def get_json(self, key: str) -> Optional[Any]:
        raw = await self.get(key)
        if raw:
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                pass
        return None

    async def set_json(self, key: str, value: Any, ttl: int = 3600) -> bool:
        return await self.set(key, json.dumps(value), ttl)

    async def increment(self, key: str, amount: int = 1) -> int:
        if self._connected:
            try:
                return await self._redis.incr(key, amount)
            except Exception:
                pass
        val = int(self._fallback.get(key, 0)) + amount
        self._fallback[key] = str(val)
        return val

    async def expire(self, key: str, ttl: int) -> bool:
        if self._connected:
            try:
                await self._redis.expire(key, ttl)
                return True
            except Exception:
                pass
        return False

    # ── Pub/Sub ──────────────────────────────

    async def publish(self, channel: str, message: str):
        if self._connected:
            try:
                await self._redis.publish(channel, message)
            except Exception:
                pass

    # ── Session Management ───────────────────

    async def set_session(self, session_id: str, data: dict, ttl: int = 86400):
        await self.set_json(f"session:{session_id}", data, ttl)

    async def get_session(self, session_id: str) -> Optional[dict]:
        return await self.get_json(f"session:{session_id}")

    async def delete_session(self, session_id: str):
        await self.delete(f"session:{session_id}")


# Singleton
cache = CacheService()
