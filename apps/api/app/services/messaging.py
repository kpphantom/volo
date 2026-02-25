"""
VOLO - Unified Messaging Service
Aggregates messages from Telegram, WhatsApp, WhatsApp Business,
iMessage, Signal, Discord, and Slack.
"""

import httpx
from typing import Optional
from datetime import datetime, timezone

from app.config import settings


class MessagingService:
    """Unified inbox across all messaging platforms."""

    def __init__(self):
        self.telegram_token = settings.telegram_bot_token
        self.whatsapp_token = settings.whatsapp_api_token
        self.whatsapp_phone_id = settings.whatsapp_phone_id
        self.whatsapp_biz_token = settings.whatsapp_business_token
        self.whatsapp_biz_phone_id = settings.whatsapp_business_phone_id
        self.signal_api_url = settings.signal_api_url
        self.discord_bot_token = settings.discord_bot_token
        self.slack_bot_token = settings.slack_bot_token

    # ── Telegram ────────────────────────────────────────────────────────

    async def telegram_get_updates(self, limit: int = 50) -> list:
        if not self.telegram_token:
            return self._demo_messages("telegram")
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://api.telegram.org/bot{self.telegram_token}/getUpdates",
                params={"limit": limit, "allowed_updates": '["message"]'},
                timeout=10.0,
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
        if not self.telegram_token:
            return {"status": "demo", "message": "Telegram not configured"}
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{self.telegram_token}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            )
            return resp.json()

    # ── WhatsApp (Meta Cloud API) ───────────────────────────────────────

    async def whatsapp_get_messages(self) -> list:
        return self._demo_messages("whatsapp")

    async def whatsapp_send(self, to: str, text: str) -> dict:
        if not self.whatsapp_token:
            return {"status": "demo", "message": "WhatsApp not configured"}
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://graph.facebook.com/v18.0/{self.whatsapp_phone_id}/messages",
                headers={"Authorization": f"Bearer {self.whatsapp_token}"},
                json={"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text}},
            )
            return resp.json()

    # ── WhatsApp Business ───────────────────────────────────────────────

    async def whatsapp_biz_get_messages(self) -> list:
        return self._demo_messages("whatsapp_business")

    async def whatsapp_biz_send(self, to: str, text: str, template: Optional[str] = None) -> dict:
        token = self.whatsapp_biz_token or self.whatsapp_token
        phone_id = self.whatsapp_biz_phone_id or self.whatsapp_phone_id
        if not token:
            return {"status": "demo", "message": "WhatsApp Business not configured"}
        payload = {"messaging_product": "whatsapp", "to": to}
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

    async def imessage_get_messages(self, limit: int = 50) -> list:
        try:
            import sqlite3
            import os as _os
            db_path = _os.path.expanduser("~/Library/Messages/chat.db")
            if not _os.path.exists(db_path):
                return self._demo_messages("imessage")
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
            return self._demo_messages("imessage")

    # ── Signal ──────────────────────────────────────────────────────────

    async def signal_get_messages(self) -> list:
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
                                "read": False, "type": "text",
                            })
                    return messages
            except Exception:
                pass
        return []

    # ── Discord ─────────────────────────────────────────────────────────

    async def discord_get_messages(self, limit: int = 50) -> list:
        if not self.discord_bot_token:
            return self._demo_messages("discord")
        headers = {"Authorization": f"Bot {self.discord_bot_token}"}
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
                        recipients = ch.get("recipients", [])
                        ch_name = ", ".join(
                            r.get("global_name") or r.get("username", "")
                            for r in recipients
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
        return all_messages or self._demo_messages("discord")

    async def discord_send(self, channel_id: str, text: str) -> dict:
        if not self.discord_bot_token:
            return {"status": "demo", "message": "Discord not configured"}
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://discord.com/api/v10/channels/{channel_id}/messages",
                headers={
                    "Authorization": f"Bot {self.discord_bot_token}",
                    "Content-Type": "application/json",
                },
                json={"content": text},
            )
            if resp.status_code in (200, 201):
                return resp.json()
            return {"error": resp.text}

    # ── Slack ───────────────────────────────────────────────────────────

    async def slack_get_messages(self, limit: int = 50) -> list:
        if not self.slack_bot_token:
            return self._demo_messages("slack")
        headers = {"Authorization": f"Bearer {self.slack_bot_token}"}
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
        return all_messages or self._demo_messages("slack")

    async def slack_send(self, channel_id: str, text: str) -> dict:
        if not self.slack_bot_token:
            return {"status": "demo", "message": "Slack not configured"}
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://slack.com/api/chat.postMessage",
                headers={
                    "Authorization": f"Bearer {self.slack_bot_token}",
                    "Content-Type": "application/json",
                },
                json={"channel": channel_id, "text": text},
            )
            return resp.json()

    # ── Unified Inbox ───────────────────────────────────────────────────

    async def get_all_messages(self) -> list:
        all_msgs = []
        fetchers = [
            self.telegram_get_updates,
            self.whatsapp_get_messages,
            self.whatsapp_biz_get_messages,
            self.imessage_get_messages,
            self.signal_get_messages,
            self.discord_get_messages,
            self.slack_get_messages,
        ]
        for fetcher in fetchers:
            try:
                msgs = await fetcher()
                all_msgs.extend(msgs)
            except Exception:
                pass
        all_msgs.sort(key=lambda m: m.get("timestamp", ""), reverse=True)
        return all_msgs

    def get_connected_platforms(self) -> list:
        return [
            {"id": "telegram", "name": "Telegram", "connected": bool(self.telegram_token), "icon": "send", "color": "#0088cc"},
            {"id": "whatsapp", "name": "WhatsApp", "connected": bool(self.whatsapp_token), "icon": "message-circle", "color": "#25D366"},
            {"id": "whatsapp_business", "name": "WhatsApp Business", "connected": bool(self.whatsapp_biz_token or self.whatsapp_token), "icon": "briefcase", "color": "#128C7E"},
            {"id": "imessage", "name": "iMessage", "connected": True, "icon": "message-square", "color": "#34C759"},
            {"id": "signal", "name": "Signal", "connected": bool(self.signal_api_url), "icon": "shield", "color": "#3A76F0"},
            {"id": "discord", "name": "Discord", "connected": bool(self.discord_bot_token), "icon": "headphones", "color": "#5865F2"},
            {"id": "slack", "name": "Slack", "connected": bool(self.slack_bot_token), "icon": "hash", "color": "#4A154B"},
        ]

    # ── Demo Data ───────────────────────────────────────────────────────

    def _demo_messages(self, platform: str) -> list:
        now = datetime.now(timezone.utc).isoformat()
        demos = {
            "telegram": [
                {"from": "Alex Chen", "content": "hey, did you see the new release?", "from_username": "@alexchen"},
                {"from": "Sarah K", "content": "Meeting at 3pm works for me", "from_username": "@sarahk"},
                {"from": "Dev Group", "content": "CI/CD pipeline is green", "from_username": "devteam"},
            ],
            "whatsapp": [
                {"from": "Mom", "content": "Call me when you get a chance", "from_username": "+1234567890"},
                {"from": "Jake", "content": "Running 10 mins late", "from_username": "+1234567891"},
            ],
            "whatsapp_business": [
                {"from": "Acme Corp", "content": "Your order #4521 has shipped!", "from_username": "+1800555001"},
            ],
            "imessage": [
                {"from": "Tom", "content": "Check out this link", "from_username": "tom@icloud.com"},
                {"from": "Emma", "content": "Loved that restaurant!", "from_username": "+1555123456"},
            ],
            "signal": [
                {"from": "Secure Contact", "content": "Documents are ready for review", "from_username": "+1555999888"},
            ],
            "discord": [
                {"from": "ModBot", "content": "Welcome to the server!", "from_username": "modbot"},
                {"from": "GameBuddy", "content": "GGs last night, lets run it back", "from_username": "gamebuddy"},
                {"from": "DevTeam", "content": "New PR merged: auth flow overhaul", "from_username": "devteam"},
            ],
            "slack": [
                {"from": "Jira Bot", "content": "VOLO-142 moved to In Progress", "from_username": "jirabot"},
                {"from": "Emily Davis", "content": "Can we sync on the Q2 roadmap?", "from_username": "emily"},
                {"from": "#general", "content": "Happy Friday everyone!", "from_username": "general"},
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
                "_demo": True,
            }
            for i, msg in enumerate(demos.get(platform, []))
        ]
