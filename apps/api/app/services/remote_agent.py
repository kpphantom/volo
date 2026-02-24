"""
VOLO — Remote Agent Service (Multi-Session)
Manages WebSocket connections between mobile clients and desktop agents.
Supports multiple concurrent coding sessions — each session has its own
repo, working directory, and chat history. One agent handles them all,
with commands scoped to a session_id so the agent knows which cwd to use.
"""

import uuid
import asyncio
import json
import time
from typing import Optional
from datetime import datetime


class AgentConnection:
    """Represents a connected desktop agent."""

    def __init__(self, agent_key: str, user_id: str, websocket):
        self.agent_key = agent_key
        self.user_id = user_id
        self.websocket = websocket
        self.connected_at = datetime.utcnow().isoformat()
        self.last_heartbeat = time.time()
        # Multi-session: track all active session_ids
        self.active_sessions: list[str] = []
        self.pending_commands: dict[str, asyncio.Future] = {}

    async def send_command(
        self,
        command_type: str,
        payload: dict,
        session_id: Optional[str] = None,
        timeout: float = 60.0,
    ) -> dict:
        """Send a command to the desktop agent and wait for the response."""
        command_id = str(uuid.uuid4())
        message = {
            "type": "command",
            "command_id": command_id,
            "command_type": command_type,
            "payload": payload,
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
        }

        loop = asyncio.get_event_loop()
        future = loop.create_future()
        self.pending_commands[command_id] = future

        try:
            await self.websocket.send_json(message)
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            return {"error": f"Command timed out after {timeout}s", "command_id": command_id}
        finally:
            self.pending_commands.pop(command_id, None)

    def resolve_command(self, command_id: str, result: dict):
        """Resolve a pending command with its result."""
        future = self.pending_commands.get(command_id)
        if future and not future.done():
            future.set_result(result)


class RemoteAgentManager:
    """
    Singleton manager for all remote agent connections.
    Supports multiple concurrent sessions per user — each session is scoped
    to a specific repo and has its own working directory on the desktop agent.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.agents: dict[str, AgentConnection] = {}
        self.user_agents: dict[str, str] = {}
        self.agent_keys: dict[str, dict] = {}
        self.sessions: dict[str, dict] = {}

    def generate_agent_key(self, user_id: str, github_username: str = "") -> str:
        key = f"volo-agent-{uuid.uuid4().hex[:16]}"
        self.agent_keys[user_id] = {
            "key": key,
            "github_username": github_username,
            "created_at": datetime.utcnow().isoformat(),
        }
        self.user_agents[user_id] = key
        return key

    def get_agent_key(self, user_id: str) -> Optional[str]:
        info = self.agent_keys.get(user_id)
        return info["key"] if info else None

    def register_agent(self, agent_key: str, user_id: str, websocket) -> AgentConnection:
        conn = AgentConnection(agent_key, user_id, websocket)
        self.agents[agent_key] = conn
        return conn

    def unregister_agent(self, agent_key: str):
        conn = self.agents.pop(agent_key, None)
        if conn:
            for future in conn.pending_commands.values():
                if not future.done():
                    future.set_exception(ConnectionError("Agent disconnected"))

    def get_agent(self, user_id: str) -> Optional[AgentConnection]:
        key = self.user_agents.get(user_id)
        if key:
            return self.agents.get(key)
        return None

    def is_agent_online(self, user_id: str) -> bool:
        agent = self.get_agent(user_id)
        if not agent:
            return False
        return (time.time() - agent.last_heartbeat) < 30

    # ── Multi-Session Management ─────────────────────────────

    def start_session(self, user_id: str, repo_full_name: str, repo_clone_url: str) -> str:
        """Start a new coding session. Multiple sessions can be active at once."""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            "session_id": session_id,
            "user_id": user_id,
            "repo": repo_full_name,
            "clone_url": repo_clone_url,
            "started_at": datetime.utcnow().isoformat(),
            "status": "active",
        }
        agent = self.get_agent(user_id)
        if agent:
            agent.active_sessions.append(session_id)
        return session_id

    def end_session(self, session_id: str):
        """End a specific session without affecting others."""
        session = self.sessions.get(session_id)
        if session:
            session["status"] = "ended"
            agent = self.get_agent(session["user_id"])
            if agent and session_id in agent.active_sessions:
                agent.active_sessions.remove(session_id)

    def get_session(self, session_id: str) -> Optional[dict]:
        return self.sessions.get(session_id)

    def get_active_sessions(self, user_id: str) -> list[dict]:
        """Get ALL active sessions for a user (not just one)."""
        return [
            {**s}
            for sid, s in self.sessions.items()
            if s["user_id"] == user_id and s["status"] == "active"
        ]

    # Legacy compat
    def get_active_session(self, user_id: str) -> Optional[dict]:
        sessions = self.get_active_sessions(user_id)
        return sessions[0] if sessions else None


# Singleton instance
remote_manager = RemoteAgentManager()
