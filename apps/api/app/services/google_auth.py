"""
VOLO — Google OAuth & Services Discovery
Handles Google sign-in, token exchange, and auto-discovery of user's Google services.
"""

import os
import httpx
from typing import Optional
from datetime import datetime, timezone


GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:3000/auth/google/callback")

# All Google scopes we request
GOOGLE_SCOPES = [
    "openid",
    "email",
    "profile",
    # Gmail
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    # Calendar
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
    # Drive
    "https://www.googleapis.com/auth/drive.readonly",
    # YouTube
    "https://www.googleapis.com/auth/youtube.readonly",
    # Contacts
    "https://www.googleapis.com/auth/contacts.readonly",
    # Fitness
    "https://www.googleapis.com/auth/fitness.activity.read",
    "https://www.googleapis.com/auth/fitness.heart_rate.read",
    "https://www.googleapis.com/auth/fitness.sleep.read",
    "https://www.googleapis.com/auth/fitness.body.read",
    # Photos
    "https://www.googleapis.com/auth/photoslibrary.readonly",
    # Tasks
    "https://www.googleapis.com/auth/tasks.readonly",
    # Keep (Notes)
    "https://www.googleapis.com/auth/keep.readonly",
]

# In-memory token store (swap for DB in production)
_user_tokens: dict[str, dict] = {}


class GoogleAuthService:
    """Handles Google OAuth2 flow and service discovery."""

    def get_auth_url(self, state: str = "volo") -> str:
        """Generate Google OAuth consent URL."""
        scopes = " ".join(GOOGLE_SCOPES)
        return (
            "https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={GOOGLE_CLIENT_ID}"
            f"&redirect_uri={GOOGLE_REDIRECT_URI}"
            f"&response_type=code"
            f"&scope={scopes}"
            f"&state={state}"
            f"&access_type=offline"
            f"&prompt=consent"
        )

    async def exchange_code(self, code: str) -> dict:
        """Exchange authorization code for tokens."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": GOOGLE_REDIRECT_URI,
                },
            )
            tokens = resp.json()

        # Get user profile
        profile = await self._get_profile(tokens.get("access_token", ""))

        user_id = profile.get("sub", profile.get("id", "unknown"))
        _user_tokens[user_id] = {
            **tokens,
            "profile": profile,
            "connected_at": datetime.now(timezone.utc).isoformat(),
        }

        return {
            "user_id": user_id,
            "profile": profile,
            "services": await self.discover_services(tokens.get("access_token", "")),
        }

    async def _get_profile(self, access_token: str) -> dict:
        """Get Google user profile."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if resp.status_code == 200:
                return resp.json()
        return {}

    async def discover_services(self, access_token: str) -> list[dict]:
        """Auto-discover which Google services the user has data in."""
        services = []
        headers = {"Authorization": f"Bearer {access_token}"}

        checks = [
            ("gmail", "Gmail", "https://gmail.googleapis.com/gmail/v1/users/me/profile", "mail"),
            ("calendar", "Google Calendar", "https://www.googleapis.com/calendar/v3/calendars/primary", "calendar"),
            ("drive", "Google Drive", "https://www.googleapis.com/drive/v3/about?fields=user", "cloud"),
            ("youtube", "YouTube", "https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true", "video"),
            ("contacts", "Google Contacts", "https://people.googleapis.com/v1/people/me?personFields=names", "contacts"),
            ("tasks", "Google Tasks", "https://tasks.googleapis.com/tasks/v1/users/@me/lists", "tasks"),
            ("photos", "Google Photos", "https://photoslibrary.googleapis.com/v1/albums?pageSize=1", "image"),
            ("fitness", "Google Fit", "https://www.googleapis.com/fitness/v1/users/me/dataSources", "fitness"),
        ]

        async with httpx.AsyncClient(timeout=5.0) as client:
            for svc_id, name, url, icon in checks:
                try:
                    resp = await client.get(url, headers=headers)
                    services.append({
                        "id": svc_id,
                        "name": name,
                        "icon": icon,
                        "connected": resp.status_code == 200,
                        "status": "active" if resp.status_code == 200 else "needs_permission",
                    })
                except Exception:
                    services.append({
                        "id": svc_id,
                        "name": name,
                        "icon": icon,
                        "connected": False,
                        "status": "error",
                    })

        return services

    async def refresh_token(self, user_id: str) -> Optional[str]:
        """Refresh an expired access token."""
        token_data = _user_tokens.get(user_id)
        if not token_data or "refresh_token" not in token_data:
            return None

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "refresh_token": token_data["refresh_token"],
                    "grant_type": "refresh_token",
                },
            )
            new_tokens = resp.json()

        if "access_token" in new_tokens:
            _user_tokens[user_id].update(new_tokens)
            return new_tokens["access_token"]
        return None

    def get_access_token(self, user_id: str) -> Optional[str]:
        """Get stored access token for a user."""
        token_data = _user_tokens.get(user_id)
        return token_data.get("access_token") if token_data else None

    def get_user_profile(self, user_id: str) -> Optional[dict]:
        """Get stored user profile."""
        token_data = _user_tokens.get(user_id)
        return token_data.get("profile") if token_data else None
