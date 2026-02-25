"""
VOLO — Onboarding Route
Handles the conversational onboarding flow and user preferences.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy import select

from app.auth import get_current_user, CurrentUser
from app.database import async_session, User

router = APIRouter()


class OnboardingStep(BaseModel):
    step: int
    data: dict


class OnboardingStatus(BaseModel):
    completed: bool
    current_step: int
    steps_total: int = 5
    collected_data: dict = {}


class UserPreferences(BaseModel):
    name: str = ""
    role: str = ""
    interests: List[str] = []


@router.get("/onboarding/status")
async def get_onboarding_status(current_user: CurrentUser = Depends(get_current_user)):
    """Get current onboarding status for the user."""
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == current_user.user_id))
        user = result.scalar_one_or_none()
    return OnboardingStatus(
        completed=bool(user and user.onboarding_completed),
        current_step=user.onboarding_step if user else 0,
        steps_total=5,
        collected_data={},
    )


@router.post("/onboarding/step")
async def submit_onboarding_step(step: OnboardingStep, current_user: CurrentUser = Depends(get_current_user)):
    """Submit a step in the onboarding process."""
    async with async_session() as session:
        user_row = await session.get(User, current_user.user_id)
        if user_row:
            user_row.onboarding_step = step.step
            await session.commit()
    return {
        "success": True,
        "step": step.step,
        "next_step": step.step + 1,
        "message": "Step completed. Continue chatting with Volo to set up more.",
    }


@router.post("/onboarding/complete")
async def complete_onboarding(current_user: CurrentUser = Depends(get_current_user)):
    """Mark onboarding as complete in the database."""
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == current_user.user_id))
        user = result.scalar_one_or_none()
        if user:
            user.onboarding_completed = True
            await session.commit()
    return {
        "success": True,
        "message": "Welcome to Volo! Your agent is fully configured and ready.",
    }


@router.post("/user/preferences")
async def save_user_preferences(prefs: UserPreferences, current_user: CurrentUser = Depends(get_current_user)):
    """Save user preferences from onboarding wizard."""
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == current_user.user_id))
        user = result.scalar_one_or_none()
        if user:
            if prefs.name:
                user.name = prefs.name
            user.onboarding_completed = True
            await session.commit()
    return {"success": True, "message": "Preferences saved."}
