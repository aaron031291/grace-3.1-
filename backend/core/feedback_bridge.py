"""
Feedback Bridge — Correlates decision chains across consensus → execute → learn → trust.

Subscribes to the cognitive event bus and automatically tracks decision_id
through all stages, closing the feedback loop.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_bridge_started = False


def start_feedback_bridge():
    """Subscribe to events and correlate decision chains."""
    global _bridge_started
    if _bridge_started:
        return

    try:
        from cognitive.event_bus import subscribe
        from core.lifecycle_cortex import get_lifecycle_cortex

        cortex = get_lifecycle_cortex()

        def _on_consensus(event):
            decision_id = event.data.get("decision_id") or event.data.get("quorum_id")
            if decision_id:
                cortex.open_decision_chain(decision_id, {
                    "result": event.data.get("result", ""),
                    "models": event.data.get("models", []),
                    "timestamp": event.timestamp,
                })

        def _on_execution(event):
            decision_id = event.data.get("decision_id")
            if decision_id:
                cortex.update_decision_chain(decision_id, "execution", {
                    "success": event.data.get("success", False),
                    "outcome": event.data.get("outcome", ""),
                })

        def _on_learning(event):
            decision_id = event.data.get("decision_id")
            if decision_id:
                cortex.update_decision_chain(decision_id, "learning", {
                    "pattern": event.data.get("pattern", ""),
                    "confidence": event.data.get("confidence", 0),
                })

        def _on_trust(event):
            decision_id = event.data.get("decision_id")
            if decision_id:
                cortex.update_decision_chain(decision_id, "trust_update", {
                    "component": event.data.get("component", ""),
                    "score": event.data.get("score", 0),
                    "delta": event.data.get("delta", 0),
                })

        subscribe("consensus.completed", _on_consensus)
        subscribe("consensus.quorum_committed", _on_consensus)
        subscribe("healing.completed", _on_execution)
        subscribe("task.completed", _on_execution)
        subscribe("learning.feedback", _on_learning)
        subscribe("learning.new_pattern", _on_learning)
        subscribe("trust.updated", _on_trust)

        _bridge_started = True
        logger.info("[FEEDBACK-BRIDGE] Decision chain correlation active")

    except Exception as e:
        logger.warning(f"[FEEDBACK-BRIDGE] Could not start: {e}")
