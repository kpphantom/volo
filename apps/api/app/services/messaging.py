"""
VOLO - Unified Messaging Service
Aggregates messages from Telegram, WhatsApp, WhatsApp Business,
iMessage, Signal, Discord, and Slack.

Each platform is a MessagingAdapter subclass. MessagingService
registers adapters and provides the unified inbox + per-platform
delegation used by the route handlers.
"""

import httpx
from typing import Optional
from datetime import datetime, timezone

from app.config import settings
from app.services.base_platform import MessagingAdapter


# ── Per-platform adapters ─────────────────────────────────────────────────────

class TelegramAdapter(MessagingAdapter):
    def __init__(self, token: str):
        self._token = token

    @property
    def platform_id(self) -> str: return "telegram"
    @property
    def name(self) -> str: return "Telegram"
    @property
    def is_configured(self) -> bool: return bool(self._token)
    @property
    def icon(self) -> str: return "send"
    @property
    def color(self) -> str: return "#0088cc"

    async def get_messages(self, limit: int = 50) -> list[dict]:
        if not self.is_configured:
            return self._wrap_demo(self._demo_data())
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://api.telegram.org/bot{self._token}/getUpdates",
                params={"limit": limit, "allowed_updates": '["message"]'},
                timeout=10.0,
            )
            if resp.status_code == 200:
                messages = []
                for update in resp.json().get("result", []):
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

    async def send_message(self, to: str, text: str, **kwargs) -> dict:
        if not self.is_configured:
            return {"status": "demo", "message": "Telegram not configured"}
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{self._token}/sendMessage",
                json={"chat_id": to, "text": text, "parse_mode": "Markdown"},
            )
            return resp.json()

    def _demo_data(self) -> list[dict]:
        return [
            {"from": "Alex Chen", "content": "hey, did you see the new release?", "from_username": "@alexchen"},
            {"from": "Sarah K", "content": "Meeting at 3pm works for me", "from_username": "@sarahk"},
            {"from": "Dev Group", "content": "CI/CD pipeline is green", "from_username": "devteam"},
        ]


class WhatsAppAdapter(MessagingAdapter):
    def __init__(self, token: str, phone_id: str):
        self._token = token
        self._phone_id = phone_id

    @property
    def platform_id(self) -> str: return "whatsapp"
    @property
    def name(self) -> str: return "WhatsApp"
    @property
    def is_configured(self) -> bool: return bool(self._token)
    @property
    def icon(self) -> str: return "message-circle"
    @property
    def color(self) -> str: return "#25D366"

    async def get_messages(self, limit: int = 50) -> list[dict]:
        return self._wrap_demo(self._demo_data())

    async def send_message(self, to: str, text: str, **kwargs) -> dict:
        if not self.is_configured:
            return {"status": "demo", "message": "WhatsApp not configured"}
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://graph.facebook.com/v18.0/{self._phone_id}/messages",
                headers={"Authorization": f"Bearer {self._token}"},
                json={"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text}},
            )
            return resp.json()

    def _demo_data(self) -> list[dict]:
        return [
            {"from": "Mom", "content": "Call me when you get a chance", "from_username": "+1234567890"},
            {"from": "Jake", "content": "Running 10 mins late", "from_username": "+1234567891"},
        ]


class WhatsAppBizAdapter(MessagingAdapter):
    def __init__(self, biz_token: str, biz_phone_id: str, fallback_token: str, fallback_phone_id: str):
        self._token = biz_token or fallback_token
        self._phone_id = biz_phone_id or fallback_phone_id

    @property
    def platform_id(self) -> str: return "whatsapp_business"
    @property
    def name(self) -> str: return "WhatsApp Business"
    @property
    def is_configured(self) -> bool: return bool(self._token)
    @property
    def icon(self) -> str: return "briefcase"
    @property
    def color(self) -> str: return "#128C7E"

    async def get_messages(self, limit: int = 50) -> list[dict]:
        return self._wrap_demo(self._demo_data())

    async def send_message(self, to: str, text: str, template: str | None = None, **kwargs) -> dict:
        if not self.is_configured:
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
                f"https://graph.facebook.com/v18.0/{self._phone_id}/messages",
                headers={"Authorization": f"Bearer {self._token}"},
                json=payload,
            )
            return resp.json()

    def _demo_data(self) -> list[dict]:
        return [
            {"from": "Acme Corp", "content": "Your order #4521 has shipped!", "from_username": "+1800555001"},
        ]


class IMessageAdapter(MessagingAdapter):
    @property
    def platform_id(self) -> str: return "imessage"
    @property
    def name(self) -> str: return "iMessage"
    @property
    def is_configured(self) -> bool: return True  # always available on macOS
    @property
    def icon(self) -> str: return "message-square"
    @property
    def color(self) -> str: return "#34C759"

    async def get_messages(self, limit: int = 50) -> list[dict]:
        try:
            import sqlite3
            import os as _os
            db_path = _os.path.expanduser("~/Library/Messages/chat.db")
            if not _os.path.exists(db_path):
                return self._wrap_demo(self._demo_data())
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT m.ROWID, m.text, m.date / 1000000000 + 978307200 as timestamp,"
                " m.is_from_me, h.id as handle_id,"
                " COALESCE(h.uncanonicalized_id, h.id) as display_name"
                " FROM message m LEFT JOIN handle h ON m.handle_id = h.ROWID"
                " WHERE m.text IS NOT NULL ORDER BY m.date DESC LIMIT ?",
                (limit,),
            )
            messages = []
            for row in cursor.fetchall():
                messages.append({
                    "platform": "imessage", "id": str(row[0]),
                    "from": "You" if row[3] else (row[5] or row[4] or "Unknown"),
                    "from_username": row[4] or "", "avatar": None,
                    "content": row[1] or "[attachment]",
                    "timestamp": datetime.fromtimestamp(row[2], tz=timezone.utc).isoformat() if row[2] else "",
                    "chat_id": row[4] or "", "chat_title": row[5] or row[4] or "Unknown",
                    "read": True, "type": "text", "is_from_me": bool(row[3]),
                })
            conn.close()
            return messages
        except Exception:
            return self._wrap_demo(self._demo_data())

    def _demo_data(self) -> list[dict]:
        return [
            {"from": "Tom", "content": "Check out this link", "from_username": "tom@icloud.com"},
            {"from": "Emma", "content": "Loved that restaurant!", "from_username": "+1555123456"},
        ]


class SignalAdapter(MessagingAdapter):
    def __init__(self, api_url: str):
        self._api_url = api_url

    @property
    def platform_id(self) -> str: return "signal"
    @property
    def name(self) -> str: return "Signal"
    @property
    def is_configured(self) -> bool: return bool(self._api_url)
    @property
    def icon(self) -> str: return "shield"
    @property
    def color(self) -> str: return "#3A76F0"

    async def get_messages(self, limit: int = 50) -> list[dict]:
        if not self.is_configured:
            return self._wrap_demo(self._demo_data())
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(f"{self._api_url}/v1/receive", timeout=5.0)
                if resp.status_code == 200:
                    messages = []
                    for item in resp.json():
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
                                "read": False, "type": "text",
                            })
                    return messages
            except Exception:
                pass
        return []

    def _demo_data(self) -> list[dict]:
        return [
            {"from": "Secure Contact", "content": "Documents are ready for review", "from_username": "+1555999888"},
        ]


class DiscordAdapter(MessagingAdapter):
    def __init__(self, token: str):
        self._token = token

    @property
    def platform_id(self) -> str: return "discord"
    @property
    def name(self) -> str: return "Discord"
    @property
    def is_configured(self) -> bool: return bool(self._token)
    @property
    def icon(self) -> str: return "headphones"
    @property
    def color(self) -> str: return "#5865F2"

    async def get_messages(self, limit: int = 50) -> list[dict]:
        if not self.is_configured:
            return self._wrap_demo(self._demo_data())
        headers = {"Authorization": f"Bot {self._token}"}
        all_messages = []
        async with httpx.AsyncClient() as client:
            try:
                dm_resp = await client.get(
                    "https://discord.com/api/v10/users/@me/channels",
                    headers=headers, timeout=10.0,
                )
                if dm_resp.status_code == 200:
                    for ch in dm_resp.json()[:10]:
                        ch_id = ch.get("id", "")
                        ch_name = ", ".join(
                            r.get("global_name") or r.get("username", "")
                            for r in ch.get("recipients", [])
                        )
                        msgs_resp = await client.get(
                            f"https://discord.com/api/v10/channels/{ch_id}/messages",
                            headers=headers, params={"limit": 5}, timeout=10.0,
                        )
                        if msgs_resp.status_code == 200:
                            for msg in msgs_resp.json():
                                author = msg.get("author", {})
                                ah = author.get("avatar", "")
                                aid = author.get("id", "")
                                avatar_url = f"https://cdn.discordapp.com/avatars/{aid}/{ah}.png" if ah else ""
                                all_messages.append({
                                    "platform": "discord",
                                    "id": msg.get("id", ""),
                                    "from": author.get("global_name") or author.get("username", "Unknown"),
                                    "from_username": author.get("username", ""),
                                    "avatar": avatar_url,
                                    "content": msg.get("content", "") or "[embed/media]",
                                    "timestamp": msg.get("timestamp", ""),
                                    "chat_id": ch_id,
                                    "chat_title": ch_name or "DM",
                                    "read": True, "type": "text",
                                    "attachments": [
                                        {"url": a.get("url", ""), "type": a.get("content_type", "")}
                                        for a in msg.get("attachments", [])
                                    ],
                                })
            except Exception:
                pass
        return all_messages or self._wrap_demo(self._demo_data())

    async def send_message(self, to: str, text: str, **kwargs) -> dict:
        if not self.is_configured:
            return {"status": "demo", "message": "Discord not configured"}
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://discord.com/api/v10/channels/{to}/messages",
                headers={"Authorization": f"Bot {self._token}", "Content-Type": "application/json"},
                json={"content": text},
            )
            if resp.status_code in (200, 201):
                return resp.json()
            return {"error": resp.text}

    def _demo_data(self) -> list[dict]:
        return [
            {"from": "ModBot", "content": "Welcome to the server!", "from_username": "modbot"},
            {"from": "GameBuddy", "content": "GGs last night, lets run it back", "from_username": "gamebuddy"},
            {"from": "DevTeam", "content": "New PR merged: auth flow overhaul", "from_username": "devteam"},
        ]


class SlackAdapter(MessagingAdapter):
    def __init__(self, token: str):
        self._token = token

    @property
    def platform_id(self) -> str: return "slack"
    @property
    def name(self) -> str: return "Slack"
    @property
    def is_configured(self) -> bool: return bool(self._token)
    @property
    def icon(self) -> str: return "hash"
    @property
    def color(self) -> str: return "#4A154B"

    async def get_messages(self, limit: int = 50) -> list[dict]:
        if not self.is_configured:
            return self._wrap_demo(self._demo_data())
        headers = {"Authorization": f"Bearer {self._token}"}
        all_messages = []
        async with httpx.AsyncClient() as client:
            try:
                conv_resp = await client.get(
                    "https://slack.com/api/conversations.list",
                    headers=headers,
                    params={"types": "im,mpim,public_channel,private_channel", "limit": 20},
                    timeout=10.0,
                )
                if conv_resp.status_code == 200:
                    conv_data = conv_resp.json()
                    if conv_data.get("ok"):
                        for ch in conv_data.get("channels", [])[:15]:
                            ch_id = ch.get("id", "")
                            ch_name = ch.get("name", "") or ch.get("user", "DM")
                            is_im = ch.get("is_im", False)
                            hist_resp = await client.get(
                                "https://slack.com/api/conversations.history",
                                headers=headers,
                                params={"channel": ch_id, "limit": 5},
                                timeout=10.0,
                            )
                            if hist_resp.status_code == 200:
                                hist_data = hist_resp.json()
                                if hist_data.get("ok"):
                                    for msg in hist_data.get("messages", []):
                                        ts = msg.get("ts", "")
                                        try:
                                            timestamp = datetime.fromtimestamp(
                                                float(ts), tz=timezone.utc
                                            ).isoformat()
                                        except (ValueError, TypeError):
                                            timestamp = ""
                                        title = f"#{ch_name}" if not is_im else ch_name
                                        all_messages.append({
                                            "platform": "slack",
                                            "id": ts,
                                            "from": msg.get("user", "Unknown"),
                                            "from_username": msg.get("user", ""),
                                            "avatar": None,
                                            "content": msg.get("text", "") or "[block]",
                                            "timestamp": timestamp,
                                            "chat_id": ch_id,
                                            "chat_title": title,
                                            "read": True, "type": "text",
                                        })
                # Resolve user display names
                if all_messages:
                    user_ids = {
                        m["from"] for m in all_messages
                        if m["from"] and not m["from"].startswith("#")
                    }
                    user_map = {}
                    for uid in list(user_ids)[:50]:
                        try:
                            u_resp = await client.get(
                                "https://slack.com/api/users.info",
                                headers=headers, params={"user": uid}, timeout=5.0,
                            )
                            if u_resp.status_code == 200:
                                u_data = u_resp.json()
                                if u_data.get("ok"):
                                    user_map[uid] = (
                                        u_data["user"].get("real_name")
                                        or u_data["user"].get("name", uid)
                                    )
                        except Exception:
                            pass
                    for m in all_messages:
                        if m["from"] in user_map:
                            m["from"] = user_map[m["from"]]
            except Exception:
                pass
        return all_messages or self._wrap_demo(self._demo_data())

    async def send_message(self, to: str, text: str, **kwargs) -> dict:
        if not self.is_configured:
            return {"status": "demo", "message": "Slack not configured"}
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://slack.com/api/chat.postMessage",
                headers={"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"},
                json={"channel": to, "text": text},
            )
            return resp.json()

    def _demo_data(self) -> list[dict]:
        return [
            {"from": "Jira Bot", "content": "VOLO-142 moved to In Progress", "from_username": "jirabot"},
            {"from": "Emily Davis", "content": "Can we sync on the Q2 roadmap?", "from_username": "emily"},
            {"from": "#general", "content": "Happy Friday everyone!", "from_username": "general"},
        ]


# ── Aggregator ────────────────────────────────────────────────────────────────

class MessagingService:
    """Unified inbox — registers adapters and provides route-facing methods."""

    def __init__(self):
        self._adapters: list[MessagingAdapter] = [
            TelegramAdapter(token=settings.telegram_bot_token),
            WhatsAppAdapter(
                token=settings.whatsapp_api_token,
                phone_id=settings.whatsapp_phone_id,
            ),
            WhatsAppBizAdapter(
                biz_token=settings.whatsapp_business_token,
                biz_phone_id=settings.whatsapp_business_phone_id,
                fallback_token=settings.whatsapp_api_token,
                fallback_phone_id=settings.whatsapp_phone_id,
            ),
            IMessageAdapter(),
            SignalAdapter(api_url=settings.signal_api_url),
            DiscordAdapter(token=settings.discord_bot_token),
            SlackAdapter(token=settings.slack_bot_token),
        ]
        # Index by platform_id for O(1) lookup
        self._by_id: dict[str, MessagingAdapter] = {a.platform_id: a for a in self._adapters}

    # ── Public API used by routes ─────────────────────────────────────

    async def get_all_messages(self) -> list[dict]:
        all_msgs: list[dict] = []
        for adapter in self._adapters:
            try:
                msgs = await adapter.get_messages()
                all_msgs.extend(msgs)
            except Exception:
                pass
        all_msgs.sort(key=lambda m: m.get("timestamp", ""), reverse=True)
        return all_msgs

    def get_connected_platforms(self) -> list[dict]:
        return [a.to_status_dict() for a in self._adapters]

    # ── Per-platform delegation (backwards-compat for route handlers) ──

    async def telegram_get_updates(self, limit: int = 50) -> list[dict]:
        return await self._by_id["telegram"].get_messages(limit)

    async def whatsapp_get_messages(self) -> list[dict]:
        return await self._by_id["whatsapp"].get_messages()

    async def whatsapp_biz_get_messages(self) -> list[dict]:
        return await self._by_id["whatsapp_business"].get_messages()

    async def imessage_get_messages(self, limit: int = 50) -> list[dict]:
        return await self._by_id["imessage"].get_messages(limit)

    async def signal_get_messages(self) -> list[dict]:
        return await self._by_id["signal"].get_messages()

    async def discord_get_messages(self, limit: int = 50) -> list[dict]:
        return await self._by_id["discord"].get_messages(limit)

    async def slack_get_messages(self, limit: int = 50) -> list[dict]:
        return await self._by_id["slack"].get_messages(limit)

    async def telegram_send(self, chat_id: str, text: str) -> dict:
        return await self._by_id["telegram"].send_message(chat_id, text)

    async def whatsapp_send(self, to: str, text: str) -> dict:
        return await self._by_id["whatsapp"].send_message(to, text)

    async def whatsapp_biz_send(self, to: str, text: str, template: Optional[str] = None) -> dict:
        return await self._by_id["whatsapp_business"].send_message(to, text, template=template)

    async def discord_send(self, channel_id: str, text: str) -> dict:
        return await self._by_id["discord"].send_message(channel_id, text)

    async def slack_send(self, channel_id: str, text: str) -> dict:
        return await self._by_id["slack"].send_message(channel_id, text)
