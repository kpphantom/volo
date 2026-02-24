"""
VOLO — Unified Messaging Routes
Aggregated inbox across Telegram, WhatsApp, iMessage, Signal.
Auto-2FA: When a platform needs a TOTP code, Volo pulls it from the vault.
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional

from app.services.messaging import MessagingService
from app.services.authenticator import authenticator_vault

router = APIRouter()
messaging = MessagingService()

DEFAULT_USER = "dev-user"


class SendMessageRequest(BaseModel):
    platform: str  # telegram, whatsapp, whatsapp_business, signal
    to: str  # chat_id or phone number
    text: str
    template: Optional[str] = None  # For WhatsApp Business templates


@router.get("/messages")
async def get_all_messages():
    """Get unified inbox — all messages from all platforms."""
    messages = await messaging.get_all_messages()
    return {
        "messages": messages,
        "total": len(messages),
        "platforms": messaging.get_connected_platforms(),
    }


@router.get("/messages/{platform}")
async def get_platform_messages(platform: str):
    """Get messages from a specific platform."""
    fetchers = {
        "telegram": messaging.telegram_get_updates,
        "whatsapp": messaging.whatsapp_get_messages,
        "whatsapp_business": messaging.whatsapp_biz_get_messages,
        "imessage": messaging.imessage_get_messages,
        "signal": messaging.signal_get_messages,
    }

    fetcher = fetchers.get(platform)
    if not fetcher:
        return {"error": f"Unknown platform: {platform}", "messages": []}

    messages = await fetcher()
    return {"platform": platform, "messages": messages, "total": len(messages)}


@router.post("/messages/send")
async def send_message(body: SendMessageRequest):
    """Send a message on a specific platform."""
    if body.platform == "telegram":
        result = await messaging.telegram_send(body.to, body.text)
    elif body.platform == "whatsapp":
        result = await messaging.whatsapp_send(body.to, body.text)
    elif body.platform == "whatsapp_business":
        result = await messaging.whatsapp_biz_send(body.to, body.text, body.template)
    else:
        return {"error": f"Send not supported for {body.platform}"}

    return {"platform": body.platform, "result": result}


@router.get("/messages/platforms")
async def get_messaging_platforms():
    """Get list of messaging platforms and their connection status + 2FA availability."""
    platforms = messaging.get_connected_platforms()

    # Check which platforms have TOTP configured in the vault
    totp_accounts = await authenticator_vault.list_accounts(user_id=DEFAULT_USER)
    totp_services = {a["service"] for a in totp_accounts}

    for p in platforms:
        p["has_2fa"] = p["id"] in totp_services

    return {"platforms": platforms}


@router.get("/messages/{platform}/2fa")
async def get_platform_2fa(platform: str):
    """
    Get the current 2FA code for a messaging platform.
    Called automatically when logging in or re-authenticating.

    Example: GET /api/messages/telegram/2fa
    Returns: {"code": "482901", "remaining_seconds": 17}

    This is the magic — set up Telegram 2FA in Volo's authenticator once,
    and the messaging page auto-fills it. No more opening Google Authenticator
    and copy-pasting codes.
    """
    result = await authenticator_vault.get_code(user_id=DEFAULT_USER, service=platform)
    if not result:
        return {
            "platform": platform,
            "has_2fa": False,
            "message": f"No authenticator configured for {platform}. "
                       f"Add one at POST /api/authenticator/add with service='{platform}'",
        }
    return {
        "platform": platform,
        "has_2fa": True,
        **result,
    }
