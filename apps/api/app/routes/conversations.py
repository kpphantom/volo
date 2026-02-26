"""
VOLO — Conversations Routes
Persistent conversation management backed by PostgreSQL.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, delete as sa_delete
from sqlalchemy.orm import selectinload

from app.auth import get_current_user, CurrentUser
from app.database import async_session, Conversation, ChatMessage
from app.services.cache import cache

router = APIRouter()


class CreateConversationRequest(BaseModel):
    title: Optional[str] = None


class BranchConversationRequest(BaseModel):
    from_message_index: int
    title: Optional[str] = None


def _conv_dict(c, preview=""):
    return {
        "id": c.id,
        "title": c.title,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        "message_count": c.message_count or 0,
        "preview": preview,
        "pinned": c.pinned or False,
    }


def _msg_dict(m):
    return {
        "id": m.id,
        "role": m.role,
        "content": m.content,
        "timestamp": m.created_at.isoformat() if m.created_at else None,
        "tool_calls": m.tool_calls,
    }


def _conv_list_cache_key(user_id: str, limit: int, offset: int, search: Optional[str]) -> str:
    return f"convlist:{user_id}:{limit}:{offset}:{search or ''}"


@router.get("/conversations")
async def list_conversations(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user),
):
    """List all conversations, optionally filtered by search."""
    cache_key = _conv_list_cache_key(current_user.user_id, limit, offset, search)
    cached = await cache.get_json(cache_key)
    if cached is not None:
        return cached

    async with async_session() as session:
        query = select(Conversation).where(Conversation.user_id == current_user.user_id)

        if search:
            query = query.where(Conversation.title.ilike(f"%{search}%"))

        count_q = select(func.count()).select_from(query.subquery())
        total = (await session.execute(count_q)).scalar() or 0

        query = query.order_by(Conversation.updated_at.desc()).offset(offset).limit(limit)
        result = await session.execute(query)
        convos = result.scalars().all()

        # Fetch all last-message previews in a single query to avoid N+1
        conv_ids = [c.id for c in convos]
        previews: dict[str, str] = {}
        if conv_ids:
            # Subquery: latest message per conversation
            from sqlalchemy import and_
            latest_subq = (
                select(
                    ChatMessage.conversation_id,
                    func.max(ChatMessage.created_at).label("max_ts"),
                )
                .where(ChatMessage.conversation_id.in_(conv_ids))
                .group_by(ChatMessage.conversation_id)
                .subquery()
            )
            preview_q = select(ChatMessage.conversation_id, ChatMessage.content).join(
                latest_subq,
                and_(
                    ChatMessage.conversation_id == latest_subq.c.conversation_id,
                    ChatMessage.created_at == latest_subq.c.max_ts,
                ),
            )
            for row in (await session.execute(preview_q)).all():
                previews[row.conversation_id] = (row.content or "")[:100]

        conv_list = [_conv_dict(c, preview=previews.get(c.id, "")) for c in convos]

    payload = {"conversations": conv_list, "total": total, "limit": limit, "offset": offset}
    await cache.set_json(cache_key, payload, ttl=30)
    return payload


async def _invalidate_conv_list(user_id: str) -> None:
    """Delete all cached conversation-list pages for this user."""
    # We use a pattern delete — delete keys matching convlist:{user_id}:*
    # When Redis is connected use SCAN+DEL; in fallback mode do a prefix scan.
    try:
        if cache.is_connected:
            async for key in cache._redis.scan_iter(f"convlist:{user_id}:*"):
                await cache._redis.delete(key)
        else:
            prefix = f"convlist:{user_id}:"
            stale = [k for k in cache._fallback._data if k.startswith(prefix)]
            for k in stale:
                cache._fallback.delete(k)
    except Exception:
        pass


@router.post("/conversations")
async def create_conversation(body: CreateConversationRequest, current_user: CurrentUser = Depends(get_current_user)):
    """Create a new conversation."""
    async with async_session() as session:
        conv = Conversation(
            user_id=current_user.user_id,
            title=body.title or "New Conversation",
        )
        session.add(conv)
        await session.commit()
        await session.refresh(conv)
    await _invalidate_conv_list(current_user.user_id)
    return _conv_dict(conv)


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    msg_limit: int = Query(100, ge=1, le=500),
    msg_offset: int = Query(0, ge=0),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get a conversation with paginated messages."""
    async with async_session() as session:
        result = await session.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == current_user.user_id,
            )
        )
        conv = result.scalar_one_or_none()

        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

        msgs_result = await session.execute(
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conversation_id)
            .order_by(ChatMessage.created_at)
            .offset(msg_offset)
            .limit(msg_limit)
        )
        messages = msgs_result.scalars().all()

        return {
            **_conv_dict(conv),
            "messages": [_msg_dict(m) for m in messages],
            "msg_limit": msg_limit,
            "msg_offset": msg_offset,
        }


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, current_user: CurrentUser = Depends(get_current_user)):
    """Delete a conversation and its messages."""
    async with async_session() as session:
        result = await session.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == current_user.user_id,
            )
        )
        conv = result.scalar_one_or_none()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

        await session.execute(
            sa_delete(ChatMessage).where(ChatMessage.conversation_id == conversation_id)
        )
        await session.delete(conv)
        await session.commit()

    await _invalidate_conv_list(current_user.user_id)
    return {"deleted": True}


@router.patch("/conversations/{conversation_id}")
async def update_conversation(conversation_id: str, body: CreateConversationRequest, current_user: CurrentUser = Depends(get_current_user)):
    """Update conversation title."""
    async with async_session() as session:
        result = await session.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == current_user.user_id,
            )
        )
        conv = result.scalar_one_or_none()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

        if body.title:
            conv.title = body.title
        conv.updated_at = datetime.utcnow()
        await session.commit()
        await session.refresh(conv)

    await _invalidate_conv_list(current_user.user_id)
    return _conv_dict(conv)


@router.post("/conversations/{conversation_id}/messages")
async def add_message(conversation_id: str, request: dict, current_user: CurrentUser = Depends(get_current_user)):
    """Add a message to a conversation (used internally by chat)."""
    async with async_session() as session:
        result = await session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conv = result.scalar_one_or_none()

        if conv and conv.user_id != current_user.user_id:
            raise HTTPException(status_code=404, detail="Conversation not found")

        if not conv:
            conv = Conversation(
                id=conversation_id,
                user_id=current_user.user_id,
                title=request.get("content", "")[:50] or "New Conversation",
            )
            session.add(conv)
            await session.flush()

        msg = ChatMessage(
            conversation_id=conversation_id,
            role=request.get("role", "user"),
            content=request.get("content", ""),
            tool_calls=request.get("tool_calls"),
        )
        session.add(msg)

        conv.message_count = (conv.message_count or 0) + 1
        conv.updated_at = datetime.utcnow()
        await session.commit()
        await session.refresh(msg)

        return _msg_dict(msg)


@router.post("/conversations/{conversation_id}/branch")
async def branch_conversation(conversation_id: str, body: BranchConversationRequest, current_user: CurrentUser = Depends(get_current_user)):
    """Branch a conversation from a specific message."""
    async with async_session() as session:
        result = await session.execute(
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(Conversation.id == conversation_id)
        )
        conv = result.scalar_one_or_none()
        if not conv or conv.user_id != current_user.user_id:
            raise HTTPException(status_code=404, detail="Conversation not found")

        original_msgs = sorted(conv.messages, key=lambda m: m.created_at)
        if body.from_message_index > len(original_msgs):
            raise HTTPException(status_code=400, detail="Invalid message index")

        new_conv = Conversation(
            user_id=current_user.user_id,
            title=body.title or f"Branch of {conv.title}",
            message_count=body.from_message_index,
        )
        session.add(new_conv)
        await session.flush()

        for m in original_msgs[:body.from_message_index]:
            session.add(ChatMessage(
                conversation_id=new_conv.id,
                role=m.role,
                content=m.content,
                tool_calls=m.tool_calls,
                metadata_=m.metadata_,
            ))

        await session.commit()
        await session.refresh(new_conv)

        return {**_conv_dict(new_conv), "branched_from": conversation_id}


@router.get("/conversations/{conversation_id}/export")
async def export_conversation(conversation_id: str, format: str = "json", current_user: CurrentUser = Depends(get_current_user)):
    """Export a conversation as JSON or Markdown."""
    async with async_session() as session:
        result = await session.execute(
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(
                Conversation.id == conversation_id,
                Conversation.user_id == current_user.user_id,
            )
        )
        conv = result.scalar_one_or_none()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

        msgs = [_msg_dict(m) for m in sorted(conv.messages, key=lambda m: m.created_at)]
        conv_dict = {
            "id": conv.id,
            "title": conv.title,
            "created_at": conv.created_at.isoformat(),
        }

        if format == "markdown":
            lines = [f"# {conv.title}", f"*{conv.created_at.isoformat()}*", ""]
            for m in msgs:
                role = "**You**" if m["role"] == "user" else "**Volo**"
                lines.append(f"{role}: {m['content']}")
                lines.append("")
            return {"format": "markdown", "content": "\n".join(lines)}

        return {"format": "json", "conversation": conv_dict, "messages": msgs}
