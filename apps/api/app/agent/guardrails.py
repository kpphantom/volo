"""
VOLO — Guardrails
Safety layer for agent actions. Enforces approval rules,
content filtering, cost limits, and action constraints.
"""

import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger("volo.guardrails")


class ActionTier:
    """Approval tier levels."""
    AUTO = "auto"             # Execute immediately
    NOTIFY = "notify"         # Execute and notify user
    APPROVE = "approve"       # Require explicit user approval
    APPROVE_2FA = "approve_2fa"  # Require 2FA for high-risk actions


# ── Tool → Tier Mapping ─────────────────────

TOOL_TIERS = {
    # Auto-execute (read-only)
    "search_memory": ActionTier.AUTO,
    "github_list_repos": ActionTier.AUTO,
    "github_get_repo": ActionTier.AUTO,
    "github_list_prs": ActionTier.AUTO,
    "trading_quote": ActionTier.AUTO,
    "trading_portfolio": ActionTier.AUTO,
    "email_list_inbox": ActionTier.AUTO,
    "calendar_list_events": ActionTier.AUTO,
    "web3_wallet_balance": ActionTier.AUTO,
    "web3_gas_price": ActionTier.AUTO,
    "web3_defi_positions": ActionTier.AUTO,
    "machine_list_files": ActionTier.AUTO,
    "machine_read_file": ActionTier.AUTO,

    # Notify after (low-risk writes)
    "store_memory": ActionTier.NOTIFY,
    "email_draft": ActionTier.NOTIFY,

    # Require approval (medium-risk)
    "email_send": ActionTier.APPROVE,
    "calendar_schedule": ActionTier.APPROVE,
    "trading_place_order": ActionTier.APPROVE,
    "machine_run_command": ActionTier.APPROVE,
    "slack_send_message": ActionTier.APPROVE,
    "social_post": ActionTier.APPROVE,

    # Require 2FA (high-risk)
    "web3_send_transaction": ActionTier.APPROVE_2FA,
    "billing_change_plan": ActionTier.APPROVE_2FA,
}

# ── Content Safety ───────────────────────────

BLOCKED_PATTERNS = [
    "rm -rf /",
    "drop table",
    "delete from users",
    "> /dev/sda",
    "chmod 777 /",
    "curl | sh",
    "eval(",
]


class Guardrails:
    """
    Safety layer that validates all agent actions before execution.
    """

    def __init__(self):
        self.daily_spend_limit = 1000.0  # USD
        self.daily_trade_limit = 10000.0
        self._daily_spend = 0.0
        self._daily_trades = 0.0
        self._action_log: list[dict] = []

    def get_tier(self, tool_name: str) -> str:
        """Get the approval tier for a tool."""
        return TOOL_TIERS.get(tool_name, ActionTier.APPROVE)

    def check_action(
        self,
        tool_name: str,
        parameters: dict,
        user_id: str = "default",
    ) -> dict:
        """
        Check if an action is allowed.
        Returns: {"allowed": bool, "tier": str, "reason": str}
        """
        tier = self.get_tier(tool_name)

        # Content safety check
        safety = self._check_content_safety(tool_name, parameters)
        if not safety["safe"]:
            return {
                "allowed": False,
                "tier": "blocked",
                "reason": safety["reason"],
            }

        # Spending limit check
        if tool_name == "trading_place_order":
            qty = float(parameters.get("quantity", 0))
            price = float(parameters.get("limit_price", 0) or 100)  # rough estimate
            order_value = qty * price
            if self._daily_trades + order_value > self.daily_trade_limit:
                return {
                    "allowed": False,
                    "tier": "blocked",
                    "reason": f"Daily trade limit of ${self.daily_trade_limit:,.0f} would be exceeded.",
                }

        # Auto-execute tier
        if tier == ActionTier.AUTO:
            return {"allowed": True, "tier": tier, "reason": "Auto-approved (read-only)"}

        # Notify tier
        if tier == ActionTier.NOTIFY:
            return {"allowed": True, "tier": tier, "reason": "Will notify user after execution"}

        # Approve tier — requires user confirmation
        if tier == ActionTier.APPROVE:
            return {
                "allowed": False,
                "tier": tier,
                "reason": "This action requires your explicit approval.",
                "approval_required": True,
                "action_description": self._describe_action(tool_name, parameters),
            }

        # 2FA tier
        if tier == ActionTier.APPROVE_2FA:
            return {
                "allowed": False,
                "tier": tier,
                "reason": "This high-risk action requires 2FA confirmation.",
                "approval_required": True,
                "requires_2fa": True,
                "action_description": self._describe_action(tool_name, parameters),
            }

        return {"allowed": False, "tier": "unknown", "reason": "Unknown action tier"}

    def record_action(self, tool_name: str, parameters: dict, result: dict):
        """Record an executed action for audit trail."""
        self._action_log.append({
            "tool": tool_name,
            "parameters": parameters,
            "success": "error" not in result,
            "timestamp": datetime.utcnow().isoformat(),
        })

        # Track spending
        if tool_name == "trading_place_order" and "error" not in result:
            qty = float(parameters.get("quantity", 0))
            price = float(parameters.get("limit_price", 0) or 100)
            self._daily_trades += qty * price

    def _check_content_safety(self, tool_name: str, parameters: dict) -> dict:
        """Check for dangerous content in parameters."""
        param_str = str(parameters).lower()
        for pattern in BLOCKED_PATTERNS:
            if pattern in param_str:
                return {"safe": False, "reason": f"Blocked dangerous pattern: {pattern}"}
        return {"safe": True}

    def _describe_action(self, tool_name: str, parameters: dict) -> str:
        """Generate human-readable description of an action."""
        descriptions = {
            "trading_place_order": lambda p: f"{p.get('side', 'buy').upper()} {p.get('quantity', '?')} {p.get('symbol', '?')} ({p.get('order_type', 'market')})",
            "email_send": lambda p: f"Send email to {p.get('to', '?')}: {p.get('subject', '?')}",
            "calendar_schedule": lambda p: f"Schedule '{p.get('title', '?')}' at {p.get('datetime', '?')}",
            "machine_run_command": lambda p: f"Run command: {p.get('command', '?')[:80]}",
            "slack_send_message": lambda p: f"Send Slack message to #{p.get('channel', '?')}",
        }
        formatter = descriptions.get(tool_name)
        if formatter:
            try:
                return formatter(parameters)
            except Exception:
                pass
        return f"Execute {tool_name} with {len(parameters)} parameters"

    def get_stats(self) -> dict:
        return {
            "daily_spend": self._daily_spend,
            "daily_trades": self._daily_trades,
            "actions_today": len(self._action_log),
            "spend_limit": self.daily_spend_limit,
            "trade_limit": self.daily_trade_limit,
        }


# Singleton
guardrails = Guardrails()
