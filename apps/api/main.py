"""
VOLO — AI Life Operating System
Main FastAPI Application
"""

import json
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()


class _JsonFormatter(logging.Formatter):
    """Emit log records as single-line JSON for structured log aggregators."""

    def format(self, record: logging.LogRecord) -> str:
        data: dict = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Merge any extra fields attached by logger.info("msg", extra={...})
        for key, value in record.__dict__.items():
            if key not in logging.LogRecord.__dict__ and key not in (
                "message", "asctime", "args", "exc_info", "exc_text", "stack_info",
            ):
                data[key] = value
        if record.exc_info:
            data["exc"] = self.formatException(record.exc_info)
        return json.dumps(data)


def _configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(_JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)


_configure_logging()

# Core routes
from app.routes import chat, integrations, memory, onboarding, health, whitelabel, system
# New routes
from app.routes import auth as auth_routes
from app.routes import webhooks as webhook_routes
from app.routes import standing_orders as standing_orders_routes
from app.routes import approvals as approval_routes
from app.routes import activity as activity_routes
from app.routes import billing as billing_routes
from app.routes import conversations as conversation_routes
from app.routes import public_api as public_api_routes
from app.routes import authenticator as authenticator_routes
# Life OS routes
from app.routes import google as google_routes
from app.routes import youtube as youtube_routes
from app.routes import messages as message_routes
from app.routes import social_feed as social_feed_routes
from app.routes import social_connect as social_connect_routes
from app.routes import social_actions as social_actions_routes
from app.routes import fitness as fitness_routes
from app.routes import remote as remote_routes
from app.routes import summarize as summarize_routes
from app.routes import finance as finance_routes

from app.database import init_db
from app.middleware import RateLimitMiddleware, RequestLogMiddleware
from app.services.cache import cache
from app.services.remote_agent import remote_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    print("🚀 Volo API starting up...")
    await init_db()
    print("✅ Database initialized")
    await cache.connect()
    print("✅ Cache connected")

    # Load persistent data into in-memory caches
    from app.services.google_auth import google_auth
    await google_auth.load_from_db()
    print("✅ Google tokens loaded")
    await remote_manager.load_keys_from_db()
    print("✅ Agent keys loaded")

    print("🧠 Agent orchestrator ready")
    yield
    print("👋 Volo API shutting down...")


app = FastAPI(
    title="Volo API",
    description="AI Life Operating System — One agent, total control.",
    version="0.1.0",
    lifespan=lifespan,
)

# Middleware (order matters — outermost first)
app.add_middleware(RequestLogMiddleware)
app.add_middleware(RateLimitMiddleware, requests_per_minute=120)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("FRONTEND_URL", "http://localhost:3000"),
        "http://localhost:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Core Routes ─────────────────────────────────────────────────────────────
app.include_router(health.router, tags=["Health"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(onboarding.router, prefix="/api", tags=["Onboarding"])
app.include_router(integrations.router, prefix="/api", tags=["Integrations"])
app.include_router(memory.router, prefix="/api", tags=["Memory"])
app.include_router(whitelabel.router, prefix="/api", tags=["White Label"])
app.include_router(system.router, prefix="/api", tags=["System"])

# ── Auth & Security ─────────────────────────────────────────────────────────
app.include_router(auth_routes.router, prefix="/api/auth", tags=["Auth"])

# ── Conversations ───────────────────────────────────────────────────────────
app.include_router(conversation_routes.router, prefix="/api", tags=["Conversations"])

# ── Workflows ───────────────────────────────────────────────────────────────
app.include_router(standing_orders_routes.router, prefix="/api", tags=["Standing Orders"])
app.include_router(approval_routes.router, prefix="/api", tags=["Approvals"])

# ── Webhooks ────────────────────────────────────────────────────────────────
app.include_router(webhook_routes.router, prefix="/api", tags=["Webhooks"])

# ── Analytics & Activity ────────────────────────────────────────────────────
app.include_router(activity_routes.router, prefix="/api", tags=["Activity"])

# ── Billing ─────────────────────────────────────────────────────────────────
app.include_router(billing_routes.router, prefix="/api", tags=["Billing"])

# ── Public API (versioned) ──────────────────────────────────────────────────
app.include_router(public_api_routes.router, prefix="/api", tags=["Public API"])
# ── Life OS ─────────────────────────────────────────────────────────────
app.include_router(google_routes.router, prefix="/api", tags=["Google"])
app.include_router(youtube_routes.router, prefix="/api", tags=["YouTube"])
app.include_router(message_routes.router, prefix="/api", tags=["Messages"])
app.include_router(social_feed_routes.router, prefix="/api", tags=["Social Feed"])
app.include_router(social_connect_routes.router, prefix="/api", tags=["Social Connect"])
app.include_router(social_actions_routes.router, prefix="/api", tags=["Social Actions"])
app.include_router(fitness_routes.router, prefix="/api", tags=["Health & Fitness"])

# ── Remote Desktop Agent
app.include_router(remote_routes.router, prefix="/api", tags=["Remote Agent"])

# ── Authenticator Vault (built-in 2FA)
app.include_router(authenticator_routes.router, prefix="/api", tags=["Authenticator"])

# ── AI Summarize
app.include_router(summarize_routes.router, prefix="/api", tags=["AI Summarize"])

# ── Finance & Budgeting
app.include_router(finance_routes.router, prefix="/api", tags=["Finance"])

@app.get("/")
async def root():
    return {
        "name": "Volo API",
        "version": "0.1.0",
        "status": "operational",
        "agent": "ready",
    }
