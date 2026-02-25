"""
VOLO — Standing Orders Routes
Manage automated recurring tasks, backed by PostgreSQL.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import select

from app.auth import get_current_user, CurrentUser
from app.database import async_session, StandingOrder

router = APIRouter()


class StandingOrderCreate(BaseModel):
    name: str
    description: str = ""
    trigger_type: str  # cron, event, condition
    trigger_config: dict = {}
    actions: list[dict] = []
    enabled: bool = True


class StandingOrderUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    trigger_config: Optional[dict] = None
    actions: Optional[list[dict]] = None
    enabled: Optional[bool] = None


def _order_dict(o):
    return {
        "id": o.id,
        "name": o.name,
        "description": o.description,
        "trigger_type": o.trigger_type,
        "trigger_config": o.trigger_config,
        "actions": o.actions,
        "enabled": o.enabled,
        "last_run_at": o.last_run_at.isoformat() if o.last_run_at else None,
        "next_run_at": o.next_run_at.isoformat() if o.next_run_at else None,
        "created_at": o.created_at.isoformat() if o.created_at else None,
    }


@router.get("/standing-orders")
async def list_standing_orders(current_user: CurrentUser = Depends(get_current_user)):
    """List all standing orders."""
    async with async_session() as session:
        result = await session.execute(
            select(StandingOrder).where(StandingOrder.user_id == current_user.user_id)
        )
        orders = result.scalars().all()
    return {"standing_orders": [_order_dict(o) for o in orders], "total": len(orders)}


@router.post("/standing-orders")
async def create_standing_order(body: StandingOrderCreate, current_user: CurrentUser = Depends(get_current_user)):
    """Create a new standing order."""
    async with async_session() as session:
        order = StandingOrder(
            user_id=current_user.user_id,
            name=body.name,
            description=body.description,
            trigger_type=body.trigger_type,
            trigger_config=body.trigger_config,
            actions=body.actions,
            enabled=body.enabled,
        )
        session.add(order)
        await session.commit()
        await session.refresh(order)
    return _order_dict(order)


@router.get("/standing-orders/{order_id}")
async def get_standing_order(order_id: str, current_user: CurrentUser = Depends(get_current_user)):
    """Get a specific standing order."""
    async with async_session() as session:
        result = await session.execute(
            select(StandingOrder).where(
                StandingOrder.id == order_id,
                StandingOrder.user_id == current_user.user_id,
            )
        )
        order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(404, "Standing order not found")
    return _order_dict(order)


@router.patch("/standing-orders/{order_id}")
async def update_standing_order(order_id: str, body: StandingOrderUpdate, current_user: CurrentUser = Depends(get_current_user)):
    """Update a standing order."""
    async with async_session() as session:
        result = await session.execute(
            select(StandingOrder).where(
                StandingOrder.id == order_id,
                StandingOrder.user_id == current_user.user_id,
            )
        )
        order = result.scalar_one_or_none()
        if not order:
            raise HTTPException(404, "Standing order not found")

        if body.name is not None:
            order.name = body.name
        if body.description is not None:
            order.description = body.description
        if body.trigger_config is not None:
            order.trigger_config = body.trigger_config
        if body.actions is not None:
            order.actions = body.actions
        if body.enabled is not None:
            order.enabled = body.enabled

        await session.commit()
        await session.refresh(order)
    return _order_dict(order)


@router.delete("/standing-orders/{order_id}")
async def delete_standing_order(order_id: str, current_user: CurrentUser = Depends(get_current_user)):
    """Delete a standing order."""
    async with async_session() as session:
        result = await session.execute(
            select(StandingOrder).where(
                StandingOrder.id == order_id,
                StandingOrder.user_id == current_user.user_id,
            )
        )
        order = result.scalar_one_or_none()
        if not order:
            return {"deleted": False}
        await session.delete(order)
        await session.commit()
    return {"deleted": True}


@router.post("/standing-orders/{order_id}/run")
async def run_standing_order(order_id: str, current_user: CurrentUser = Depends(get_current_user)):
    """Manually trigger a standing order."""
    async with async_session() as session:
        result = await session.execute(
            select(StandingOrder).where(
                StandingOrder.id == order_id,
                StandingOrder.user_id == current_user.user_id,
            )
        )
        order = result.scalar_one_or_none()
        if not order:
            raise HTTPException(404, "Standing order not found")

        order.last_run_at = datetime.utcnow()
        await session.commit()
        await session.refresh(order)
    return {"executed": True, "order": _order_dict(order)}
