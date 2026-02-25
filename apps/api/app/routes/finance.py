"""
VOLO — Finance / Banking Routes
Plaid integration, budgeting, transaction categorization.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select

from app.auth import get_current_user, CurrentUser
from app.database import async_session, Integration
from app.services.plaid_service import plaid_service

logger = logging.getLogger("volo.finance")
router = APIRouter()


class PlaidExchangeRequest(BaseModel):
    public_token: str


class BudgetUpdate(BaseModel):
    category: str
    limit: float


# ── Plaid Link ──────────────────────────────────────────────────────────

@router.get("/finance/plaid/link-token")
async def get_link_token(current_user: CurrentUser = Depends(get_current_user)):
    """Create a Plaid Link token for the frontend widget."""
    result = await plaid_service.create_link_token(current_user.user_id)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.post("/finance/plaid/exchange")
async def exchange_token(body: PlaidExchangeRequest, current_user: CurrentUser = Depends(get_current_user)):
    """Exchange public_token from Plaid Link for access_token and store it."""
    result = await plaid_service.exchange_public_token(body.public_token)
    if "error" in result:
        raise HTTPException(400, result["error"])

    # Store access token as an integration
    async with async_session() as session:
        existing = await session.execute(
            select(Integration).where(
                Integration.user_id == current_user.user_id,
                Integration.type == "plaid",
            )
        )
        integration = existing.scalar_one_or_none()
        if integration:
            integration.config = {
                "access_token": result["access_token"],
                "item_id": result["item_id"],
            }
            integration.status = "connected"
            integration.last_sync_at = datetime.utcnow()
        else:
            session.add(Integration(
                user_id=current_user.user_id,
                type="plaid",
                category="finance",
                name="Bank Account (Plaid)",
                status="connected",
                config={
                    "access_token": result["access_token"],
                    "item_id": result["item_id"],
                },
            ))
        await session.commit()

    return {"success": True, "message": "Bank account connected!"}


# ── Helper to get access token ──────────────────────────────────────────

async def _get_plaid_token(user_id: str) -> Optional[str]:
    """Get stored Plaid access token for user."""
    async with async_session() as session:
        result = await session.execute(
            select(Integration).where(
                Integration.user_id == user_id,
                Integration.type == "plaid",
                Integration.status == "connected",
            )
        )
        integration = result.scalar_one_or_none()
        if integration and integration.config:
            return integration.config.get("access_token")
    return None


# ── Finance Dashboard Data ──────────────────────────────────────────────

@router.get("/finance/overview")
async def finance_overview(current_user: CurrentUser = Depends(get_current_user)):
    """
    Get full finance overview — accounts, balances, spending, transactions.
    Returns demo data if Plaid isn't connected.
    """
    token = await _get_plaid_token(current_user.user_id)

    if not token:
        # Return demo data
        return plaid_service.get_demo_data()

    # Fetch real data from Plaid
    try:
        balances = await plaid_service.get_balances(token)
        spending = await plaid_service.get_spending_breakdown(token, days=30)
        txn_data = await plaid_service.get_transactions(token, days=30, count=50)

        # Load budgets from user preferences
        budgets = await _get_budgets(current_user.user_id, spending.get("categories", []))

        return {
            "accounts": balances.get("accounts", []),
            "total_current": balances.get("total_current", 0),
            "total_available": balances.get("total_available", 0),
            "spending": spending,
            "transactions": txn_data.get("transactions", []),
            "budgets": budgets,
            "is_demo": False,
        }
    except Exception as e:
        logger.exception("Failed to fetch Plaid data")
        return {**plaid_service.get_demo_data(), "error": str(e)}


@router.get("/finance/transactions")
async def get_transactions(
    days: int = 30,
    count: int = 100,
    offset: int = 0,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get transactions for the connected bank."""
    token = await _get_plaid_token(current_user.user_id)
    if not token:
        return {"transactions": plaid_service.get_demo_data()["transactions"], "is_demo": True}

    return await plaid_service.get_transactions(token, days=days, count=count, offset=offset)


@router.get("/finance/balances")
async def get_balances(current_user: CurrentUser = Depends(get_current_user)):
    """Get real-time account balances."""
    token = await _get_plaid_token(current_user.user_id)
    if not token:
        demo = plaid_service.get_demo_data()
        return {"accounts": demo["accounts"], "total_current": demo["total_current"], "total_available": demo["total_available"], "is_demo": True}

    return await plaid_service.get_balances(token)


# ── Budgets ─────────────────────────────────────────────────────────────

async def _get_budgets(user_id: str, categories: list) -> list:
    """Load budget limits from user's integration config or return defaults."""
    async with async_session() as session:
        result = await session.execute(
            select(Integration).where(
                Integration.user_id == user_id,
                Integration.type == "plaid_budgets",
            )
        )
        integration = result.scalar_one_or_none()
        saved_budgets = integration.config if integration else {}

    budgets = []
    default_limits = {
        "FOOD_AND_DRINK": 800,
        "ENTERTAINMENT": 300,
        "SHOPPING": 500,
        "TRANSPORTATION": 400,
        "RENT_AND_UTILITIES": 2000,
        "GENERAL_SERVICES": 300,
        "TRANSFER_OUT": 500,
    }

    for cat_data in categories:
        cat = cat_data["name"]
        spent = cat_data["amount"]
        limit = saved_budgets.get(cat, default_limits.get(cat, 500))
        budgets.append({
            "category": cat,
            "limit": limit,
            "spent": spent,
            "pct": round(spent / limit * 100, 1) if limit > 0 else 0,
        })

    return budgets


@router.post("/finance/budgets")
async def update_budget(body: BudgetUpdate, current_user: CurrentUser = Depends(get_current_user)):
    """Update a budget limit for a spending category."""
    async with async_session() as session:
        result = await session.execute(
            select(Integration).where(
                Integration.user_id == current_user.user_id,
                Integration.type == "plaid_budgets",
            )
        )
        integration = result.scalar_one_or_none()
        if integration:
            config = integration.config or {}
            config[body.category] = body.limit
            integration.config = config
            integration.last_sync_at = datetime.utcnow()
        else:
            session.add(Integration(
                user_id=current_user.user_id,
                type="plaid_budgets",
                category="finance",
                name="Budget Settings",
                status="active",
                config={body.category: body.limit},
            ))
        await session.commit()

    return {"success": True, "category": body.category, "limit": body.limit}


@router.get("/finance/status")
async def finance_status(current_user: CurrentUser = Depends(get_current_user)):
    """Check if Plaid is connected."""
    token = await _get_plaid_token(current_user.user_id)
    return {
        "plaid_connected": token is not None,
        "plaid_configured": bool(plaid_service.client_id and plaid_service.secret),
    }
