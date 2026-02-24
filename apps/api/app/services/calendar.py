"""
VOLO — Calendar Service
Google Calendar integration for scheduling and event management.
"""

import os
import logging
from typing import Optional
from datetime import datetime, timedelta
import httpx

logger = logging.getLogger("volo.calendar")


class CalendarService:
    """Handles calendar operations via Google Calendar API."""

    GCAL_BASE = "https://www.googleapis.com/calendar/v3"

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
                "error": "Calendar not connected.",
                "message": "Connect Google Calendar through Settings → Integrations.",
            }
        return None

    async def list_events(
        self,
        days_ahead: int = 7,
        calendar_id: str = "primary",
    ) -> dict:
        err = self._check_auth()
        if err:
            return err

        now = datetime.utcnow()
        time_max = now + timedelta(days=days_ahead)

        client = await self._get_client()
        resp = await client.get(
            f"{self.GCAL_BASE}/calendars/{calendar_id}/events",
            headers={"Authorization": f"Bearer {self.access_token}"},
            params={
                "timeMin": now.isoformat() + "Z",
                "timeMax": time_max.isoformat() + "Z",
                "singleEvents": True,
                "orderBy": "startTime",
                "maxResults": 50,
            },
        )

        if resp.status_code != 200:
            return {"error": f"Calendar API error: {resp.status_code}"}

        data = resp.json()
        events = []
        for event in data.get("items", []):
            start = event.get("start", {})
            end = event.get("end", {})
            events.append({
                "id": event["id"],
                "title": event.get("summary", "(no title)"),
                "description": event.get("description", ""),
                "start": start.get("dateTime", start.get("date", "")),
                "end": end.get("dateTime", end.get("date", "")),
                "location": event.get("location", ""),
                "attendees": [
                    {"email": a["email"], "status": a.get("responseStatus", "needsAction")}
                    for a in event.get("attendees", [])
                ],
                "meeting_url": event.get("hangoutLink", ""),
                "status": event.get("status", "confirmed"),
            })

        return {"events": events, "total": len(events), "days_ahead": days_ahead}

    async def create_event(
        self,
        title: str,
        start_time: str,
        duration_minutes: int = 60,
        description: str = "",
        attendees: list[str] = None,
        calendar_id: str = "primary",
    ) -> dict:
        err = self._check_auth()
        if err:
            return err

        start_dt = datetime.fromisoformat(start_time.replace("Z", ""))
        end_dt = start_dt + timedelta(minutes=duration_minutes)

        event_body = {
            "summary": title,
            "description": description,
            "start": {"dateTime": start_dt.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": "UTC"},
        }
        if attendees:
            event_body["attendees"] = [{"email": e} for e in attendees]

        client = await self._get_client()
        resp = await client.post(
            f"{self.GCAL_BASE}/calendars/{calendar_id}/events",
            headers={"Authorization": f"Bearer {self.access_token}"},
            json=event_body,
        )

        if resp.status_code in (200, 201):
            data = resp.json()
            return {
                "success": True,
                "event_id": data["id"],
                "html_link": data.get("htmlLink", ""),
                "title": title,
                "start": start_time,
                "duration_minutes": duration_minutes,
            }
        return {"error": f"Failed to create event: {resp.status_code}"}

    async def find_free_slots(
        self,
        days_ahead: int = 3,
        duration_minutes: int = 30,
    ) -> dict:
        """Find available time slots in the calendar."""
        events_result = await self.list_events(days_ahead=days_ahead)
        if "error" in events_result:
            return events_result

        # Simple slot finder — checks 9am-6pm windows
        busy_times = []
        for event in events_result.get("events", []):
            try:
                start = datetime.fromisoformat(event["start"].replace("Z", "+00:00"))
                end = datetime.fromisoformat(event["end"].replace("Z", "+00:00"))
                busy_times.append((start, end))
            except (ValueError, KeyError):
                continue

        free_slots = []
        now = datetime.utcnow()
        for day_offset in range(days_ahead):
            day = now + timedelta(days=day_offset)
            work_start = day.replace(hour=9, minute=0, second=0, microsecond=0)
            work_end = day.replace(hour=18, minute=0, second=0, microsecond=0)

            if work_start < now:
                work_start = now

            current = work_start
            while current + timedelta(minutes=duration_minutes) <= work_end:
                slot_end = current + timedelta(minutes=duration_minutes)
                is_free = all(
                    slot_end <= busy_start or current >= busy_end
                    for busy_start, busy_end in busy_times
                )
                if is_free:
                    free_slots.append({
                        "start": current.isoformat(),
                        "end": slot_end.isoformat(),
                    })
                current += timedelta(minutes=30)

        return {"free_slots": free_slots[:10], "total": len(free_slots)}
