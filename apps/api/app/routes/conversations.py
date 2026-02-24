"""
VOLO — Conversations Routes
Persistent conversation management: list, get, branch, delete.
"""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter()

# In-memory conversation store (swap for DB in production)
_conversations: dict[str, dict] = {}
_messages: dict[str, list[dict]] = {}


class CreateConversationRequest(BaseModel):
    title: Optional[str] = None


class BranchConversationRequest(BaseModel):
    from_message_index: int
    title: Optional[str] = None


@router.get("/conversations")
async def list_conversations(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: Optional[str] = None,
):
    """List all conversations, optionally filtered by search."""
    convos = list(_conversations.values())

    if search:
        search_lower = search.lower()
        convos = [
            c for c in convos
            if search_lower in c.get("title", "").lower()
            or any(search_lower in m.get("content", "").lower() for m in _messages.get(c["id"], []))
        ]

    convos.sort(key=lambda c: c.get("updated_at", ""), reverse=True)
    total = len(convos)
    convos = convos[offset: offset + limit]

    return {"conversations": convos, "total": total, "limit": limit, "offset": offset}


@router.post("/conversations")
async def create_conversation(body: CreateConversationRequest):
    """Create a new conversation."""
    conv_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    conv = {
        "id": conv_id,
        "title": body.title or "New Conversation",
        "created_at": now,
        "updated_at": now,
        "message_count": 0,
        "preview": "",
    }
    _conversations[conv_id] = conv
    _messages[conv_id] = []
    return conv


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get a conversation with its messages."""
    conv = _conversations.get(conversation_id)
    if not conv:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Conversation not found")

    return {
        **conv,
        "messages": _messages.get(conversation_id, []),
    }


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation."""
    if conversation_id in _conversations:
        del _conversations[conversation_id]
        _messages.pop(conversation_id, None)
        return {"deleted": True}

    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Conversation not found")


@router.patch("/conversations/{conversation_id}")
async def update_conversation(conversation_id: str, body: CreateConversationRequest):
    """Update conversation title."""
    conv = _conversations.get(conversation_id)
    if not conv:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Conversation not found")

    if body.title:
        conv["title"] = body.title
    conv["updated_at"] = datetime.utcnow().isoformat()
    return conv


@router.post("/conversations/{conversation_id}/messages")
async def add_message(conversation_id: str, request: dict):
    """Add a message to a conversation (used internally by chat)."""
    conv = _conversations.get(conversation_id)
    if not conv:
        # Auto-create conversation
        now = datetime.utcnow().isoformat()
        conv = {
            "id": conversation_id,
            "title": request.get("content", "")[:50] or "New Conversation",
            "created_at": now,
            "updated_at": now,
            "message_count": 0,
            "preview": "",
        }
        _conversations[conversation_id] = conv
        _messages[conversation_id] = []

    msg = {
        "id": str(uuid.uuid4()),
        "role": request.get("role", "user"),
        "content": request.get("content", ""),
        "timestamp": datetime.utcnow().isoformat(),
        "tool_calls": request.get("tool_calls"),
    }
    _messages[conversation_id].append(msg)
    conv["message_count"] = len(_messages[conversation_id])
    conv["updated_at"] = msg["timestamp"]
    conv["preview"] = msg["content"][:100]
    return msg


@router.post("/conversations/{conversation_id}/branch")
async def branch_conversation(conversation_id: str, body: BranchConversationRequest):
    """Branch a conversation from a specific message."""
    if conversation_id not in _conversations:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Conversation not found")

    original_msgs = _messages.get(conversation_id, [])
    if body.from_message_index > len(original_msgs):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid message index")

    # Create new conversation with messages up to the branch point
    new_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    branched_msgs = [dict(m) for m in original_msgs[: body.from_message_index]]

    new_conv = {
        "id": new_id,
        "title": body.title or f"Branch of {_conversations[conversation_id]['title']}",
        "created_at": now,
        "updated_at": now,
        "message_count": len(branched_msgs),
        "preview": branched_msgs[-1]["content"][:100] if branched_msgs else "",
        "branched_from": conversation_id,
    }
    _conversations[new_id] = new_conv
    _messages[new_id] = branched_msgs
    return new_conv


@router.get("/conversations/{conversation_id}/export")
async def export_conversation(conversation_id: str, format: str = "json"):
    """Export a conversation as JSON or Markdown."""
    conv = _conversations.get(conversation_id)
    if not conv:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Conversation not found")

    msgs = _messages.get(conversation_id, [])

    if format == "markdown":
        lines = [f"# {conv['title']}", f"*{conv['created_at']}*", ""]
        for m in msgs:
            role = "**You**" if m["role"] == "user" else "**Volo**"
            lines.append(f"{role}: {m['content']}")
            lines.append("")
        return {"format": "markdown", "content": "\n".join(lines)}

    return {"format": "json", "conversation": conv, "messages": msgs}
