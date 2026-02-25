"""Integration tests for the /api/chat SSE endpoint with mocked orchestrator."""

import json
import pytest
from unittest.mock import patch
from httpx import AsyncClient


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _simple_agent(*args, **kwargs):
    """Async generator that emits a single text chunk then finishes."""
    yield {"content": "Hello from the mocked agent!"}


async def _tool_call_agent(*args, **kwargs):
    """Simulates a tool call followed by a text response."""
    yield {"tool_calls": [{"name": "search_web", "input": {"query": "pytest"}}]}
    yield {"content": "Here are the results."}


async def _error_agent(*args, **kwargs):
    """Raises immediately to test the error path."""
    raise RuntimeError("Simulated orchestrator failure")
    yield  # make it a generator


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_chat_returns_sse_stream(auth_client: AsyncClient):
    """POST /api/chat streams SSE events and ends with [DONE]."""
    with patch("app.routes.chat.orchestrator.run", side_effect=_simple_agent):
        response = await auth_client.post(
            "/api/chat",
            json={"message": "Hello Volo"},
        )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")
    assert "Hello from the mocked agent!" in response.text
    assert "[DONE]" in response.text


@pytest.mark.asyncio
async def test_chat_includes_conversation_id(auth_client: AsyncClient):
    """The first SSE event carries a conversation_id."""
    with patch("app.routes.chat.orchestrator.run", side_effect=_simple_agent):
        response = await auth_client.post(
            "/api/chat",
            json={"message": "Give me a conv ID"},
        )

    # Parse the first data: line
    lines = [l for l in response.text.splitlines() if l.startswith("data:")]
    first = json.loads(lines[0].removeprefix("data: "))
    assert "conversation_id" in first


@pytest.mark.asyncio
async def test_chat_uses_supplied_conversation_id(auth_client: AsyncClient):
    """If a conversation_id is provided it appears in the response."""
    # Create a conversation first so the FK exists
    create = await auth_client.post("/api/conversations", json={"title": "Chat Test"})
    conv_id = create.json()["id"]

    with patch("app.routes.chat.orchestrator.run", side_effect=_simple_agent):
        response = await auth_client.post(
            "/api/chat",
            json={"message": "Continue this conversation", "conversation_id": conv_id},
        )

    assert response.status_code == 200
    assert conv_id in response.headers.get("x-conversation-id", "")


@pytest.mark.asyncio
async def test_chat_tool_call_in_stream(auth_client: AsyncClient):
    """Tool call chunks are forwarded to the client."""
    with patch("app.routes.chat.orchestrator.run", side_effect=_tool_call_agent):
        response = await auth_client.post(
            "/api/chat",
            json={"message": "Search for something"},
        )

    assert response.status_code == 200
    assert "search_web" in response.text
    assert "Here are the results." in response.text


@pytest.mark.asyncio
async def test_chat_gracefully_handles_orchestrator_error(auth_client: AsyncClient):
    """An orchestrator exception results in an error message, not a 500."""
    with patch("app.routes.chat.orchestrator.run", side_effect=_error_agent):
        response = await auth_client.post(
            "/api/chat",
            json={"message": "Trigger an error"},
        )

    assert response.status_code == 200  # stream is still opened
    assert "error" in response.text.lower()
    assert "[DONE]" in response.text


@pytest.mark.asyncio
@pytest.mark.xfail(reason="Dev bypass still active — see §1.2")
async def test_chat_requires_auth(client: AsyncClient):
    """POST /api/chat without a token returns 401."""
    client.headers.pop("Authorization", None)
    with patch("app.routes.chat.orchestrator.run", side_effect=_simple_agent):
        response = await client.post("/api/chat", json={"message": "Hello"})
    assert response.status_code == 401
