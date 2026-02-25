"""
VOLO — Tool Registry
Defines all tools available to the agent with LIVE execution.
Each tool is a capability the agent can invoke during conversation.
"""

from typing import Any, Callable, Optional
from app.services.github import GitHubService
from app.services.trading import TradingService
from app.services.email import EmailService
from app.services.calendar import CalendarService
from app.services.slack import SlackService
from app.services.social import SocialService
from app.services.machine import MachineService
from app.services.web3 import Web3Service
from app.services.plaid_service import plaid_service
from app.agent.memory import MemoryManager


class Tool:
    """A tool the agent can invoke."""

    def __init__(
        self,
        name: str,
        description: str,
        parameters: dict,
        category: str,
        handler: Optional[Callable] = None,
    ):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.category = category
        self._handler = handler

    def to_anthropic_format(self) -> dict:
        """Convert to Anthropic tool format."""
        props = {}
        required = []
        for k, v in self.parameters.items():
            prop = {pk: pv for pk, pv in v.items() if pk != "required"}
            props[k] = prop
            if v.get("required", False):
                required.append(k)

        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": props,
                "required": required,
            },
        }

    async def execute(self, **kwargs) -> Any:
        """Execute the tool."""
        if self._handler:
            return await self._handler(**kwargs)
        return {"error": f"Tool '{self.name}' has no handler configured."}


class ToolRegistry:
    """Registry of all available tools with live execution."""

    def __init__(self):
        self.tools: dict[str, Tool] = {}
        # Service instances — shared across tools
        self.github = GitHubService()
        self.trading = TradingService()
        self.memory = MemoryManager()
        self.email = EmailService()
        self.calendar = CalendarService()
        self.slack = SlackService()
        self.social = SocialService()
        self.machine = MachineService()
        self.web3 = Web3Service()
        self._register_builtin_tools()

    def register(self, tool: Tool):
        self.tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self.tools.get(name)

    def get_tool_definitions(self) -> list[dict]:
        return [tool.to_anthropic_format() for tool in self.tools.values()]

    async def execute(self, name: str, **kwargs) -> Any:
        tool = self.get(name)
        if not tool:
            return {"error": f"Tool '{name}' not found"}
        try:
            result = await tool.execute(**kwargs)
            return result
        except Exception as e:
            return {"error": f"Tool '{name}' failed: {str(e)}"}

    def _register_builtin_tools(self):
        """Register all built-in tools with live handlers."""

        # =====================================================================
        # MEMORY TOOLS
        # =====================================================================
        self.register(Tool(
            name="store_memory",
            description="Store a fact, preference, or piece of information about the user for future reference. Use this when the user shares something you should remember.",
            parameters={
                "category": {
                    "type": "string",
                    "enum": ["fact", "preference", "relationship", "project", "decision", "goal"],
                    "description": "Category of the memory",
                    "required": True,
                },
                "content": {
                    "type": "string",
                    "description": "The information to remember",
                    "required": True,
                },
                "source": {
                    "type": "string",
                    "description": "Where this information came from",
                },
            },
            category="memory",
            handler=self._handle_store_memory,
        ))

        self.register(Tool(
            name="search_memory",
            description="Search your memory for information about the user, their projects, preferences, or past decisions.",
            parameters={
                "query": {
                    "type": "string",
                    "description": "What to search for in memory",
                    "required": True,
                },
            },
            category="memory",
            handler=self._handle_search_memory,
        ))

        # =====================================================================
        # GITHUB TOOLS
        # =====================================================================
        self.register(Tool(
            name="github_list_repos",
            description="List all GitHub repositories for the connected user. Shows repo name, language, description, and last updated time.",
            parameters={
                "sort": {
                    "type": "string",
                    "enum": ["updated", "created", "pushed", "name"],
                    "description": "How to sort the repositories",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of repos to return (default 20)",
                },
            },
            category="code",
            handler=self._handle_github_list_repos,
        ))

        self.register(Tool(
            name="github_get_repo",
            description="Get detailed information about a specific GitHub repository including languages, recent commits, and activity.",
            parameters={
                "repo": {
                    "type": "string",
                    "description": "Repository name in 'owner/repo' format",
                    "required": True,
                },
            },
            category="code",
            handler=self._handle_github_get_repo,
        ))

        self.register(Tool(
            name="github_list_prs",
            description="List pull requests for a repository.",
            parameters={
                "repo": {
                    "type": "string",
                    "description": "Repository name in 'owner/repo' format",
                    "required": True,
                },
                "state": {
                    "type": "string",
                    "enum": ["open", "closed", "all"],
                    "description": "Filter by PR state",
                },
            },
            category="code",
            handler=self._handle_github_list_prs,
        ))

        # =====================================================================
        # TRADING TOOLS
        # =====================================================================
        self.register(Tool(
            name="trading_portfolio",
            description="Get the user's current trading portfolio — positions, P&L, allocation.",
            parameters={
                "account": {
                    "type": "string",
                    "enum": ["all", "stocks", "crypto"],
                    "description": "Which account to show",
                },
            },
            category="finance",
            handler=self._handle_trading_portfolio,
        ))

        self.register(Tool(
            name="trading_quote",
            description="Get a real-time quote for a stock or cryptocurrency.",
            parameters={
                "symbol": {
                    "type": "string",
                    "description": "Ticker symbol (e.g., AAPL, BTC, ETH, SOL)",
                    "required": True,
                },
            },
            category="finance",
            handler=self._handle_trading_quote,
        ))

        self.register(Tool(
            name="trading_place_order",
            description="Place a trading order. ALWAYS requires user approval before execution.",
            parameters={
                "symbol": {
                    "type": "string",
                    "description": "Ticker symbol",
                    "required": True,
                },
                "side": {
                    "type": "string",
                    "enum": ["buy", "sell"],
                    "required": True,
                },
                "quantity": {
                    "type": "number",
                    "description": "Number of shares/units",
                    "required": True,
                },
                "order_type": {
                    "type": "string",
                    "enum": ["market", "limit", "stop", "stop_limit"],
                    "description": "Order type",
                    "required": True,
                },
                "limit_price": {
                    "type": "number",
                    "description": "Limit price (required for limit orders)",
                },
            },
            category="finance",
            handler=self._handle_trading_place_order,
        ))

        # =====================================================================
        # COMMUNICATION TOOLS — Live handlers via services
        # =====================================================================
        self.register(Tool(
            name="email_list_inbox",
            description="List recent emails from the user's inbox.",
            parameters={
                "filter": {
                    "type": "string",
                    "enum": ["all", "unread", "important", "needs_reply"],
                    "description": "Filter type",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of emails to return",
                },
            },
            category="communication",
            handler=self._handle_email_list_inbox,
        ))

        self.register(Tool(
            name="email_draft",
            description="Draft an email for the user to review before sending.",
            parameters={
                "to": {"type": "string", "description": "Recipient email", "required": True},
                "subject": {"type": "string", "description": "Subject line", "required": True},
                "body": {"type": "string", "description": "Email body", "required": True},
            },
            category="communication",
            handler=self._handle_email_draft,
        ))

        self.register(Tool(
            name="email_send",
            description="Send an email. Requires user approval first.",
            parameters={
                "to": {"type": "string", "description": "Recipient email", "required": True},
                "subject": {"type": "string", "description": "Subject line", "required": True},
                "body": {"type": "string", "description": "Email body (plain text or HTML)", "required": True},
            },
            category="communication",
            handler=self._handle_email_send,
        ))

        self.register(Tool(
            name="calendar_list_events",
            description="List upcoming calendar events.",
            parameters={
                "days": {"type": "integer", "description": "Days ahead (default 7)"},
            },
            category="communication",
            handler=self._handle_calendar_list_events,
        ))

        self.register(Tool(
            name="calendar_schedule",
            description="Schedule a new calendar event.",
            parameters={
                "title": {"type": "string", "description": "Event title", "required": True},
                "datetime": {"type": "string", "description": "ISO datetime", "required": True},
                "duration_minutes": {"type": "integer", "description": "Duration", "required": True},
                "attendees": {"type": "array", "items": {"type": "string"}, "description": "Attendees"},
            },
            category="communication",
            handler=self._handle_calendar_schedule,
        ))

        self.register(Tool(
            name="slack_send_message",
            description="Send a message to a Slack channel or DM.",
            parameters={
                "channel": {"type": "string", "description": "Channel name or ID", "required": True},
                "message": {"type": "string", "description": "Message text", "required": True},
                "thread_ts": {"type": "string", "description": "Thread timestamp for replies"},
            },
            category="communication",
            handler=self._handle_slack_send,
        ))

        self.register(Tool(
            name="slack_list_channels",
            description="List Slack channels.",
            parameters={},
            category="communication",
            handler=self._handle_slack_list_channels,
        ))

        self.register(Tool(
            name="social_post",
            description="Post to social media (Twitter, LinkedIn, or both).",
            parameters={
                "content": {"type": "string", "description": "Post content", "required": True},
                "platforms": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["twitter", "linkedin"]},
                    "description": "Which platforms to post to",
                    "required": True,
                },
            },
            category="communication",
            handler=self._handle_social_post,
        ))

        # =====================================================================
        # MACHINE CONTROL — Live handlers
        # =====================================================================
        self.register(Tool(
            name="machine_run_command",
            description="Execute a shell command on the user's connected machine. Safety-checked.",
            parameters={
                "command": {"type": "string", "description": "Shell command", "required": True},
                "machine_id": {"type": "string", "description": "Machine ID (default: local)"},
            },
            category="machine",
            handler=self._handle_machine_run_command,
        ))

        self.register(Tool(
            name="machine_list_files",
            description="List files in a directory on a connected machine.",
            parameters={
                "path": {"type": "string", "description": "Directory path", "required": True},
            },
            category="machine",
            handler=self._handle_machine_list_files,
        ))

        self.register(Tool(
            name="machine_read_file",
            description="Read a file from a connected machine.",
            parameters={
                "path": {"type": "string", "description": "File path", "required": True},
            },
            category="machine",
            handler=self._handle_machine_read_file,
        ))

        # =====================================================================
        # WEB3 TOOLS — Live handlers
        # =====================================================================
        self.register(Tool(
            name="web3_wallet_balance",
            description="Get the balance of a connected crypto wallet.",
            parameters={
                "chain": {
                    "type": "string",
                    "enum": ["ethereum", "solana", "polygon", "arbitrum", "base"],
                    "description": "Blockchain network",
                    "required": True,
                },
            },
            category="web3",
            handler=self._handle_web3_wallet_balance,
        ))

        self.register(Tool(
            name="web3_defi_positions",
            description="Get DeFi positions — lending, borrowing, LP, yields.",
            parameters={
                "protocol": {"type": "string", "description": "Protocol or 'all'"},
            },
            category="web3",
            handler=self._handle_web3_defi_positions,
        ))

        self.register(Tool(
            name="web3_gas_price",
            description="Get current gas prices for a blockchain.",
            parameters={
                "chain": {
                    "type": "string",
                    "enum": ["ethereum", "polygon", "arbitrum", "base"],
                    "description": "Blockchain",
                    "required": True,
                },
            },
            category="web3",
            handler=self._handle_web3_gas_price,
        ))

        # =====================================================================
        # FINANCE / PLAID TOOLS
        # =====================================================================
        self.register(Tool(
            name="finance_get_balances",
            description="Get the user's bank account balances including checking, savings, and credit cards. Shows current balance and available balance per account.",
            parameters={},
            category="finance",
            handler=self._handle_finance_get_balances,
        ))

        self.register(Tool(
            name="finance_get_transactions",
            description="Get recent bank transactions. Shows merchant name, amount, date, and category for each transaction.",
            parameters={
                "days": {"type": "integer", "description": "Number of days of history (default 30, max 90)"},
                "count": {"type": "integer", "description": "Max transactions to return (default 20)"},
            },
            category="finance",
            handler=self._handle_finance_get_transactions,
        ))

        self.register(Tool(
            name="finance_spending_breakdown",
            description="Get a spending breakdown by category (food, rent, entertainment, shopping, etc.) for a time period. Shows total spent, income, net savings, and per-category amounts with percentages.",
            parameters={
                "days": {"type": "integer", "description": "Number of days to analyze (default 30)"},
            },
            category="finance",
            handler=self._handle_finance_spending_breakdown,
        ))

        self.register(Tool(
            name="finance_overview",
            description="Get a complete finance overview — accounts, balances, spending breakdown, recent transactions, and budget status. Best tool for a general financial summary.",
            parameters={},
            category="finance",
            handler=self._handle_finance_overview,
        ))

        # =====================================================================
        # ENHANCED CALENDAR & EMAIL TOOLS
        # =====================================================================
        self.register(Tool(
            name="calendar_find_free_slots",
            description="Find available free time slots in the user's calendar. Useful for scheduling meetings.",
            parameters={
                "days": {"type": "integer", "description": "Days ahead to search (default 3)"},
                "duration_minutes": {"type": "integer", "description": "Required slot duration in minutes (default 30)"},
            },
            category="communication",
            handler=self._handle_calendar_find_free_slots,
        ))

        self.register(Tool(
            name="email_triage",
            description="Triage the user's inbox — get unread or important emails that need attention. Returns prioritized list with subject, sender, and snippet.",
            parameters={
                "filter": {
                    "type": "string",
                    "enum": ["unread", "important", "needs_reply", "all"],
                    "description": "Which emails to show",
                },
                "limit": {"type": "integer", "description": "Max emails (default 10)"},
            },
            category="communication",
            handler=self._handle_email_triage,
        ))

    # =========================================================================
    # HANDLER IMPLEMENTATIONS
    # =========================================================================

    async def _handle_store_memory(self, **kwargs) -> dict:
        result = await self.memory.store(
            category=kwargs.get("category", "fact"),
            content=kwargs.get("content", ""),
            source=kwargs.get("source", "conversation"),
        )
        return {"stored": True, "memory_id": result["id"], "content": result["content"]}

    async def _handle_search_memory(self, **kwargs) -> dict:
        results = await self.memory.search(query=kwargs.get("query", ""))
        return {"results": results, "count": len(results)}

    async def _handle_github_list_repos(self, **kwargs) -> dict:
        return await self.github.list_repos(
            sort=kwargs.get("sort", "updated"),
            limit=kwargs.get("limit", 20),
        )

    async def _handle_github_get_repo(self, **kwargs) -> dict:
        repo = kwargs.get("repo", "")
        if not repo:
            return {"error": "Missing required parameter: repo"}
        return await self.github.get_repo(repo)

    async def _handle_github_list_prs(self, **kwargs) -> dict:
        repo = kwargs.get("repo", "")
        if not repo:
            return {"error": "Missing required parameter: repo"}
        return await self.github.list_prs(repo, state=kwargs.get("state", "open"))

    async def _handle_trading_portfolio(self, **kwargs) -> dict:
        return await self.trading.get_portfolio(account=kwargs.get("account", "all"))

    async def _handle_trading_quote(self, **kwargs) -> dict:
        symbol = kwargs.get("symbol", "")
        if not symbol:
            return {"error": "Missing required parameter: symbol"}
        return await self.trading.get_quote(symbol)

    async def _handle_trading_place_order(self, **kwargs) -> dict:
        required = ["symbol", "side", "quantity", "order_type"]
        for field in required:
            if field not in kwargs:
                return {"error": f"Missing required parameter: {field}"}
        return await self.trading.place_order(
            symbol=kwargs["symbol"],
            side=kwargs["side"],
            quantity=kwargs["quantity"],
            order_type=kwargs["order_type"],
            limit_price=kwargs.get("limit_price"),
        )

    def _handle_not_connected(self, service_name: str, connect_to: str):
        """Factory for creating 'not connected' handlers."""
        async def handler(**kwargs):
            return {
                "error": f"{service_name} is not connected yet.",
                "message": f"To use this feature, connect {connect_to} through the integrations setup.",
                "action": "Ask the user if they'd like to set up this integration now.",
            }
        return handler

    # =========================================================================
    # EMAIL HANDLERS
    # =========================================================================

    async def _handle_email_list_inbox(self, **kwargs) -> dict:
        return await self.email.list_inbox(
            filter_type=kwargs.get("filter", "all"),
            limit=kwargs.get("limit", 20),
        )

    async def _handle_email_draft(self, **kwargs) -> dict:
        return await self.email.draft_email(
            to=kwargs["to"],
            subject=kwargs["subject"],
            body=kwargs["body"],
        )

    async def _handle_email_send(self, **kwargs) -> dict:
        return await self.email.send_email(
            to=kwargs["to"],
            subject=kwargs["subject"],
            body=kwargs["body"],
        )

    # =========================================================================
    # CALENDAR HANDLERS
    # =========================================================================

    async def _handle_calendar_list_events(self, **kwargs) -> dict:
        return await self.calendar.list_events(days=kwargs.get("days", 7))

    async def _handle_calendar_schedule(self, **kwargs) -> dict:
        return await self.calendar.create_event(
            title=kwargs["title"],
            start_time=kwargs["datetime"],
            duration_minutes=kwargs.get("duration_minutes", 60),
            attendees=kwargs.get("attendees", []),
        )

    # =========================================================================
    # SLACK HANDLERS
    # =========================================================================

    async def _handle_slack_send(self, **kwargs) -> dict:
        return await self.slack.send_message(
            channel=kwargs["channel"],
            text=kwargs["message"],
            thread_ts=kwargs.get("thread_ts"),
        )

    async def _handle_slack_list_channels(self, **kwargs) -> dict:
        return await self.slack.list_channels()

    # =========================================================================
    # SOCIAL HANDLERS
    # =========================================================================

    async def _handle_social_post(self, **kwargs) -> dict:
        platforms = kwargs.get("platforms", ["twitter"])
        content = kwargs["content"]
        if len(platforms) > 1 or "all" in platforms:
            return await self.social.post_to_all(content)
        elif "twitter" in platforms:
            return await self.social.twitter_post(content)
        elif "linkedin" in platforms:
            return await self.social.linkedin_post(content)
        return {"error": "Unknown platform"}

    # =========================================================================
    # MACHINE HANDLERS
    # =========================================================================

    async def _handle_machine_run_command(self, **kwargs) -> dict:
        return await self.machine.run_command(
            command=kwargs["command"],
            machine_id=kwargs.get("machine_id", "local"),
        )

    async def _handle_machine_list_files(self, **kwargs) -> dict:
        return await self.machine.list_files(path=kwargs["path"])

    async def _handle_machine_read_file(self, **kwargs) -> dict:
        return await self.machine.read_file(path=kwargs["path"])

    # =========================================================================
    # WEB3 HANDLERS
    # =========================================================================

    async def _handle_web3_wallet_balance(self, **kwargs) -> dict:
        return await self.web3.get_wallet_balance(chain=kwargs["chain"])

    async def _handle_web3_defi_positions(self, **kwargs) -> dict:
        return await self.web3.get_defi_positions(protocol=kwargs.get("protocol", "all"))

    async def _handle_web3_gas_price(self, **kwargs) -> dict:
        return await self.web3.get_gas_price(chain=kwargs["chain"])

    # =========================================================================
    # FINANCE / PLAID HANDLERS
    # =========================================================================

    async def _handle_finance_get_balances(self, **kwargs) -> dict:
        # Try real Plaid data first, fall back to demo
        from app.database import SessionLocal
        from app.models import Integration
        try:
            async with SessionLocal() as db:
                from sqlalchemy import select
                result = await db.execute(
                    select(Integration).where(
                        Integration.type == "plaid"
                    ).limit(1)
                )
                integration = result.scalar_one_or_none()
                if integration and integration.config:
                    access_token = integration.config.get("access_token")
                    if access_token:
                        return await plaid_service.get_balances(access_token)
        except Exception:
            pass
        # Return demo data
        demo = plaid_service.get_demo_data()
        return {
            "accounts": demo["accounts"],
            "total_current": demo["total_current"],
            "total_available": demo["total_available"],
            "is_demo": True,
        }

    async def _handle_finance_get_transactions(self, **kwargs) -> dict:
        days = min(kwargs.get("days", 30), 90)
        count = min(kwargs.get("count", 20), 100)
        from app.database import SessionLocal
        from app.models import Integration
        try:
            async with SessionLocal() as db:
                from sqlalchemy import select
                result = await db.execute(
                    select(Integration).where(
                        Integration.type == "plaid"
                    ).limit(1)
                )
                integration = result.scalar_one_or_none()
                if integration and integration.config:
                    access_token = integration.config.get("access_token")
                    if access_token:
                        return await plaid_service.get_transactions(access_token, days=days, count=count)
        except Exception:
            pass
        demo = plaid_service.get_demo_data()
        return {"transactions": demo["transactions"][:count], "is_demo": True}

    async def _handle_finance_spending_breakdown(self, **kwargs) -> dict:
        days = min(kwargs.get("days", 30), 90)
        from app.database import SessionLocal
        from app.models import Integration
        try:
            async with SessionLocal() as db:
                from sqlalchemy import select
                result = await db.execute(
                    select(Integration).where(
                        Integration.type == "plaid"
                    ).limit(1)
                )
                integration = result.scalar_one_or_none()
                if integration and integration.config:
                    access_token = integration.config.get("access_token")
                    if access_token:
                        return await plaid_service.get_spending_breakdown(access_token, days=days)
        except Exception:
            pass
        demo = plaid_service.get_demo_data()
        return {**demo["spending"], "is_demo": True}

    async def _handle_finance_overview(self, **kwargs) -> dict:
        from app.database import SessionLocal
        from app.models import Integration
        try:
            async with SessionLocal() as db:
                from sqlalchemy import select
                result = await db.execute(
                    select(Integration).where(
                        Integration.type == "plaid"
                    ).limit(1)
                )
                integration = result.scalar_one_or_none()
                if integration and integration.config:
                    access_token = integration.config.get("access_token")
                    if access_token:
                        balances = await plaid_service.get_balances(access_token)
                        spending = await plaid_service.get_spending_breakdown(access_token)
                        txns = await plaid_service.get_transactions(access_token, count=10)
                        return {
                            **balances,
                            "spending": spending,
                            "recent_transactions": txns.get("transactions", [])[:10],
                            "is_demo": False,
                        }
        except Exception:
            pass
        return {**plaid_service.get_demo_data(), "is_demo": True}

    # =========================================================================
    # ENHANCED CALENDAR & EMAIL HANDLERS
    # =========================================================================

    async def _handle_calendar_find_free_slots(self, **kwargs) -> dict:
        return await self.calendar.find_free_slots(
            days_ahead=kwargs.get("days", 3),
            duration_minutes=kwargs.get("duration_minutes", 30),
        )

    async def _handle_email_triage(self, **kwargs) -> dict:
        return await self.email.list_inbox(
            filter_type=kwargs.get("filter", "unread"),
            limit=kwargs.get("limit", 10),
        )
