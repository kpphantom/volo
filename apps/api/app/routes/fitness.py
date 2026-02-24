"""
VOLO — Health & Fitness Routes
Health dashboard, steps, heart rate, sleep, workouts, body metrics.
"""

from fastapi import APIRouter, Query

from app.services.health import HealthService
from app.services.google_auth import GoogleAuthService

router = APIRouter()
google_auth = GoogleAuthService()


@router.get("/health/dashboard")
async def get_health_dashboard(days: int = Query(7, ge=1, le=90)):
    """Get complete health dashboard with wellness score."""
    token = google_auth.get_access_token("dev-user") or ""
    health = HealthService(google_access_token=token)
    dashboard = await health.get_dashboard(days)
    return dashboard


@router.get("/health/steps")
async def get_steps(days: int = Query(7, ge=1, le=90)):
    """Get daily step counts."""
    token = google_auth.get_access_token("dev-user") or ""
    health = HealthService(google_access_token=token)
    steps = await health.get_steps(days)
    return {"steps": steps, "period_days": days}


@router.get("/health/heart-rate")
async def get_heart_rate(days: int = Query(7, ge=1, le=90)):
    """Get heart rate data."""
    token = google_auth.get_access_token("dev-user") or ""
    health = HealthService(google_access_token=token)
    data = await health.get_heart_rate(days)
    return {"heart_rate": data, "period_days": days}


@router.get("/health/sleep")
async def get_sleep(days: int = Query(7, ge=1, le=90)):
    """Get sleep data."""
    token = google_auth.get_access_token("dev-user") or ""
    health = HealthService(google_access_token=token)
    data = await health.get_sleep(days)
    return {"sleep": data, "period_days": days}


@router.get("/health/workouts")
async def get_workouts(days: int = Query(30, ge=1, le=365)):
    """Get workout sessions."""
    token = google_auth.get_access_token("dev-user") or ""
    health = HealthService(google_access_token=token)
    data = await health.get_workouts(days)
    return {"workouts": data, "period_days": days}


@router.get("/health/body")
async def get_body_metrics():
    """Get body metrics (weight, BMI, body fat)."""
    token = google_auth.get_access_token("dev-user") or ""
    health = HealthService(google_access_token=token)
    data = await health.get_body_metrics()
    return {"body": data}
