"""
Diagnostic Engine — re-export from diagnostic_machine.

Canonical import path for the new architecture.
"""

from diagnostic_machine.diagnostic_engine import (
    DiagnosticEngine,
    get_diagnostic_engine,
    start_diagnostic_engine,
    stop_diagnostic_engine,
    EngineState,
    TriggerSource,
)

try:
    from cognitive.trust_engine import get_trust_engine, TrustEngine
except ImportError:
    get_trust_engine = None
    TrustEngine = None

__all__ = [
    "DiagnosticEngine",
    "get_diagnostic_engine",
    "start_diagnostic_engine",
    "stop_diagnostic_engine",
    "EngineState",
    "TriggerSource",
    "get_trust_engine",
    "TrustEngine",
]
