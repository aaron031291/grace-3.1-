"""
Deterministic Logger
=====================
Structured, deterministic logging for component lifecycle events.

Every event is:
1. AST-verified (if it's a code file)
2. Genesis Key tracked (full provenance)
3. Timestamped with monotonic ordering
4. Severity-classified deterministically

No LLM needed. Pure structural event capture.
"""

import ast
import time
import logging
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).parent.parent

_log_lock = threading.Lock()
_event_log: List[Dict[str, Any]] = []
_MAX_LOG_SIZE = 2000


@dataclass
class DeterministicEvent:
    """A single deterministic lifecycle event."""
    event_id: str
    event_type: str
    component: str
    severity: str  # critical, warning, info, debug
    message: str
    timestamp: str
    deterministic: bool = True
    verified: bool = False
    details: Optional[Dict[str, Any]] = None
    genesis_key_id: Optional[str] = None


def log_event(
    event_type: str,
    component: str,
    message: str,
    severity: str = "info",
    details: Optional[Dict[str, Any]] = None,
    file_path: Optional[str] = None,
    track_genesis: bool = True,
) -> DeterministicEvent:
    """
    Log a deterministic lifecycle event.

    If file_path is provided, AST-verifies the file first.
    Optionally creates a Genesis Key for full provenance.
    """
    event = DeterministicEvent(
        event_id=f"DLOG-{int(time.time() * 1000)}-{id(threading.current_thread()) % 1000:03d}",
        event_type=event_type,
        component=component,
        severity=severity,
        message=message,
        timestamp=datetime.now(timezone.utc).isoformat(),
        details=details or {},
    )

    if file_path:
        full_path = BACKEND_ROOT / file_path if not Path(file_path).is_absolute() else Path(file_path)
        if full_path.exists() and full_path.suffix == ".py":
            try:
                ast.parse(full_path.read_text(errors="ignore"))
                event.verified = True
            except SyntaxError as e:
                event.verified = False
                event.details["syntax_error"] = f"{e.msg} (line {e.lineno})"
                if severity == "info":
                    event.severity = "warning"

    if track_genesis:
        try:
            from api._genesis_tracker import track
            result = track(
                key_type="system_event",
                what=f"[{event_type}] {component}: {message}",
                who="deterministic_logger",
                where=file_path,
                how="deterministic_lifecycle",
                output_data={"event_id": event.event_id, "severity": severity},
                tags=["deterministic", "lifecycle", event_type, component],
            )
            if result and hasattr(result, "key_id"):
                event.genesis_key_id = result.key_id
        except Exception:
            pass

    with _log_lock:
        _event_log.append(asdict(event))
        if len(_event_log) > _MAX_LOG_SIZE:
            _event_log[:] = _event_log[-_MAX_LOG_SIZE:]

    log_fn = {
        "critical": logger.error,
        "warning": logger.warning,
        "info": logger.info,
        "debug": logger.debug,
    }.get(severity, logger.info)

    log_fn(f"[DETERMINISTIC-LOG] [{event_type}] {component}: {message}")

    return event


def log_component_registered(component: str, file_path: Optional[str] = None, details: Optional[Dict] = None) -> DeterministicEvent:
    """Log when a new component is discovered or registered."""
    return log_event("COMPONENT_REGISTERED", component, f"Component registered: {component}", "info", details, file_path)


def log_component_alive(component: str, latency_ms: float = 0) -> DeterministicEvent:
    """Log when a probe confirms a component is alive."""
    return log_event("PROBE_ALIVE", component, f"Alive (latency: {latency_ms:.0f}ms)", "info",
                      {"latency_ms": latency_ms})


def log_component_dead(component: str, error: str = "") -> DeterministicEvent:
    """Log when a probe finds a component is dead."""
    return log_event("PROBE_DEAD", component, f"Dead: {error}", "critical",
                      {"error": error})


def log_scan_started(component: str, scan_type: str = "deterministic") -> DeterministicEvent:
    """Log when a deterministic scan starts for a component."""
    return log_event("SCAN_STARTED", component, f"Deterministic scan started ({scan_type})", "info",
                      {"scan_type": scan_type})


def log_scan_result(component: str, issues_found: int, critical: int = 0) -> DeterministicEvent:
    """Log scan results."""
    sev = "critical" if critical > 0 else "warning" if issues_found > 0 else "info"
    return log_event("SCAN_RESULT", component, f"Scan complete: {issues_found} issues ({critical} critical)", sev,
                      {"issues_found": issues_found, "critical": critical})


def log_fix_attempted(component: str, fix_type: str, deterministic: bool = True) -> DeterministicEvent:
    """Log when a fix is attempted."""
    method = "deterministic" if deterministic else "llm_assisted"
    return log_event("FIX_ATTEMPTED", component, f"Fix attempted ({method}): {fix_type}", "info",
                      {"fix_type": fix_type, "deterministic": deterministic})


def log_fix_result(component: str, success: bool, fix_type: str) -> DeterministicEvent:
    """Log the result of a fix attempt."""
    sev = "info" if success else "warning"
    status = "succeeded" if success else "failed"
    return log_event("FIX_RESULT", component, f"Fix {status}: {fix_type}", sev,
                      {"success": success, "fix_type": fix_type})


def log_heal_escalated(component: str, reason: str, to: str = "llm") -> DeterministicEvent:
    """Log when healing escalates from deterministic to LLM/coding agent."""
    return log_event("HEAL_ESCALATED", component, f"Escalated to {to}: {reason}", "warning",
                      {"escalated_to": to, "reason": reason})


def log_verify_result(component: str, healthy: bool, iteration: int = 1) -> DeterministicEvent:
    """Log verification after a fix/heal cycle."""
    sev = "info" if healthy else "warning"
    status = "healthy" if healthy else "still unhealthy"
    return log_event("VERIFY_RESULT", component, f"Verification (iter {iteration}): {status}", sev,
                      {"healthy": healthy, "iteration": iteration})


def get_event_log(component: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """Get the deterministic event log, optionally filtered by component."""
    with _log_lock:
        if component:
            filtered = [e for e in _event_log if e.get("component") == component]
        else:
            filtered = list(_event_log)
    return filtered[-limit:]


def get_event_summary() -> Dict[str, Any]:
    """Get a summary of all deterministic events."""
    with _log_lock:
        events = list(_event_log)

    if not events:
        return {"total_events": 0, "components": {}, "by_type": {}, "by_severity": {}}

    components: Dict[str, int] = {}
    by_type: Dict[str, int] = {}
    by_severity: Dict[str, int] = {}

    for e in events:
        comp = e.get("component", "unknown")
        components[comp] = components.get(comp, 0) + 1
        etype = e.get("event_type", "unknown")
        by_type[etype] = by_type.get(etype, 0) + 1
        sev = e.get("severity", "info")
        by_severity[sev] = by_severity.get(sev, 0) + 1

    return {
        "total_events": len(events),
        "components": components,
        "by_type": by_type,
        "by_severity": by_severity,
        "latest": events[-5:] if events else [],
    }
