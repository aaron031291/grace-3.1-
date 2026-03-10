from datetime import datetime, timezone
from typing import Optional


def ensure_aware(dt: Optional[datetime]) -> Optional[datetime]:
    \"\"\"
    Ensure a datetime is timezone-aware UTC.
    If dt is None, returns None. 
    If dt is naive, assumes it is UTC and makes it aware.
    If dt is aware, converts it to UTC.
    \"\"\"
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
