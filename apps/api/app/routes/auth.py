"""
VOLO — Auth Routes
Registration, login, token refresh, OAuth callbacks.
All user data persisted to PostgreSQL.
"""

import os
import uuid
import secrets
import hashlib
import base64
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional
import httpx
from sqlalchemy import select

from app.auth import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
    generate_api_key,
)
from app.database import async_session, User, Integration

router = APIRouter()

# Twitter PKCE state (transient — intentionally in-memory)
_twitter_pkce: dict[str, dict] = {}


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/register")
async def register(req: RegisterRequest):
    """Register a new user."""
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
    """Login with email and password."""
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
    """Refresh access token."""
    payload = decode_token(req.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(400, "Invalid refresh token")

    user_id = payload["sub"]
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(404, "User not found")

    access_token = create_access_token(user_id, user.tenant_id, user.role)
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me")
async def me(request: Request):
    """Get current user profile."""
    return {
        "id": "dev-user",
        "email": "dev@volo.ai",
        "name": "Developer",
        "role": "owner",
        "tenant_id": "volo-default",
    }


@router.post("/api-keys")
async def create_api_key_route(request: Request):
    """Create a new API key for programmatic access."""
    raw_key, key_hash, prefix = generate_api_key()
    return {
        "key": raw_key,
        "prefix": prefix,
        "message": "Store this key securely — it won't be shown again.",
    }


# ── OAuth Placeholders ──────────────────────

@router.get("/google")
async def google_oauth_start():
    return {"message": "Google OAuth not configured. Add GOOGLE_CLIENT_ID to .env."}


@router.get("/google/callback")
async def google_oauth_callback(code: str = "", state: str = ""):
    return {"message": "Google OAuth callback received", "code": code[:10] + "..."}


@router.get("/github-oauth")
async def github_oauth_start():
    return {"message": "GitHub OAuth not configured. Add GITHUB_CLIENT_ID to .env."}


# ── X / Twitter OAuth 2.0 with PKCE ─────────────────────────

TWITTER_CLIENT_ID = os.getenv("TWITTER_CLIENT_ID", "")
TWITTER_CLIENT_SECRET = os.getenv("TWITTER_CLIENT_SECRET", "")
TWITTER_REDIRECT_URI = os.getenv(
    "TWITTER_REDIRECT_URI",
    os.getenv("FRONTEND_URL", "http://localhost:3000") + "/auth/twitter/callback"
)


@router.get("/twitter")
async def twitter_oauth_start():
    """Redirect to X / Twitter OAuth 2.0 consent screen with PKCE."""
    if not TWITTER_CLIENT_ID:
        return {"message": "Twitter OAuth not configured. Add TWITTER_CLIENT_ID to .env."}

    code_verifier = secrets.token_urlsafe(64)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).rstrip(b"=").decode()

    state = secrets.token_urlsafe(32)
    _twitter_pkce[state] = {
        "code_verifier": code_verifier,
        "created_at": datetime.utcnow().isoformat(),
    }

    if len(_twitter_pkce) > 100:
        oldest_keys = sorted(_twitter_pkce.keys(), key=lambda k: _twitter_pkce[k]["created_at"])
        for k in oldest_keys[:len(_twitter_pkce) - 100]:
            del _twitter_pkce[k]

    scopes = "tweet.read users.read offline.access"
    auth_url = (
        f"https://twitter.com/i/oauth2/authorize"
        f"?response_type=code"
        f"&client_id={TWITTER_CLIENT_ID}"
        f"&redirect_uri={TWITTER_REDIRECT_URI}"
        f"&scope={scopes}"
        f"&state={state}"
        f"&code_challenge={code_challenge}"
        f"&code_challenge_method=S256"
    )

    return {"url": auth_url, "state": state}


@router.get("/twitter/callback")
async def twitter_oauth_callback(code: str = "", state: str = ""):
    """Handle Twitter/X OAuth 2.0 callback — exchange code for tokens."""
    if not code or not state:
        raise HTTPException(400, "Missing code or state parameter")

    pkce_data = _twitter_pkce.pop(state, None)
    if not pkce_data:
        raise HTTPException(400, "Invalid or expired state parameter")

    code_verifier = pkce_data["code_verifier"]

    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://api.twitter.com/2/oauth2/token",
            data={
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": TWITTER_REDIRECT_URI,
                "code_verifier": code_verifier,
            },
            auth=(TWITTER_CLIENT_ID, TWITTER_CLIENT_SECRET) if TWITTER_CLIENT_SECRET else None,
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

    twitter_id = twitter_user.get("id", "")
    twitter_username = twitter_user.get("username", "")
    user_id = f"twitter-{twitter_id}"

    # Persist user + Twitter tokens to PostgreSQL
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        existing_user = result.scalar_one_or_none()

        if not existing_user:
            session.add(User(
                id=user_id,
                tenant_id="volo-default",
                email=f"{twitter_username}@x.com",
                name=twitter_user.get("name", twitter_username),
                avatar_url=twitter_user.get("profile_image_url", ""),
                role="owner",
                preferences={
                    "provider": "twitter",
                    "twitter_id": twitter_id,
                    "twitter_username": twitter_username,
                },
            ))
            await session.flush()

        # Upsert Twitter integration tokens
        int_result = await session.execute(
            select(Integration).where(
                Integration.user_id == user_id,
                Integration.type == "twitter",
            )
        )
        existing_int = int_result.scalar_one_or_none()

        if existing_int:
            existing_int.config = {
                "access_token": tokens.get("access_token"),
                "refresh_token": tokens.get("refresh_token"),
            }
            existing_int.status = "connected"
        else:
            session.add(Integration(
                user_id=user_id,
                type="twitter",
                category="social",
                name="Twitter/X",
                status="connected",
                config={
                    "access_token": tokens.get("access_token"),
                    "refresh_token": tokens.get("refresh_token"),
                },
            ))

        await session.commit()

    access_token = create_access_token(user_id)
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

    return RedirectResponse(
        url=f"{frontend_url}/?auth_token={access_token}&provider=twitter"
        f"&user_id={user_id}&name={twitter_user.get('name', '')}"
        f"&username={twitter_username}"
        f"&avatar={twitter_user.get('profile_image_url', '')}",
        status_code=302,
    )
