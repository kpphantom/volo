"""
VOLO — Middleware
Rate limiting, request logging, audit trail, error tracking.
"""

import time
import uuid
import logging
from collections import defaultdict
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("volo")


# ── Rate Limiter ─────────────────────────────

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiter.
    In production, use Redis-backed rate limiting.
    """

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.rpm = requests_per_minute
        self._requests: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks
        if request.url.path in ("/health", "/", "/docs", "/openapi.json"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        # Clean old entries
        self._requests[client_ip] = [
            t for t in self._requests[client_ip] if now - t < 60
        ]

        if len(self._requests[client_ip]) >= self.rpm:
            return Response(
                content='{"detail": "Rate limit exceeded. Try again in a minute."}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": "60"},
            )

        self._requests[client_ip].append(now)
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
            f"[{request_id}] {request.method} {request.url.path} "
            f"→ {response.status_code} ({duration_ms:.0f}ms)"
        )

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration_ms:.0f}ms"
        return response


# ── Audit Trail (in-memory for dev) ──────────

class AuditTrail:
    """
    Records security-relevant actions for compliance.
    In production, writes to the audit_log database table.
    """

    _log: list[dict] = []

    @classmethod
    def record(
        cls,
        action: str,
        user_id: str = None,
        resource_type: str = None,
        resource_id: str = None,
        details: dict = None,
        ip_address: str = None,
    ):
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
        cls._log.append(entry)
        # Keep last 10000 entries in memory
        if len(cls._log) > 10000:
            cls._log = cls._log[-5000:]
        return entry

    @classmethod
    def query(
        cls,
        user_id: str = None,
        action: str = None,
        limit: int = 50,
    ) -> list[dict]:
        results = cls._log
        if user_id:
            results = [e for e in results if e.get("user_id") == user_id]
        if action:
            results = [e for e in results if e.get("action") == action]
        return list(reversed(results[:limit]))
