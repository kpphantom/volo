"""
VOLO — Activity & Audit Routes
Activity feed, audit log, and usage analytics.
"""

from fastapi import APIRouter
from app.middleware import AuditTrail

router = APIRouter()


@router.get("/activity")
async def get_activity(limit: int = 50, user_id: str = None):
    """Get activity feed — recent actions across all domains."""
    entries = AuditTrail.query(user_id=user_id, limit=limit)
    return {"activity": entries, "total": len(entries)}


@router.get("/audit-log")
async def get_audit_log(
    action: str = None,
    user_id: str = None,
    limit: int = 100,
):
    """Get audit log entries for compliance."""
    entries = AuditTrail.query(user_id=user_id, action=action, limit=limit)
    return {"entries": entries, "total": len(entries)}


@router.get("/analytics/usage")
async def get_usage_analytics():
    """Get usage analytics — messages, tool calls, integrations used."""
    all_entries = AuditTrail.query(limit=10000)

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
async def get_conversation_analytics():
    """Get conversation analytics."""
    return {
        "total_conversations": 0,
        "total_messages": 0,
        "avg_messages_per_conversation": 0,
        "tool_calls_total": 0,
        "most_used_tools": [],
        "period": "all_time",
    }


@router.get("/analytics/integrations")
async def get_integration_analytics():
    """Get integration usage analytics."""
    return {
        "total_integrations": 0,
        "active_integrations": [],
        "api_calls_by_integration": {},
        "period": "all_time",
    }
