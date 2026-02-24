"""
VOLO — Google OAuth & Services Routes
Handles Google sign-in flow and service discovery.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from app.auth import get_current_user, CurrentUser
from app.services.google_auth import google_auth

router = APIRouter()


class GoogleCallbackRequest(BaseModel):
    code: str
    state: Optional[str] = None


@router.get("/google/auth-url")
async def get_google_auth_url():
    """Get the Google OAuth consent URL to redirect the user to."""
    url = google_auth.get_auth_url()
    return {"auth_url": url}


@router.post("/google/callback")
async def google_callback(body: GoogleCallbackRequest, current_user: CurrentUser = Depends(get_current_user)):
    """Exchange Google OAuth code for tokens and discover services."""
    try:
        result = await google_auth.exchange_code(body.code, user_id=current_user.user_id)
        return {
            "success": True,
            "user_id": result["user_id"],
            "profile": result["profile"],
            "services": result["services"],
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth exchange failed: {str(e)}")


@router.get("/google/services")
async def get_google_services(current_user: CurrentUser = Depends(get_current_user)):
    """Get discovered Google services for the authenticated user."""
    token = google_auth.get_access_token(current_user.user_id)
    if token:
        services = await google_auth.discover_services(token)
        return {"services": services, "connected": True}

    # Demo mode — return all services as available
    return {
        "connected": False,
        "services": [
            {"id": "gmail", "name": "Gmail", "icon": "mail", "connected": True, "status": "demo"},
            {"id": "calendar", "name": "Google Calendar", "icon": "calendar", "connected": True, "status": "demo"},
            {"id": "drive", "name": "Google Drive", "icon": "cloud", "connected": True, "status": "demo"},
            {"id": "youtube", "name": "YouTube", "icon": "video", "connected": True, "status": "demo"},
            {"id": "contacts", "name": "Google Contacts", "icon": "contacts", "connected": True, "status": "demo"},
            {"id": "photos", "name": "Google Photos", "icon": "image", "connected": True, "status": "demo"},
            {"id": "tasks", "name": "Google Tasks", "icon": "tasks", "connected": True, "status": "demo"},
            {"id": "fitness", "name": "Google Fit", "icon": "fitness", "connected": True, "status": "demo"},
            {"id": "maps", "name": "Google Maps", "icon": "map", "connected": True, "status": "demo"},
            {"id": "keep", "name": "Google Keep", "icon": "sticky-note", "connected": True, "status": "demo"},
            {"id": "docs", "name": "Google Docs", "icon": "file-text", "connected": True, "status": "demo"},
            {"id": "sheets", "name": "Google Sheets", "icon": "table", "connected": True, "status": "demo"},
        ],
    }


@router.get("/google/profile")
async def get_google_profile(current_user: CurrentUser = Depends(get_current_user)):
    """Get stored Google profile for the authenticated user."""
    profile = google_auth.get_user_profile(current_user.user_id)
    if profile:
        return profile

    # Demo profile
    return {
        "name": "Volo User",
        "email": "user@gmail.com",
        "picture": "",
        "locale": "en",
    }
