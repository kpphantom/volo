"""
VOLO — System & Config Routes
Provides system status and in-app configuration management.
"""

import os
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from app.config import settings
from app.agent.memory import MemoryManager

router = APIRouter()

# Shared memory instance (same one used by orchestrator)
_memory = None

def _get_memory() -> MemoryManager:
    global _memory
    if _memory is None:
        _memory = MemoryManager()
    return _memory


# ── System Status ──────────────────────────────────────────────

@router.get("/system/status")
async def system_status():
    """Returns system health info for the dashboard."""
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", settings.anthropic_api_key)
    ai_configured = bool(
        anthropic_key
        and len(anthropic_key) > 10
        and not anthropic_key.startswith("your-")
    )

    github_token = os.getenv("GITHUB_TOKEN", "")
    github_connected = bool(github_token and len(github_token) > 5 and not github_token.startswith("your-"))

    alpaca_key = os.getenv("ALPACA_API_KEY", "")
    alpaca_connected = bool(alpaca_key and len(alpaca_key) > 5)

    memory = _get_memory()
    memories = await memory.get_all()

    integrations_count = sum([
        1 if github_connected else 0,
        1 if alpaca_connected else 0,
        1,  # CoinGecko is always available
    ])

    return {
        "status": "healthy",
        "ai_configured": ai_configured,
        "ai_model": settings.default_model,
        "integrations_count": integrations_count,
        "integrations": {
            "github": github_connected,
            "alpaca": alpaca_connected,
            "coingecko": True,
        },
        "memories_count": len(memories),
        "version": "0.1.0",
    }


# ── Config Management ─────────────────────────────────────────

class KeySave(BaseModel):
    key_name: str
    key_value: str

@router.post("/config/keys")
async def save_key(payload: KeySave):
    """Save an API key to environment (in-memory for this session)."""
    allowed_keys = {
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "GITHUB_TOKEN",
        "ALPACA_API_KEY",
        "ALPACA_SECRET_KEY",
    }
    if payload.key_name not in allowed_keys:
        return {"ok": False, "message": f"Key {payload.key_name} is not a recognized config key"}

    os.environ[payload.key_name] = payload.key_value

    # Also update settings object if applicable
    key_lower = payload.key_name.lower()
    if hasattr(settings, key_lower):
        object.__setattr__(settings, key_lower, payload.key_value)

    return {"ok": True, "message": f"{payload.key_name} saved for this session"}


@router.get("/config/test-key/{key_name}")
async def test_key(key_name: str):
    """Test if an API key is present and valid."""
    value = os.getenv(key_name, "")
    if not value or len(value) < 5 or value.startswith("your-"):
        return {"valid": False, "message": "Key not set or placeholder"}

    # Specific validation
    if key_name == "ANTHROPIC_API_KEY":
        if value.startswith("sk-ant-"):
            return {"valid": True, "message": "Key format looks correct"}
        return {"valid": False, "message": "Expected key starting with sk-ant-"}

    if key_name == "OPENAI_API_KEY":
        if value.startswith("sk-"):
            return {"valid": True, "message": "Key format looks correct"}
        return {"valid": False, "message": "Expected key starting with sk-"}

    if key_name == "GITHUB_TOKEN":
        if value.startswith("ghp_") or value.startswith("github_pat_"):
            return {"valid": True, "message": "Token format looks correct"}
        return {"valid": False, "message": "Expected token starting with ghp_ or github_pat_"}

    # Default: if it exists and isn't a placeholder, assume valid
    return {"valid": True, "message": "Key is set"}
