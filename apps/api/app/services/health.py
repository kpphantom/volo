"""
VOLO — Health & Fitness Service
Integrates with Apple Health (via export), Google Fit API, and device sensors.
"""

import httpx
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
        """Get complete health dashboard shaped for the frontend DashboardData contract."""
        steps_list = await self.get_steps(days)
        heart_list = await self.get_heart_rate(days)
        sleep_list = await self.get_sleep(days)
        workouts_list = await self.get_workouts(days)
        body = await self.get_body_metrics()

        score = self._calculate_wellness_score(steps_list, heart_list, sleep_list, workouts_list)

        # ── Steps (most recent day) ────────────────────────────────────
        today_steps = steps_list[0] if steps_list else {}
        step_count = today_steps.get("steps", 0)
        step_goal = 10000

        # ── Heart rate (most recent day) ──────────────────────────────
        today_hr = heart_list[0] if heart_list else {}
        avg_bpm = today_hr.get("avg_bpm", 72)
        min_bpm = today_hr.get("min_bpm", 58)
        max_bpm = today_hr.get("max_bpm", 145)

        # ── Sleep (most recent night) ─────────────────────────────────
        last_sleep = sleep_list[0] if sleep_list else {}
        sleep_hours = last_sleep.get("hours", 0.0)
        quality_map = {"good": 85, "fair": 65, "poor": 40}
        quality_score = quality_map.get(last_sleep.get("quality", "fair"), 65)
        weekly_avg = round(
            sum(s.get("hours", 0) for s in sleep_list) / max(len(sleep_list), 1), 1
        ) if sleep_list else 0.0

        # Approximate sleep stage breakdown (standard architecture ratios)
        deep_h = round(sleep_hours * 0.20, 1)
        rem_h = round(sleep_hours * 0.25, 1)
        light_h = round(sleep_hours * 0.50, 1)
        awake_h = round(sleep_hours * 0.05, 1)

        # ── Workouts ─────────────────────────────────────────────────
        mapped_workouts = [
            {
                "type": w.get("type", "Workout"),
                "duration_min": w.get("duration_mins", 0),
                "calories": w.get("calories", 0),
                "date": w.get("date", ""),
                "intensity": self._estimate_intensity(w.get("calories", 0), w.get("duration_mins", 30)),
            }
            for w in workouts_list
        ]

        # ── Body ──────────────────────────────────────────────────────
        height_m = body.get("height_m", 0)
        height_cm = round(height_m * 100) if height_m else body.get("height_cm", 0)

        return {
            "wellness_score": score,
            "steps": {
                "date": today_steps.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
                "count": step_count,
                "goal": step_goal,
                "distance_km": round(step_count * 0.0008, 1),
                "calories": round(step_count * 0.04),
            },
            "heart_rate": {
                "current": avg_bpm,
                "resting": min_bpm,
                "max_today": max_bpm,
                "min_today": min_bpm,
                "avg_today": avg_bpm,
                "zones": self._estimate_hr_zones(avg_bpm, max_bpm),
            },
            "sleep": {
                "last_night": {
                    "duration_hours": sleep_hours,
                    "deep_hours": deep_h,
                    "light_hours": light_h,
                    "rem_hours": rem_h,
                    "awake_hours": awake_h,
                    "quality_score": quality_score,
                    "bedtime": "",
                    "wake_time": "",
                },
                "weekly_avg": weekly_avg,
            },
            "workouts": mapped_workouts,
            "body": {
                "weight_kg": body.get("weight_kg", 0),
                "height_cm": height_cm,
                "bmi": body.get("bmi", 0),
                "body_fat_pct": body.get("body_fat_pct", 0),
                "muscle_mass_kg": body.get("muscle_mass_kg", 0),
            },
            "period_days": days,
        }

    def _estimate_intensity(self, calories: int, duration_mins: int) -> str:
        """Derive workout intensity from calories-per-minute burn rate."""
        if not duration_mins:
            return "medium"
        rate = calories / duration_mins
        if rate >= 8:
            return "high"
        if rate >= 5:
            return "medium"
        return "low"

    def _estimate_hr_zones(self, avg_bpm: int, max_bpm: int) -> list[dict]:
        """
        Approximate heart-rate zone distribution for a day.
        Without per-minute data, derive minutes from the daily max BPM.
        """
        peak_mins = max(0, (max_bpm - 170) * 2) if max_bpm > 170 else 0
        cardio_mins = max(0, (max_bpm - 140) * 3) if max_bpm > 140 else 0
        fat_burn_mins = max(0, (max_bpm - 110) * 4) if max_bpm > 110 else 0
        rest_mins = max(0, 1440 - peak_mins - cardio_mins - fat_burn_mins)
        return [
            {"zone": "Fat Burn", "minutes": fat_burn_mins, "color": "#f59e0b"},
            {"zone": "Cardio", "minutes": cardio_mins, "color": "#ef4444"},
            {"zone": "Peak", "minutes": peak_mins, "color": "#dc2626"},
            {"zone": "Rest", "minutes": rest_mins, "color": "#22c55e"},
        ]

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
                "_demo": True,
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
                "_demo": True,
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
                "_demo": True,
            }
            for i in range(days)
        ]

    def _demo_workouts(self) -> list[dict]:
        base = datetime.now(timezone.utc)
        return [
            {"id": "w1", "name": "Morning Run", "type": "Running", "date": (base - timedelta(days=1)).isoformat(), "duration_mins": 32, "calories": 340, "_demo": True},
            {"id": "w2", "name": "Yoga Flow", "type": "Yoga", "date": (base - timedelta(days=2)).isoformat(), "duration_mins": 45, "calories": 180, "_demo": True},
            {"id": "w3", "name": "Strength Training", "type": "Strength", "date": (base - timedelta(days=3)).isoformat(), "duration_mins": 55, "calories": 420, "_demo": True},
            {"id": "w4", "name": "Evening Walk", "type": "Walking", "date": (base - timedelta(days=4)).isoformat(), "duration_mins": 28, "calories": 120, "_demo": True},
            {"id": "w5", "name": "HIIT Session", "type": "HIIT", "date": (base - timedelta(days=6)).isoformat(), "duration_mins": 25, "calories": 380, "_demo": True},
        ]

    def _demo_body(self) -> dict:
        return {
            "weight_kg": 75.2,
            "height_m": 1.78,
            "body_fat_pct": 18.5,
            "bmi": round(75.2 / (1.78 ** 2), 1),
            "_demo": True,
        }
