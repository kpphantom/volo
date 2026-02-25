"""
VOLO — Plaid Banking Service
Connect bank accounts, fetch transactions, balances, and categorize spending.
Uses Plaid API (https://plaid.com/docs/)
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
import httpx

from app.config import settings

logger = logging.getLogger("volo.plaid")


class PlaidService:
    """Handles Plaid API operations for banking data."""

    ENVS = {
        "sandbox": "https://sandbox.plaid.com",
        "development": "https://development.plaid.com",
        "production": "https://production.plaid.com",
    }

    def __init__(self):
        self.client_id = settings.plaid_client_id
        self.secret = settings.plaid_secret
        env = settings.plaid_env or "sandbox"
        self.base_url = self.ENVS.get(env, self.ENVS["sandbox"])
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    def _check_auth(self) -> Optional[dict]:
        if not self.client_id or not self.secret:
            return {
                "error": "Plaid not configured.",
                "message": "Set PLAID_CLIENT_ID and PLAID_SECRET to connect your bank accounts.",
                "setup_url": "https://dashboard.plaid.com/signup",
            }
        return None

    def _headers(self) -> dict:
        return {"Content-Type": "application/json"}

    def _auth_body(self) -> dict:
        return {"client_id": self.client_id, "secret": self.secret}

    # ── Link Token (for frontend Plaid Link widget) ─────────────────────

    async def create_link_token(self, user_id: str) -> dict:
        """Create a link_token for Plaid Link initialization."""
        err = self._check_auth()
        if err:
            return err

        client = await self._get_client()
        resp = await client.post(
            f"{self.base_url}/link/token/create",
            headers=self._headers(),
            json={
                **self._auth_body(),
                "user": {"client_user_id": user_id},
                "client_name": "Volo",
                "products": ["transactions"],
                "country_codes": ["US", "CA", "GB"],
                "language": "en",
                "redirect_uri": None,
            },
        )
        data = resp.json()
        if "link_token" in data:
            return {"link_token": data["link_token"], "expiration": data.get("expiration")}
        return {"error": data.get("error_message", "Failed to create link token")}

    async def exchange_public_token(self, public_token: str) -> dict:
        """Exchange a public_token from Plaid Link for an access_token."""
        err = self._check_auth()
        if err:
            return err

        client = await self._get_client()
        resp = await client.post(
            f"{self.base_url}/item/public_token/exchange",
            headers=self._headers(),
            json={**self._auth_body(), "public_token": public_token},
        )
        data = resp.json()
        if "access_token" in data:
            return {
                "access_token": data["access_token"],
                "item_id": data["item_id"],
            }
        return {"error": data.get("error_message", "Token exchange failed")}

    # ── Accounts ────────────────────────────────────────────────────────

    async def get_accounts(self, access_token: str) -> dict:
        """Get all linked bank accounts."""
        client = await self._get_client()
        resp = await client.post(
            f"{self.base_url}/accounts/get",
            headers=self._headers(),
            json={**self._auth_body(), "access_token": access_token},
        )
        data = resp.json()
        if "accounts" in data:
            return {
                "accounts": [
                    {
                        "id": acc["account_id"],
                        "name": acc.get("name", ""),
                        "official_name": acc.get("official_name", ""),
                        "type": acc.get("type", ""),
                        "subtype": acc.get("subtype", ""),
                        "mask": acc.get("mask", ""),
                        "balance": {
                            "current": acc.get("balances", {}).get("current"),
                            "available": acc.get("balances", {}).get("available"),
                            "currency": acc.get("balances", {}).get("iso_currency_code", "USD"),
                        },
                    }
                    for acc in data["accounts"]
                ],
                "institution": data.get("item", {}).get("institution_id", ""),
            }
        return {"error": data.get("error_message", "Failed to fetch accounts")}

    # ── Balances ────────────────────────────────────────────────────────

    async def get_balances(self, access_token: str) -> dict:
        """Get real-time balances for all accounts."""
        client = await self._get_client()
        resp = await client.post(
            f"{self.base_url}/accounts/balance/get",
            headers=self._headers(),
            json={**self._auth_body(), "access_token": access_token},
        )
        data = resp.json()
        if "accounts" in data:
            accounts = []
            total_current = 0.0
            total_available = 0.0
            for acc in data["accounts"]:
                bal = acc.get("balances", {})
                current = bal.get("current") or 0
                available = bal.get("available") or 0
                total_current += current
                total_available += available
                accounts.append({
                    "id": acc["account_id"],
                    "name": acc.get("name", ""),
                    "type": acc.get("type", ""),
                    "subtype": acc.get("subtype", ""),
                    "mask": acc.get("mask", ""),
                    "current": current,
                    "available": available,
                    "currency": bal.get("iso_currency_code", "USD"),
                })
            return {
                "accounts": accounts,
                "total_current": total_current,
                "total_available": total_available,
            }
        return {"error": data.get("error_message", "Failed to fetch balances")}

    # ── Transactions ────────────────────────────────────────────────────

    async def get_transactions(
        self,
        access_token: str,
        days: int = 30,
        count: int = 100,
        offset: int = 0,
    ) -> dict:
        """Get recent transactions."""
        client = await self._get_client()
        end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        start_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

        resp = await client.post(
            f"{self.base_url}/transactions/get",
            headers=self._headers(),
            json={
                **self._auth_body(),
                "access_token": access_token,
                "start_date": start_date,
                "end_date": end_date,
                "options": {"count": count, "offset": offset},
            },
        )
        data = resp.json()
        if "transactions" in data:
            txns = []
            for t in data["transactions"]:
                txns.append({
                    "id": t.get("transaction_id", ""),
                    "name": t.get("name", ""),
                    "merchant": t.get("merchant_name", ""),
                    "amount": t.get("amount", 0),
                    "date": t.get("date", ""),
                    "category": t.get("personal_finance_category", {}).get("primary", t.get("category", [""])[0] if t.get("category") else ""),
                    "category_detail": t.get("personal_finance_category", {}).get("detailed", ""),
                    "pending": t.get("pending", False),
                    "account_id": t.get("account_id", ""),
                    "currency": t.get("iso_currency_code", "USD"),
                    "logo_url": t.get("logo_url"),
                })
            return {
                "transactions": txns,
                "total": data.get("total_transactions", len(txns)),
                "start_date": start_date,
                "end_date": end_date,
            }
        return {"error": data.get("error_message", "Failed to fetch transactions")}

    # ── Spending Breakdown ──────────────────────────────────────────────

    async def get_spending_breakdown(self, access_token: str, days: int = 30) -> dict:
        """Categorize spending over the given period."""
        txn_data = await self.get_transactions(access_token, days=days, count=500)
        if "error" in txn_data:
            return txn_data

        categories: dict[str, float] = {}
        total_spent = 0.0
        total_income = 0.0

        for txn in txn_data["transactions"]:
            amount = txn["amount"]
            cat = txn.get("category") or "Other"
            if amount > 0:  # Plaid: positive = money out (expense)
                total_spent += amount
                categories[cat] = categories.get(cat, 0) + amount
            else:
                total_income += abs(amount)

        # Sort categories by amount
        sorted_cats = sorted(categories.items(), key=lambda x: x[1], reverse=True)

        return {
            "total_spent": round(total_spent, 2),
            "total_income": round(total_income, 2),
            "net": round(total_income - total_spent, 2),
            "categories": [
                {"name": cat, "amount": round(amt, 2), "pct": round(amt / total_spent * 100, 1) if total_spent else 0}
                for cat, amt in sorted_cats
            ],
            "period_days": days,
            "transaction_count": len(txn_data["transactions"]),
        }

    # ── Demo Data (when Plaid not configured) ───────────────────────────

    def get_demo_data(self) -> dict:
        """Return demo financial data for UI rendering when Plaid isn't connected."""
        now = datetime.now(timezone.utc)
        return {
            "accounts": [
                {"id": "demo-checking", "name": "Primary Checking", "type": "depository", "subtype": "checking", "mask": "4521", "current": 8432.50, "available": 8232.50, "currency": "USD"},
                {"id": "demo-savings", "name": "High-Yield Savings", "type": "depository", "subtype": "savings", "mask": "7890", "current": 24150.00, "available": 24150.00, "currency": "USD"},
                {"id": "demo-credit", "name": "Cash Back Card", "type": "credit", "subtype": "credit card", "mask": "3344", "current": 1285.30, "available": 8714.70, "currency": "USD"},
            ],
            "total_current": 33867.80,
            "total_available": 41097.20,
            "spending": {
                "total_spent": 3842.50,
                "total_income": 6500.00,
                "net": 2657.50,
                "categories": [
                    {"name": "FOOD_AND_DRINK", "amount": 685.40, "pct": 17.8},
                    {"name": "RENT_AND_UTILITIES", "amount": 1650.00, "pct": 42.9},
                    {"name": "TRANSPORTATION", "amount": 342.80, "pct": 8.9},
                    {"name": "ENTERTAINMENT", "amount": 245.60, "pct": 6.4},
                    {"name": "SHOPPING", "amount": 428.90, "pct": 11.2},
                    {"name": "GENERAL_SERVICES", "amount": 189.50, "pct": 4.9},
                    {"name": "TRANSFER_OUT", "amount": 300.30, "pct": 7.8},
                ],
                "period_days": 30,
                "transaction_count": 67,
            },
            "transactions": [
                {"id": "demo-1", "name": "Whole Foods Market", "merchant": "Whole Foods", "amount": 87.42, "date": (now - timedelta(days=1)).strftime("%Y-%m-%d"), "category": "FOOD_AND_DRINK", "pending": False},
                {"id": "demo-2", "name": "Uber Trip", "merchant": "Uber", "amount": 24.50, "date": (now - timedelta(days=1)).strftime("%Y-%m-%d"), "category": "TRANSPORTATION", "pending": False},
                {"id": "demo-3", "name": "Netflix", "merchant": "Netflix", "amount": 15.99, "date": (now - timedelta(days=2)).strftime("%Y-%m-%d"), "category": "ENTERTAINMENT", "pending": False},
                {"id": "demo-4", "name": "Rent Payment", "merchant": None, "amount": 1650.00, "date": (now - timedelta(days=3)).strftime("%Y-%m-%d"), "category": "RENT_AND_UTILITIES", "pending": False},
                {"id": "demo-5", "name": "Amazon", "merchant": "Amazon", "amount": 129.99, "date": (now - timedelta(days=4)).strftime("%Y-%m-%d"), "category": "SHOPPING", "pending": False},
                {"id": "demo-6", "name": "Starbucks", "merchant": "Starbucks", "amount": 6.45, "date": (now - timedelta(days=4)).strftime("%Y-%m-%d"), "category": "FOOD_AND_DRINK", "pending": False},
                {"id": "demo-7", "name": "Direct Deposit", "merchant": None, "amount": -3250.00, "date": (now - timedelta(days=5)).strftime("%Y-%m-%d"), "category": "INCOME", "pending": False},
                {"id": "demo-8", "name": "Electric Company", "merchant": "ConEd", "amount": 142.30, "date": (now - timedelta(days=7)).strftime("%Y-%m-%d"), "category": "RENT_AND_UTILITIES", "pending": False},
                {"id": "demo-9", "name": "Spotify", "merchant": "Spotify", "amount": 9.99, "date": (now - timedelta(days=8)).strftime("%Y-%m-%d"), "category": "ENTERTAINMENT", "pending": False},
                {"id": "demo-10", "name": "Target", "merchant": "Target", "amount": 67.82, "date": (now - timedelta(days=9)).strftime("%Y-%m-%d"), "category": "SHOPPING", "pending": False},
            ],
            "budgets": [
                {"category": "FOOD_AND_DRINK", "limit": 800, "spent": 685.40, "pct": 85.7},
                {"category": "ENTERTAINMENT", "limit": 300, "spent": 245.60, "pct": 81.9},
                {"category": "SHOPPING", "limit": 500, "spent": 428.90, "pct": 85.8},
                {"category": "TRANSPORTATION", "limit": 400, "spent": 342.80, "pct": 85.7},
            ],
            "is_demo": True,
        }


plaid_service = PlaidService()
