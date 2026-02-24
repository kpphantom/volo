"""
VOLO — Shared OAuth Utilities
Find-or-create user from OAuth profile, issue JWT, redirect to frontend.
"""

import uuid
from datetime import datetime
from urllib.parse import urlencode, quote

from sqlalchemy import select, or_

from app.auth import create_access_token, create_refresh_token
from app.database import async_session, User, Integration
from app.config import settings


async def find_or_create_oauth_user(
    *,
    provider: str,
    provider_id: str,
    email: str,
    name: str,
    avatar_url: str | None = None,
    access_token: str | None = None,
    refresh_token: str | None = None,
) -> dict:
    """
    Find an existing user by provider+provider_id or email.
    If not found, create a new user.
    Returns dict with user info + JWT tokens.
    """
    async with async_session() as session:
        # 1. Try to find by provider + provider_id
        result = await session.execute(
            select(User).where(
                User.provider == provider,
                User.provider_id == provider_id,
            )
        )
        user = result.scalar_one_or_none()

        # 2. If not found, try by email (link accounts)
        if not user and email:
            result = await session.execute(
                select(User).where(User.email == email)
            )
            user = result.scalar_one_or_none()
            # Update existing user with OAuth provider info
            if user:
                user.provider = user.provider or provider
                user.provider_id = user.provider_id or provider_id
                if avatar_url and not user.avatar_url:
                    user.avatar_url = avatar_url

        # 3. Create new user
        if not user:
            user_id = str(uuid.uuid4())
            user = User(
                id=user_id,
                tenant_id="volo-default",
                email=email,
                name=name,
                avatar_url=avatar_url,
                provider=provider,
                provider_id=provider_id,
                role="owner",
            )
            session.add(user)
            await session.flush()

        # 4. Update last_active_at
        user.last_active_at = datetime.utcnow()

        # 5. Upsert integration if we have OAuth tokens
        if access_token:
            int_result = await session.execute(
                select(Integration).where(
                    Integration.user_id == user.id,
                    Integration.type == provider,
                )
            )
            existing_int = int_result.scalar_one_or_none()

            if existing_int:
                existing_int.config = {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                }
                existing_int.status = "connected"
            else:
                session.add(Integration(
                    user_id=user.id,
                    type=provider,
                    category="social" if provider in ("twitter", "discord", "facebook") else "auth",
                    name=provider.title(),
                    status="connected",
                    config={
                        "access_token": access_token,
                        "refresh_token": refresh_token,
                    },
                ))

        await session.commit()

        # Build response
        jwt_access = create_access_token(user.id, user.tenant_id or "volo-default", user.role or "owner")
        jwt_refresh = create_refresh_token(user.id)

        return {
            "user_id": user.id,
            "email": user.email,
            "name": user.name,
            "avatar": user.avatar_url or "",
            "provider": provider,
            "access_token": jwt_access,
            "refresh_token": jwt_refresh,
        }


def build_frontend_redirect(user_data: dict) -> str:
    """Build the frontend redirect URL with auth params."""
    frontend_url = settings.frontend_url.rstrip("/")
    params = {
        "auth_token": user_data["access_token"],
        "provider": user_data["provider"],
        "user_id": user_data["user_id"],
        "name": user_data["name"],
        "avatar": user_data.get("avatar", ""),
    }
    return f"{frontend_url}/?{urlencode(params, quote_via=quote)}"
