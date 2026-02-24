"""
VOLO — Remote Agent & GitHub Repos Routes
Handles desktop agent pairing, WebSocket relay, session management,
coding chat (autonomous agent loop), and GitHub repository listing.
"""

import os
import json
import time
import asyncio
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query, Request
from fastapi.responses import StreamingResponse, PlainTextResponse
from pydantic import BaseModel
import httpx
from sqlalchemy import select

from app.services.remote_agent import remote_manager
from app.agent.coding_agent import CodingAgent
from app.database import async_session, Integration

router = APIRouter()
coding_agent = CodingAgent()


# ── Models ─────────────────────────────────────────────────────

class GenerateKeyRequest(BaseModel):
    user_id: str = "dev-user"
    github_username: str = ""
    github_token: str = ""


class StartSessionRequest(BaseModel):
    user_id: str = "dev-user"
    repo_full_name: str
    repo_clone_url: str


class RemoteCommandRequest(BaseModel):
    user_id: str = "dev-user"
    session_id: str = ""  # Scopes command to a specific session/repo cwd
    command_type: str  # run_command, read_file, write_file, list_dir
    payload: dict


class RemoteChatRequest(BaseModel):
    user_id: str = "dev-user"
    session_id: str
    message: str
    messages: list[dict] = []  # Conversation history


class ApprovalRequest(BaseModel):
    approval_id: str
    decision: str  # "allow" or "skip"


class UndoWriteRequest(BaseModel):
    user_id: str = "dev-user"
    session_id: str
    backup_id: str


# ── Approval Manager (cross-request coordination) ───────────────

class ApprovalManager:
    """Manages Allow/Skip approval flow between SSE stream and user taps."""

    def __init__(self):
        self.pending: dict[str, asyncio.Event] = {}
        self.results: dict[str, str] = {}

    async def request_approval(self, approval_id: str, timeout: float = 300.0) -> str:
        """Called from CodingAgent. Blocks until user responds or timeout."""
        event = asyncio.Event()
        self.pending[approval_id] = event
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
            return self.results.pop(approval_id, "skip")
        except asyncio.TimeoutError:
            return "skip"
        finally:
            self.pending.pop(approval_id, None)

    def resolve(self, approval_id: str, decision: str):
        """Called from approve endpoint when user taps Allow/Skip."""
        self.results[approval_id] = decision
        event = self.pending.get(approval_id)
        if event:
            event.set()


approval_manager = ApprovalManager()


# ── Agent Key Management ───────────────────────────────────────

@router.post("/remote/agent-key")
async def generate_agent_key(body: GenerateKeyRequest):
    """Generate or retrieve an agent key for pairing the desktop agent."""
    existing = remote_manager.get_agent_key(body.user_id)
    if existing:
        return {
            "agent_key": existing,
            "is_new": False,
            "online": remote_manager.is_agent_online(body.user_id),
        }
    key = remote_manager.generate_agent_key(body.user_id, body.github_username)
    # Store github token if provided (for repo listing)
    if body.github_token:
        info = remote_manager.agent_keys.get(body.user_id, {})
        info["github_token"] = body.github_token
    return {"agent_key": key, "is_new": True, "online": False}


# ── One-line Setup Script ─────────────────────────────────────

@router.get("/setup/{agent_key}")
async def get_setup_script(agent_key: str, request: Request):
    """
    Returns a bash script that installs and starts the Volo desktop agent.
    Usage: curl -sL "https://volo.kingpinstrategies.com/api/setup/AGENT_KEY" | bash
    """
    # Determine server URL from the incoming request
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.headers.get("host", "localhost:8000"))
    base_url = f"{scheme}://{host}"
    ws_scheme = "wss" if scheme == "https" else "ws"
    ws_url = f"{ws_scheme}://{host}"

    script = f'''#!/bin/bash
# ══════════════════════════════════════════════
#  Volo Desktop Agent — One-Line Install
# ══════════════════════════════════════════════
set -e

AGENT_KEY="{agent_key}"
SERVER_URL="{ws_url}"
INSTALL_DIR="$HOME/.volo"

echo ""
echo "══════════════════════════════════════════"
echo "  🚀 Setting up Volo Desktop Agent"
echo "══════════════════════════════════════════"
echo ""

# ── Check Node.js ────────────────────────────
if ! command -v node &>/dev/null; then
    echo "❌ Node.js not found."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "   Install: brew install node"
    else
        echo "   Install: https://nodejs.org"
    fi
    exit 1
fi
echo "✅ Node.js $(node -v)"

# ── Create install directory ─────────────────
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"
echo "📁 Installing to $INSTALL_DIR"

# ── Write agent.js ───────────────────────────
echo "📥 Downloading agent..."
curl -sL "{base_url}/api/setup/{agent_key}/agent.js" -o agent.js

# ── Write package.json ───────────────────────
cat > package.json << 'PKGJSON'
{{
  "name": "volo-desktop-agent",
  "version": "1.0.0",
  "main": "agent.js",
  "scripts": {{ "start": "node agent.js" }},
  "dependencies": {{ "ws": "^8.16.0", "dotenv": "^16.4.0" }}
}}
PKGJSON

# ── Write .env ───────────────────────────────
cat > .env << ENVFILE
VOLO_AGENT_KEY=$AGENT_KEY
VOLO_SERVER_URL=$SERVER_URL
WORK_DIR=~/Projects
ENVFILE

# ── Install dependencies ─────────────────────
echo "📦 Installing dependencies..."
npm install --production --silent 2>/dev/null

echo ""
echo "══════════════════════════════════════════"
echo "  ✅ Volo agent installed!"
echo "  📂 $INSTALL_DIR"
echo "══════════════════════════════════════════"
echo ""
echo "  Starting agent..."
echo ""

# ── Start agent ──────────────────────────────
node agent.js
'''
    return PlainTextResponse(content=script, media_type="text/plain")


@router.get("/setup/{agent_key}/agent.js")
async def get_agent_js(agent_key: str):
    """Serve the agent.js file for the setup script to download."""
    possible_paths = [
        "/app/agent.js",  # Docker path (copied during build)
        os.path.join(os.path.dirname(__file__), "../../../../apps/agent/agent.js"),  # Local dev
        os.path.join(os.getcwd(), "apps/agent/agent.js"),
    ]
    for p in possible_paths:
        resolved = os.path.realpath(p)
        if os.path.exists(resolved):
            with open(resolved) as f:
                return PlainTextResponse(content=f.read(), media_type="application/javascript")

    # Fallback: serve a minimal agent inline
    return PlainTextResponse(
        content="console.error('Agent file not found on server. Please check deployment.'); process.exit(1);",
        media_type="application/javascript",
    )


@router.get("/remote/agent-status")
async def get_agent_status(user_id: str = Query("dev-user")):
    """Check if the user's desktop agent is online."""
    online = remote_manager.is_agent_online(user_id)
    sessions = remote_manager.get_active_sessions(user_id)
    agent = remote_manager.get_agent(user_id)
    return {
        "online": online,
        "connected_at": agent.connected_at if agent else None,
        "sessions": sessions,
        # Legacy compat
        "session": sessions[0] if sessions else None,
    }


@router.get("/remote/sessions")
async def list_sessions(user_id: str = Query("dev-user")):
    """List all active coding sessions for a user."""
    sessions = remote_manager.get_active_sessions(user_id)
    return {"sessions": sessions, "count": len(sessions)}


# ── Session Management ─────────────────────────────────────────

@router.post("/remote/session/start")
async def start_session(body: StartSessionRequest):
    """Start a remote coding session on a specific repo."""
    if not remote_manager.is_agent_online(body.user_id):
        raise HTTPException(status_code=400, detail="Desktop agent is not connected")

    session_id = remote_manager.start_session(
        body.user_id, body.repo_full_name, body.repo_clone_url
    )

    # Tell the agent to open the repo
    agent = remote_manager.get_agent(body.user_id)
    if agent:
        try:
            result = await agent.send_command("open_repo", {
                "repo": body.repo_full_name,
                "clone_url": body.repo_clone_url,
                "session_id": session_id,
            }, session_id=session_id, timeout=30.0)
        except Exception:
            result = {"status": "command_sent"}

    return {"session_id": session_id, "status": "active", "repo": body.repo_full_name}


@router.post("/remote/session/end")
async def end_session(session_id: str = Query(...)):
    """End a remote coding session."""
    session = remote_manager.get_session(session_id)
    if session:
        # Tell agent to clean up this session's context
        agent = remote_manager.get_agent(session["user_id"])
        if agent:
            try:
                await agent.send_command("close_session", {
                    "session_id": session_id,
                }, timeout=5.0)
            except Exception:
                pass
    remote_manager.end_session(session_id)
    return {"status": "ended"}


# ── Remote Command Execution ───────────────────────────────────

@router.post("/remote/execute")
async def execute_remote_command(body: RemoteCommandRequest):
    """Execute a command on the user's desktop agent."""
    agent = remote_manager.get_agent(body.user_id)
    if not agent or not remote_manager.is_agent_online(body.user_id):
        raise HTTPException(status_code=400, detail="Desktop agent is not connected")

    allowed_commands = {"run_command", "read_file", "write_file", "list_dir", "open_vscode", "close_session"}
    if body.command_type not in allowed_commands:
        raise HTTPException(status_code=400, detail=f"Unsupported command: {body.command_type}")

    result = await agent.send_command(
        body.command_type, body.payload, session_id=body.session_id
    )
    return {"result": result, "command_type": body.command_type, "session_id": body.session_id}


# ── Coding Chat (Autonomous Agent Loop) ───────────────────────

@router.post("/remote/chat")
async def remote_chat(body: RemoteChatRequest):
    """
    Autonomous coding chat. The AI reads files, runs commands, writes code
    on the user's desktop — streaming every step back so they see exactly
    what's happening on their machine. Full agent loop, not single-shot.
    """
    agent = remote_manager.get_agent(body.user_id)
    if not agent or not remote_manager.is_agent_online(body.user_id):
        raise HTTPException(status_code=400, detail="Desktop agent is not connected")

    session = remote_manager.get_session(body.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    repo = session.get("repo", "unknown")

    async def event_stream():
        try:
            yield f"data: {json.dumps({'session_id': body.session_id})}\n\n"

            async for chunk in coding_agent.run(
                message=body.message,
                session_id=body.session_id,
                repo=repo,
                history=body.messages,
                agent_connection=agent,
                approval_manager=approval_manager,
            ):
                yield f"data: {json.dumps(chunk)}\n\n"

            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


# ── Approval & Undo Endpoints ─────────────────────────────────────

@router.post("/remote/approve")
async def approve_action(body: ApprovalRequest):
    """User taps Allow or Skip on a pending command."""
    if body.decision not in ("allow", "skip"):
        raise HTTPException(status_code=400, detail="Decision must be 'allow' or 'skip'")
    approval_manager.resolve(body.approval_id, body.decision)
    return {"status": "resolved", "decision": body.decision}


@router.post("/remote/undo")
async def undo_write(body: UndoWriteRequest):
    """User taps Undo on a file change — restores the original content."""
    agent = remote_manager.get_agent(body.user_id)
    if not agent or not remote_manager.is_agent_online(body.user_id):
        raise HTTPException(status_code=400, detail="Desktop agent is not connected")

    result = await agent.send_command(
        "undo_write",
        {"backup_id": body.backup_id},
        session_id=body.session_id,
        timeout=10.0,
    )
    return {"result": result}


# ── GitHub Repos ───────────────────────────────────────────────

@router.get("/remote/github/repos")
async def list_github_repos(
    user_id: str = Query("dev-user"),
    sort: str = Query("updated"),
    per_page: int = Query(30),
):
    """List the user's GitHub repositories."""
    # Try to get token from agent key info or env
    token = None
    info = remote_manager.agent_keys.get(user_id, {})
    if info.get("github_token"):
        token = info["github_token"]
    if not token:
        token = os.getenv("GITHUB_TOKEN", "")

    # Check Integration table for stored GitHub OAuth token
    if not token:
        try:
            async with async_session() as session:
                result = await session.execute(
                    select(Integration).where(
                        Integration.user_id == user_id,
                        Integration.type == "github",
                        Integration.status == "connected",
                    )
                )
                integration = result.scalar_one_or_none()
                if integration and integration.config and integration.config.get("access_token"):
                    token = integration.config["access_token"]
        except Exception:
            pass

    if token:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.github.com/user/repos",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.github+json",
                    },
                    params={"sort": sort, "per_page": per_page, "type": "all"},
                    timeout=15.0,
                )
                if response.status_code == 200:
                    repos = response.json()
                    return {
                        "repos": [
                            {
                                "id": r["id"],
                                "name": r["name"],
                                "full_name": r["full_name"],
                                "description": r.get("description", ""),
                                "language": r.get("language", ""),
                                "private": r["private"],
                                "clone_url": r["clone_url"],
                                "ssh_url": r["ssh_url"],
                                "html_url": r["html_url"],
                                "updated_at": r["updated_at"],
                                "stargazers_count": r.get("stargazers_count", 0),
                                "default_branch": r.get("default_branch", "main"),
                            }
                            for r in repos
                        ],
                        "connected": True,
                    }
                else:
                    return {"repos": [], "connected": False, "error": "Invalid token"}
        except Exception as e:
            return {"repos": [], "connected": False, "error": str(e)}

    # Demo mode — return sample repos
    return {
        "connected": False,
        "repos": [
            {
                "id": 1,
                "name": "volo",
                "full_name": "user/volo",
                "description": "AI Life Operating System",
                "language": "TypeScript",
                "private": False,
                "clone_url": "https://github.com/user/volo.git",
                "ssh_url": "git@github.com:user/volo.git",
                "html_url": "https://github.com/user/volo",
                "updated_at": "2026-02-23T00:00:00Z",
                "stargazers_count": 42,
                "default_branch": "main",
            },
            {
                "id": 2,
                "name": "loginto",
                "full_name": "user/loginto",
                "description": "Remote desktop web app",
                "language": "JavaScript",
                "private": False,
                "clone_url": "https://github.com/user/loginto.git",
                "ssh_url": "git@github.com:user/loginto.git",
                "html_url": "https://github.com/user/loginto",
                "updated_at": "2026-02-21T00:00:00Z",
                "stargazers_count": 12,
                "default_branch": "main",
            },
            {
                "id": 3,
                "name": "my-portfolio",
                "full_name": "user/my-portfolio",
                "description": "Personal portfolio site",
                "language": "React",
                "private": False,
                "clone_url": "https://github.com/user/my-portfolio.git",
                "ssh_url": "git@github.com:user/my-portfolio.git",
                "html_url": "https://github.com/user/my-portfolio",
                "updated_at": "2026-02-18T00:00:00Z",
                "stargazers_count": 5,
                "default_branch": "main",
            },
        ],
    }


# ── WebSocket Relay ────────────────────────────────────────────

# Server-side connection tuning
WS_PING_INTERVAL = 25       # Send app-level ping every 25s
WS_RECEIVE_TIMEOUT = 60     # If nothing received in 60s, assume dead
                             # (agent heartbeats every 15s, so 60s = 4 missed beats)


@router.websocket("/remote/ws/{agent_key}")
async def agent_websocket(websocket: WebSocket, agent_key: str):
    """
    WebSocket endpoint for desktop agents.
    Rock-solid connection with server-side health monitoring.
    """
    await websocket.accept()

    # Find which user owns this key
    user_id = None
    for uid, info in remote_manager.agent_keys.items():
        if info.get("key") == agent_key:
            user_id = uid
            break

    if not user_id:
        await websocket.send_json({"type": "error", "message": "Invalid agent key"})
        await websocket.close(code=4001)
        return

    # Register the connection
    conn = remote_manager.register_agent(agent_key, user_id, websocket)
    conn.last_heartbeat = time.time()
    print(f"🖥️  Desktop agent connected: user={user_id}, key={agent_key[:20]}...")

    await websocket.send_json({
        "type": "connected",
        "message": "Connected to Volo. Waiting for commands.",
        "user_id": user_id,
    })

    # ── Server-side ping task ────────────────────────────────
    # Sends periodic app-level pings to keep the connection alive and
    # prevent reverse proxies / load balancers from killing idle WS.
    async def server_ping_loop():
        try:
            while True:
                await asyncio.sleep(WS_PING_INTERVAL)
                try:
                    await websocket.send_json({"type": "ping", "ts": time.time()})
                except Exception:
                    break  # Connection dead — exit loop
        except asyncio.CancelledError:
            pass

    ping_task = asyncio.create_task(server_ping_loop())

    try:
        while True:
            # ── Receive with timeout ─────────────────────────
            # If agent sends nothing for WS_RECEIVE_TIMEOUT seconds
            # (heartbeats come every 15s), the connection is dead.
            try:
                raw = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=WS_RECEIVE_TIMEOUT,
                )
            except asyncio.TimeoutError:
                print(f"⏰ Agent timeout (no data in {WS_RECEIVE_TIMEOUT}s): user={user_id}")
                break

            # ── Parse JSON safely ────────────────────────────
            try:
                data = json.loads(raw)
            except (json.JSONDecodeError, ValueError) as e:
                print(f"⚠️  Malformed message from agent ({user_id}): {e}")
                continue  # Don't disconnect on a single bad message

            msg_type = data.get("type")

            if msg_type == "heartbeat":
                conn.last_heartbeat = time.time()
                try:
                    await websocket.send_json({"type": "heartbeat_ack"})
                except Exception:
                    break

            elif msg_type == "pong":
                # Agent responded to our server-side ping
                conn.last_heartbeat = time.time()

            elif msg_type == "command_result":
                conn.last_heartbeat = time.time()
                command_id = data.get("command_id")
                result = data.get("result", {})
                if command_id:
                    conn.resolve_command(command_id, result)

            elif msg_type == "stream":
                conn.last_heartbeat = time.time()

    except WebSocketDisconnect:
        print(f"🔌 Desktop agent disconnected: user={user_id}")
    except Exception as e:
        print(f"❌ Agent WebSocket error: {e}")
    finally:
        # Clean up server-side ping task
        ping_task.cancel()
        try:
            await ping_task
        except asyncio.CancelledError:
            pass
        remote_manager.unregister_agent(agent_key)
