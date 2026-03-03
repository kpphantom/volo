"""
VOLO — Social Platform OAuth Service
Handles OAuth flows for Twitter/X, Instagram, TikTok, and Facebook.
Stores tokens in the Integration table per user.
"""

import logging
from datetime import datetime

import httpx
from sqlalchemy import select, and_

from app.config import settings
from app.database import async_session, Integration
from app.services.cache import cache
from app.services.oauth import store_oauth_state, pop_oauth_state

logger = logging.getLogger("volo.social_oauth")

# Thin aliases used by social_connect routes (keep "social_state:" prefix for isolation)
async def _store_state(provider: str, extra: dict | None = None) -> str:
    return await store_oauth_state(provider, extra, key_prefix="social_state")

async def _pop_state(state: str, provider: str) -> dict:
    return await pop_oauth_state(state, provider, key_prefix="social_state")


class SocialOAuthService:
    """Manages OAuth for social platforms and persists tokens."""

    # ── Token Storage ────────────────────────────────────────────────

    async def store_tokens(self, user_id: str, platform: str, token_data: dict, profile: dict = None):
        """Save platform tokens + profile to Integration table."""
        async with async_session() as session:
            result = await session.execute(
                select(Integration).where(
                    and_(Integration.user_id == user_id, Integration.type == platform)
                )
            )
            integration = result.scalar_one_or_none()

            config = {
                "access_token": token_data.get("access_token", ""),
                "refresh_token": token_data.get("refresh_token", ""),
                "expires_in": token_data.get("expires_in"),
                "token_type": token_data.get("token_type", "Bearer"),
                "scope": token_data.get("scope", ""),
                "connected_at": datetime.utcnow().isoformat(),
                "profile": profile or {},
            }

            if integration:
                integration.config = config
                integration.status = "connected"
                integration.last_sync_at = datetime.utcnow()
            else:
                integration = Integration(
                    user_id=user_id,
                    type=platform,
                    category="social",
                    name=platform.title(),
                    status="connected",
                    config=config,
                )
                session.add(integration)
            await session.commit()
        # Cache access token
        await cache.set(f"social_token:{user_id}:{platform}", config["access_token"], ttl=3600)

    async def get_access_token(self, user_id: str, platform: str) -> str | None:
        """Retrieve cached or stored access token."""
        cached = await cache.get(f"social_token:{user_id}:{platform}")
        if cached:
            return cached
        async with async_session() as session:
            result = await session.execute(
                select(Integration).where(
                    and_(Integration.user_id == user_id, Integration.type == platform)
                )
            )
            integration = result.scalar_one_or_none()
            if integration and integration.status == "connected":
                token = integration.config.get("access_token", "")
                if token:
                    await cache.set(f"social_token:{user_id}:{platform}", token, ttl=3600)
                return token
        return None

    async def get_connection_status(self, user_id: str) -> dict:
        """Get connection status for all social platforms."""
        platforms = ["twitter", "instagram", "tiktok", "facebook", "reddit", "linkedin"]
        status = {}
        async with async_session() as session:
            for p in platforms:
                result = await session.execute(
                    select(Integration).where(
                        and_(Integration.user_id == user_id, Integration.type == p)
                    )
                )
                integration = result.scalar_one_or_none()
                profile = {}
                if integration and integration.config:
                    profile = integration.config.get("profile", {})
                status[p] = {
                    "connected": bool(integration and integration.status == "connected"),
                    "username": profile.get("username", ""),
                    "name": profile.get("name", ""),
                    "avatar": profile.get("avatar", ""),
                }
        return status

    async def disconnect(self, user_id: str, platform: str) -> bool:
        """Disconnect a social platform."""
        async with async_session() as session:
            result = await session.execute(
                select(Integration).where(
                    and_(Integration.user_id == user_id, Integration.type == platform)
                )
            )
            integration = result.scalar_one_or_none()
            if integration:
                integration.status = "disconnected"
                integration.config = {}
                await session.commit()
                await cache.delete(f"social_token:{user_id}:{platform}")
                return True
        return False

    # ── Twitter / X ──────────────────────────────────────────────────

    def twitter_auth_url(self, state: str, code_challenge: str) -> str:
        redirect_uri = settings.twitter_redirect_uri or f"{settings.frontend_url}/api/social/connect/twitter/callback"
        scopes = "tweet.read tweet.write users.read like.read like.write offline.access"
        return (
            f"https://twitter.com/i/oauth2/authorize"
            f"?response_type=code"
            f"&client_id={settings.twitter_client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&scope={scopes}"
            f"&state={state}"
            f"&code_challenge={code_challenge}"
            f"&code_challenge_method=S256"
        )

    async def twitter_exchange(self, code: str, code_verifier: str) -> dict:
        redirect_uri = settings.twitter_redirect_uri or f"{settings.frontend_url}/api/social/connect/twitter/callback"
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.twitter.com/2/oauth2/token",
                data={
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                    "code_verifier": code_verifier,
                },
                auth=(settings.twitter_client_id, settings.twitter_client_secret),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if resp.status_code != 200:
                raise ValueError(f"Twitter token exchange failed: {resp.text}")
            tokens = resp.json()

            # Get user profile
            user_resp = await client.get(
                "https://api.twitter.com/2/users/me",
                params={"user.fields": "id,name,username,profile_image_url,public_metrics"},
                headers={"Authorization": f"Bearer {tokens['access_token']}"},
            )
            profile = {}
            if user_resp.status_code == 200:
                u = user_resp.json().get("data", {})
                profile = {
                    "id": u.get("id"),
                    "name": u.get("name"),
                    "username": f"@{u.get('username', '')}",
                    "avatar": u.get("profile_image_url", ""),
                    "followers": u.get("public_metrics", {}).get("followers_count", 0),
                }
            return {"tokens": tokens, "profile": profile}

    # ── Instagram (Meta Graph API) ───────────────────────────────────

    def instagram_auth_url(self, state: str) -> str:
        client_id = settings.instagram_client_id or settings.facebook_app_id
        redirect_uri = settings.instagram_redirect_uri or f"{settings.frontend_url}/api/social/connect/instagram/callback"
        scopes = "instagram_basic,instagram_manage_comments,instagram_manage_insights,pages_show_list,pages_read_engagement"
        return (
            f"https://www.facebook.com/v18.0/dialog/oauth"
            f"?client_id={client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&scope={scopes}"
            f"&state={state}"
            f"&response_type=code"
        )

    async def instagram_exchange(self, code: str) -> dict:
        client_id = settings.instagram_client_id or settings.facebook_app_id
        client_secret = settings.instagram_client_secret or settings.facebook_app_secret
        redirect_uri = settings.instagram_redirect_uri or f"{settings.frontend_url}/api/social/connect/instagram/callback"
        async with httpx.AsyncClient() as client:
            # Exchange code for short-lived token
            resp = await client.post(
                "https://graph.facebook.com/v18.0/oauth/access_token",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "code": code,
                    "grant_type": "authorization_code",
                },
            )
            if resp.status_code != 200:
                raise ValueError(f"Instagram token exchange failed: {resp.text}")
            tokens = resp.json()

            access_token = tokens.get("access_token", "")

            # Exchange for long-lived token
            ll_resp = await client.get(
                "https://graph.facebook.com/v18.0/oauth/access_token",
                params={
                    "grant_type": "fb_exchange_token",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "fb_exchange_token": access_token,
                },
            )
            if ll_resp.status_code == 200:
                ll_data = ll_resp.json()
                tokens["access_token"] = ll_data.get("access_token", access_token)
                tokens["expires_in"] = ll_data.get("expires_in", 5184000)

            # Get Instagram Business Account via pages
            pages_resp = await client.get(
                "https://graph.facebook.com/v18.0/me/accounts",
                params={"access_token": tokens["access_token"]},
            )
            ig_account_id = None
            ig_username = ""
            if pages_resp.status_code == 200:
                for page in pages_resp.json().get("data", []):
                    page_id = page["id"]
                    ig_resp = await client.get(
                        f"https://graph.facebook.com/v18.0/{page_id}",
                        params={
                            "fields": "instagram_business_account",
                            "access_token": tokens["access_token"],
                        },
                    )
                    if ig_resp.status_code == 200:
                        ig_data = ig_resp.json().get("instagram_business_account", {})
                        if ig_data.get("id"):
                            ig_account_id = ig_data["id"]
                            # Get IG profile
                            ig_profile_resp = await client.get(
                                f"https://graph.facebook.com/v18.0/{ig_account_id}",
                                params={
                                    "fields": "username,name,profile_picture_url,followers_count,media_count",
                                    "access_token": tokens["access_token"],
                                },
                            )
                            if ig_profile_resp.status_code == 200:
                                ig_p = ig_profile_resp.json()
                                ig_username = ig_p.get("username", "")
                            break

            # If no business account, try personal IG token exchange
            if not ig_account_id:
                me_resp = await client.get(
                    "https://graph.facebook.com/v18.0/me",
                    params={"fields": "id,name", "access_token": tokens["access_token"]},
                )
                me_data = me_resp.json() if me_resp.status_code == 200 else {}

            profile = {
                "id": ig_account_id or me_data.get("id", "") if not ig_account_id else ig_account_id,
                "name": ig_username or (me_data.get("name", "") if not ig_account_id else ig_username),
                "username": f"@{ig_username}" if ig_username else "",
                "avatar": "",
                "ig_account_id": ig_account_id,
            }
            tokens["ig_account_id"] = ig_account_id
            return {"tokens": tokens, "profile": profile}

    # ── TikTok ───────────────────────────────────────────────────────

    def tiktok_auth_url(self, state: str) -> str:
        redirect_uri = settings.tiktok_redirect_uri or f"{settings.frontend_url}/api/social/connect/tiktok/callback"
        scopes = "user.info.basic,video.list"
        return (
            f"https://www.tiktok.com/v2/auth/authorize/"
            f"?client_key={settings.tiktok_client_key}"
            f"&response_type=code"
            f"&scope={scopes}"
            f"&redirect_uri={redirect_uri}"
            f"&state={state}"
        )

    async def tiktok_exchange(self, code: str) -> dict:
        redirect_uri = settings.tiktok_redirect_uri or f"{settings.frontend_url}/api/social/connect/tiktok/callback"
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://open.tiktokapis.com/v2/oauth/token/",
                data={
                    "client_key": settings.tiktok_client_key,
                    "client_secret": settings.tiktok_client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if resp.status_code != 200:
                raise ValueError(f"TikTok token exchange failed: {resp.text}")
            tokens = resp.json()

            access_token = tokens.get("access_token", "")
            # Get user info
            user_resp = await client.get(
                "https://open.tiktokapis.com/v2/user/info/",
                params={"fields": "open_id,union_id,avatar_url,display_name,username,follower_count"},
                headers={"Authorization": f"Bearer {access_token}"},
            )
            profile = {}
            if user_resp.status_code == 200:
                u = user_resp.json().get("data", {}).get("user", {})
                profile = {
                    "id": u.get("open_id", ""),
                    "name": u.get("display_name", ""),
                    "username": f"@{u.get('username', '')}",
                    "avatar": u.get("avatar_url", ""),
                    "followers": u.get("follower_count", 0),
                }
            return {"tokens": tokens, "profile": profile}

    # ── Facebook ─────────────────────────────────────────────────────

    def facebook_auth_url(self, state: str) -> str:
        redirect_uri = settings.facebook_redirect_uri or f"{settings.frontend_url}/api/social/connect/facebook/callback"
        scopes = "public_profile,email,user_posts,user_likes,pages_show_list"
        return (
            f"https://www.facebook.com/v18.0/dialog/oauth"
            f"?client_id={settings.facebook_app_id}"
            f"&redirect_uri={redirect_uri}"
            f"&scope={scopes}"
            f"&state={state}"
            f"&response_type=code"
        )

    async def facebook_exchange(self, code: str) -> dict:
        redirect_uri = settings.facebook_redirect_uri or f"{settings.frontend_url}/api/social/connect/facebook/callback"
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://graph.facebook.com/v18.0/oauth/access_token",
                params={
                    "client_id": settings.facebook_app_id,
                    "client_secret": settings.facebook_app_secret,
                    "redirect_uri": redirect_uri,
                    "code": code,
                },
            )
            if resp.status_code != 200:
                raise ValueError(f"Facebook token exchange failed: {resp.text}")
            tokens = resp.json()

            access_token = tokens.get("access_token", "")
            # Exchange for long-lived token
            ll_resp = await client.get(
                "https://graph.facebook.com/v18.0/oauth/access_token",
                params={
                    "grant_type": "fb_exchange_token",
                    "client_id": settings.facebook_app_id,
                    "client_secret": settings.facebook_app_secret,
                    "fb_exchange_token": access_token,
                },
            )
            if ll_resp.status_code == 200:
                ll_data = ll_resp.json()
                tokens["access_token"] = ll_data.get("access_token", access_token)
                tokens["expires_in"] = ll_data.get("expires_in", 5184000)

            # Get profile
            me_resp = await client.get(
                "https://graph.facebook.com/v18.0/me",
                params={
                    "fields": "id,name,picture.type(large),email",
                    "access_token": tokens["access_token"],
                },
            )
            profile = {}
            if me_resp.status_code == 200:
                u = me_resp.json()
                profile = {
                    "id": u.get("id", ""),
                    "name": u.get("name", ""),
                    "username": u.get("name", ""),
                    "avatar": u.get("picture", {}).get("data", {}).get("url", ""),
                }
            return {"tokens": tokens, "profile": profile}


    # ── Twitter token refresh ────────────────────────────────────────

    async def get_integration_data(self, user_id: str, platform: str) -> dict | None:
        """Return the full stored integration config, or None if not connected."""
        async with async_session() as session:
            result = await session.execute(
                select(Integration).where(
                    and_(Integration.user_id == user_id, Integration.type == platform)
                )
            )
            integration = result.scalar_one_or_none()
            if integration and integration.status == "connected":
                return integration.config
        return None

    async def twitter_refresh(self, user_id: str) -> str | None:
        """
        Refresh an expired Twitter access token using the stored refresh_token.
        Returns the new access token on success, None on failure.
        Twitter OAuth 2.0 access tokens expire after 2 hours when offline.access was granted.
        """
        from app.config import settings  # avoid circular import at module level

        config = await self.get_integration_data(user_id, "twitter")
        if not config:
            return None
        refresh_token = config.get("refresh_token", "")
        if not refresh_token or not settings.twitter_client_id:
            return None

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://api.twitter.com/2/oauth2/token",
                    data={"grant_type": "refresh_token", "refresh_token": refresh_token},
                    auth=(settings.twitter_client_id, settings.twitter_client_secret),
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                if resp.status_code != 200:
                    logger.warning("Twitter refresh failed: HTTP %d %s", resp.status_code, resp.text[:200])
                    return None
                tokens = resp.json()
                new_access = tokens.get("access_token", "")
                if not new_access:
                    return None
                # Rotate both tokens (Twitter may issue a new refresh_token)
                new_config = {
                    **config,
                    "access_token": new_access,
                    "refresh_token": tokens.get("refresh_token", refresh_token),
                }
                async with async_session() as session:
                    result = await session.execute(
                        select(Integration).where(
                            and_(Integration.user_id == user_id, Integration.type == "twitter")
                        )
                    )
                    integration = result.scalar_one_or_none()
                    if integration:
                        integration.config = new_config
                        await session.commit()
                await cache.set(f"social_token:{user_id}:twitter", new_access, ttl=3600)
                logger.info("Twitter token refreshed for user %s", user_id)
                return new_access
        except Exception:
            logger.exception("Twitter token refresh error for user %s", user_id)
        return None


social_oauth = SocialOAuthService()
