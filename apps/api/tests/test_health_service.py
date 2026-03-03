"""
Tests for HealthService.get_dashboard() — verifies the summary object shape
that the frontend expects.

The bug: backend returned raw lists for steps/heart_rate/sleep, but the
frontend called .toLocaleString() on fields like data.steps.count (which
was undefined on a list).  get_dashboard() now transforms these into summary
dicts.
"""

import pytest
from app.services.health import HealthService


@pytest.mark.asyncio
async def test_dashboard_steps_is_summary_dict_not_list():
    """steps must be a dict with count/goal — not the raw daily list."""
    svc = HealthService()
    data = await svc.get_dashboard()
    steps = data["steps"]
    assert isinstance(steps, dict), "steps must be a summary dict, not a list"
    assert "count" in steps
    assert "goal" in steps


@pytest.mark.asyncio
async def test_dashboard_steps_count_is_int_not_none():
    """steps.count must be an integer — None caused .toLocaleString() crash."""
    svc = HealthService()
    data = await svc.get_dashboard()
    assert isinstance(data["steps"]["count"], int)
    assert data["steps"]["count"] is not None


@pytest.mark.asyncio
async def test_dashboard_steps_goal_is_positive_int():
    svc = HealthService()
    data = await svc.get_dashboard()
    assert data["steps"]["goal"] > 0


@pytest.mark.asyncio
async def test_dashboard_heart_rate_is_summary_dict_not_list():
    """heart_rate must be a dict with current/resting, not the raw list."""
    svc = HealthService()
    data = await svc.get_dashboard()
    hr = data["heart_rate"]
    assert isinstance(hr, dict), "heart_rate must be a summary dict, not a list"
    assert "current" in hr
    assert "resting" in hr


@pytest.mark.asyncio
async def test_dashboard_heart_rate_current_is_int():
    svc = HealthService()
    data = await svc.get_dashboard()
    assert isinstance(data["heart_rate"]["current"], int)


@pytest.mark.asyncio
async def test_dashboard_heart_rate_zones_is_list_of_dicts():
    """heart_rate.zones must be a list of {zone, minutes, color} objects."""
    svc = HealthService()
    data = await svc.get_dashboard()
    zones = data["heart_rate"]["zones"]
    assert isinstance(zones, list)
    assert len(zones) > 0
    for z in zones:
        assert "zone" in z
        assert "minutes" in z


@pytest.mark.asyncio
async def test_dashboard_sleep_has_last_night_shape():
    """sleep.last_night must have duration_hours — not a raw list entry."""
    svc = HealthService()
    data = await svc.get_dashboard()
    sleep = data["sleep"]
    assert isinstance(sleep, dict)
    assert "last_night" in sleep
    ln = sleep["last_night"]
    assert "duration_hours" in ln
    assert isinstance(ln["duration_hours"], (int, float))


@pytest.mark.asyncio
async def test_dashboard_sleep_has_weekly_avg():
    svc = HealthService()
    data = await svc.get_dashboard()
    assert "weekly_avg" in data["sleep"]
    assert isinstance(data["sleep"]["weekly_avg"], (int, float))


@pytest.mark.asyncio
async def test_dashboard_workouts_use_duration_min_not_duration_mins():
    """Workouts must expose duration_min (renamed from duration_mins for frontend)."""
    svc = HealthService()
    data = await svc.get_dashboard()
    for w in data["workouts"]:
        assert "duration_min" in w, "frontend expects duration_min (no 's')"
        assert "duration_mins" not in w, "old key must not leak through"


@pytest.mark.asyncio
async def test_dashboard_workouts_have_intensity():
    """Workouts must include an intensity field derived from calories/duration."""
    svc = HealthService()
    data = await svc.get_dashboard()
    for w in data["workouts"]:
        assert "intensity" in w
        assert w["intensity"] in ("low", "medium", "high")


@pytest.mark.asyncio
async def test_dashboard_body_has_height_cm_not_height_m():
    """Body metrics must expose height_cm (not height_m) for frontend display."""
    svc = HealthService()
    data = await svc.get_dashboard()
    body = data["body"]
    assert "height_cm" in body
    assert "height_m" not in body


@pytest.mark.asyncio
async def test_dashboard_has_wellness_score():
    svc = HealthService()
    data = await svc.get_dashboard()
    assert "wellness_score" in data
    assert 0 <= data["wellness_score"] <= 100


@pytest.mark.asyncio
async def test_estimate_intensity_high():
    svc = HealthService()
    assert svc._estimate_intensity(calories=400, duration_mins=40) == "high"


@pytest.mark.asyncio
async def test_estimate_intensity_medium():
    # 270 cal / 45 min = 6.0 cal/min  →  5 ≤ rate < 8 → "medium"
    svc = HealthService()
    assert svc._estimate_intensity(calories=270, duration_mins=45) == "medium"


@pytest.mark.asyncio
async def test_estimate_intensity_low():
    svc = HealthService()
    assert svc._estimate_intensity(calories=120, duration_mins=60) == "low"


@pytest.mark.asyncio
async def test_estimate_intensity_no_crash_on_zero_duration():
    """Zero duration must not raise ZeroDivisionError."""
    svc = HealthService()
    result = svc._estimate_intensity(calories=0, duration_mins=0)
    assert result == "medium"  # default when no data
