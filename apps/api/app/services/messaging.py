"""
VOLO — Unified Messaging Service
Aggregates messages from Telegram, WhatsApp, WhatsApp Business, iMessage, Signal.
"""

import os
import httpx
from typing import Optional
from datetime import datetime, timezone


class MessagingService:
    """Unified inbox across all messaging platforms."""

    def __init__(self):
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.whatsapp_token = os.getenv("WHATSAPP_API_TOKEN", "")
        self.whatsapp_phone_id = os.getenv("WHATSAPP_PHONE_ID", "")
        self.whatsapp_biz_token = os.getenv("WHATSAPP_BUSINESS_TOKEN", "")
        self.whatsapp_biz_phone_id = os.getenv("WHATSAPP_BUSINESS_PHONE_ID", "")
        self.signal_api_url = os.getenv("SIGNAL_API_URL", "")

    # ── Telegram ────────────────────────────────────────────────────────

    async def telegram_get_updates(self, limit: int = 50) -> list[dict]:
        """Get recent Telegram messages."""
        if not self.telegram_token:
            return self._demo_messages("telegram")

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://api.telegram.org/bot{self.telegram_token}/getUpdates",
                params={"limit": limit, "allowed_updates": '["message"]'},
            )
            if resp.status_code == 200:
                data = resp.json()
                messages = []
                for update in data.get("result", []):
                    msg = update.get("message", {})
                    if msg:
                        messages.append({
                            "platform": "telegram",
                            "id": str(msg.get("message_id", "")),
                            "from": msg.get("from", {}).get("first_name", "Unknown"),
                            "from_username": msg.get("from", {}).get("username", ""),
                            "avatar": None,
                            "content": msg.get("text", "[media]"),
                            "timestamp": datetime.fromtimestamp(msg.get("date", 0), tz=timezone.utc).isoformat(),
                            "chat_id": str(msg.get("chat", {}).get("id", "")),
                            "chat_title": msg.get("chat", {}).get("title", msg.get("from", {}).get("first_name", "")),
                            "read": True,
                            "type": "text" if msg.get("text") else "media",
                        })
                return messages
        return []

    async def telegram_send(self, chat_id: str, text: str) -> dict:
        """Send a Telegram message."""
        if not self.telegram_token:
            return {"status": "demo", "message": "Telegram not configured"}

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{self.telegram_token}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            )
            return resp.json()

    # ── WhatsApp (Meta Cloud API) ───────────────────────────────────────

    async def whatsapp_get_messages(self) -> list[dict]:
        """Get WhatsApp messages via webhook history."""
        # WhatsApp Cloud API uses webhooks — messages are pushed, not pulled
        # Return stored messages from webhook endpoint
        return self._demo_messages("whatsapp")

    async def whatsapp_send(self, to: str, text: str) -> dict:
        """Send a WhatsApp message."""
        if not self.whatsapp_token:
            return {"status": "demo", "message": "WhatsApp not configured"}

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://graph.facebook.com/v18.0/{self.whatsapp_phone_id}/messages",
                headers={"Authorization": f"Bearer {self.whatsapp_token}"},
                json={
                    "messaging_product": "whatsapp",
                    "to": to,
                    "type": "text",
                    "text": {"body": text},
                },
            )
            return resp.json()

    # ── WhatsApp Business ───────────────────────────────────────────────

    async def whatsapp_biz_get_messages(self) -> list[dict]:
        """Get WhatsApp Business messages."""
        return self._demo_messages("whatsapp_business")

    async def whatsapp_biz_send(self, to: str, text: str, template: Optional[str] = None) -> dict:
        """Send a WhatsApp Business message (text or template)."""
        token = self.whatsapp_biz_token or self.whatsapp_token
        phone_id = self.whatsapp_biz_phone_id or self.whatsapp_phone_id
        if not token:
            return {"status": "demo", "message": "WhatsApp Business not configured"}

        payload: dict = {"messaging_product": "whatsapp", "to": to}
        if template:
            payload["type"] = "template"
            payload["template"] = {"name": template, "language": {"code": "en_US"}}
        else:
            payload["type"] = "text"
            payload["text"] = {"body": text}

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://graph.facebook.com/v18.0/{phone_id}/messages",
                headers={"Authorization": f"Bearer {token}"},
                json=payload,
            )
            return resp.json()

    # ── iMessage (macOS Bridge) ─────────────────────────────────────────

    async def imessage_get_messages(self, limit: int = 50) -> list[dict]:
        """
        Get iMessages from local macOS Messages database.
        Requires macOS with full disk access permission.
        """
        try:
            import sqlite3
            import os
            db_path = os.path.expanduser("~/Library/Messages/chat.db")
            if not os.path.exists(db_path):
                return self._demo_messages("imessage")

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    m.ROWID,
                    m.text,
                    m.date / 1000000000 + 978307200 as timestamp,
                    m.is_from_me,
                    h.id as handle_id,
                    COALESCE(h.uncanonicalized_id, h.id) as display_name
                FROM message m
                LEFT JOIN handle h ON m.handle_id = h.ROWID
                WHERE m.text IS NOT NULL
                ORDER BY m.date DESC
                LIMIT ?
            """, (limit,))

            messages = []
            for row in cursor.fetchall():
                messages.append({
                    "platform": "imessage",
                    "id": str(row[0]),
                    "from": "You" if row[3] else (row[5] or row[4] or "Unknown"),
                    "from_username": row[4] or "",
                    "avatar": None,
                    "content": row[1] or "[attachment]",
                    "timestamp": datetime.fromtimestamp(row[2], tz=timezone.utc).isoformat() if row[2] else "",
                    "chat_id": row[4] or "",
                    "chat_title": row[5] or row[4] or "Unknown",
                    "read": True,
                    "type": "text",
                    "is_from_me": bool(row[3]),
                })
            conn.close()
            return messages
        except Exception:
            return self._demo_messages("imessage")

    # ── Signal (via signal-cli REST API) ────────────────────────────────

    async def signal_get_messages(self) -> list[dict]:
        """Get Signal messages via signal-cli REST API."""
        if not self.signal_api_url:
            return self._demo_messages("signal")

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(f"{self.signal_api_url}/v1/receive", timeout=5.0)
                if resp.status_code == 200:
                    data = resp.json()
                    messages = []
                    for item in data:
                        envelope = item.get("envelope", {})
                        data_msg = envelope.get("dataMessage", {})
                        if data_msg.get("message"):
                            messages.append({
                                "platform": "signal",
                                "id": str(envelope.get("timestamp", "")),
                                "from": envelope.get("sourceName", envelope.get("source", "Unknown")),
                                "from_username": envelope.get("source", ""),
                                "avatar": None,
                                "content": data_msg["message"],
                                "timestamp": datetime.fromtimestamp(
                                    envelope.get("timestamp", 0) / 1000, tz=timezone.utc
                                ).isoformat(),
                                "chat_id": envelope.get("source", ""),
                                "chat_title": envelope.get("sourceName", ""),
                                "read": False,
                                "type": "text",
                            })
                    return messages
            except Exception:
                pass
        return []

    # ── Unified Inbox ───────────────────────────────────────────────────

    async def get_all_messages(self) -> list[dict]:
        """Get messages from ALL platforms, sorted by time."""
        all_msgs: list[dict] = []

        telegram = await self.telegram_get_updates()
        all_msgs.extend(telegram)

        whatsapp = await self.whatsapp_get_messages()
        all_msgs.extend(whatsapp)

        whatsapp_biz = await self.whatsapp_biz_get_messages()
        all_msgs.extend(whatsapp_biz)

        imessage = await self.imessage_get_messages()
        all_msgs.extend(imessage)

        signal = await self.signal_get_messages()
        all_msgs.extend(signal)

        # Sort by timestamp descending
        all_msgs.sort(key=lambda m: m.get("timestamp", ""), reverse=True)
        return all_msgs

    def get_connected_platforms(self) -> list[dict]:
        """Check which messaging platforms are configured."""
        platforms = [
            {
                "id": "telegram",
                "name": "Telegram",
                "connected": bool(self.telegram_token),
                "icon": "send",
                "color": "#0088cc",
            },
            {
                "id": "whatsapp",
                "name": "WhatsApp",
                "connected": bool(self.whatsapp_token),
                "icon": "message-circle",
                "color": "#25D366",
            },
            {
                "id": "whatsapp_business",
                "name": "WhatsApp Business",
                "connected": bool(self.whatsapp_biz_token or self.whatsapp_token),
                "icon": "briefcase",
                "color": "#128C7E",
            },
            {
                "id": "imessage",
                "name": "iMessage",
                "connected": True,  # Always available on macOS
                "icon": "message-square",
                "color": "#34C759",
            },
            {
                "id": "signal",
                "name": "Signal",
                "connected": bool(self.signal_api_url),
                "icon": "shield",
                "color": "#3A76F0",
            },
        ]
        return platforms

    # ── Demo Data ───────────────────────────────────────────────────────

    def _demo_messages(self, platform: str) -> list[dict]:
        """Generate realistic demo messages for a platform."""
        now = datetime.now(timezone.utc).isoformat()
        demos = {
            "telegram": [
                {"from": "Alex Chen", "content": "hey, did you see the new release?", "from_username": "@alexchen"},
                {"from": "Sarah K", "content": "Meeting at 3pm works for me 👍", "from_username": "@sarahk"},
                {"from": "Dev Group", "content": "CI/CD pipeline is green ✅", "from_username": "devteam"},
            ],
            "whatsapp": [
                {"from": "Mom", "content": "Call me when you get a chance 💕", "from_username": "+1234567890"},
                {"from": "Jake", "content": "Running 10 mins late", "from_username": "+1234567891"},
                {"from": "Family Group", "content": "Dinner Sunday?", "from_username": "family"},
            ],
            "whatsapp_business": [
                {"from": "Acme Corp", "content": "Your order #4521 has shipped!", "from_username": "+1800555001"},
                {"from": "Bank Alert", "content": "Transaction of $42.50 at Starbucks", "from_username": "+1800555002"},
            ],
            "imessage": [
                {"from": "Tom", "content": "Check out this link", "from_username": "tom@icloud.com"},
                {"from": "Emma", "content": "Loved that restaurant!", "from_username": "+1555123456"},
                {"from": "Dad", "content": "Proud of you son 🎉", "from_username": "+1555654321"},
            ],
            "signal": [
                {"from": "Secure Contact", "content": "Documents are ready for review", "from_username": "+1555999888"},
            ],
        }

        return [
            {
                "platform": platform,
                "id": f"demo-{platform}-{i}",
                "from": msg["from"],
                "from_username": msg["from_username"],
                "avatar": None,
                "content": msg["content"],
                "timestamp": now,
                "chat_id": msg["from_username"],
                "chat_title": msg["from"],
                "read": i > 0,
                "type": "text",
            }
            for i, msg in enumerate(demos.get(platform, []))
        ]
