"""
TimeSense Governance Layer

Overarching temporal governance that integrates TimeSense into every component
that needs time awareness. Rather than modifying each component individually,
this layer provides a universal timing decorator and SLA enforcement system
that wraps any operation.

Components that need TimeSense:
1.  Ingestion pipeline     - chunk/embed/store timing, throughput monitoring
2.  Self-healing           - heal operation SLAs, timeout enforcement
3.  Code Agent             - task execution timing, deadline tracking
4.  3-Layer Reasoning      - L1/L2/L3 phase timing, total reasoning SLA
5.  Retrieval              - search latency monitoring, freshness decay
6.  Chat endpoint          - end-to-end response time SLA
7.  Handshake protocol     - heartbeat cycle timing, death timeout
8.  Closed-loop ecosystem  - improvement cycle timing, convergence rate
9.  Librarian              - document processing timing
10. Governance             - rule check latency, audit cycle timing
11. Learning pipeline      - expansion timing, learning velocity
12. Memory systems         - recall latency, consolidation timing

This is the temporal nervous system — if anything takes too long,
TimeSense detects it and can trigger self-healing.
"""

import logging
import time
import functools
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)

def _track_ts_gov(desc, **kw):
    try:
        from cognitive.learning_hook import track_learning_event
        track_learning_event("timesense_governance", desc, **kw)
    except Exception:
        pass


@dataclass
class SLADefinition:
    """Service Level Agreement for an operation."""
    operation: str
    max_duration_ms: float
    warning_threshold_ms: float
    critical_threshold_ms: float
    component: str = ""
    auto_heal_on_breach: bool = False
    description: str = ""


@dataclass
class SLAViolation:
    """Record of an SLA being breached."""
    operation: str
    component: str
    expected_ms: float
    actual_ms: float
    severity: str  # warning / critical / breach
    timestamp: datetime = field(default_factory=datetime.now)
    auto_healed: bool = False


# ============================================================================
# SLA DEFINITIONS FOR EVERY COMPONENT
# ============================================================================

DEFAULT_SLAS: Dict[str, SLADefinition] = {
    # Ingestion
    "ingestion.chunk": SLADefinition("ingestion.chunk", 5000, 3000, 8000, "ingestion", description="Text chunking"),
    "ingestion.embed": SLADefinition("ingestion.embed", 10000, 5000, 20000, "ingestion", description="Embedding generation"),
    "ingestion.store": SLADefinition("ingestion.store", 3000, 1500, 5000, "ingestion", description="Vector storage"),
    "ingestion.full": SLADefinition("ingestion.full", 30000, 15000, 60000, "ingestion", True, "Full document ingestion"),

    # Self-healing
    "healing.assess": SLADefinition("healing.assess", 5000, 2000, 10000, "healing", description="Health assessment"),
    "healing.execute": SLADefinition("healing.execute", 30000, 15000, 60000, "healing", description="Heal execution"),
    "healing.cycle": SLADefinition("healing.cycle", 60000, 30000, 120000, "healing", True, "Full healing cycle"),

    # Code Agent
    "agent.understand": SLADefinition("agent.understand", 10000, 5000, 20000, "code_agent", description="Task understanding"),
    "agent.plan": SLADefinition("agent.plan", 15000, 8000, 30000, "code_agent", description="Plan creation"),
    "agent.execute": SLADefinition("agent.execute", 300000, 120000, 600000, "code_agent", description="Task execution"),

    # 3-Layer Reasoning
    "reasoning.layer1": SLADefinition("reasoning.layer1", 60000, 30000, 120000, "reasoning", description="Parallel reasoning"),
    "reasoning.layer2": SLADefinition("reasoning.layer2", 60000, 30000, 120000, "reasoning", description="Synthesis reasoning"),
    "reasoning.layer3": SLADefinition("reasoning.layer3", 30000, 15000, 60000, "reasoning", description="Grace verification"),
    "reasoning.full": SLADefinition("reasoning.full", 180000, 90000, 300000, "reasoning", True, "Full 3-layer pipeline"),

    # Retrieval
    "retrieval.search": SLADefinition("retrieval.search", 2000, 1000, 5000, "retrieval", description="Vector search"),
    "retrieval.rerank": SLADefinition("retrieval.rerank", 3000, 1500, 5000, "retrieval", description="Result reranking"),

    # Chat
    "chat.response": SLADefinition("chat.response", 15000, 8000, 30000, "chat", True, "End-to-end chat response"),
    "chat.streaming": SLADefinition("chat.streaming", 5000, 2000, 10000, "chat", description="First token latency"),

    # Handshake
    "handshake.pulse": SLADefinition("handshake.pulse", 10000, 5000, 30000, "handshake", description="Heartbeat cycle"),
    "handshake.check": SLADefinition("handshake.check", 500, 200, 1000, "handshake", description="Single component check"),

    # Closed-loop
    "closedloop.cycle": SLADefinition("closedloop.cycle", 60000, 30000, 120000, "closed_loop", description="Improvement cycle"),
    "closedloop.analyze": SLADefinition("closedloop.analyze", 10000, 5000, 20000, "closed_loop", description="Agent self-analysis"),

    # Librarian
    "librarian.process": SLADefinition("librarian.process", 15000, 8000, 30000, "librarian", description="Document processing"),
    "librarian.categorize": SLADefinition("librarian.categorize", 5000, 2000, 10000, "librarian", description="AI categorization"),

    # Learning
    "learning.expand": SLADefinition("learning.expand", 30000, 15000, 60000, "learning", description="Neighbor expansion"),
    "learning.study": SLADefinition("learning.study", 20000, 10000, 40000, "learning", description="Study session"),

    # Memory
    "memory.recall": SLADefinition("memory.recall", 1000, 500, 3000, "memory", description="Memory recall"),
    "memory.consolidate": SLADefinition("memory.consolidate", 30000, 15000, 60000, "memory", description="Memory consolidation"),

    # Governance
    "governance.check": SLADefinition("governance.check", 500, 200, 1000, "governance", description="Governance rule check"),
    "governance.audit": SLADefinition("governance.audit", 10000, 5000, 20000, "governance", description="Audit cycle"),
}


class TimeSenseGovernance:
    """
    Overarching temporal governance layer.

    Provides:
    - Universal operation timing via decorator
    - SLA enforcement for every component
    - Violation tracking and alerting
    - Auto-healing trigger on SLA breach
    - Performance trend analysis
    - Feeds all timing data into TimeSense engine
    """

    def __init__(self):
        self.slas = dict(DEFAULT_SLAS)
        self.violations: List[SLAViolation] = []
        self._lock = threading.Lock()
        self._timesense = None

        self.stats = {
            "total_operations": 0,
            "total_violations": 0,
            "total_warnings": 0,
            "total_breaches": 0,
            "total_auto_heals": 0,
        }

    @property
    def timesense(self):
        """Lazy-init TimeSense engine."""
        if self._timesense is None:
            try:
                from cognitive.timesense import TimeSenseEngine
                self._timesense = TimeSenseEngine()
            except Exception:
                pass
        return self._timesense

    def time_operation(self, operation: str, component: str = ""):
        """
        Decorator that times an operation and enforces its SLA.

        Usage:
            ts_gov = get_timesense_governance()

            @ts_gov.time_operation("retrieval.search", "retrieval")
            def search(query):
                ...
        """
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start = time.time()
                success = True
                result = None
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    success = False
                    raise
                finally:
                    duration_ms = (time.time() - start) * 1000
                    self._record_timing(operation, component, duration_ms, success)
            return wrapper

        return decorator

    def time_async_operation(self, operation: str, component: str = ""):
        """Async version of time_operation decorator."""
        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                start = time.time()
                success = True
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception:
                    success = False
                    raise
                finally:
                    duration_ms = (time.time() - start) * 1000
                    self._record_timing(operation, component, duration_ms, success)
            return wrapper
        return decorator

    def record(self, operation: str, duration_ms: float, component: str = "", success: bool = True, data_bytes: float = 0):
        """Manually record an operation timing (for code that can't use decorators)."""
        self._record_timing(operation, component, duration_ms, success, data_bytes)

    def _record_timing(self, operation: str, component: str, duration_ms: float, success: bool, data_bytes: float = 0):
        """Core timing recording with SLA enforcement."""
        with self._lock:
            self.stats["total_operations"] += 1

        # Feed to TimeSense engine
        if self.timesense:
            try:
                self.timesense.record_operation(
                    operation=operation,
                    duration_ms=duration_ms,
                    component=component,
                    success=success,
                    data_bytes=data_bytes,
                )
            except Exception:
                pass

        # Check SLA
        sla = self.slas.get(operation)
        if sla:
            self._check_sla(sla, duration_ms, component)

    def _check_sla(self, sla: SLADefinition, duration_ms: float, component: str):
        """Check if an operation violated its SLA."""
        if duration_ms > sla.critical_threshold_ms:
            severity = "breach"
        elif duration_ms > sla.max_duration_ms:
            severity = "critical"
        elif duration_ms > sla.warning_threshold_ms:
            severity = "warning"
        else:
            return

        violation = SLAViolation(
            operation=sla.operation,
            component=component or sla.component,
            expected_ms=sla.max_duration_ms,
            actual_ms=duration_ms,
            severity=severity,
        )

        with self._lock:
            self.violations.append(violation)
            if len(self.violations) > 1000:
                self.violations = self.violations[-1000:]

            if severity == "breach":
                self.stats["total_breaches"] += 1
            elif severity == "critical":
                self.stats["total_violations"] += 1
            else:
                self.stats["total_warnings"] += 1

        logger.warning(
            f"[TIMESENSE-GOV] SLA {severity}: {sla.operation} took {duration_ms:.0f}ms "
            f"(limit: {sla.max_duration_ms:.0f}ms)"
        )

        # Auto-heal on breach if configured
        if severity == "breach" and sla.auto_heal_on_breach:
            self._trigger_auto_heal(sla, violation)

    def _trigger_auto_heal(self, sla: SLADefinition, violation: SLAViolation):
        """Trigger self-healing when an SLA is breached."""
        try:
            from genesis.unified_intelligence import UnifiedIntelligenceEngine
            from database.session import SessionLocal
            session = SessionLocal()
            if session:
                try:
                    engine = UnifiedIntelligenceEngine(session)
                    engine.record(
                        source_system="timesense_governance",
                        signal_type="sla_breach",
                        signal_name=f"breach_{sla.operation}",
                        value_numeric=violation.actual_ms,
                        value_json={
                            "operation": sla.operation,
                            "expected_ms": sla.max_duration_ms,
                            "actual_ms": violation.actual_ms,
                            "component": violation.component,
                        },
                        severity="critical",
                        trust_score=0.3,
                        component_name=violation.component,
                        ttl_seconds=600,
                    )
                finally:
                    session.close()

            violation.auto_healed = True
            with self._lock:
                self.stats["total_auto_heals"] += 1

            _track_ts_gov(
                f"SLA breach auto-heal: {sla.operation} ({violation.actual_ms:.0f}ms)",
                outcome="triggered"
            )
        except Exception as e:
            logger.debug(f"[TIMESENSE-GOV] Auto-heal trigger failed: {e}")

    def get_sla_status(self) -> Dict[str, Any]:
        """Get current SLA status across all components."""
        component_status = defaultdict(lambda: {"total": 0, "violations": 0, "breaches": 0})

        for v in self.violations[-200:]:
            cs = component_status[v.component]
            cs["total"] += 1
            if v.severity in ("critical", "breach"):
                cs["violations"] += 1
            if v.severity == "breach":
                cs["breaches"] += 1

        return {
            "stats": self.stats,
            "total_slas_defined": len(self.slas),
            "recent_violations": len(self.violations),
            "component_health": dict(component_status),
            "worst_violations": [
                {
                    "operation": v.operation,
                    "component": v.component,
                    "expected_ms": v.expected_ms,
                    "actual_ms": v.actual_ms,
                    "severity": v.severity,
                    "timestamp": v.timestamp.isoformat(),
                }
                for v in sorted(self.violations[-20:], key=lambda x: x.actual_ms, reverse=True)[:10]
            ],
        }

    def add_sla(self, operation: str, max_ms: float, warn_ms: float = None, critical_ms: float = None, component: str = "", auto_heal: bool = False):
        """Add or update an SLA definition."""
        self.slas[operation] = SLADefinition(
            operation=operation,
            max_duration_ms=max_ms,
            warning_threshold_ms=warn_ms or (max_ms * 0.6),
            critical_threshold_ms=critical_ms or (max_ms * 1.5),
            component=component,
            auto_heal_on_breach=auto_heal,
        )


_ts_governance: Optional[TimeSenseGovernance] = None

def get_timesense_governance() -> TimeSenseGovernance:
    """Get the global TimeSense governance singleton."""
    global _ts_governance
    if _ts_governance is None:
        _ts_governance = TimeSenseGovernance()
    return _ts_governance
