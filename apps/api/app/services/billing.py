"""
VOLO — Billing Service
Stripe integration for subscriptions and payments.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger("volo.billing")


class BillingService:
    """Handles Stripe billing operations."""

    def __init__(self):
        self.stripe_key = os.getenv("STRIPE_SECRET_KEY", "")
        self._stripe = None

    @property
    def stripe(self):
        if self._stripe is None and self.stripe_key:
            try:
                import stripe
                stripe.api_key = self.stripe_key
                self._stripe = stripe
            except ImportError:
                logger.warning("stripe package not installed")
        return self._stripe

    def _check_stripe(self) -> Optional[dict]:
        if not self.stripe_key or not self.stripe:
            return {"error": "Billing not configured. Add STRIPE_SECRET_KEY."}
        return None

    async def create_customer(self, email: str, name: str, tenant_id: str) -> dict:
        err = self._check_stripe()
        if err:
            return err

        customer = self.stripe.Customer.create(
            email=email,
            name=name,
            metadata={"tenant_id": tenant_id},
        )
        return {"customer_id": customer.id, "email": email}

    async def create_checkout_session(
        self,
        customer_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
    ) -> dict:
        err = self._check_stripe()
        if err:
            return err

        session = self.stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
        )
        return {"checkout_url": session.url, "session_id": session.id}

    async def get_subscription(self, subscription_id: str) -> dict:
        err = self._check_stripe()
        if err:
            return err

        sub = self.stripe.Subscription.retrieve(subscription_id)
        return {
            "id": sub.id,
            "status": sub.status,
            "plan": sub.items.data[0].price.id if sub.items.data else None,
            "current_period_end": sub.current_period_end,
        }

    async def cancel_subscription(self, subscription_id: str) -> dict:
        err = self._check_stripe()
        if err:
            return err

        sub = self.stripe.Subscription.modify(
            subscription_id,
            cancel_at_period_end=True,
        )
        return {"status": "canceling", "cancel_at_period_end": True}

    async def get_usage(self, tenant_id: str) -> dict:
        """Get usage metrics for billing purposes."""
        return {
            "tenant_id": tenant_id,
            "plan": "free",
            "usage": {
                "messages_this_month": 0,
                "api_calls_this_month": 0,
                "storage_mb": 0,
                "integrations_connected": 0,
            },
            "limits": {
                "messages_per_month": 1000,
                "api_calls_per_month": 10000,
                "storage_mb": 100,
                "integrations": 3,
            },
        }

    async def get_plans(self) -> list[dict]:
        """Get available pricing plans."""
        return [
            {
                "id": "free",
                "name": "Free",
                "price": 0,
                "features": [
                    "1,000 messages/month",
                    "3 integrations",
                    "100MB storage",
                    "Community support",
                ],
            },
            {
                "id": "pro",
                "name": "Pro",
                "price": 29,
                "price_id": os.getenv("STRIPE_PRICE_PRO", ""),
                "features": [
                    "Unlimited messages",
                    "Unlimited integrations",
                    "10GB storage",
                    "Priority support",
                    "Multi-model AI",
                    "Custom tools",
                ],
            },
            {
                "id": "enterprise",
                "name": "Enterprise",
                "price": 99,
                "price_id": os.getenv("STRIPE_PRICE_ENTERPRISE", ""),
                "features": [
                    "Everything in Pro",
                    "White-label branding",
                    "Custom domain",
                    "SSO / SAML",
                    "Dedicated support",
                    "SLA guarantee",
                    "Audit logs",
                ],
            },
        ]
