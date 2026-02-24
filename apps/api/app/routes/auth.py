"""
VOLO - Auth Routes
Registration, login, token refresh, /me, and OAuth flows for
Google, GitHub, Discord, and Twitter/X.
"""

import uuid
import secrets
import hashlib
import base64
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional
import httpx
from sqlalchemy import select

from app.auth import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
    generate_api_key, get_current_user, CurrentUser,
)
from app.database import async_session, User, Integration
from app.config import settings
from app.services.oauth import find_or_create_oauth_user, build_frontend_redirect

router = APIRouter()

# -- In-memory PKCE / state stores (transient) --
_oauth_states: dict[str, dict] = {}


def _store_state(provider: str, extra: dict | None = None) -> str:
    """Generate and store an OAuth state parameter."""
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = {
        "provider": provider,
        "created_at": datetime.utcnow().isoformat(),
        **(extra or {}),
    }
    if len(_oauth_states) > 200:
        oldest = sorted(_oauth_states, key=lambda k: _oauth_states[k]["created_at"])
        for k in oldest[: len(_oauth_states) - 200]:
            del _oauth_states[k]
    return state


def _pop_state(state: str, provider: str) -> dict:
    """Retrieve and consume an OAuth state. Raises 400 if invalid."""
    data = _oauth_states.pop(state, None)
    if not data or data.get("provider") != provider:
        raise HTTPException(400, "Invalid or expired OAuth state")
    return data


# -- Request / Response Models --

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


# ===== Email Auth =====

@router.post("/register")
async def register(req: RegisterRequest):
    """Register a new user with email + password."""
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.email == req.email)
        )
        if result.scalar_one_or_none():
            raise HTTPException(400, "Email already registered")

        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            tenant_id="volo-default",
            email=req.email,
            name=req.name,
            password_hash=hash_password(req.password),
            provider="email",
            role="owner",
        )
        session.add(user)
        await session.commit()

    access_token = create_access_token(user_id)
    refresh_token = create_refresh_token(user_id)

    return {
        "user": {"id": user_id, "email": req.email, "name": req.name},
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/login")
async def login(req: LoginRequest):
    """Login with email + password."""
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.email == req.email)
        )
        user = result.scalar_one_or_none()

    if not user or not user.password_hash or not verify_password(req.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")

    access_token = create_access_token(user.id, user.tenant_id, user.role)
    refresh_token = create_refresh_token(user.id)

    return {
        "user": {"id": user.id, "email": user.email, "name": user.name},
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/refresh")
async def refresh(req: RefreshRequest):
    """Refresh access token using a refresh token."""
    payload = decode_token(req.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(400, "Invalid refresh token")

    user_id = payload["sub"]
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(404, "User not found")

    access_token = create_access_token(user_id, user.tenant_id, user.role)
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me")
async def me(current_user: CurrentUser = Depends(get_current_user)):
    """Get the currently authenticated user profile from the database."""
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == current_user.user_id))
        user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(404, "User not found")

    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "avatar": user.avatar_url,
        "role": user.role,
        "provider": user.provider,
        "tenant_id": user.tenant_id,
        "onboarding_completed": user.onboarding_completed,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@router.post("/api-keys")
async def create_api_key_route(request: Request):
    """Create a new API key for programmatic access."""
    raw_key, key_hash, prefix = generate_api_key()
    return {
        "key": raw_key,
        "prefix": prefix,
        "message": "Store this key securely - it will not be shown again.",
    }


# ===== Google OAuth 2.0 =====

@router.get("/google")
async def google_oauth_start():
    """Redirect to Google OAuth consent screen for login."""
    if not settings.google_client_id:
        raise HTTPException(501, "Google OAuth not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.")

    state = _store_state("google")
    redirect_uri = settings.google_redirect_uri or f"{settings.frontend_url}/api/auth/google/callback"
    scopes = "openid email profile"
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={settings.google_client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope={scopes}"
        f"&state={state}"
        f"&access_type=offline"
        f"&prompt=consent"
    )
    return {"url": auth_url}


@router.get("/google/callback")
async def google_oauth_callback(code: str = "", state: str = ""):
    """Handle Google OAuth callback."""
    if not code or not state:
        raise HTTPException(400, "Missing code or state")

    _pop_state(state, "google")
    redirect_uri = settings.google_redirect_uri or f"{settings.frontend_url}/api/auth/google/callback"

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            },
        )
        if token_resp.status_code != 200:
            raise HTTPException(400, f"Google token exchange failed: {token_resp.text}")
        tokens = token_resp.json()

        profile_resp = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        if profile_resp.status_code != 200:
            raise HTTPException(400, "Failed to fetch Google profile")
        profile = profile_resp.json()

    user_data = await find_or_create_oauth_user(
        provider="google",
        provider_id=profile.get("id", ""),
        email=profile.get("email", ""),
        name=profile.get("name", "Google User"),
        avatar_url=profile.get("picture"),
        access_token=tokens.get("access_token"),
        refresh_token=tokens.get("refresh_token"),
    )

    return RedirectResponse(url=build_frontend_redirect(user_data), status_code=302)


# ===== GitHub OAuth 2.0 =====

@router.get("/github")
async def github_oauth_start():
    """Redirect to GitHub OAuth consent screen."""
    if not settings.github_client_id:
        raise HTTPException(501, "GitHub OAuth not configured. Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET.")

    state = _store_state("github")
    redirect_uri = settings.github_redirect_uri or f"{settings.frontend_url}/api/auth/github/callback"
    auth_url = (
        f"https://github.com/login/oauth/authorize?"
        f"client_id={settings.github_client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&scope=read:user user:email"
        f"&state={state}"
    )
    return {"url": auth_url}


@router.get("/github/callback")
async def github_oauth_callback(code: str = "", state: str = ""):
    """Handle GitHub OAuth callback."""
    if not code or not state:
        raise HTTPException(400, "Missing code or state")

    _pop_state(state, "github")
    redirect_uri = settings.github_redirect_uri or f"{settings.frontend_url}/api/auth/github/callback"

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
            },
            headers={"Accept": "application/json"},
        )
        if token_resp.status_code != 200:
            raise HTTPException(400, f"GitHub token exchange failed: {token_resp.text}")
        tokens = token_resp.json()

        gh_access_token = tokens.get("access_token")
        if not gh_access_token:
            raise HTTPException(400, f"GitHub did not return access_token: {tokens}")

        profile_resp = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {gh_access_token}",
                "Accept": "application/json",
            },
        )
        profile = profile_resp.json()

        email = profile.get("email") or ""
        if not email:
            email_resp = await client.get(
                "https://api.github.com/user/emails",
                headers={
                    "Authorization": f"Bearer {gh_access_token}",
                    "Accept": "application/json",
                },
            )
            emails = email_resp.json()
            if isinstance(emails, list):
                primary = next((e for e in emails if e.get("primary")), None)
                email = (primary or emails[0]).get("email", "") if emails else ""

    user_data = await find_or_create_oauth_user(
        provider="github",
        provider_id=str(profile.get("id", "")),
        email=email or f"{profile.get('login', 'user')}@github.com",
        name=profile.get("name") or profile.get("login", "GitHub User"),
        avatar_url=profile.get("avatar_url"),
        access_token=gh_access_token,
    )

    return RedirectResponse(url=build_frontend_redirect(user_data), status_code=302)


# ===== Discord OAuth 2.0 =====

@router.get("/discord")
async def discord_oauth_start():
    """Redirect to Discord OAuth consent screen."""
    if not settings.discord_client_id:
        raise HTTPException(501, "Discord OAuth not configured. Set DISCORD_CLIENT_ID and DISCORD_CLIENT_SECRET.")

    state = _store_state("discord")
    redirect_uri = settings.discord_redirect_uri or f"{settings.frontend_url}/api/auth/discord/callback"
    auth_url = (
        f"https://discord.com/api/oauth2/authorize?"
        f"client_id={settings.discord_client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope=identify email"
        f"&state={state}"
    )
    return {"url": auth_url}


@router.get("/discord/callback")
async def discord_oauth_callback(code: str = "", state: str = ""):
    """Handle Discord OAuth callback."""
    if not code or not state:
        raise HTTPException(400, "Missing code or state")

    _pop_state(state, "discord")
    redirect_uri = settings.discord_redirect_uri or f"{settings.frontend_url}/api/auth/discord/callback"

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://discord.com/api/oauth2/token",
            data={
                "client_id": settings.discord_client_id,
                "client_secret": settings.discord_client_secret,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if token_resp.status_code != 200:
            raise HTTPException(400, f"Discord token exchange failed: {token_resp.text}")
        tokens = token_resp.json()

        profile_resp = await client.get(
            "https://discord.com/api/v10/users/@me",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        profile = profile_resp.json()

    discord_id = profile.get("id", "")
    username = profile.get("username", "")
    avatar_hash = profile.get("avatar", "")
    avatar_url = f"https://cdn.discordapp.com/avatars/{discord_id}/{avatar_hash}.png" if avatar_hash else ""

    user_data = await find_or_create_oauth_user(
        provider="discord",
        provider_id=discord_id,
        email=profile.get("email") or f"{username}@discord.com",
        name=profile.get("global_name") or username or "Discord User",
        avatar_url=avatar_url,
        access_token=tokens.get("access_token"),
        refresh_token=tokens.get("refresh_token"),
    )

    return RedirectResponse(url=build_frontend_redirect(user_data), status_code=302)


# ===== X / Twitter OAuth 2.0 with PKCE =====

@router.get("/twitter")
async def twitter_oauth_start():
    """Redirect to X / Twitter OAuth 2.0 consent screen with PKCE."""
    if not settings.twitter_client_id:
        raise HTTPException(501, "Twitter OAuth not configured. Set TWITTER_CLIENT_ID and TWITTER_CLIENT_SECRET.")

    code_verifier = secrets.token_urlsafe(64)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).rstrip(b"=").decode()

    redirect_uri = settings.twitter_redirect_uri or f"{settings.frontend_url}/api/auth/twitter/callback"
    state = _store_state("twitter", {"code_verifier": code_verifier})

    scopes = "tweet.read users.read offline.access"
    auth_url = (
        f"https://twitter.com/i/oauth2/authorize"
        f"?response_type=code"
        f"&client_id={settings.twitter_client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&scope={scopes}"
        f"&state={state}"
        f"&code_challenge={code_challenge}"
        f"&code_challenge_method=S256"
    )
    return {"url": auth_url, "state": state}


@router.get("/twitter/callback")
async def twitter_oauth_callback(code: str = "", state: str = ""):
    """Handle Twitter/X OAuth 2.0 callback."""
    if not code or not state:
        raise HTTPException(400, "Missing code or state parameter")

    state_data = _pop_state(state, "twitter")
    code_verifier = state_data["code_verifier"]
    redirect_uri = settings.twitter_redirect_uri or f"{settings.frontend_url}/api/auth/twitter/callback"

    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://api.twitter.com/2/oauth2/token",
            data={
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
                "code_verifier": code_verifier,
            },
            auth=(settings.twitter_client_id, settings.twitter_client_secret) if settings.twitter_client_secret else None,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if token_response.status_code != 200:
            raise HTTPException(400, f"Twitter token exchange failed: {token_response.text}")

        tokens = token_response.json()

        user_response = await client.get(
            "https://api.twitter.com/2/users/me",
            params={"user.fields": "id,name,username,profile_image_url"},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

        if user_response.status_code != 200:
            raise HTTPException(400, "Failed to fetch Twitter user profile")

        twitter_user = user_response.json().get("data", {})

    user_data = await find_or_create_oauth_user(
        provider="twitter",
        provider_id=twitter_user.get("id", ""),
        email=f"{twitter_user.get('username', 'user')}@x.com",
        name=twitter_user.get("name", twitter_user.get("username", "Twitter User")),
        avatar_url=twitter_user.get("profile_image_url"),
        access_token=tokens.get("access_token"),
        refresh_token=tokens.get("refresh_token"),
    )

    return RedirectResponse(url=build_frontend_redirect(user_data), status_code=302)


# ===== Apple Sign-In (placeholder) =====

@router.get("/apple")
async def apple_oauth_start():
    """Apple Sign-In requires an Apple Developer account with Sign In with Apple configured."""
    raise HTTPException(501, "Apple Sign-In not yet configured. Requires Apple Developer Program enrollment.")


# ===== Provider availability check =====

@router.get("/providers")
async def list_providers():
    """Return which OAuth providers are configured and available."""
    return {
        "providers": {
            "email": True,
            "google": bool(settings.google_client_id),
            "github": bool(settings.github_client_id),
            "twitter": bool(settings.twitter_client_id),
            "discord": bool(settings.discord_client_id),
            "apple": False,
            "facebook": False,
            "linkedin": False,
            "tiktok": False,
            "snapchat": False,
            "instagram": False,
        }
    }
