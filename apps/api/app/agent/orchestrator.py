"""
VOLO — Agent Orchestrator
The brain of Volo. Routes user intent to specialized sub-agents,
manages tool calls, memory, multi-step planning, guardrails, and context windows.
"""

import os
import json
from typing import AsyncGenerator
from datetime import datetime

from app.agent.tools import ToolRegistry
from app.agent.memory import MemoryManager
from app.agent.prompts import SYSTEM_PROMPT, ONBOARDING_PROMPT
from app.agent.context_manager import ContextWindow
from app.agent.guardrails import guardrails
from app.agent.multi_agent import MultiAgentOrchestrator


class AgentOrchestrator:
    """
    Core agent that:
    1. Classifies user intent and routes to sub-agents
    2. Retrieves relevant memory/context with RAG
    3. Manages context window to stay within token limits
    4. Applies guardrails and safety checks
    5. Calls the LLM with appropriate tools
    6. Executes tool calls with approval flow
    7. Streams response back
    8. Stores new memories from the conversation
    """

    MAX_TOOL_ROUNDS = 10

    def __init__(self):
        self.tool_registry = ToolRegistry()
        self.memory = MemoryManager()
        self.model = os.getenv("DEFAULT_MODEL", "claude-sonnet-4-20250514")
        self.context_window = ContextWindow()
        self.multi_agent = MultiAgentOrchestrator()
        self._client = None
        self._openai_client = None

    @property
    def client(self):
        """Lazy-initialize the Anthropic client."""
        if self._client is None:
            api_key = os.getenv("ANTHROPIC_API_KEY", "")
            if not api_key or api_key.startswith("your-") or len(api_key) < 20:
                return None
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=api_key)
            except Exception:
                self._client = None
        return self._client

    @property
    def openai_client(self):
        """Lazy-initialize the OpenAI client for fallback."""
        if self._openai_client is None:
            api_key = os.getenv("OPENAI_API_KEY", "")
            if not api_key or api_key.startswith("your-") or len(api_key) < 20:
                return None
            try:
                import openai
                self._openai_client = openai.OpenAI(api_key=api_key)
            except Exception:
                self._openai_client = None
        return self._openai_client

    async def run(
        self,
        message: str,
        conversation_id: str,
        history: list[dict] = None,
    ) -> AsyncGenerator[dict, None]:
        """
        Main agent loop. Processes a user message and yields response chunks.
        Supports multi-model fallback, guardrails, and context management.
        """
        history = history or []

        # 1. Retrieve relevant memories
        relevant_memories = await self.memory.search(message)
        memory_context = self._format_memories(relevant_memories)

        # 2. Determine if this is onboarding
        is_onboarding = len(history) <= 2
        system_prompt = ONBOARDING_PROMPT if is_onboarding else SYSTEM_PROMPT

        # Inject current datetime
        now = datetime.now()
        system_prompt = system_prompt.replace(
            "{datetime}", now.strftime("%Y-%m-%d %H:%M:%S")
        ).replace(
            "{timezone}", "local"
        )

        if memory_context:
            system_prompt += f"\n\n## Your Memory (things you know about this user):\n{memory_context}"

        # 3. Build and trim messages within context window
        messages = self._build_messages(history, message)
        messages = self.context_window.build_messages(
            messages=messages,
            system_prompt=system_prompt,
            memories=relevant_memories,
            model=self.model,
        )

        # 4. Get available tools
        tools = self.tool_registry.get_tool_definitions()

        # 5. Route — try primary model, fall back to secondary
        if self.client:
            async for chunk in self._run_agent_loop(system_prompt, messages, tools):
                yield chunk
        elif self.openai_client:
            async for chunk in self._run_openai_loop(system_prompt, messages, tools):
                yield chunk
        else:
            async for chunk in self._fallback_response(message, is_onboarding):
                yield chunk

    async def _run_agent_loop(
        self,
        system_prompt: str,
        messages: list[dict],
        tools: list[dict],
    ) -> AsyncGenerator[dict, None]:
        """
        Full agent loop with tool execution and guardrails.
        """
        round_count = 0

        while round_count < self.MAX_TOOL_ROUNDS:
            round_count += 1

            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    system=system_prompt,
                    messages=messages,
                    tools=tools if tools else None,
                )
            except Exception as e:
                # Try OpenAI fallback on Anthropic failure
                if self.openai_client:
                    yield {"content": "\n*Switching to fallback model...*\n"}
                    async for chunk in self._run_openai_loop(system_prompt, messages, tools):
                        yield chunk
                    return
                yield {"content": f"\n\n*Error communicating with AI model: {str(e)}*"}
                return

            has_tool_use = False
            text_content = ""
            tool_results = []

            for block in response.content:
                if block.type == "text":
                    text_content += block.text
                elif block.type == "tool_use":
                    has_tool_use = True

                    # Check guardrails before executing
                    check = guardrails.check_action(
                        tool_name=block.name,
                        parameters=block.input,
                        user_tier="admin",
                    )

                    if not check["allowed"]:
                        # Tool blocked by guardrails
                        yield {
                            "tool_call": {
                                "id": block.id,
                                "name": block.name,
                                "status": "blocked",
                                "reason": check.get("reason", "Blocked by safety policy"),
                            }
                        }
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps({
                                "error": f"Action blocked: {check.get('reason', 'safety policy')}",
                                "requires": check.get("tier", "approval"),
                            }),
                        })
                        continue

                    if check.get("requires_approval"):
                        yield {
                            "tool_call": {
                                "id": block.id,
                                "name": block.name,
                                "status": "needs_approval",
                                "description": check.get("description", ""),
                            }
                        }
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps({
                                "pending": "This action requires user approval before execution.",
                                "description": check.get("description", ""),
                            }),
                        })
                        continue

                    # Execute the tool
                    yield {
                        "tool_call": {
                            "id": block.id,
                            "name": block.name,
                            "status": "running",
                        }
                    }

                    try:
                        result = await self.tool_registry.execute(
                            block.name, **block.input
                        )
                    except Exception as e:
                        result = {"error": str(e)}

                    # Record for spending tracking
                    guardrails.record_action(block.name, block.input)

                    yield {
                        "tool_call": {
                            "id": block.id,
                            "name": block.name,
                            "status": "completed",
                        }
                    }

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result) if isinstance(result, dict) else str(result),
                    })

            # Stream text content
            if text_content:
                words = text_content.split(" ")
                chunk_size = 3
                for i in range(0, len(words), chunk_size):
                    chunk = " ".join(words[i : i + chunk_size])
                    if i > 0:
                        chunk = " " + chunk
                    yield {"content": chunk}

            if has_tool_use:
                messages.append({
                    "role": "assistant",
                    "content": [
                        {"type": b.type, **({"text": b.text} if b.type == "text" else {"id": b.id, "name": b.name, "input": b.input})}
                        for b in response.content
                    ],
                })
                messages.append({
                    "role": "user",
                    "content": tool_results,
                })
                continue
            else:
                return

        yield {"content": "\n\n*Reached maximum tool execution rounds. Stopping here.*"}

    async def _run_openai_loop(
        self,
        system_prompt: str,
        messages: list[dict],
        tools: list[dict],
    ) -> AsyncGenerator[dict, None]:
        """OpenAI fallback loop — converts Anthropic format to OpenAI format."""
        openai_messages = [{"role": "system", "content": system_prompt}]
        for msg in messages:
            if isinstance(msg.get("content"), str):
                openai_messages.append({"role": msg["role"], "content": msg["content"]})

        # Convert tools to OpenAI function format
        openai_tools = []
        for tool in tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"],
                },
            })

        try:
            model = os.getenv("OPENAI_MODEL", "gpt-4o")
            response = self.openai_client.chat.completions.create(
                model=model,
                messages=openai_messages,
                tools=openai_tools if openai_tools else None,
                max_tokens=4096,
            )

            choice = response.choices[0]
            if choice.message.content:
                words = choice.message.content.split(" ")
                chunk_size = 3
                for i in range(0, len(words), chunk_size):
                    chunk = " ".join(words[i : i + chunk_size])
                    if i > 0:
                        chunk = " " + chunk
                    yield {"content": chunk}

            if choice.message.tool_calls:
                for tc in choice.message.tool_calls:
                    yield {
                        "tool_call": {
                            "id": tc.id,
                            "name": tc.function.name,
                            "status": "running",
                        }
                    }
                    try:
                        args = json.loads(tc.function.arguments)
                        result = await self.tool_registry.execute(tc.function.name, **args)
                    except Exception as e:
                        result = {"error": str(e)}

                    yield {
                        "tool_call": {
                            "id": tc.id,
                            "name": tc.function.name,
                            "status": "completed",
                        }
                    }

        except Exception as e:
            yield {"content": f"\n\n*OpenAI fallback error: {str(e)}*"}

    async def _fallback_response(
        self, message: str, is_onboarding: bool
    ) -> AsyncGenerator[dict, None]:
        """
        Intelligent fallback when no API key is configured.
        """
        msg_lower = message.lower()

        if is_onboarding or "get started" in msg_lower or "set up" in msg_lower:
            response = """Welcome to **Volo** — your AI Life Operating System. 🧠

I'm here to be your single point of control for everything: code, trading, communications, and more.

Let's get you set up. I'll ask you a few questions to configure everything:

**1. What's your name?** (so I know what to call you)

**2. What do you primarily do?** For example:
   - 💻 Software development
   - 📈 Trading / investing
   - 🏢 Business management
   - 🎨 Content creation
   - All of the above

**3. Which tools do you use most?** I can connect to:
   - **GitHub** — manage all your code projects
   - **Gmail/Outlook** — email triage and auto-drafts
   - **Google Calendar** — scheduling and meeting prep
   - **Alpaca/Coinbase** — trading and portfolio tracking
   - **Slack/Discord** — messaging
   - **Twitter/LinkedIn** — social media management

Just tell me about yourself and I'll configure everything step by step. No forms, no setup wizards — just a conversation. ✨"""

        elif "github" in msg_lower or "repo" in msg_lower or "code" in msg_lower:
            response = """Great — let's connect your **GitHub** account.

I'll need a **Personal Access Token** to access your repositories. Here's how to create one:

1. Go to [github.com/settings/tokens](https://github.com/settings/tokens)
2. Click **"Generate new token (classic)"**
3. Give it a name like "Volo Agent"
4. Select these scopes: `repo`, `read:org`, `read:user`
5. Generate and paste the token here

Once connected, I'll be able to:
- 📂 See all your repos and understand your codebase
- 🔍 Find shared modules across projects
- 🔄 Review PRs, manage issues, trigger deployments
- 📊 Track project health and tech debt

**Paste your GitHub token when ready** (it will be encrypted and stored securely)."""

        elif any(w in msg_lower for w in ["trading", "portfolio", "stock", "crypto", "price", "quote"]):
            # Try to get a crypto quote even without API key
            symbol_hints = {
                "btc": "BTC", "bitcoin": "BTC", "eth": "ETH", "ethereum": "ETH",
                "sol": "SOL", "solana": "SOL",
            }
            found_symbol = None
            for keyword, sym in symbol_hints.items():
                if keyword in msg_lower:
                    found_symbol = sym
                    break

            if found_symbol:
                try:
                    result = await self.tool_registry.trading.get_quote(found_symbol)
                    if "error" not in result:
                        price = result.get("price", 0)
                        change = result.get("change_24h_pct", 0)
                        direction = "📈" if change >= 0 else "📉"
                        response = f"""Here's the latest on **{found_symbol}**:

{direction} **${price:,.2f}** ({'+' if change >= 0 else ''}{change:.2f}% 24h)

| Metric | Value |
|--------|-------|
| Market Cap | ${result.get('market_cap', 0):,.0f} |
| 24h Volume | ${result.get('volume_24h', 0):,.0f} |

Want me to set up **Alpaca** for stock trading or track more crypto? I can also set alerts for price movements."""
                    else:
                        response = self._generic_trading_response()
                except Exception:
                    response = self._generic_trading_response()
            else:
                response = self._generic_trading_response()

        elif any(w in msg_lower for w in ["email", "calendar", "gmail"]):
            response = """Let's connect your **email and calendar**.

**Email** (choose one):
- 📧 **Gmail** — full inbox management, auto-categorize, draft replies
- 📧 **Outlook** — same capabilities for Microsoft accounts

**Calendar** (choose one):
- 📅 **Google Calendar** — scheduling, conflict detection, meeting prep
- 📅 **Outlook Calendar** — same for Microsoft

Once connected, I'll:
- Triage your inbox (urgent / needs reply / FYI)
- Draft replies in your writing style
- Prepare meeting briefs before each call
- Find open time slots for scheduling
- Track follow-ups

Want to start with **Gmail** or **Outlook**?"""

        elif "name" in msg_lower or "call me" in msg_lower:
            response = """Got it! I'll remember that. 

What do you primarily work on? This helps me prioritize which integrations to set up first and how to organize your workspace.

For example:
- If you're a **developer**, I'll prioritize GitHub, CI/CD, and project management
- If you're a **trader**, I'll focus on brokerage connections and market data
- If you're a **business owner**, I'll set up email, calendar, and financial tracking first
- If you're **all of the above** — we'll do it all! 🚀"""

        else:
            response = f"""I hear you! I'm Volo, your AI Life Operating System.

Right now I'm running in **setup mode** — I need an AI model API key to unlock my full capabilities.

**To activate full AI:**
1. Get an API key from [Anthropic](https://console.anthropic.com/) or [OpenAI](https://platform.openai.com/)
2. Add it to your `.env` file:
   ```
   ANTHROPIC_API_KEY=your-key-here
   ```
3. Restart the API server

**Even without an API key, I can still help you:**
- Set up integrations (GitHub, email, trading)
- Configure your preferences
- Walk through the onboarding flow
- Get live crypto prices (try: "What's the price of Bitcoin?")

What would you like to do?"""

        # Stream words in chunks for natural feel
        words = response.split(" ")
        chunk_size = 3
        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i : i + chunk_size])
            if i > 0:
                chunk = " " + chunk
            yield {"content": chunk}

    def _generic_trading_response(self) -> str:
        return """Let's set up your **trading & finance** integrations.

I support these platforms:

**Stocks & Options:**
- 🟢 **Alpaca** — commission-free trading API (paper & live)

**Crypto (free — no API key needed):**
- 🟡 Live prices for BTC, ETH, SOL, and 100+ tokens
- Just ask me "What's the price of Bitcoin?"

**To connect Alpaca:**
1. Go to [app.alpaca.markets](https://app.alpaca.markets)
2. Sign up → Paper Trading → Get API keys
3. Tell me your API Key and Secret Key

Which platform(s) do you use? I'll walk you through connecting each one."""

    def _build_messages(self, history: list[dict], current_message: str) -> list[dict]:
        """Build the messages array for the LLM."""
        messages = []
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": current_message})
        return messages

    def _format_memories(self, memories: list) -> str:
        """Format retrieved memories into context string."""
        if not memories:
            return ""
        lines = []
        for m in memories:
            lines.append(f"- [{m.get('category', 'fact')}] {m.get('content', '')}")
        return "\n".join(lines)
