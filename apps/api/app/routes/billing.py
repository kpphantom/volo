"""
VOLO — Billing Routes
Subscription management, plan info, checkout sessions.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.auth import get_current_user, CurrentUser
from app.database import async_session, User
from app.services.billing import BillingService

router = APIRouter()
billing = BillingService()


@router.get("/billing/plans")
async def get_plans():
    """Get available pricing plans."""
    plans = await billing.get_plans()
    return {"plans": plans}


@router.get("/billing/usage")
async def get_usage(current_user: CurrentUser = Depends(get_current_user)):
    """Get current usage for the tenant."""
    usage = await billing.get_usage(current_user.tenant_id)
    return usage


class CheckoutRequest(BaseModel):
    plan: str
    success_url: str = "http://localhost:3000/settings?tab=billing&status=success"
    cancel_url: str = "http://localhost:3000/settings?tab=billing&status=canceled"


@router.post("/billing/checkout")
async def create_checkout(body: CheckoutRequest, current_user: CurrentUser = Depends(get_current_user)):
    """Create a Stripe checkout session."""
    plans = await billing.get_plans()
    plan = next((p for p in plans if p["id"] == body.plan), None)
    if not plan:
        return {"error": f"Plan '{body.plan}' not found"}
    if not plan.get("price_id"):
        return {"error": "No Stripe price configured for this plan"}

    async with async_session() as session:
        user_row = await session.get(User, current_user.user_id)
        customer_id = getattr(user_row, "stripe_customer_id", "") or "" if user_row else ""

    result = await billing.create_checkout_session(
        customer_id=customer_id,
        price_id=plan["price_id"],
        success_url=body.success_url,
        cancel_url=body.cancel_url,
    )
    return result


@router.get("/billing/subscription")
async def get_subscription(current_user: CurrentUser = Depends(get_current_user)):
    """Get current subscription status."""
    return {
        "plan": "free",
        "status": "active",
        "message": "Upgrade to Pro for unlimited access.",
    }
