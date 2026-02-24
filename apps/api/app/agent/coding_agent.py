"""
VOLO — Coding Agent
Autonomous AI coding agent for remote sessions. When the user chats from
their phone, this agent reads files, runs commands, writes code, and
streams every step back — just like Copilot in VS Code.

Key difference from the generic orchestrator:
- Tools execute through the WebSocket relay to the user's desktop agent
- Full agent loop (up to 15 rounds) with tool results fed back to the AI
- Coding-focused system prompt and tool set
- Every tool call + result is streamed so the user sees what's happening
"""

import os
import json
import asyncio
from typing import AsyncGenerator, Optional
from datetime import datetime

from app.agent.context_manager import ContextWindow


# ── Coding-Specific System Prompt ───────────────────────────────

CODING_SYSTEM_PROMPT = """You are Volo, an autonomous AI coding agent. The user is chatting from their phone and you have full access to their desktop machine via a connected agent.

## YOUR CAPABILITIES
You can execute these tools on the user's actual machine:
- **read_file**: Read any file from their codebase
- **write_file**: Create or overwrite files
- **run_command**: Execute any shell command (git, npm, python, etc.)
- **list_dir**: List directory contents

## HOW YOU WORK
You are an autonomous agent, not a chatbot. When the user asks you to do something:
1. **Plan** — Think about what steps are needed
2. **Execute** — Use your tools to read files, understand context, make changes
3. **Verify** — Run tests, check for errors, confirm the change works
4. **Report** — Tell the user exactly what you did and what the result was

## RULES
1. **Always read before writing** — Understand the existing code before modifying it
2. **Show your work** — The user can see each tool call you make. Be transparent.
3. **Chain operations** — Don't stop after one step. Read a file, analyze it, edit it, run tests — all in one response.
4. **Be precise** — When editing files, write the complete new file content. No placeholders or "// rest of file" comments.
5. **Use the terminal** — Run `git status`, `npm test`, `python -m pytest`, etc. to verify your changes.
6. **Handle errors** — If a command fails, read the error, fix the issue, and try again.

## FORMATTING
- Use markdown for explanations
- Use code blocks with language tags when showing code
- Be concise but thorough — the user is on a phone screen

## CONTEXT
- Current date/time: {datetime}
- Working on repo: {repo}
- Session: {session_id}
"""


class CodingAgent:
    """
    Autonomous coding agent that executes tools through the remote
    desktop agent and streams every step to the user's phone.
    """

    MAX_TOOL_ROUNDS = 15

    def __init__(self):
        self.model = os.getenv("DEFAULT_MODEL", "claude-sonnet-4-20250514")
        self.context_window = ContextWindow()
        self._client = None

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

    def _get_tools(self) -> list[dict]:
        """Define the coding-specific tool set (Anthropic format)."""
        return [
            {
                "name": "read_file",
                "description": "Read the contents of a file from the user's machine. Use this to understand existing code before making changes.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "File path relative to the repo root (e.g., 'src/index.ts', 'package.json')",
                        },
                    },
                    "required": ["path"],
                },
            },
            {
                "name": "write_file",
                "description": "Write content to a file on the user's machine. Creates the file if it doesn't exist, overwrites if it does. Always write the COMPLETE file content.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "File path relative to the repo root",
                        },
                        "content": {
                            "type": "string",
                            "description": "The complete file content to write",
                        },
                    },
                    "required": ["path", "content"],
                },
            },
            {
                "name": "run_command",
                "description": "Execute a shell command on the user's machine. Use for: git operations, running tests, installing packages, building, linting, etc. The command runs in the repo's root directory.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "Shell command to execute (e.g., 'git status', 'npm test', 'cat src/file.ts')",
                        },
                    },
                    "required": ["command"],
                },
            },
            {
                "name": "list_dir",
                "description": "List the contents of a directory on the user's machine. Use to explore the project structure.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Directory path relative to repo root. Use '.' for the repo root.",
                        },
                    },
                    "required": ["path"],
                },
            },
        ]

    async def run(
        self,
        message: str,
        session_id: str,
        repo: str,
        history: list[dict],
        agent_connection,  # AgentConnection instance
        approval_manager=None,  # For command Allow/Skip flow
    ) -> AsyncGenerator[dict, None]:
        """
        Main agent loop. Processes a user message, executes tools on the
        user's desktop via the agent connection, and streams everything back.

        Yields dicts with these possible keys:
        - {"content": "..."} — text from the AI
        - {"tool_call": {"name": ..., "input": ..., "status": ...}} — tool starting/approval
        - {"tool_result": {"name": ..., "result": ..., "status": ...}} — tool finished
        - {"file_change": {...}} — file written, pending Keep/Undo
        - {"error": "..."} — error message
        """
        if not self.client:
            yield {"content": "AI model not configured. Set ANTHROPIC_API_KEY in your environment."}
            return

        # Build system prompt
        now = datetime.now()
        system_prompt = CODING_SYSTEM_PROMPT.replace(
            "{datetime}", now.strftime("%Y-%m-%d %H:%M:%S")
        ).replace(
            "{repo}", repo
        ).replace(
            "{session_id}", session_id
        )

        # Build messages from history + new message
        messages = []
        for msg in history:
            if msg.get("role") in ("user", "assistant") and msg.get("content"):
                messages.append({"role": msg["role"], "content": msg["content"]})

        messages.append({"role": "user", "content": message})

        # Trim to context window
        messages = self.context_window.build_messages(
            messages=messages,
            system_prompt=system_prompt,
            memories=[],
            model=self.model,
        )

        tools = self._get_tools()

        # Agent loop
        round_count = 0
        while round_count < self.MAX_TOOL_ROUNDS:
            round_count += 1

            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=8192,
                    system=system_prompt,
                    messages=messages,
                    tools=tools,
                )
            except Exception as e:
                yield {"error": f"AI model error: {str(e)}"}
                return

            has_tool_use = False
            text_content = ""
            tool_results = []

            for block in response.content:
                if block.type == "text":
                    text_content += block.text

                elif block.type == "tool_use":
                    has_tool_use = True
                    tool_name = block.name
                    tool_input = block.input
                    sanitized = _sanitize_input_for_display(tool_name, tool_input)

                    # ── Command approval: require Allow/Skip before executing ──
                    if tool_name == "run_command" and approval_manager:
                        yield {
                            "tool_call": {
                                "id": block.id,
                                "name": tool_name,
                                "input": sanitized,
                                "status": "pending_approval",
                            }
                        }

                        decision = await approval_manager.request_approval(
                            block.id, timeout=300.0
                        )

                        if decision == "skip":
                            skip_result = {"skipped": True, "message": "Command skipped by user"}
                            yield {
                                "tool_result": {
                                    "id": block.id,
                                    "name": tool_name,
                                    "input": sanitized,
                                    "result": skip_result,
                                    "status": "skipped",
                                }
                            }
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": json.dumps(skip_result),
                            })
                            continue

                        # Approved — transition to running
                        yield {
                            "tool_call": {
                                "id": block.id,
                                "name": tool_name,
                                "input": sanitized,
                                "status": "running",
                            }
                        }
                    else:
                        # Non-command tools: start running immediately
                        yield {
                            "tool_call": {
                                "id": block.id,
                                "name": tool_name,
                                "input": sanitized,
                                "status": "running",
                            }
                        }

                    # Remap parameter names to match agent.js expectations
                    agent_payload = dict(tool_input)
                    if tool_name == "read_file" and "path" in agent_payload:
                        agent_payload["file_path"] = agent_payload.pop("path")
                    elif tool_name == "write_file" and "path" in agent_payload:
                        agent_payload["file_path"] = agent_payload.pop("path")
                    elif tool_name == "list_dir" and "path" in agent_payload:
                        agent_payload["dir_path"] = agent_payload.pop("path")

                    # Execute tool on the user's desktop via agent relay
                    try:
                        result = await agent_connection.send_command(
                            tool_name,
                            agent_payload,
                            session_id=session_id,
                            timeout=120.0,
                        )
                    except Exception as e:
                        result = {"error": str(e)}

                    # Stream: tool completed with result
                    yield {
                        "tool_result": {
                            "id": block.id,
                            "name": tool_name,
                            "input": sanitized,
                            "result": _format_result_for_display(tool_name, result),
                            "status": "completed",
                        }
                    }

                    # ── File change: emit Keep/Undo event for write_file ──
                    if tool_name == "write_file" and isinstance(result, dict) and result.get("success"):
                        yield {
                            "file_change": {
                                "id": block.id,
                                "backup_id": result.get("backup_id", ""),
                                "file_path": result.get("file_path", ""),
                                "had_original": result.get("had_original", False),
                                "lines_added": result.get("lines_added", 0),
                                "lines_removed": result.get("lines_removed", 0),
                            }
                        }

                    # Build tool result for the AI to see
                    result_str = json.dumps(result) if isinstance(result, dict) else str(result)
                    # Truncate very long results to avoid blowing context
                    if len(result_str) > 30000:
                        result_str = result_str[:30000] + "\n... [truncated, result too long]"

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_str,
                    })

            # Stream text content (word by word for real-time feel)
            if text_content:
                words = text_content.split(" ")
                chunk_size = 3
                for i in range(0, len(words), chunk_size):
                    chunk = " ".join(words[i : i + chunk_size])
                    if i > 0:
                        chunk = " " + chunk
                    yield {"content": chunk}

            # If tools were used, feed results back to the AI and continue
            if has_tool_use:
                # Reconstruct assistant message with all content blocks
                assistant_content = []
                for b in response.content:
                    if b.type == "text":
                        assistant_content.append({"type": "text", "text": b.text})
                    elif b.type == "tool_use":
                        assistant_content.append({
                            "type": "tool_use",
                            "id": b.id,
                            "name": b.name,
                            "input": b.input,
                        })

                messages.append({
                    "role": "assistant",
                    "content": assistant_content,
                })
                messages.append({
                    "role": "user",
                    "content": tool_results,
                })
                # Continue the loop — AI will see tool results and decide next step
                continue
            else:
                # No tool calls — AI is done
                return

        yield {"content": "\n\n*Reached maximum tool execution rounds. Stopping here.*"}


def _sanitize_input_for_display(tool_name: str, tool_input: dict) -> dict:
    """
    Sanitize tool input for display on the user's phone.
    For write_file, truncate the content preview.
    """
    display = dict(tool_input)
    if tool_name == "write_file" and "content" in display:
        content = display["content"]
        lines = content.split("\n")
        if len(lines) > 10:
            display["content"] = "\n".join(lines[:10]) + f"\n... ({len(lines)} lines total)"
        elif len(content) > 500:
            display["content"] = content[:500] + f"... ({len(content)} chars)"
    return display


def _format_result_for_display(tool_name: str, result: dict) -> dict:
    """
    Format tool result for display. Truncate long outputs.
    """
    display = dict(result)

    # For run_command, keep stdout/stderr but truncate if huge
    if tool_name == "run_command":
        for key in ("stdout", "stderr"):
            if key in display and isinstance(display[key], str) and len(display[key]) > 5000:
                display[key] = display[key][:5000] + f"\n... [truncated, {len(result[key])} chars total]"

    # For read_file, truncate long file contents
    if tool_name == "read_file" and "content" in display:
        content = display["content"]
        if isinstance(content, str) and len(content) > 8000:
            display["content"] = content[:8000] + f"\n... [truncated, {len(content)} chars total]"

    return display
