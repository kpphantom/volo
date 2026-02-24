"""
VOLO — Google OAuth & Services Discovery
DB-backed token storage with in-memory cache for fast sync access.
"""

import os
import httpx
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import select

from app.database import async_session, Integration, User

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:3000/auth/google/callback")

GOOGLE_SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/contacts.readonly",
    "https://www.googleapis.com/auth/fitness.activity.read",
    "https://www.googleapis.com/auth/fitness.heart_rate.read",
    "https://www.googleapis.com/auth/fitness.sleep.read",
    "https://www.googleapis.com/auth/fitness.body.read",
    "https://www.googleapis.com/auth/photoslibrary.readonly",
    "https://www.googleapis.com/auth/tasks.readonly",
    "https://www.googleapis.com/auth/keep.readonly",
]


class GoogleAuthService:
    """Handles Google OAuth2 flow with DB-backed persistent token storage."""

    def __init__(self):
        # In-memory cache backed by DB — fast sync access, persistent storage
        self._cache: dict[str, dict] = {}

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

    async def exchange_code(self, code: str, user_id: str = "dev-user") -> dict:
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

        profile = await self._get_profile(tokens.get("access_token", ""))
        google_sub = profile.get("sub", profile.get("id", user_id))

        # Ensure user exists for FK constraint
        async with async_session() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            if not result.scalar_one_or_none():
                session.add(User(
                    id=user_id,
                    tenant_id="volo-default",
                    email=profile.get("email", f"{google_sub}@google.com"),
                    name=profile.get("name", "Google User"),
                    avatar_url=profile.get("picture"),
                    role="owner",
                ))
                await session.commit()

        await self._save_tokens(user_id, tokens, profile)

        return {
            "user_id": user_id,
            "profile": profile,
            "services": await self.discover_services(tokens.get("access_token", "")),
        }

    async def _get_profile(self, access_token: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if resp.status_code == 200:
                return resp.json()
        return {}

    async def _save_tokens(self, user_id: str, tokens: dict, profile: dict):
        """Persist Google tokens to DB and update cache."""
        config = {
            "access_token": tokens.get("access_token"),
            "refresh_token": tokens.get("refresh_token"),
            "token_type": tokens.get("token_type"),
            "expires_in": tokens.get("expires_in"),
            "profile": profile,
            "connected_at": datetime.now(timezone.utc).isoformat(),
        }

        async with async_session() as session:
            result = await session.execute(
                select(Integration).where(
                    Integration.user_id == user_id,
                    Integration.type == "google",
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                if not config.get("refresh_token") and existing.config:
                    config["refresh_token"] = existing.config.get("refresh_token")
                existing.config = config
                existing.status = "connected"
                existing.last_sync_at = datetime.utcnow()
            else:
                session.add(Integration(
                    user_id=user_id,
                    type="google",
                    category="auth",
                    name="Google",
                    status="connected",
                    config=config,
                ))
            await session.commit()

        self._cache[user_id] = config

    async def _load_tokens(self, user_id: str) -> Optional[dict]:
        """Load from cache, falling back to DB."""
        if user_id in self._cache:
            return self._cache[user_id]

        async with async_session() as session:
            result = await session.execute(
                select(Integration).where(
                    Integration.user_id == user_id,
                    Integration.type == "google",
                )
            )
            integration = result.scalar_one_or_none()
            if integration and integration.config:
                self._cache[user_id] = integration.config
                return integration.config
        return None

    async def discover_services(self, access_token: str) -> list[dict]:
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
                        "id": svc_id, "name": name, "icon": icon,
                        "connected": resp.status_code == 200,
                        "status": "active" if resp.status_code == 200 else "needs_permission",
                    })
                except Exception:
                    services.append({
                        "id": svc_id, "name": name, "icon": icon,
                        "connected": False, "status": "error",
                    })

        return services

    async def refresh_token(self, user_id: str) -> Optional[str]:
        """Refresh an expired access token."""
        token_data = await self._load_tokens(user_id)
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
            profile = token_data.get("profile", {})
            await self._save_tokens(user_id, {**token_data, **new_tokens}, profile)
            return new_tokens["access_token"]
        return None

    def get_access_token(self, user_id: str) -> Optional[str]:
        """Sync access to cached token (called from sync contexts like youtube.py)."""
        cached = self._cache.get(user_id)
        return cached.get("access_token") if cached else None

    def get_user_profile(self, user_id: str) -> Optional[dict]:
        """Sync access to cached profile."""
        cached = self._cache.get(user_id)
        return cached.get("profile") if cached else None

    async def load_from_db(self):
        """Load all Google integrations into cache on startup."""
        try:
            async with async_session() as session:
                result = await session.execute(
                    select(Integration).where(Integration.type == "google")
                )
                for integration in result.scalars().all():
                    if integration.config:
                        self._cache[integration.user_id] = integration.config
            print(f"  Google tokens loaded: {len(self._cache)} users")
        except Exception as e:
            print(f"  Google token load skipped: {e}")


# Module-level singleton — import this, not GoogleAuthService()
google_auth = GoogleAuthService()
