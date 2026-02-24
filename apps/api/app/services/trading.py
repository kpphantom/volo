"""
VOLO — Trading Service
Live market data and paper trading via Alpaca / free APIs.
"""

import os
from typing import Optional
import httpx


class TradingService:
    """Handles trading operations — Alpaca for stocks, free APIs for crypto."""

    ALPACA_BASE = "https://paper-api.alpaca.markets"  # Paper trading by default
    ALPACA_DATA = "https://data.alpaca.markets"
    COINGECKO_BASE = "https://api.coingecko.com/api/v3"

    def __init__(self):
        self.alpaca_key = os.getenv("ALPACA_API_KEY", "")
        self.alpaca_secret = os.getenv("ALPACA_SECRET_KEY", "")
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    def _alpaca_headers(self) -> dict:
        return {
            "APCA-API-KEY-ID": self.alpaca_key,
            "APCA-API-SECRET-KEY": self.alpaca_secret,
        }

    def _check_alpaca(self) -> Optional[dict]:
        if not self.alpaca_key or not self.alpaca_secret:
            return {
                "error": "Alpaca not connected. Ask the user for their API key and secret.",
                "setup_hint": "Go to app.alpaca.markets → Paper Trading → API Keys",
            }
        return None

    async def get_portfolio(self, account: str = "all") -> dict:
        """Get portfolio overview."""
        # Try Alpaca for stocks
        if account in ("all", "stocks"):
            err = self._check_alpaca()
            if err and account == "stocks":
                return err

            if not err:
                client = await self._get_client()
                acct_resp = await client.get(
                    f"{self.ALPACA_BASE}/v2/account",
                    headers=self._alpaca_headers(),
                )
                positions_resp = await client.get(
                    f"{self.ALPACA_BASE}/v2/positions",
                    headers=self._alpaca_headers(),
                )

                if acct_resp.status_code == 200:
                    acct = acct_resp.json()
                    positions = positions_resp.json() if positions_resp.status_code == 200 else []

                    return {
                        "account": {
                            "equity": acct.get("equity", "0"),
                            "cash": acct.get("cash", "0"),
                            "buying_power": acct.get("buying_power", "0"),
                            "portfolio_value": acct.get("portfolio_value", "0"),
                            "day_pnl": str(
                                float(acct.get("equity", 0))
                                - float(acct.get("last_equity", 0))
                            ),
                        },
                        "positions": [
                            {
                                "symbol": p["symbol"],
                                "qty": p["qty"],
                                "market_value": p["market_value"],
                                "avg_entry": p["avg_entry_price"],
                                "current_price": p["current_price"],
                                "unrealized_pnl": p["unrealized_pl"],
                                "pnl_pct": p["unrealized_plpc"],
                                "side": p["side"],
                            }
                            for p in positions
                        ],
                        "total_positions": len(positions),
                    }

        return {
            "error": "No trading accounts connected.",
            "setup_hint": "Connect Alpaca (stocks) or Coinbase (crypto) to see your portfolio.",
        }

    async def get_quote(self, symbol: str) -> dict:
        """Get a real-time quote for a stock or crypto."""
        symbol = symbol.upper().strip()

        # Check if it's a crypto symbol
        crypto_map = {
            "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana",
            "DOGE": "dogecoin", "ADA": "cardano", "XRP": "ripple",
            "DOT": "polkadot", "AVAX": "avalanche-2", "MATIC": "matic-network",
            "LINK": "chainlink", "UNI": "uniswap", "AAVE": "aave",
        }

        # Strip -USD suffix for crypto
        base_symbol = symbol.replace("-USD", "").replace("USD", "")

        if base_symbol in crypto_map:
            return await self._get_crypto_quote(base_symbol, crypto_map[base_symbol])

        # Try Alpaca for stock data
        err = self._check_alpaca()
        if err:
            # Fallback: still try to give crypto data if available
            if base_symbol in crypto_map:
                return await self._get_crypto_quote(base_symbol, crypto_map[base_symbol])
            return err

        client = await self._get_client()
        resp = await client.get(
            f"{self.ALPACA_DATA}/v2/stocks/{symbol}/quotes/latest",
            headers=self._alpaca_headers(),
        )

        if resp.status_code == 200:
            data = resp.json()
            quote = data.get("quote", {})
            return {
                "symbol": symbol,
                "type": "stock",
                "bid": quote.get("bp", 0),
                "ask": quote.get("ap", 0),
                "mid": round((quote.get("bp", 0) + quote.get("ap", 0)) / 2, 2),
                "bid_size": quote.get("bs", 0),
                "ask_size": quote.get("as", 0),
                "timestamp": quote.get("t", ""),
            }

        return {"error": f"Could not get quote for {symbol}"}

    async def _get_crypto_quote(self, symbol: str, coingecko_id: str) -> dict:
        """Get crypto price from CoinGecko (free, no API key)."""
        client = await self._get_client()
        resp = await client.get(
            f"{self.COINGECKO_BASE}/simple/price",
            params={
                "ids": coingecko_id,
                "vs_currencies": "usd",
                "include_24hr_change": "true",
                "include_market_cap": "true",
                "include_24hr_vol": "true",
            },
        )

        if resp.status_code == 200:
            data = resp.json().get(coingecko_id, {})
            return {
                "symbol": symbol,
                "type": "crypto",
                "price": data.get("usd", 0),
                "change_24h_pct": round(data.get("usd_24h_change", 0), 2),
                "market_cap": data.get("usd_market_cap", 0),
                "volume_24h": data.get("usd_24h_vol", 0),
            }

        return {"error": f"Could not get crypto price for {symbol}"}

    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "market",
        limit_price: Optional[float] = None,
    ) -> dict:
        """Place a trading order via Alpaca. Returns order for approval display."""
        err = self._check_alpaca()
        if err:
            return err

        order_data = {
            "symbol": symbol.upper(),
            "qty": str(quantity),
            "side": side,
            "type": order_type,
            "time_in_force": "day",
        }
        if limit_price and order_type in ("limit", "stop_limit"):
            order_data["limit_price"] = str(limit_price)

        client = await self._get_client()
        resp = await client.post(
            f"{self.ALPACA_BASE}/v2/orders",
            headers=self._alpaca_headers(),
            json=order_data,
        )

        if resp.status_code in (200, 201):
            order = resp.json()
            return {
                "success": True,
                "order": {
                    "id": order["id"],
                    "symbol": order["symbol"],
                    "side": order["side"],
                    "qty": order["qty"],
                    "type": order["type"],
                    "status": order["status"],
                    "submitted_at": order["submitted_at"],
                },
            }

        return {"error": f"Order failed: {resp.text[:200]}"}
