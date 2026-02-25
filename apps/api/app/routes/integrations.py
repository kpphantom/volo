"""
VOLO — Integrations Route
Handles connecting and managing external service integrations.
Persisted to PostgreSQL Integration table.
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select

from app.auth import get_current_user, CurrentUser
from app.database import async_session, Integration

router = APIRouter()


class IntegrationConnect(BaseModel):
    type: str  # github, gmail, alpaca, etc.
    credentials: dict  # will be stored in config JSON
    config: Optional[dict] = {}


class IntegrationStatus(BaseModel):
    id: str
    type: str
    category: str
    name: str
    status: str
    last_sync_at: Optional[str] = None


# Available integration definitions
AVAILABLE_INTEGRATIONS = [
    {
        "type": "github",
        "category": "code",
        "name": "GitHub",
        "description": "Access repositories, PRs, issues, and CI/CD",
        "required_fields": ["access_token"],
        "oauth_supported": True,
    },
    {
        "type": "gmail",
        "category": "communication",
        "name": "Gmail",
        "description": "Read, draft, and send emails. Auto-categorize inbox.",
        "required_fields": ["oauth_token"],
        "oauth_supported": True,
    },
    {
        "type": "google_calendar",
        "category": "communication",
        "name": "Google Calendar",
        "description": "Schedule events, detect conflicts, prepare meeting briefs",
        "required_fields": ["oauth_token"],
        "oauth_supported": True,
    },
    {
        "type": "slack",
        "category": "communication",
        "name": "Slack",
        "description": "Read channels, send messages, summarize threads",
        "required_fields": ["bot_token"],
        "oauth_supported": True,
    },
    {
        "type": "alpaca",
        "category": "finance",
        "name": "Alpaca Trading",
        "description": "Stock trading, portfolio management, market data",
        "required_fields": ["api_key", "secret_key"],
        "oauth_supported": False,
    },
    {
        "type": "coinbase",
        "category": "finance",
        "name": "Coinbase",
        "description": "Crypto trading, wallet management, DeFi access",
        "required_fields": ["api_key", "api_secret"],
        "oauth_supported": True,
    },
    {
        "type": "binance",
        "category": "finance",
        "name": "Binance",
        "description": "Crypto spot & futures trading",
        "required_fields": ["api_key", "api_secret"],
        "oauth_supported": False,
    },
    {
        "type": "plaid",
        "category": "finance",
        "name": "Plaid (Banking)",
        "description": "Connect bank accounts for cash flow tracking and expense categorization",
        "required_fields": ["public_token"],
        "oauth_supported": True,
    },
    {
        "type": "twitter",
        "category": "social",
        "name": "Twitter / X",
        "description": "Post, schedule, monitor mentions and DMs",
        "required_fields": ["bearer_token"],
        "oauth_supported": True,
    },
    {
        "type": "linkedin",
        "category": "social",
        "name": "LinkedIn",
        "description": "Post content, manage connections, inbox management",
        "required_fields": ["oauth_token"],
        "oauth_supported": True,
    },
    {
        "type": "remote_machine",
        "category": "machine",
        "name": "Remote Machine",
        "description": "Execute commands, access files on your computers",
        "required_fields": ["machine_token"],
        "oauth_supported": False,
    },
    {
        "type": "ethereum_wallet",
        "category": "web3",
        "name": "Ethereum Wallet",
        "description": "Track ETH/ERC-20 balances, DeFi positions, NFTs",
        "required_fields": ["wallet_address"],
        "oauth_supported": False,
    },
    {
        "type": "solana_wallet",
        "category": "web3",
        "name": "Solana Wallet",
        "description": "Track SOL/SPL balances, DeFi positions, NFTs",
        "required_fields": ["wallet_address"],
        "oauth_supported": False,
    },
]


@router.get("/integrations")
async def list_integrations(current_user: CurrentUser = Depends(get_current_user)):
    """List all available integrations and their connection status."""
    async with async_session() as session:
        result = await session.execute(
            select(Integration).where(Integration.user_id == current_user.user_id)
        )
        connected = [
            {
                "id": i.id,
                "type": i.type,
                "category": i.category,
                "name": i.name,
                "status": i.status,
                "last_sync_at": i.last_sync_at.isoformat() if i.last_sync_at else None,
                "created_at": i.created_at.isoformat() if i.created_at else None,
            }
            for i in result.scalars().all()
        ]

    return {
        "available": AVAILABLE_INTEGRATIONS,
        "connected": connected,
    }


@router.post("/integrations/connect")
async def connect_integration(integration: IntegrationConnect, current_user: CurrentUser = Depends(get_current_user)):
    """Connect a new integration."""
    valid_types = [i["type"] for i in AVAILABLE_INTEGRATIONS]
    if integration.type not in valid_types:
        raise HTTPException(400, f"Unknown integration type: {integration.type}")

    # Find display info
    info = next((i for i in AVAILABLE_INTEGRATIONS if i["type"] == integration.type), {})

    async with async_session() as session:
        # Upsert — replace existing integration of same type
        result = await session.execute(
            select(Integration).where(
                Integration.user_id == current_user.user_id,
                Integration.type == integration.type,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.config = {**integration.credentials, **(integration.config or {})}
            existing.status = "connected"
            existing.last_sync_at = datetime.utcnow()
        else:
            session.add(Integration(
                user_id=current_user.user_id,
                type=integration.type,
                category=info.get("category", "other"),
                name=info.get("name", integration.type),
                status="connected",
                config={**integration.credentials, **(integration.config or {})},
            ))

        await session.commit()

    return {
        "success": True,
        "integration": {
            "type": integration.type,
            "status": "connected",
            "message": f"{info.get('name', integration.type)} connected successfully.",
        },
    }


@router.delete("/integrations/{integration_id}")
async def disconnect_integration(integration_id: str, current_user: CurrentUser = Depends(get_current_user)):
    """Disconnect an integration."""
    async with async_session() as session:
        result = await session.execute(
            select(Integration).where(
                Integration.id == integration_id,
                Integration.user_id == current_user.user_id,
            )
        )
        integration = result.scalar_one_or_none()
        if not integration:
            raise HTTPException(404, "Integration not found")

        await session.delete(integration)
        await session.commit()

    return {"success": True, "message": f"Integration {integration_id} disconnected."}


@router.post("/integrations/{integration_id}/sync")
async def sync_integration(integration_id: str, current_user: CurrentUser = Depends(get_current_user)):
    """Trigger a manual sync for an integration."""
    async with async_session() as session:
        result = await session.execute(
            select(Integration).where(
                Integration.id == integration_id,
                Integration.user_id == current_user.user_id,
            )
        )
        integration = result.scalar_one_or_none()
        if not integration:
            raise HTTPException(404, "Integration not found")

        integration.last_sync_at = datetime.utcnow()
        await session.commit()

    return {"success": True, "message": f"Sync started for {integration_id}"}
