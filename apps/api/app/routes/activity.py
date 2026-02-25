"""
VOLO — Activity & Audit Routes
Activity feed, audit log, and usage analytics.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from app.auth import get_current_user, CurrentUser
from app.database import async_session, ChatMessage, Conversation
from app.middleware import AuditTrail

router = APIRouter()


@router.get("/activity")
async def get_activity(limit: int = 50, current_user: CurrentUser = Depends(get_current_user)):
    """Get activity feed — recent actions across all domains."""
    entries = await AuditTrail.query(user_id=current_user.user_id, limit=limit)
    return {"activity": entries, "total": len(entries)}


@router.get("/audit-log")
async def get_audit_log(
    action: str = None,
    limit: int = 100,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get audit log entries for compliance."""
    entries = await AuditTrail.query(user_id=current_user.user_id, action=action, limit=limit)
    return {"entries": entries, "total": len(entries)}


@router.get("/analytics/usage")
async def get_usage_analytics(current_user: CurrentUser = Depends(get_current_user)):
    """Get usage analytics — messages, tool calls, integrations used."""
    all_entries = await AuditTrail.query(user_id=current_user.user_id, limit=10000)

    # Aggregate by action type
    action_counts: dict[str, int] = {}
    for entry in all_entries:
        action = entry.get("action", "unknown")
        action_counts[action] = action_counts.get(action, 0) + 1

    return {
        "total_actions": len(all_entries),
        "action_breakdown": action_counts,
        "period": "all_time",
    }


@router.get("/analytics/conversations")
async def get_conversation_analytics(current_user: CurrentUser = Depends(get_current_user)):
    """Get conversation analytics."""
    async with async_session() as session:
        total_convs = (await session.execute(
            select(func.count()).select_from(Conversation).where(Conversation.user_id == current_user.user_id)
        )).scalar() or 0
        total_msgs = (await session.execute(
            select(func.count()).select_from(ChatMessage).join(
                Conversation, ChatMessage.conversation_id == Conversation.id
            ).where(Conversation.user_id == current_user.user_id)
        )).scalar() or 0
    avg = round(total_msgs / total_convs, 1) if total_convs else 0
    return {
        "total_conversations": total_convs,
        "total_messages": total_msgs,
        "avg_messages_per_conversation": avg,
        "period": "all_time",
    }


@router.get("/analytics/integrations")
async def get_integration_analytics(current_user: CurrentUser = Depends(get_current_user)):
    """Get integration usage analytics."""
    return {
        "total_integrations": 0,
        "active_integrations": [],
        "api_calls_by_integration": {},
        "period": "all_time",
    }
