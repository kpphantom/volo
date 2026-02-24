"""
VOLO — Health & Fitness Service
Integrates with Apple Health (via export), Google Fit API, and device sensors.
"""

import os
import json
import httpx
from typing import Optional
from datetime import datetime, timezone, timedelta


class HealthService:
    """Unified health & fitness data aggregator."""

    def __init__(self, google_access_token: str = ""):
        self.google_token = google_access_token
        self.headers = {"Authorization": f"Bearer {google_access_token}"} if google_access_token else {}

    # ── Google Fit ──────────────────────────────────────────────────────

    async def get_steps(self, days: int = 7) -> list[dict]:
        """Get daily step count from Google Fit."""
        if not self.google_token:
            return self._demo_steps(days)

        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate",
                headers=self.headers,
                json={
                    "aggregateBy": [{"dataTypeName": "com.google.step_count.delta"}],
                    "bucketByTime": {"durationMillis": 86400000},
                    "startTimeMillis": int(start.timestamp() * 1000),
                    "endTimeMillis": int(end.timestamp() * 1000),
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                steps = []
                for bucket in data.get("bucket", []):
                    ds = bucket.get("dataset", [{}])[0]
                    points = ds.get("point", [])
                    count = points[0]["value"][0]["intVal"] if points else 0
                    steps.append({
                        "date": datetime.fromtimestamp(
                            int(bucket["startTimeMillis"]) / 1000, tz=timezone.utc
                        ).strftime("%Y-%m-%d"),
                        "steps": count,
                    })
                return steps
        return self._demo_steps(days)

    async def get_heart_rate(self, days: int = 7) -> list[dict]:
        """Get heart rate data from Google Fit."""
        if not self.google_token:
            return self._demo_heart_rate(days)

        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate",
                headers=self.headers,
                json={
                    "aggregateBy": [{"dataTypeName": "com.google.heart_rate.bpm"}],
                    "bucketByTime": {"durationMillis": 86400000},
                    "startTimeMillis": int(start.timestamp() * 1000),
                    "endTimeMillis": int(end.timestamp() * 1000),
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                rates = []
                for bucket in data.get("bucket", []):
                    ds = bucket.get("dataset", [{}])[0]
                    points = ds.get("point", [])
                    if points:
                        vals = [p["value"][0]["fpVal"] for p in points]
                        rates.append({
                            "date": datetime.fromtimestamp(
                                int(bucket["startTimeMillis"]) / 1000, tz=timezone.utc
                            ).strftime("%Y-%m-%d"),
                            "avg_bpm": round(sum(vals) / len(vals)),
                            "min_bpm": round(min(vals)),
                            "max_bpm": round(max(vals)),
                        })
                return rates
        return self._demo_heart_rate(days)

    async def get_sleep(self, days: int = 7) -> list[dict]:
        """Get sleep data from Google Fit."""
        if not self.google_token:
            return self._demo_sleep(days)

        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate",
                headers=self.headers,
                json={
                    "aggregateBy": [{"dataTypeName": "com.google.sleep.segment"}],
                    "bucketByTime": {"durationMillis": 86400000},
                    "startTimeMillis": int(start.timestamp() * 1000),
                    "endTimeMillis": int(end.timestamp() * 1000),
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                sleep_data = []
                for bucket in data.get("bucket", []):
                    ds = bucket.get("dataset", [{}])[0]
                    points = ds.get("point", [])
                    total_mins = 0
                    for p in points:
                        start_ns = int(p.get("startTimeNanos", 0))
                        end_ns = int(p.get("endTimeNanos", 0))
                        total_mins += (end_ns - start_ns) / (60 * 1e9)
                    if total_mins > 0:
                        sleep_data.append({
                            "date": datetime.fromtimestamp(
                                int(bucket["startTimeMillis"]) / 1000, tz=timezone.utc
                            ).strftime("%Y-%m-%d"),
                            "hours": round(total_mins / 60, 1),
                            "quality": "good" if total_mins >= 420 else "fair" if total_mins >= 360 else "poor",
                        })
                return sleep_data
        return self._demo_sleep(days)

    async def get_workouts(self, days: int = 30) -> list[dict]:
        """Get workout sessions."""
        if not self.google_token:
            return self._demo_workouts()

        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://www.googleapis.com/fitness/v1/users/me/sessions",
                headers=self.headers,
                params={
                    "startTime": start.isoformat(),
                    "endTime": end.isoformat(),
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                workouts = []
                for session in data.get("session", []):
                    start_ms = int(session.get("startTimeMillis", 0))
                    end_ms = int(session.get("endTimeMillis", 0))
                    duration_mins = (end_ms - start_ms) / 60000
                    workouts.append({
                        "id": session.get("id", ""),
                        "name": session.get("name", "Workout"),
                        "type": self._activity_type(session.get("activityType", 0)),
                        "date": datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc).isoformat(),
                        "duration_mins": round(duration_mins),
                        "calories": 0,  # Would need separate dataset query
                    })
                return workouts
        return self._demo_workouts()

    async def get_body_metrics(self) -> dict:
        """Get latest body metrics (weight, BMI, body fat)."""
        if not self.google_token:
            return self._demo_body()

        end = datetime.now(timezone.utc)
        start = end - timedelta(days=30)

        metrics: dict = {}
        async with httpx.AsyncClient() as client:
            for dtype, key in [
                ("com.google.weight", "weight_kg"),
                ("com.google.height", "height_m"),
                ("com.google.body.fat.percentage", "body_fat_pct"),
            ]:
                resp = await client.post(
                    "https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate",
                    headers=self.headers,
                    json={
                        "aggregateBy": [{"dataTypeName": dtype}],
                        "bucketByTime": {"durationMillis": int((end - start).total_seconds() * 1000)},
                        "startTimeMillis": int(start.timestamp() * 1000),
                        "endTimeMillis": int(end.timestamp() * 1000),
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    buckets = data.get("bucket", [])
                    if buckets:
                        points = buckets[0].get("dataset", [{}])[0].get("point", [])
                        if points:
                            metrics[key] = round(points[-1]["value"][0]["fpVal"], 1)

        return metrics or self._demo_body()

    async def get_dashboard(self, days: int = 7) -> dict:
        """Get complete health dashboard."""
        steps = await self.get_steps(days)
        heart = await self.get_heart_rate(days)
        sleep = await self.get_sleep(days)
        workouts = await self.get_workouts(days)
        body = await self.get_body_metrics()

        # Calculate wellness score (0-100)
        score = self._calculate_wellness_score(steps, heart, sleep, workouts)

        return {
            "wellness_score": score,
            "steps": steps,
            "heart_rate": heart,
            "sleep": sleep,
            "workouts": workouts,
            "body": body,
            "period_days": days,
        }

    def _calculate_wellness_score(self, steps, heart, sleep, workouts) -> int:
        """Calculate a 0-100 wellness score."""
        score = 50  # baseline

        # Steps contribution (0-25 points)
        if steps:
            avg_steps = sum(s["steps"] for s in steps) / len(steps)
            score += min(25, int(avg_steps / 400))  # 10k steps = 25 pts

        # Sleep contribution (0-25 points)
        if sleep:
            avg_sleep = sum(s["hours"] for s in sleep) / len(sleep)
            if 7 <= avg_sleep <= 9:
                score += 25
            elif 6 <= avg_sleep < 7 or 9 < avg_sleep <= 10:
                score += 15
            else:
                score += 5

        # Heart rate contribution (0-15 points)
        if heart:
            avg_hr = sum(h["avg_bpm"] for h in heart) / len(heart)
            if 55 <= avg_hr <= 75:
                score += 15
            elif 50 <= avg_hr <= 85:
                score += 10
            else:
                score += 5

        # Workout contribution (0-10 points)
        if workouts:
            days_with_workout = len(set(w.get("date", "")[:10] for w in workouts))
            score += min(10, days_with_workout * 3)

        return min(100, score)

    def _activity_type(self, code: int) -> str:
        types = {
            7: "Walking", 8: "Running", 1: "Biking", 80: "Pilates",
            82: "Yoga", 3: "Still", 97: "Strength", 72: "Swimming",
            35: "HIIT", 113: "Crossfit",
        }
        return types.get(code, "Other")

    # ── Demo Data ───────────────────────────────────────────────────────

    def _demo_steps(self, days: int) -> list[dict]:
        import random
        base = datetime.now(timezone.utc)
        return [
            {
                "date": (base - timedelta(days=i)).strftime("%Y-%m-%d"),
                "steps": random.randint(4000, 14000),
            }
            for i in range(days)
        ]

    def _demo_heart_rate(self, days: int) -> list[dict]:
        import random
        base = datetime.now(timezone.utc)
        return [
            {
                "date": (base - timedelta(days=i)).strftime("%Y-%m-%d"),
                "avg_bpm": random.randint(62, 78),
                "min_bpm": random.randint(48, 58),
                "max_bpm": random.randint(110, 165),
            }
            for i in range(days)
        ]

    def _demo_sleep(self, days: int) -> list[dict]:
        import random
        base = datetime.now(timezone.utc)
        return [
            {
                "date": (base - timedelta(days=i)).strftime("%Y-%m-%d"),
                "hours": round(random.uniform(5.5, 9.0), 1),
                "quality": random.choice(["good", "fair", "poor"]),
            }
            for i in range(days)
        ]

    def _demo_workouts(self) -> list[dict]:
        base = datetime.now(timezone.utc)
        return [
            {"id": "w1", "name": "Morning Run", "type": "Running", "date": (base - timedelta(days=1)).isoformat(), "duration_mins": 32, "calories": 340},
            {"id": "w2", "name": "Yoga Flow", "type": "Yoga", "date": (base - timedelta(days=2)).isoformat(), "duration_mins": 45, "calories": 180},
            {"id": "w3", "name": "Strength Training", "type": "Strength", "date": (base - timedelta(days=3)).isoformat(), "duration_mins": 55, "calories": 420},
            {"id": "w4", "name": "Evening Walk", "type": "Walking", "date": (base - timedelta(days=4)).isoformat(), "duration_mins": 28, "calories": 120},
            {"id": "w5", "name": "HIIT Session", "type": "HIIT", "date": (base - timedelta(days=6)).isoformat(), "duration_mins": 25, "calories": 380},
        ]

    def _demo_body(self) -> dict:
        return {
            "weight_kg": 75.2,
            "height_m": 1.78,
            "body_fat_pct": 18.5,
            "bmi": round(75.2 / (1.78 ** 2), 1),
        }
