"""
VOLO — Standing Orders Routes
Manage automated recurring tasks, cron-based jobs, event-triggered actions.
"""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

# In-memory store (DB in production)
_standing_orders: list[dict] = []


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


@router.get("/standing-orders")
async def list_standing_orders():
    """List all standing orders."""
    return {"standing_orders": _standing_orders, "total": len(_standing_orders)}


@router.post("/standing-orders")
async def create_standing_order(body: StandingOrderCreate):
    """Create a new standing order."""
    order = {
        "id": str(uuid.uuid4()),
        "name": body.name,
        "description": body.description,
        "trigger_type": body.trigger_type,
        "trigger_config": body.trigger_config,
        "actions": body.actions,
        "enabled": body.enabled,
        "run_count": 0,
        "last_run_at": None,
        "next_run_at": None,
        "created_at": datetime.utcnow().isoformat(),
    }
    _standing_orders.append(order)
    return order


@router.get("/standing-orders/{order_id}")
async def get_standing_order(order_id: str):
    """Get a specific standing order."""
    for order in _standing_orders:
        if order["id"] == order_id:
            return order
    return {"error": "Standing order not found"}


@router.patch("/standing-orders/{order_id}")
async def update_standing_order(order_id: str, body: StandingOrderUpdate):
    """Update a standing order."""
    for order in _standing_orders:
        if order["id"] == order_id:
            if body.name is not None:
                order["name"] = body.name
            if body.description is not None:
                order["description"] = body.description
            if body.trigger_config is not None:
                order["trigger_config"] = body.trigger_config
            if body.actions is not None:
                order["actions"] = body.actions
            if body.enabled is not None:
                order["enabled"] = body.enabled
            return order
    return {"error": "Standing order not found"}


@router.delete("/standing-orders/{order_id}")
async def delete_standing_order(order_id: str):
    """Delete a standing order."""
    global _standing_orders
    before = len(_standing_orders)
    _standing_orders = [o for o in _standing_orders if o["id"] != order_id]
    return {"deleted": len(_standing_orders) < before}


@router.post("/standing-orders/{order_id}/run")
async def run_standing_order(order_id: str):
    """Manually trigger a standing order."""
    for order in _standing_orders:
        if order["id"] == order_id:
            order["run_count"] = order.get("run_count", 0) + 1
            order["last_run_at"] = datetime.utcnow().isoformat()
            return {"executed": True, "order": order}
    return {"error": "Standing order not found"}
