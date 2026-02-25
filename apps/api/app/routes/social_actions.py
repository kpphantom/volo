"""
VOLO — Social Actions Routes
Like, comment, repost, and follow across connected social platforms.
"""

import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

import httpx

from app.auth import get_current_user, CurrentUser
from app.services.social_oauth import social_oauth

logger = logging.getLogger("volo.social_actions")
router = APIRouter()


class LikeRequest(BaseModel):
    post_id: str


class CommentRequest(BaseModel):
    post_id: str
    text: str


class RepostRequest(BaseModel):
    post_id: str
    quote: Optional[str] = None


class PostRequest(BaseModel):
    text: str
    media_urls: Optional[list[str]] = None


# ── Like / Unlike ────────────────────────────────────────────────────

@router.post("/social/{platform}/like")
async def like_post(
    platform: str,
    req: LikeRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Like a post on the specified platform."""
    token = await social_oauth.get_access_token(current_user.user_id, platform)
    if not token:
        raise HTTPException(401, f"Not connected to {platform}. Connect your account first.")

    handlers = {
        "twitter": _twitter_like,
        "instagram": _instagram_like,
        "facebook": _facebook_like,
        "reddit": _reddit_vote,
    }
    handler = handlers.get(platform)
    if not handler:
        raise HTTPException(400, f"Like not supported for {platform}")

    result = await handler(token, req.post_id, current_user.user_id)
    return {"status": "liked", "platform": platform, "post_id": req.post_id, **result}


@router.delete("/social/{platform}/like")
async def unlike_post(
    platform: str,
    post_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Unlike a post on the specified platform."""
    token = await social_oauth.get_access_token(current_user.user_id, platform)
    if not token:
        raise HTTPException(401, f"Not connected to {platform}")

    if platform == "twitter":
        result = await _twitter_unlike(token, post_id, current_user.user_id)
        return {"status": "unliked", **result}
    raise HTTPException(400, f"Unlike not supported for {platform}")


# ── Comment / Reply ──────────────────────────────────────────────────

@router.post("/social/{platform}/comment")
async def comment_on_post(
    platform: str,
    req: CommentRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Comment on / reply to a post."""
    token = await social_oauth.get_access_token(current_user.user_id, platform)
    if not token:
        raise HTTPException(401, f"Not connected to {platform}")

    handlers = {
        "twitter": _twitter_reply,
        "instagram": _instagram_comment,
        "facebook": _facebook_comment,
        "reddit": _reddit_comment,
    }
    handler = handlers.get(platform)
    if not handler:
        raise HTTPException(400, f"Comments not supported for {platform}")

    result = await handler(token, req.post_id, req.text)
    return {"status": "commented", "platform": platform, **result}


# ── Repost / Retweet / Share ─────────────────────────────────────────

@router.post("/social/{platform}/repost")
async def repost(
    platform: str,
    req: RepostRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Repost / retweet / share a post."""
    token = await social_oauth.get_access_token(current_user.user_id, platform)
    if not token:
        raise HTTPException(401, f"Not connected to {platform}")

    if platform == "twitter":
        result = await _twitter_retweet(token, req.post_id, current_user.user_id)
        return {"status": "reposted", **result}
    elif platform == "facebook":
        result = await _facebook_share(token, req.post_id, req.quote)
        return {"status": "shared", **result}
    raise HTTPException(400, f"Repost not supported for {platform}")


# ── Create Post ──────────────────────────────────────────────────────

@router.post("/social/{platform}/post")
async def create_post(
    platform: str,
    req: PostRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Create a new post on the specified platform."""
    token = await social_oauth.get_access_token(current_user.user_id, platform)
    if not token:
        raise HTTPException(401, f"Not connected to {platform}")

    if platform == "twitter":
        result = await _twitter_post(token, req.text)
        return {"status": "posted", **result}
    elif platform == "facebook":
        result = await _facebook_post(token, req.text)
        return {"status": "posted", **result}
    raise HTTPException(400, f"Posting not supported for {platform}")


# ═════════════════════════════════════════════════════════════════════
# Platform-Specific Implementations
# ═════════════════════════════════════════════════════════════════════

# ── Twitter / X ──────────────────────────────────────────────────────

async def _get_twitter_user_id(token: str) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.twitter.com/2/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.status_code == 200:
            return resp.json().get("data", {}).get("id", "")
    return ""


async def _twitter_like(token: str, tweet_id: str, user_id: str) -> dict:
    twitter_uid = await _get_twitter_user_id(token)
    if not twitter_uid:
        raise HTTPException(400, "Could not resolve Twitter user ID")
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://api.twitter.com/2/users/{twitter_uid}/likes",
            json={"tweet_id": tweet_id},
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        if resp.status_code in (200, 201):
            return {"liked": True}
        raise HTTPException(resp.status_code, f"Twitter like failed: {resp.text}")


async def _twitter_unlike(token: str, tweet_id: str, user_id: str) -> dict:
    twitter_uid = await _get_twitter_user_id(token)
    if not twitter_uid:
        raise HTTPException(400, "Could not resolve Twitter user ID")
    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"https://api.twitter.com/2/users/{twitter_uid}/likes/{tweet_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.status_code in (200, 204):
            return {"unliked": True}
        raise HTTPException(resp.status_code, f"Twitter unlike failed: {resp.text}")


async def _twitter_reply(token: str, tweet_id: str, text: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.twitter.com/2/tweets",
            json={"text": text, "reply": {"in_reply_to_tweet_id": tweet_id}},
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        if resp.status_code in (200, 201):
            return {"reply_id": resp.json().get("data", {}).get("id")}
        raise HTTPException(resp.status_code, f"Twitter reply failed: {resp.text}")


async def _twitter_retweet(token: str, tweet_id: str, user_id: str) -> dict:
    twitter_uid = await _get_twitter_user_id(token)
    if not twitter_uid:
        raise HTTPException(400, "Could not resolve Twitter user ID")
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://api.twitter.com/2/users/{twitter_uid}/retweets",
            json={"tweet_id": tweet_id},
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        if resp.status_code in (200, 201):
            return {"retweeted": True}
        raise HTTPException(resp.status_code, f"Retweet failed: {resp.text}")


async def _twitter_post(token: str, text: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.twitter.com/2/tweets",
            json={"text": text},
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        if resp.status_code in (200, 201):
            data = resp.json().get("data", {})
            return {"tweet_id": data.get("id")}
        raise HTTPException(resp.status_code, f"Tweet failed: {resp.text}")


# ── Instagram ────────────────────────────────────────────────────────

async def _instagram_like(token: str, media_id: str, user_id: str) -> dict:
    """Instagram Graph API doesn't support liking via API."""
    raise HTTPException(status_code=501, detail="Instagram like not supported via API")


async def _instagram_comment(token: str, media_id: str, text: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://graph.facebook.com/v18.0/{media_id}/comments",
            data={"message": text, "access_token": token},
        )
        if resp.status_code in (200, 201):
            return {"comment_id": resp.json().get("id")}
        raise HTTPException(resp.status_code, f"Instagram comment failed: {resp.text}")


# ── Facebook ─────────────────────────────────────────────────────────

async def _facebook_like(token: str, post_id: str, user_id: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://graph.facebook.com/v18.0/{post_id}/likes",
            data={"access_token": token},
        )
        if resp.status_code == 200:
            return {"liked": resp.json().get("success", True)}
        raise HTTPException(resp.status_code, f"Facebook like failed: {resp.text}")


async def _facebook_comment(token: str, post_id: str, text: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://graph.facebook.com/v18.0/{post_id}/comments",
            data={"message": text, "access_token": token},
        )
        if resp.status_code in (200, 201):
            return {"comment_id": resp.json().get("id")}
        raise HTTPException(resp.status_code, f"Facebook comment failed: {resp.text}")


async def _facebook_share(token: str, post_id: str, quote: str = None) -> dict:
    async with httpx.AsyncClient() as client:
        data = {"link": f"https://www.facebook.com/{post_id}", "access_token": token}
        if quote:
            data["message"] = quote
        resp = await client.post(
            "https://graph.facebook.com/v18.0/me/feed",
            data=data,
        )
        if resp.status_code in (200, 201):
            return {"share_id": resp.json().get("id")}
        raise HTTPException(resp.status_code, f"Facebook share failed: {resp.text}")


async def _facebook_post(token: str, text: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://graph.facebook.com/v18.0/me/feed",
            data={"message": text, "access_token": token},
        )
        if resp.status_code in (200, 201):
            return {"post_id": resp.json().get("id")}
        raise HTTPException(resp.status_code, f"Facebook post failed: {resp.text}")


# ── Reddit ───────────────────────────────────────────────────────────

async def _reddit_vote(token: str, post_id: str, user_id: str) -> dict:
    """Reddit upvote (requires user OAuth token with 'vote' scope)."""
    raise HTTPException(status_code=501, detail="Reddit voting requires OAuth — not yet implemented")


async def _reddit_comment(token: str, post_id: str, text: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://oauth.reddit.com/api/comment",
            data={"thing_id": f"t3_{post_id}", "text": text},
            headers={"Authorization": f"Bearer {token}", "User-Agent": "Volo/1.0"},
        )
        if resp.status_code == 200:
            return {"commented": True}
        return {"info": "Reddit commenting requires user OAuth."}
