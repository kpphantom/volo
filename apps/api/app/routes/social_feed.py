"""
VOLO — Unified Social Feed Routes
Aggregated social media from Twitter, Instagram, LinkedIn, Reddit, TikTok, Facebook.
"""

from fastapi import APIRouter, Query
from typing import Optional

from app.services.social_feed import SocialFeedService

router = APIRouter()
social_feed = SocialFeedService()


@router.get("/social/feed")
async def get_unified_feed(
    platforms: Optional[str] = Query(None, description="Comma-separated platform list"),
):
    """Get unified social feed from all connected platforms."""
    platform_list = platforms.split(",") if platforms else None
    posts = await social_feed.get_unified_feed(platform_list)
    return {
        "posts": posts,
        "total": len(posts),
        "platforms": social_feed.get_connected_platforms(),
    }


@router.get("/social/feed/{platform}")
async def get_platform_feed(platform: str):
    """Get feed from a specific social platform."""
    fetchers = {
        "twitter": social_feed.twitter_timeline,
        "instagram": social_feed.instagram_feed,
        "linkedin": social_feed.linkedin_feed,
        "reddit": social_feed.reddit_feed,
        "tiktok": social_feed.tiktok_feed,
        "facebook": social_feed.facebook_feed,
    }

    fetcher = fetchers.get(platform)
    if not fetcher:
        return {"error": f"Unknown platform: {platform}", "posts": []}

    posts = await fetcher()
    return {"platform": platform, "posts": posts, "total": len(posts)}


@router.get("/social/platforms")
async def get_social_platforms():
    """Get list of social platforms and their connection status."""
    return {"platforms": social_feed.get_connected_platforms()}
