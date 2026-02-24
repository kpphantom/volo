"""
VOLO — Billing Routes
Subscription management, plan info, checkout sessions.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from app.services.billing import BillingService

router = APIRouter()
billing = BillingService()


@router.get("/billing/plans")
async def get_plans():
    """Get available pricing plans."""
    plans = await billing.get_plans()
    return {"plans": plans}


@router.get("/billing/usage")
async def get_usage():
    """Get current usage for the tenant."""
    usage = await billing.get_usage("volo-default")
    return usage


class CheckoutRequest(BaseModel):
    plan: str
    success_url: str = "http://localhost:3000/settings?tab=billing&status=success"
    cancel_url: str = "http://localhost:3000/settings?tab=billing&status=canceled"


@router.post("/billing/checkout")
async def create_checkout(body: CheckoutRequest):
    """Create a Stripe checkout session."""
    plans = await billing.get_plans()
    plan = next((p for p in plans if p["id"] == body.plan), None)
    if not plan:
        return {"error": f"Plan '{body.plan}' not found"}
    if not plan.get("price_id"):
        return {"error": "No Stripe price configured for this plan"}

    result = await billing.create_checkout_session(
        customer_id="",  # Would be fetched from DB
        price_id=plan["price_id"],
        success_url=body.success_url,
        cancel_url=body.cancel_url,
    )
    return result


@router.get("/billing/subscription")
async def get_subscription():
    """Get current subscription status."""
    return {
        "plan": "free",
        "status": "active",
        "message": "Upgrade to Pro for unlimited access.",
    }
