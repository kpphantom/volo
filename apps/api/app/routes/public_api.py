"""
VOLO — Public API Routes
RESTful API for programmatic access to Volo features.
Authenticated via API keys.
"""

import json
import uuid

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.agent.orchestrator import AgentOrchestrator

router = APIRouter()
orchestrator = AgentOrchestrator()


class PublicChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    stream: bool = False


class PublicMemoryRequest(BaseModel):
    category: str
    content: str
    source: str = "api"


@router.post("/v1/chat")
async def api_chat(body: PublicChatRequest):
    """
    Public API — Send a message and get a response.
    Non-streaming version collects full response.
    """
    conversation_id = body.conversation_id or str(uuid.uuid4())
    full_response = ""
    tool_calls = []

    async for chunk in orchestrator.run(
        message=body.message,
        conversation_id=conversation_id,
    ):
        if "content" in chunk:
            full_response += chunk["content"]
        if "tool_call" in chunk:
            tool_calls.append(chunk["tool_call"])

    return {
        "id": str(uuid.uuid4()),
        "conversation_id": conversation_id,
        "response": full_response.strip(),
        "tool_calls": tool_calls,
        "model": orchestrator.model,
    }


@router.post("/v1/memory")
async def api_store_memory(body: PublicMemoryRequest):
    """Public API — Store a memory."""
    result = await orchestrator.memory.store(
        category=body.category,
        content=body.content,
        source=body.source,
    )
    return result


@router.get("/v1/memory")
async def api_list_memories(category: Optional[str] = None):
    """Public API — List memories."""
    memories = await orchestrator.memory.get_all(category=category)
    return {"memories": memories, "total": len(memories)}


@router.get("/v1/tools")
async def api_list_tools():
    """Public API — List available tools."""
    tools = orchestrator.tool_registry.get_tool_definitions()
    return {
        "tools": [
            {"name": t["name"], "description": t["description"]}
            for t in tools
        ],
        "total": len(tools),
    }


@router.post("/v1/tools/{tool_name}")
async def api_execute_tool(tool_name: str, request: Request):
    """Public API — Execute a tool directly."""
    body = await request.json()
    result = await orchestrator.tool_registry.execute(tool_name, **body)
    return {"tool": tool_name, "result": result}


@router.get("/v1/status")
async def api_status():
    """Public API — Get system status."""
    return {
        "status": "operational",
        "version": "0.1.0",
        "endpoints": [
            "POST /api/v1/chat",
            "POST /api/v1/memory",
            "GET /api/v1/memory",
            "GET /api/v1/tools",
            "POST /api/v1/tools/{tool_name}",
        ],
    }
