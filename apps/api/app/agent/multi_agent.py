"""
VOLO — Multi-Agent Orchestration
Specialized sub-agents for different domains that can be
delegated to by the main orchestrator.
"""

import logging
from typing import Any, Optional

logger = logging.getLogger("volo.multi_agent")


class SubAgent:
    """Base class for specialized sub-agents."""

    def __init__(self, name: str, domain: str, description: str):
        self.name = name
        self.domain = domain
        self.description = description

    async def can_handle(self, intent: str, message: str) -> float:
        """Return confidence score 0-1 that this agent can handle the request."""
        return 0.0

    async def process(self, message: str, context: dict) -> dict:
        """Process a request. Returns structured response."""
        return {"error": f"Agent '{self.name}' not implemented."}


class CodeAgent(SubAgent):
    """Handles code-related tasks: repos, PRs, deployments, code review."""

    def __init__(self):
        super().__init__("code_agent", "engineering", "Manages code, repos, PRs, and deployments")
        self.keywords = ["code", "repo", "github", "deploy", "pr", "pull request", "commit",
                         "branch", "merge", "pipeline", "ci", "cd", "build", "test", "debug",
                         "refactor", "lint", "package", "dependency", "version"]

    async def can_handle(self, intent: str, message: str) -> float:
        msg_lower = message.lower()
        matches = sum(1 for kw in self.keywords if kw in msg_lower)
        return min(matches * 0.2, 1.0)

    async def process(self, message: str, context: dict) -> dict:
        return {
            "agent": self.name,
            "domain": self.domain,
            "suggested_tools": ["github_list_repos", "github_get_repo", "github_list_prs"],
            "context_needed": ["github_token", "active_repos"],
        }


class TradingAgent(SubAgent):
    """Handles trading and finance tasks."""

    def __init__(self):
        super().__init__("trading_agent", "finance", "Manages trading, portfolio, and market analysis")
        self.keywords = ["trade", "buy", "sell", "portfolio", "stock", "crypto", "bitcoin",
                         "ethereum", "price", "quote", "market", "position", "p&l", "profit",
                         "loss", "invest", "dividend", "options", "futures", "defi", "wallet"]

    async def can_handle(self, intent: str, message: str) -> float:
        msg_lower = message.lower()
        matches = sum(1 for kw in self.keywords if kw in msg_lower)
        return min(matches * 0.25, 1.0)

    async def process(self, message: str, context: dict) -> dict:
        return {
            "agent": self.name,
            "domain": self.domain,
            "suggested_tools": ["trading_quote", "trading_portfolio"],
            "requires_approval": any(w in message.lower() for w in ["buy", "sell", "trade", "order"]),
        }


class CommunicationsAgent(SubAgent):
    """Handles email, calendar, and messaging tasks."""

    def __init__(self):
        super().__init__("comms_agent", "communications", "Manages email, calendar, and messaging")
        self.keywords = ["email", "gmail", "send", "reply", "inbox", "calendar", "meeting",
                         "schedule", "appointment", "slack", "message", "notification",
                         "reminder", "follow up", "draft", "compose"]

    async def can_handle(self, intent: str, message: str) -> float:
        msg_lower = message.lower()
        matches = sum(1 for kw in self.keywords if kw in msg_lower)
        return min(matches * 0.2, 1.0)

    async def process(self, message: str, context: dict) -> dict:
        return {
            "agent": self.name,
            "domain": self.domain,
            "suggested_tools": ["email_list_inbox", "calendar_list_events"],
        }


class ResearchAgent(SubAgent):
    """Handles research, analysis, and information synthesis."""

    def __init__(self):
        super().__init__("research_agent", "research", "Conducts research and analysis")
        self.keywords = ["research", "analyze", "compare", "summary", "explain", "what is",
                         "how does", "why", "find", "search", "look up", "pros and cons",
                         "trends", "report", "data", "statistics"]

    async def can_handle(self, intent: str, message: str) -> float:
        msg_lower = message.lower()
        matches = sum(1 for kw in self.keywords if kw in msg_lower)
        return min(matches * 0.15, 1.0)

    async def process(self, message: str, context: dict) -> dict:
        return {
            "agent": self.name,
            "domain": self.domain,
            "suggested_tools": ["search_memory"],
        }


class MultiAgentOrchestrator:
    """
    Routes requests to the best sub-agent based on intent classification.
    Can also coordinate between multiple agents for cross-domain tasks.
    """

    def __init__(self):
        self.agents: list[SubAgent] = [
            CodeAgent(),
            TradingAgent(),
            CommunicationsAgent(),
            ResearchAgent(),
        ]

    async def classify(self, message: str) -> list[dict]:
        """
        Classify a message and rank which agents should handle it.
        Returns sorted list of (agent, confidence) pairs.
        """
        scores = []
        for agent in self.agents:
            confidence = await agent.can_handle("", message)
            if confidence > 0.1:
                scores.append({
                    "agent": agent.name,
                    "domain": agent.domain,
                    "confidence": round(confidence, 2),
                    "description": agent.description,
                })

        scores.sort(key=lambda x: x["confidence"], reverse=True)
        return scores

    async def route(self, message: str, context: dict = None) -> dict:
        """Route a message to the best agent."""
        context = context or {}
        rankings = await self.classify(message)

        if not rankings:
            return {"agent": "general", "confidence": 1.0, "message": "Handled by general agent"}

        best = rankings[0]
        agent = next(a for a in self.agents if a.name == best["agent"])
        result = await agent.process(message, context)
        result["confidence"] = best["confidence"]
        result["all_rankings"] = rankings

        return result

    def get_agent_info(self) -> list[dict]:
        """Get info about all available agents."""
        return [
            {
                "name": a.name,
                "domain": a.domain,
                "description": a.description,
            }
            for a in self.agents
        ]
