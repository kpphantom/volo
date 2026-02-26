"""
VOLO — Redis Cache Service
Provides caching, pub/sub, and session management.
Falls back gracefully when Redis is unavailable.
"""

import json
import time
import logging
from collections import OrderedDict
from typing import Optional, Any

from app.config import settings

logger = logging.getLogger("volo.cache")

_FALLBACK_MAX_KEYS = 10_000


class _FallbackCache:
    """
    Bounded LRU dict with per-key TTL.
    Used only when Redis is unavailable.
    Caps at _FALLBACK_MAX_KEYS entries; evicts LRU when full.
    """

    def __init__(self, maxsize: int = _FALLBACK_MAX_KEYS):
        self._maxsize = maxsize
        self._data: OrderedDict[str, tuple[Any, Optional[float]]] = OrderedDict()

    def get(self, key: str) -> Optional[Any]:
        entry = self._data.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if expires_at is not None and time.monotonic() > expires_at:
            del self._data[key]
            return None
        # Move to end (most-recently-used)
        self._data.move_to_end(key)
        return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        expires_at = time.monotonic() + ttl if ttl is not None else None
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = (value, expires_at)
        while len(self._data) > self._maxsize:
            self._data.popitem(last=False)  # evict LRU

    def incr(self, key: str, amount: int = 1) -> int:
        existing = self.get(key)
        new_val = (int(existing) if existing is not None else 0) + amount
        # Preserve existing TTL by fetching raw entry
        raw = self._data.get(key)
        expires_at = raw[1] if raw is not None else None
        self._data[key] = (str(new_val), expires_at)
        if key in self._data:
            self._data.move_to_end(key)
        return new_val

    def expire(self, key: str, ttl: int) -> None:
        raw = self._data.get(key)
        if raw is not None:
            self._data[key] = (raw[0], time.monotonic() + ttl)

    def delete(self, key: str) -> None:
        self._data.pop(key, None)


class CacheService:
    """
    Redis-backed cache with graceful fallback to in-memory.
    """

    def __init__(self):
        self._redis = None
        self._connected = False
        self._fallback = _FallbackCache()

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
        self._fallback.set(key, value, ttl)
        return True

    async def delete(self, key: str) -> bool:
        if self._connected:
            try:
                await self._redis.delete(key)
                return True
            except Exception:
                pass
        self._fallback.delete(key)
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
        return self._fallback.incr(key, amount)

    async def expire(self, key: str, ttl: int) -> bool:
        if self._connected:
            try:
                await self._redis.expire(key, ttl)
                return True
            except Exception:
                pass
        self._fallback.expire(key, ttl)
        return True

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
