"""
ML Intelligence API — thin bridge for api.ml_intelligence_api import.

Exposes get_orchestrator() that returns the ML Intelligence orchestrator
(neural trust, bandit, meta-learning, etc.) for app startup and Grace systems integration.
"""


def get_orchestrator():
    """Return the singleton ML Intelligence orchestrator."""
    from ml_intelligence.integration_orchestrator import get_ml_orchestrator
    return get_ml_orchestrator()
