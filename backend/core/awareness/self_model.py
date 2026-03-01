"""
Self-Model — unified temporal awareness + self-mirror.

Merges:
  - cognitive/time_sense.py (TimeSense)
  - cognitive/mirror_self_modeling.py (MirrorSelfModeling)

Both implementations stay in original files.
This provides the unified interface.
"""

from cognitive.time_sense import TimeSense

try:
    from cognitive.mirror_self_modeling import MirrorSelfModeling
except ImportError:
    MirrorSelfModeling = None


class SelfModel:
    """Grace's self-awareness: time + mirror + patterns."""

    def __init__(self, session=None):
        self.time = TimeSense
        self.mirror = MirrorSelfModeling(session) if session and MirrorSelfModeling else None

    def now(self) -> dict:
        """Current temporal context."""
        return self.time.get_context()

    def reflect(self) -> dict:
        """Self-mirror observation."""
        if self.mirror:
            try:
                return self.mirror.observe()
            except Exception:
                pass
        return {"patterns": [], "status": "mirror_unavailable"}

    def urgency(self, deadline_iso: str) -> dict:
        """Calculate urgency of a deadline."""
        return self.time.urgency_score(deadline_iso)

    def activity_patterns(self, timestamps: list) -> dict:
        """Analyze activity patterns from timestamps."""
        return self.time.activity_patterns(timestamps)


__all__ = ["SelfModel", "TimeSense", "MirrorSelfModeling"]
