"""
VOLO — Approval Routes
Manage agent action approvals (trading, sending emails, etc.)
"""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

# In-memory store
_approvals: list[dict] = []


class ApprovalCreate(BaseModel):
    action: str
    description: str = ""
    tool_name: str = ""
    parameters: dict = {}
    tier: str = "approve"


@router.get("/approvals")
async def list_approvals(status: Optional[str] = None):
    """List approval requests."""
    results = _approvals
    if status:
        results = [a for a in results if a["status"] == status]
    return {"approvals": list(reversed(results))[:50], "total": len(results)}


@router.get("/approvals/pending")
async def list_pending():
    """List pending approvals."""
    pending = [a for a in _approvals if a["status"] == "pending"]
    return {"approvals": list(reversed(pending)), "total": len(pending)}


@router.post("/approvals")
async def create_approval(body: ApprovalCreate):
    """Create a new approval request (usually triggered by the agent)."""
    approval = {
        "id": str(uuid.uuid4()),
        "action": body.action,
        "description": body.description,
        "tool_name": body.tool_name,
        "parameters": body.parameters,
        "tier": body.tier,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
        "resolved_at": None,
    }
    _approvals.append(approval)
    return approval


@router.post("/approvals/{approval_id}/approve")
async def approve_action(approval_id: str):
    """Approve a pending action."""
    for a in _approvals:
        if a["id"] == approval_id and a["status"] == "pending":
            a["status"] = "approved"
            a["resolved_at"] = datetime.utcnow().isoformat()
            # TODO: Execute the approved action via tool registry
            return {"approved": True, "approval": a}
    return {"error": "Approval not found or already resolved"}


@router.post("/approvals/{approval_id}/deny")
async def deny_action(approval_id: str, reason: str = ""):
    """Deny a pending action."""
    for a in _approvals:
        if a["id"] == approval_id and a["status"] == "pending":
            a["status"] = "denied"
            a["resolved_at"] = datetime.utcnow().isoformat()
            a["deny_reason"] = reason
            return {"denied": True, "approval": a}
    return {"error": "Approval not found or already resolved"}
