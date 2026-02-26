"""
VOLO — Middleware
Rate limiting, request logging, audit trail, error tracking.
"""

import asyncio
import time
import uuid
import logging
from datetime import datetime, timedelta
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("volo")


# ── Rate Limiter ─────────────────────────────

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis-backed rate limiter (shared across all workers)."""

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.rpm = requests_per_minute

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        import os
        if os.getenv("TESTING") == "1":
            return await call_next(request)
        if request.url.path in ("/health", "/", "/docs", "/openapi.json"):
            return await call_next(request)

        from app.services.cache import cache
        client_ip = request.client.host if request.client else "unknown"
        key = f"rate:{client_ip}"
        count = await cache.increment(key)
        if count == 1:
            await cache.expire(key, 60)
        if count > self.rpm:
            return Response(
                content='{"detail": "Rate limit exceeded. Try again in a minute."}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": "60"},
            )
        return await call_next(request)


# ── Request Logger ───────────────────────────

class RequestLogMiddleware(BaseHTTPMiddleware):
    """Logs all requests with timing info."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())[:8]
        start = time.time()

        # Attach request ID
        request.state.request_id = request_id

        response = await call_next(request)

        duration_ms = (time.time() - start) * 1000
        logger.info(
            "request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round(duration_ms),
            },
        )

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration_ms:.0f}ms"
        return response


# ── Audit Trail ──────────────────────────────

class AuditTrail:
    """
    Records security-relevant actions for compliance.
    Persists to the audit_logs database table (fire-and-forget).
    """

    @classmethod
    def record(
        cls,
        action: str,
        user_id: str = None,
        resource_type: str = None,
        resource_id: str = None,
        details: dict = None,
        ip_address: str = None,
    ) -> dict:
        entry = {
            "id": str(uuid.uuid4()),
            "timestamp": time.time(),
            "action": action,
            "user_id": user_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details or {},
            "ip_address": ip_address,
        }
        try:
            asyncio.get_running_loop().create_task(cls._persist(entry))
        except RuntimeError:
            pass  # No running event loop (e.g. during tests / startup)
        return entry

    @classmethod
    async def _persist(cls, entry: dict):
        from datetime import datetime as _dt
        from app.database import async_session, AuditLog
        try:
            async with async_session() as session:
                session.add(AuditLog(
                    id=entry["id"],
                    timestamp=_dt.utcfromtimestamp(entry["timestamp"]),
                    action=entry["action"],
                    user_id=entry.get("user_id"),
                    resource_type=entry.get("resource_type"),
                    resource_id=entry.get("resource_id"),
                    details=entry.get("details", {}),
                    ip_address=entry.get("ip_address"),
                ))
                await session.commit()
        except Exception:
            logger.debug("AuditTrail._persist failed", exc_info=True)

    @classmethod
    async def purge_old_logs(cls, retention_days: int = 90) -> int:
        """
        Delete audit log rows older than retention_days.
        Returns the number of rows deleted.
        Should be called periodically (e.g. once per day at startup).
        """
        from sqlalchemy import delete
        from app.database import async_session, AuditLog
        cutoff = datetime.utcnow() - timedelta(days=retention_days)
        try:
            async with async_session() as session:
                result = await session.execute(
                    delete(AuditLog).where(AuditLog.timestamp < cutoff)
                )
                await session.commit()
                deleted = result.rowcount
            if deleted:
                logger.info("audit_log_purge", extra={"deleted": deleted, "retention_days": retention_days})
            return deleted
        except Exception:
            logger.warning("AuditTrail.purge_old_logs failed", exc_info=True)
            return 0

    @classmethod
    async def query(
        cls,
        user_id: str = None,
        action: str = None,
        limit: int = 50,
    ) -> list[dict]:
        from sqlalchemy import select
        from app.database import async_session, AuditLog
        try:
            async with async_session() as session:
                q = select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit)
                if user_id:
                    q = q.where(AuditLog.user_id == user_id)
                if action:
                    q = q.where(AuditLog.action == action)
                result = await session.execute(q)
                rows = result.scalars().all()
            return [
                {
                    "id": r.id,
                    "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                    "action": r.action,
                    "user_id": r.user_id,
                    "resource_type": r.resource_type,
                    "resource_id": r.resource_id,
                    "details": r.details,
                    "ip_address": r.ip_address,
                }
                for r in rows
            ]
        except Exception:
            logger.debug("AuditTrail.query failed", exc_info=True)
            return []
