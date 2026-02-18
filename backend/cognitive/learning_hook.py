"""
Universal Learning Hook

ONE function any subsystem calls to feed the learning tracker.
Eliminates duplicate boilerplate across 16+ systems.

Usage from any module:
    from cognitive.learning_hook import track_learning_event
    track_learning_event("my_system", "what happened", outcome="success", data={...})

Non-blocking, non-fatal. If tracker unavailable, silently drops.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_tracker = None
_session_factory = None


def _get_tracker():
    """Lazy-init tracker + session. Called once, cached."""
    global _tracker, _session_factory
    if _tracker is not None:
        return _tracker, _session_factory

    try:
        from database.session import SessionLocal
        from cognitive.llm_interaction_tracker import LLMInteractionTracker

        _session_factory = SessionLocal
        _s = _session_factory()
        _tracker = LLMInteractionTracker(_s)
        return _tracker, _session_factory
    except Exception:
        return None, None


def track_learning_event(
    source: str,
    description: str,
    outcome: str = "success",
    confidence: float = 0.7,
    interaction_type: str = "reasoning",
    data: Optional[Dict[str, Any]] = None,
    duration_ms: float = 0.0,
    error: Optional[str] = None,
):
    """
    Universal learning hook. Call from ANY subsystem.

    Args:
        source: Which system produced this (e.g. "timesense", "magma", "sandbox")
        description: What happened (human-readable)
        outcome: "success", "failure", "partial_success"
        confidence: How confident the system is (0-1)
        interaction_type: "reasoning", "command_execution", "coding_task", etc.
        data: Any structured data to record
        duration_ms: How long it took
        error: Error message if failed
    """
    try:
        tracker, factory = _get_tracker()
        if tracker is None:
            return

        session = factory()
        from cognitive.llm_interaction_tracker import LLMInteractionTracker
        t = LLMInteractionTracker(session)

        t.record_interaction(
            prompt=f"[{source.upper()}] {description[:500]}",
            response=str(data)[:2000] if data else description[:500],
            model_used=source,
            interaction_type=interaction_type,
            outcome=outcome,
            confidence_score=confidence,
            duration_ms=duration_ms,
            error_message=error,
            metadata=data,
        )
        session.commit()
        session.close()
    except Exception:
        pass  # Never block the calling system
