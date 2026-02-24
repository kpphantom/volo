"""
VOLO — Webhook Routes
Receive and dispatch webhooks from external services.
"""

import uuid
import hmac
import hashlib
import json
import logging
from datetime import datetime

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("volo.webhooks")

router = APIRouter()

# In-memory webhook store
_webhooks: list[dict] = []
_webhook_events: list[dict] = []


class WebhookCreate(BaseModel):
    url: str
    events: list[str]
    secret: str = ""


class WebhookEvent(BaseModel):
    source: str
    event_type: str
    payload: dict


@router.post("/webhooks")
async def create_webhook(body: WebhookCreate):
    """Register a new outbound webhook."""
    webhook = {
        "id": str(uuid.uuid4()),
        "url": body.url,
        "events": body.events,
        "secret": body.secret or str(uuid.uuid4()),
        "active": True,
        "created_at": datetime.utcnow().isoformat(),
    }
    _webhooks.append(webhook)
    return webhook


@router.get("/webhooks")
async def list_webhooks():
    """List all registered webhooks."""
    return {"webhooks": _webhooks}


@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(webhook_id: str):
    """Delete a webhook."""
    global _webhooks
    _webhooks = [w for w in _webhooks if w["id"] != webhook_id]
    return {"deleted": True}


# ── Inbound Webhooks ────────────────────────

@router.post("/webhooks/github")
async def github_webhook(request: Request):
    """Receive GitHub webhook events (push, PR, issue, etc.)."""
    body = await request.body()
    event_type = request.headers.get("X-GitHub-Event", "unknown")
    delivery_id = request.headers.get("X-GitHub-Delivery", "")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON payload")

    event = {
        "id": delivery_id or str(uuid.uuid4()),
        "source": "github",
        "type": event_type,
        "summary": _summarize_github_event(event_type, payload),
        "received_at": datetime.utcnow().isoformat(),
    }
    _webhook_events.append(event)
    logger.info(f"GitHub webhook: {event_type} — {event['summary']}")

    return {"received": True, "event_type": event_type}


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    """Receive Stripe webhook events (subscription, payment, etc.)."""
    body = await request.body()
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON payload")

    event_type = payload.get("type", "unknown")
    event = {
        "id": payload.get("id", str(uuid.uuid4())),
        "source": "stripe",
        "type": event_type,
        "received_at": datetime.utcnow().isoformat(),
    }
    _webhook_events.append(event)
    logger.info(f"Stripe webhook: {event_type}")

    return {"received": True, "event_type": event_type}


@router.post("/webhooks/slack")
async def slack_webhook(request: Request):
    """Receive Slack event subscriptions."""
    body = await request.json()

    # Slack URL verification challenge
    if body.get("type") == "url_verification":
        return {"challenge": body.get("challenge")}

    event = body.get("event", {})
    _webhook_events.append({
        "id": str(uuid.uuid4()),
        "source": "slack",
        "type": event.get("type", "unknown"),
        "received_at": datetime.utcnow().isoformat(),
    })

    return {"ok": True}


@router.get("/webhooks/events")
async def list_webhook_events(limit: int = 50):
    """List recent webhook events."""
    return {"events": list(reversed(_webhook_events))[:limit]}


def _summarize_github_event(event_type: str, payload: dict) -> str:
    repo = payload.get("repository", {}).get("full_name", "")
    if event_type == "push":
        commits = payload.get("commits", [])
        return f"{len(commits)} commit(s) pushed to {repo}"
    elif event_type == "pull_request":
        action = payload.get("action", "")
        pr = payload.get("pull_request", {})
        return f"PR #{pr.get('number', '?')} {action}: {pr.get('title', '')}"
    elif event_type == "issues":
        action = payload.get("action", "")
        issue = payload.get("issue", {})
        return f"Issue #{issue.get('number', '?')} {action}: {issue.get('title', '')}"
    return f"{event_type} event for {repo}"
