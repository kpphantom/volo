"""
VOLO — Chat Route
Handles conversation with the AI agent, streaming responses.
"""

import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

from app.agent.orchestrator import AgentOrchestrator

router = APIRouter()
orchestrator = AgentOrchestrator()


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    messages: Optional[list] = None


@router.post("/chat")
async def chat(request: ChatRequest):
    """
    Main chat endpoint. Streams agent responses as Server-Sent Events.
    """
    conversation_id = request.conversation_id or str(uuid.uuid4())

    async def event_stream():
        try:
            # Send conversation ID
            yield f"data: {json.dumps({'conversation_id': conversation_id})}\n\n"

            # Run agent and stream response
            async for chunk in orchestrator.run(
                message=request.message,
                conversation_id=conversation_id,
                history=request.messages or [],
            ):
                yield f"data: {json.dumps(chunk)}\n\n"

            yield "data: [DONE]\n\n"
        except Exception as e:
            error_msg = f"I encountered an error: {str(e)}. Let me try again."
            yield f"data: {json.dumps({'content': error_msg})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Conversation-ID": conversation_id,
        },
    )


# Conversations moved to app/routes/conversations.py
