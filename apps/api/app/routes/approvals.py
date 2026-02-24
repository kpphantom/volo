"""
VOLO — Approval Routes
Manage agent action approvals, backed by PostgreSQL.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.database import async_session, ApprovalRequest

router = APIRouter()

DEFAULT_USER = "dev-user"


class ApprovalCreate(BaseModel):
    action: str
    description: str = ""
    tool_name: str = ""
    parameters: dict = {}
    tier: str = "approve"


def _approval_dict(a):
    return {
        "id": a.id,
        "action": a.action,
        "description": a.description,
        "tool_name": a.tool_name,
        "parameters": a.parameters,
        "tier": a.tier,
        "status": a.status,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
    }


@router.get("/approvals")
async def list_approvals(status: Optional[str] = None):
    """List approval requests."""
    async with async_session() as session:
        query = select(ApprovalRequest).where(ApprovalRequest.user_id == DEFAULT_USER)
        if status:
            query = query.where(ApprovalRequest.status == status)
        query = query.order_by(ApprovalRequest.created_at.desc()).limit(50)
        result = await session.execute(query)
        approvals = result.scalars().all()
    return {"approvals": [_approval_dict(a) for a in approvals], "total": len(approvals)}


@router.get("/approvals/pending")
async def list_pending():
    """List pending approvals."""
    async with async_session() as session:
        result = await session.execute(
            select(ApprovalRequest).where(
                ApprovalRequest.user_id == DEFAULT_USER,
                ApprovalRequest.status == "pending",
            ).order_by(ApprovalRequest.created_at.desc())
        )
        pending = result.scalars().all()
    return {"approvals": [_approval_dict(a) for a in pending], "total": len(pending)}


@router.post("/approvals")
async def create_approval(body: ApprovalCreate):
    """Create a new approval request."""
    async with async_session() as session:
        approval = ApprovalRequest(
            user_id=DEFAULT_USER,
            action=body.action,
            description=body.description,
            tool_name=body.tool_name,
            parameters=body.parameters,
            tier=body.tier,
        )
        session.add(approval)
        await session.commit()
        await session.refresh(approval)
    return _approval_dict(approval)


@router.post("/approvals/{approval_id}/approve")
async def approve_action(approval_id: str):
    """Approve a pending action."""
    async with async_session() as session:
        result = await session.execute(
            select(ApprovalRequest).where(ApprovalRequest.id == approval_id)
        )
        a = result.scalar_one_or_none()
        if not a or a.status != "pending":
            raise HTTPException(404, "Approval not found or already resolved")

        a.status = "approved"
        a.resolved_at = datetime.utcnow()
        await session.commit()
    return {"approved": True, "approval": _approval_dict(a)}


@router.post("/approvals/{approval_id}/deny")
async def deny_action(approval_id: str, reason: str = ""):
    """Deny a pending action."""
    async with async_session() as session:
        result = await session.execute(
            select(ApprovalRequest).where(ApprovalRequest.id == approval_id)
        )
        a = result.scalar_one_or_none()
        if not a or a.status != "pending":
            raise HTTPException(404, "Approval not found or already resolved")

        a.status = "denied"
        a.resolved_at = datetime.utcnow()
        await session.commit()
    return {"denied": True, "approval": _approval_dict(a)}
