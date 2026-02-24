"""
VOLO — Context Window Manager
Manages token budgets, sliding context windows, memory injection,
and ensures the LLM always has the most relevant context.
"""

import json
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger("volo.context")

# Approximate token counts (conservative)
CHARS_PER_TOKEN = 4
MODEL_LIMITS = {
    "claude-sonnet-4-20250514": 200_000,
    "claude-3-5-sonnet-20241022": 200_000,
    "claude-3-haiku-20240307": 200_000,
    "gpt-4o": 128_000,
    "gpt-4o-mini": 128_000,
    "gpt-4-turbo": 128_000,
    "gpt-3.5-turbo": 16_385,
}


def estimate_tokens(text: str) -> int:
    return len(text) // CHARS_PER_TOKEN


class ContextWindow:
    """
    Manages the context window for LLM calls.
    - Prioritizes recent messages and relevant memories
    - Automatically truncates to fit within token limits
    - Injects system context (memories, active integrations, user preferences)
    """

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        self.model = model
        self.max_tokens = MODEL_LIMITS.get(model, 200_000)
        # Reserve tokens for: system prompt (~2K), tools (~3K), response (~4K)
        self.available_tokens = self.max_tokens - 9_000

    def build_messages(
        self,
        messages: list[dict] = None,
        current_message: str = None,
        system_prompt: str = "",
        memories: list[dict] = None,
        active_integrations: list[str] = None,
        history: list[dict] = None,
        model: str = None,
    ) -> list[dict]:
        """
        Trim messages to fit within token budget.
        Accepts either pre-built messages list or history + current_message.
        Returns trimmed messages list.
        """
        if model:
            self.max_tokens = MODEL_LIMITS.get(model, 200_000)
            self.available_tokens = self.max_tokens - 9_000

        # If pre-built messages provided (from orchestrator), just trim them
        if messages is not None:
            system_tokens = estimate_tokens(system_prompt or "")
            remaining = self.available_tokens - system_tokens

            # Walk from the end, keeping as many recent messages as fit
            trimmed = []
            used = 0
            for msg in reversed(messages):
                content = msg.get("content", "")
                msg_tokens = estimate_tokens(content)
                if used + msg_tokens > remaining:
                    trimmed.insert(0, {
                        "role": "user",
                        "content": "[Earlier conversation context was trimmed to fit.]"
                    })
                    break
                trimmed.insert(0, {"role": msg.get("role", "user"), "content": content})
                used += msg_tokens
            return trimmed

        # Legacy path: build from history + current_message
        if history is None:
            history = []

        system_tokens = estimate_tokens(system_prompt or "")
        current_msg_tokens = estimate_tokens(current_message or "")
        remaining = self.available_tokens - system_tokens - current_msg_tokens

        built = []
        history_tokens = 0
        for msg in reversed(history):
            content = msg.get("content", "")
            msg_tokens = estimate_tokens(content)
            if history_tokens + msg_tokens > remaining:
                built.insert(0, {
                    "role": "user",
                    "content": "[Earlier conversation context was trimmed to fit.]"
                })
                break
            built.insert(0, {"role": msg.get("role", "user"), "content": content})
            history_tokens += msg_tokens

        if current_message:
            built.append({"role": "user", "content": current_message})

        return built

    def _format_memories(self, memories: list[dict]) -> str:
        lines = []
        for m in memories[:20]:  # Cap at 20 memories
            category = m.get("category", "fact")
            content = m.get("content", "")
            confidence = m.get("confidence", 1.0)
            if confidence < 0.5:
                content += " (low confidence)"
            lines.append(f"- [{category}] {content}")
        return "\n".join(lines)

    def get_usage_stats(self, system_prompt: str, messages: list[dict]) -> dict:
        """Get token usage statistics."""
        system_tokens = estimate_tokens(system_prompt)
        message_tokens = sum(estimate_tokens(m.get("content", "")) for m in messages)
        total = system_tokens + message_tokens

        return {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system_tokens": system_tokens,
            "message_tokens": message_tokens,
            "total_tokens": total,
            "utilization_pct": round(total / self.max_tokens * 100, 1),
            "remaining_tokens": self.max_tokens - total,
        }
