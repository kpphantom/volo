"""
VOLO — Chat Route
Handles conversation with the AI agent, streaming responses.
Messages are persisted to PostgreSQL during the stream.
"""

import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select

from app.agent.orchestrator import AgentOrchestrator
from app.database import async_session, Conversation, ChatMessage

router = APIRouter()
orchestrator = AgentOrchestrator()

DEFAULT_USER = "dev-user"


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    messages: Optional[list] = None


@router.post("/chat")
async def chat(request: ChatRequest):
    """
    Main chat endpoint. Streams agent responses as Server-Sent Events.
    Persists both user message and assistant response to the database.
    """
    conversation_id = request.conversation_id or str(uuid.uuid4())

    # Ensure conversation exists in DB
    async with async_session() as session:
        result = await session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conv = result.scalar_one_or_none()

        if not conv:
            conv = Conversation(
                id=conversation_id,
                user_id=DEFAULT_USER,
                title=request.message[:60] or "New Conversation",
            )
            session.add(conv)
            await session.flush()

        # Persist user message
        session.add(ChatMessage(
            conversation_id=conversation_id,
            role="user",
            content=request.message,
        ))
        conv.message_count = (conv.message_count or 0) + 1
        conv.updated_at = datetime.utcnow()
        await session.commit()

    async def event_stream():
        full_response = ""
        tool_calls = []
        try:
            yield f"data: {json.dumps({'conversation_id': conversation_id})}\n\n"

            async for chunk in orchestrator.run(
                message=request.message,
                conversation_id=conversation_id,
                history=request.messages or [],
            ):
                yield f"data: {json.dumps(chunk)}\n\n"

                # Accumulate the response
                if isinstance(chunk, dict):
                    if "content" in chunk:
                        full_response += chunk["content"]
                    if "tool_calls" in chunk:
                        tool_calls.extend(chunk["tool_calls"])

            yield "data: [DONE]\n\n"
        except Exception as e:
            error_msg = f"I encountered an error: {str(e)}. Let me try again."
            full_response = error_msg
            yield f"data: {json.dumps({'content': error_msg})}\n\n"
            yield "data: [DONE]\n\n"
        finally:
            # Persist assistant response after stream completes
            if full_response:
                try:
                    async with async_session() as session:
                        session.add(ChatMessage(
                            conversation_id=conversation_id,
                            role="assistant",
                            content=full_response,
                            tool_calls=tool_calls if tool_calls else None,
                        ))
                        result = await session.execute(
                            select(Conversation).where(Conversation.id == conversation_id)
                        )
                        conv = result.scalar_one_or_none()
                        if conv:
                            conv.message_count = (conv.message_count or 0) + 1
                            conv.updated_at = datetime.utcnow()
                        await session.commit()
                except Exception:
                    pass  # Don't crash the stream if DB write fails

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Conversation-ID": conversation_id,
        },
    )
