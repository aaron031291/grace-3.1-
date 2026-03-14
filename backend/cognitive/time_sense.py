"""
TimeSense — Grace's Temporal Awareness Layer

Provides time-based intelligence across the system:
- Current time context awareness
- Deadline tracking and urgency scoring
- Time-based task prioritisation
- Activity pattern analysis (busiest hours, days)
- Overdue detection
- Time-until estimates
- Daily/weekly/monthly rhythm detection
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class TimeSense:
    """Grace's sense of time — temporal awareness for the entire system."""

    @staticmethod
    def get_context() -> Dict[str, Any]:
        """Alias for now_context() — used by mirror, qwen-net, and component health."""
        return TimeSense.now_context()

    @staticmethod
    def now_context() -> Dict[str, Any]:
        """What does Grace know about RIGHT NOW."""
        now = datetime.now(timezone.utc)
        hour = now.hour
        dow = now.weekday()
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        if hour < 6:
            period = "late_night"
            period_label = "Late Night"
        elif hour < 12:
            period = "morning"
            period_label = "Morning"
        elif hour < 17:
            period = "afternoon"
            period_label = "Afternoon"
        elif hour < 21:
            period = "evening"
            period_label = "Evening"
        else:
            period = "night"
            period_label = "Night"

        return {
            "timestamp": now.isoformat(),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "day_of_week": day_names[dow],
            "day_number": dow,
            "is_weekend": dow >= 5,
            "is_business_hours": 9 <= hour <= 17 and dow < 5,
            "period": period,
            "period_label": period_label,
            "hour": hour,
            "week_number": now.isocalendar()[1],
            "month": now.strftime("%B"),
            "year": now.year,
        }

    @staticmethod
    def urgency_score(deadline_iso: str) -> Dict[str, Any]:
        """Calculate urgency based on how close the deadline is."""
        try:
            deadline_str = deadline_iso.replace("Z", "+00:00")
            deadline = datetime.fromisoformat(deadline_str)
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            return {"urgency": 0, "label": "no_deadline"}

        now = datetime.now(timezone.utc)
        delta = deadline - now
        hours_left = delta.total_seconds() / 3600

        if hours_left < 0:
            return {"urgency": 1.0, "label": "overdue", "overdue_by": str(-delta), "hours_overdue": round(-hours_left, 1)}
        elif hours_left < 1:
            return {"urgency": 0.95, "label": "critical", "hours_left": round(hours_left, 1)}
        elif hours_left < 4:
            return {"urgency": 0.85, "label": "urgent", "hours_left": round(hours_left, 1)}
        elif hours_left < 24:
            return {"urgency": 0.7, "label": "today", "hours_left": round(hours_left, 1)}
        elif hours_left < 72:
            return {"urgency": 0.5, "label": "soon", "days_left": round(hours_left / 24, 1)}
        elif hours_left < 168:
            return {"urgency": 0.3, "label": "this_week", "days_left": round(hours_left / 24, 1)}
        else:
            return {"urgency": 0.1, "label": "later", "days_left": round(hours_left / 24, 1)}

    @staticmethod
    def time_until(target_iso: str) -> Dict[str, Any]:
        """Human-readable time until a target."""
        try:
            target_str = target_iso.replace("Z", "+00:00")
            target = datetime.fromisoformat(target_str)
            if target.tzinfo is None:
                target = target.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            return {"text": "unknown", "seconds": 0}

        now = datetime.now(timezone.utc)
        delta = target - now
        secs = delta.total_seconds()

        if secs < 0:
            return {"text": f"{_fmt_duration(-secs)} ago", "seconds": secs, "is_past": True}
        return {"text": f"in {_fmt_duration(secs)}", "seconds": secs, "is_past": False}

    @staticmethod
    def activity_patterns(timestamps: List[str]) -> Dict[str, Any]:
        """Analyse a list of timestamps to find activity patterns."""
        if not timestamps:
            return {"total": 0, "patterns": {}}

        hours = [0] * 24
        days = [0] * 7

        for ts in timestamps:
            try:
                dt_str = ts.replace("Z", "+00:00")
                dt = datetime.fromisoformat(dt_str)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                hours[dt.hour] += 1
                days[dt.weekday()] += 1
            except (ValueError, TypeError):
                continue

        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        peak_hour = max(range(24), key=lambda i: hours[i])
        peak_day = max(range(7), key=lambda i: days[i])
        quiet_hour = min(range(24), key=lambda i: hours[i])

        return {
            "total": len(timestamps),
            "by_hour": {f"{h:02d}:00": hours[h] for h in range(24) if hours[h] > 0},
            "by_day": {day_names[d]: days[d] for d in range(7)},
            "peak_hour": f"{peak_hour:02d}:00",
            "peak_day": day_names[peak_day],
            "quiet_hour": f"{quiet_hour:02d}:00",
            "busiest_period": "morning" if peak_hour < 12 else "afternoon" if peak_hour < 17 else "evening",
        }

    @staticmethod
    def prioritise_by_time(tasks: List[Dict]) -> List[Dict]:
        """Re-prioritise tasks based on temporal urgency."""
        scored = []
        for task in tasks:
            deadline = task.get("scheduled_for") or task.get("deadline")
            urgency = TimeSense.urgency_score(deadline) if deadline else {"urgency": 0, "label": "no_deadline"}

            priority_weight = {"critical": 0.4, "high": 0.3, "medium": 0.2, "low": 0.1}.get(task.get("priority", "medium"), 0.2)

            combined_score = (urgency["urgency"] * 0.6) + (priority_weight * 0.4)

            scored.append({
                **task,
                "time_urgency": urgency,
                "combined_score": round(combined_score, 3),
            })

        scored.sort(key=lambda x: x["combined_score"], reverse=True)
        return scored


def _fmt_duration(secs: float) -> str:
    """Format seconds into human-readable duration."""
    if secs < 60:
        return f"{int(secs)}s"
    if secs < 3600:
        return f"{int(secs / 60)}m"
    if secs < 86400:
        h = int(secs / 3600)
        m = int((secs % 3600) / 60)
        return f"{h}h {m}m" if m else f"{h}h"
    d = int(secs / 86400)
    h = int((secs % 86400) / 3600)
    return f"{d}d {h}h" if h else f"{d}d"
