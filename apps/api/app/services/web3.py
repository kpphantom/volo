"""
VOLO — Web3 Service
Blockchain wallet, DeFi, and transaction management.
"""

import os
import logging
from typing import Optional
import httpx

logger = logging.getLogger("volo.web3")


class Web3Service:
    """Handles Web3 operations across multiple chains."""

    ETHERSCAN_BASE = "https://api.etherscan.io/api"
    SOLSCAN_BASE = "https://public-api.solscan.io"

    def __init__(self):
        self.eth_address: Optional[str] = os.getenv("ETH_WALLET_ADDRESS", "")
        self.sol_address: Optional[str] = os.getenv("SOL_WALLET_ADDRESS", "")
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def get_wallet_balance(self, chain: str = "ethereum") -> dict:
        """Get wallet balance for a specific chain."""
        if chain == "ethereum":
            if not self.eth_address:
                return {"error": "No Ethereum wallet connected. Add ETH_WALLET_ADDRESS."}
            return await self._get_eth_balance()
        elif chain == "solana":
            if not self.sol_address:
                return {"error": "No Solana wallet connected. Add SOL_WALLET_ADDRESS."}
            return await self._get_sol_balance()
        else:
            return {"error": f"Chain '{chain}' not supported yet. Supported: ethereum, solana"}

    async def _get_eth_balance(self) -> dict:
        client = await self._get_client()
        etherscan_key = os.getenv("ETHERSCAN_API_KEY", "")
        resp = await client.get(
            self.ETHERSCAN_BASE,
            params={
                "module": "account",
                "action": "balance",
                "address": self.eth_address,
                "apikey": etherscan_key,
            },
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "1":
                balance_wei = int(data.get("result", 0))
                balance_eth = balance_wei / 1e18
                return {
                    "chain": "ethereum",
                    "address": self.eth_address,
                    "balance": balance_eth,
                    "symbol": "ETH",
                }
        return {"error": "Failed to fetch ETH balance"}

    async def _get_sol_balance(self) -> dict:
        client = await self._get_client()
        resp = await client.get(
            f"{self.SOLSCAN_BASE}/account/{self.sol_address}",
        )
        if resp.status_code == 200:
            data = resp.json()
            return {
                "chain": "solana",
                "address": self.sol_address,
                "balance": data.get("lamports", 0) / 1e9,
                "symbol": "SOL",
            }
        return {"error": "Failed to fetch SOL balance"}

    async def get_gas_price(self, chain: str = "ethereum") -> dict:
        """Get current gas prices."""
        if chain != "ethereum":
            return {"error": f"Gas price for {chain} not supported yet."}

        client = await self._get_client()
        etherscan_key = os.getenv("ETHERSCAN_API_KEY", "")
        resp = await client.get(
            self.ETHERSCAN_BASE,
            params={
                "module": "gastracker",
                "action": "gasoracle",
                "apikey": etherscan_key,
            },
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "1":
                result = data.get("result", {})
                return {
                    "chain": "ethereum",
                    "slow": f"{result.get('SafeGasPrice', '?')} Gwei",
                    "standard": f"{result.get('ProposeGasPrice', '?')} Gwei",
                    "fast": f"{result.get('FastGasPrice', '?')} Gwei",
                }
        return {"error": "Failed to get gas prices"}

    async def get_defi_positions(self, protocol: str = "all") -> dict:
        """Get DeFi positions (placeholder — would integrate with DefiLlama/Zapper)."""
        return {
            "positions": [],
            "message": "DeFi position tracking requires wallet connection. Connect your wallet in Settings.",
            "supported_protocols": ["Aave", "Uniswap", "Compound", "Lido", "Curve"],
        }

    async def get_nfts(self, chain: str = "ethereum") -> dict:
        """Get NFTs owned by the connected wallet."""
        if not self.eth_address:
            return {"error": "No wallet connected."}
        return {
            "nfts": [],
            "message": "NFT tracking available after connecting an Alchemy or Moralis API key.",
        }
