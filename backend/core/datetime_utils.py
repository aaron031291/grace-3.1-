"""
Timezone-safe datetime helpers.

Use when subtracting datetimes that may be timezone-aware (e.g. from DB or ISO strings)
from datetime.utcnow() to avoid "can't subtract offset-naive and offset-aware datetimes".
"""

from datetime import datetime, timezone
from typing import Optional


def as_naive_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Convert a datetime to naive UTC for use in (datetime.utcnow() - x) style math.
    If dt is None, returns None. If dt is naive, returns it unchanged (assumes UTC).
    If dt is aware, converts to UTC and strips tzinfo.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)
