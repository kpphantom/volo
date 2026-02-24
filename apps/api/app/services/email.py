"""
VOLO — Email Service
Gmail and Outlook integration for inbox management.
"""

import os
import logging
from typing import Optional
import httpx

logger = logging.getLogger("volo.email")


class EmailService:
    """Handles email operations via Gmail or Outlook APIs."""

    GMAIL_BASE = "https://gmail.googleapis.com/gmail/v1"

    def __init__(self):
        self.access_token: Optional[str] = None
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    def _check_auth(self) -> Optional[dict]:
        if not self.access_token:
            return {
                "error": "Email not connected.",
                "message": "Connect Gmail or Outlook through Settings → Integrations.",
                "action": "setup_integration",
            }
        return None

    async def list_inbox(
        self,
        filter_type: str = "all",
        limit: int = 20,
    ) -> dict:
        err = self._check_auth()
        if err:
            return err

        client = await self._get_client()
        query = ""
        if filter_type == "unread":
            query = "is:unread"
        elif filter_type == "important":
            query = "is:important"
        elif filter_type == "needs_reply":
            query = "is:unread -category:promotions -category:social"

        resp = await client.get(
            f"{self.GMAIL_BASE}/users/me/messages",
            headers={"Authorization": f"Bearer {self.access_token}"},
            params={"q": query, "maxResults": limit},
        )

        if resp.status_code != 200:
            return {"error": f"Gmail API error: {resp.status_code}"}

        data = resp.json()
        messages = []
        for msg_ref in data.get("messages", [])[:limit]:
            detail = await self._get_message(msg_ref["id"])
            if detail:
                messages.append(detail)

        return {"emails": messages, "total": len(messages), "filter": filter_type}

    async def _get_message(self, msg_id: str) -> Optional[dict]:
        client = await self._get_client()
        resp = await client.get(
            f"{self.GMAIL_BASE}/users/me/messages/{msg_id}",
            headers={"Authorization": f"Bearer {self.access_token}"},
            params={"format": "metadata", "metadataHeaders": ["Subject", "From", "Date"]},
        )
        if resp.status_code != 200:
            return None

        data = resp.json()
        headers = {h["name"]: h["value"] for h in data.get("payload", {}).get("headers", [])}
        return {
            "id": msg_id,
            "subject": headers.get("Subject", "(no subject)"),
            "from": headers.get("From", "unknown"),
            "date": headers.get("Date", ""),
            "snippet": data.get("snippet", ""),
            "labels": data.get("labelIds", []),
            "unread": "UNREAD" in data.get("labelIds", []),
        }

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        reply_to: Optional[str] = None,
    ) -> dict:
        err = self._check_auth()
        if err:
            return err

        import base64
        from email.mime.text import MIMEText

        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        if reply_to:
            message["In-Reply-To"] = reply_to

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        client = await self._get_client()
        resp = await client.post(
            f"{self.GMAIL_BASE}/users/me/messages/send",
            headers={"Authorization": f"Bearer {self.access_token}"},
            json={"raw": raw},
        )

        if resp.status_code in (200, 201):
            return {"success": True, "message_id": resp.json().get("id")}
        return {"error": f"Failed to send email: {resp.status_code}"}

    async def draft_email(
        self,
        to: str,
        subject: str,
        body: str,
    ) -> dict:
        err = self._check_auth()
        if err:
            return err

        import base64
        from email.mime.text import MIMEText

        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        client = await self._get_client()
        resp = await client.post(
            f"{self.GMAIL_BASE}/users/me/drafts",
            headers={"Authorization": f"Bearer {self.access_token}"},
            json={"message": {"raw": raw}},
        )

        if resp.status_code in (200, 201):
            return {"success": True, "draft_id": resp.json().get("id"), "message": "Draft saved"}
        return {"error": f"Failed to create draft: {resp.status_code}"}
