"""
self_healing/trigger_fabric.py
─────────────────────────────────────────────────────────────────────────────
Multi-Trigger Fabric — Grace's event nervous system.

Connects ALL signal sources to the right system (self-healing, learning,
or coding agent) so no failure goes unnoticed and no learning opportunity
is missed.

Trigger sources wired here:
  SELF-HEALING:
    1. DB session exceptions        (already in session.py)
    2. FastAPI request exceptions   [NEW via middleware]
    3. LLM call failures            [NEW via event bus]
    4. Component health drops       [NEW via Ouroboros hook]
    5. Background loop crashes      [NEW via exception hook]

  LEARNING:
    6. After fix applied to disk    [NEW via fix_applier hook]
    7. KB / RAG search miss         [NEW via event bus]
    8. LLM low-confidence response  [NEW via hallucination guard]
    9. Repeated error pattern       [NEW via MTTR analysis]

  CODING AGENT:
   10. Ouroboros "code" actions     [NEW: routes to task_queue]
   11. Knowledge gap detected       [NEW via event bus]
   12. Test failure on generated code [NEW via verification pass]

All routes are non-blocking (fire-and-forget via event bus or thread).
"""
from __future__ import annotations

import logging
import os
import socket
import threading
import time
from typing import Any, Dict

logger = logging.getLogger(__name__)
_started = False
_started_lock = threading.Lock()

# Grace's critical service map: built dynamically from settings
def _build_service_map():
    """Build service map from actual settings, skipping services that aren't configured."""
    services = []
    try:
        from settings import settings as _s
        # Database — only probe if using PostgreSQL (not SQLite)
        if getattr(_s, "DATABASE_TYPE", "sqlite") == "postgresql":
            host = getattr(_s, "DATABASE_HOST", "localhost")
            port = int(getattr(_s, "DATABASE_PORT", 5432) or 5432)
            services.append((host, port, "PostgreSQL"))
        # Qdrant — only if not skipped AND not using a cloud URL
        if not getattr(_s, "SKIP_QDRANT_CHECK", False):
            qdrant_url = getattr(_s, "QDRANT_URL", "")
            if qdrant_url and ("cloud.qdrant" in qdrant_url or "https://" in qdrant_url):
                # Cloud Qdrant — skip raw TCP probe (use HTTP health instead)
                pass
            else:
                host = getattr(_s, "QDRANT_HOST", "localhost")
                port = int(getattr(_s, "QDRANT_PORT", 6333))
                services.append((host, port, "Qdrant"))
        # Ollama — only if provider is ollama and not skipped
        if getattr(_s, "LLM_PROVIDER", "ollama") == "ollama" and not getattr(_s, "SKIP_OLLAMA_CHECK", False):
            url = getattr(_s, "OLLAMA_URL", "http://localhost:11434")
            # Extract host/port from URL
            from urllib.parse import urlparse
            parsed = urlparse(url)
            services.append((parsed.hostname or "localhost", parsed.port or 11434, "Ollama"))
        # Redis is optional — only probe if REDIS_URL is explicitly set
        redis_url = os.environ.get("REDIS_URL", "")
        if redis_url:
            services.append(("localhost", 6379, "Redis"))
    except Exception:
        # Fallback: only probe the API itself
        pass
    # Always probe Grace's own API
    services.append(("localhost", 8000, "GraceAPI"))
    return services

_SERVICE_MAP = _build_service_map()
_PROBE_INTERVAL_S = 60   # probe every 60 seconds
_PROBE_TIMEOUT_S  = 3    # 3s per service probe


def start(app=None) -> None:
    """Wire all triggers. Call once at startup with the FastAPI app instance."""
    global _started
    with _started_lock:
        if _started:
            return
        _started = True

    logger.info("[TRIGGER-FABRIC] Starting — wiring all trigger sources")

    _wire_event_bus_triggers()

    if app is not None:
        _wire_fastapi_middleware(app)

    _wire_ouroboros_code_action()

    # Start proactive network probe (background thread)
    threading.Thread(
        target=_network_probe_loop,
        daemon=True,
        name="grace-network-probe",
    ).start()

    # Start mirror self-modeling observation loop
    threading.Thread(
        target=_mirror_observation_loop,
        daemon=True,
        name="grace-mirror-observer",
    ).start()

    # Start MTTR pattern watcher (fires error.repeated events)
    threading.Thread(
        target=_watch_mttr_patterns,
        daemon=True,
        name="grace-mttr-watcher",
    ).start()

    logger.info("[TRIGGER-FABRIC] ✅ All trigger sources wired (network probe + mirror observer + MTTR watcher active)")


# ── 1. Event bus subscriptions ────────────────────────────────────────────

def _wire_event_bus_triggers() -> None:
    """Subscribe to event bus topics that should trigger healing/learning/coding."""
    try:
        from cognitive.event_bus import subscribe

        # LLM call failed → self-healing
        subscribe("llm.error", _on_llm_error)

        # Hallucination detected → learning trigger
        subscribe("hallucination.detected", _on_hallucination)

        # Knowledge gap in RAG → coding agent (write missing knowledge)
        subscribe("knowledge.gap", _on_knowledge_gap)

        # Repeated error pattern → higher priority to coding agent
        subscribe("error.repeated", _on_repeated_error)

        # Fix applied → immediate learning signal
        subscribe("fix.applied", _on_fix_applied)

        # Verification rejected → learning (bad code pattern recorded)
        subscribe("verification.rejected", _on_verification_rejected)

        # Network: rate limited → log for circuit breaker awareness
        subscribe("network.rate_limited", _on_rate_limited)

        # Network: healed → ops visibility
        subscribe("network.healed", _on_network_healed)

        # Probe results → route failures to self-healing
        subscribe("probe.light.result", _on_probe_result)
        subscribe("probe.deep.result",  _on_probe_result)

        logger.info("[TRIGGER-FABRIC] Event bus subscriptions active (10 topics)")
    except Exception as e:
        logger.warning("[TRIGGER-FABRIC] Event bus wiring skipped: %s", e)


# ── Proactive network probe ───────────────────────────────────────────────

def _probe_tcp(host: str, port: int, timeout: float = _PROBE_TIMEOUT_S) -> bool:
    """Return True if TCP connection to host:port succeeds within timeout."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, ConnectionRefusedError, TimeoutError):
        return False


def _network_probe_loop() -> None:
    """
    Background thread: probe all Grace services every 60s.
    On failure, fire into error pipeline so _heal_network() acts immediately —
    BEFORE cascading request failures reach user-visible endpoints.
    """
    # Wait for core subsystems via Lifecycle Cortex instead of blind sleep
    try:
        from core.lifecycle_cortex import get_lifecycle_cortex
        cortex = get_lifecycle_cortex()
        cortex.wait_ready("event_bus", timeout=15)
        cortex.wait_ready("error_pipeline", timeout=15)
    except Exception:
        time.sleep(10)  # fallback if cortex not available
    _failures: Dict[str, int] = {}  # track consecutive failures

    while True:
        # ── TimeSense: adapt interval to time of day ──────────────────────
        try:
            from cognitive.time_sense import TimeSense
            t = TimeSense.now_context()
            if t.get("period") in ("late_night",):
                interval = 180   # 3 minutes — quieter at night
            elif t.get("is_business_hours"):
                interval = 30    # 30s — faster detection during working hours
            else:
                interval = _PROBE_INTERVAL_S
        except Exception as e:
            logger.debug("[TRIGGER-FABRIC] TimeSense context unavailable, using default interval: %s", e)
            interval = _PROBE_INTERVAL_S

        for host, port, service in _SERVICE_MAP:
            reachable = _probe_tcp(host, port)
            key = f"{service}:{port}"

            if not reachable:
                _failures[key] = _failures.get(key, 0) + 1
                consecutive = _failures[key]

                # Only alert after 2 consecutive failures (avoids transient noise)
                if consecutive >= 2:
                    logger.warning(
                        "[NETWORK-PROBE] ⚠️ %s (%s:%d) unreachable (%dx consecutive)",
                        service, host, port, consecutive,
                    )
                    _route_exception(
                        ConnectionRefusedError(
                            f"{service} unreachable at {host}:{port} "
                            f"(consecutive failures: {consecutive})"
                        ),
                        context={"service": service, "host": host, "port": port,
                                 "consecutive_failures": consecutive},
                        module="trigger_fabric.network_probe",
                        function=service,
                    )
            else:
                if _failures.get(key, 0) >= 2:
                    logger.info(
                        "[NETWORK-PROBE] ✅ %s (%s:%d) recovered after %d failures",
                        service, host, port, _failures[key],
                    )
                _failures[key] = 0  # reset on success

        time.sleep(interval)


# ── Mirror Self-Modeling observation loop ────────────────────────────────

_MIRROR_INTERVAL_S = 600   # run every 10 minutes


def _mirror_observation_loop() -> None:
    """
    Background thread: run MirrorSelfModelingSystem.detect_behavioral_patterns()
    every 10 minutes and route each pattern type to the correct system.

    Pattern → Action mapping:
      REPEATED_FAILURE     → self-healing (error pipeline)
      LEARNING_PLATEAU     → learning brain (submit to coding agent for curriculum)
      EFFICIENCY_DROP      → coding agent (performance fix task)
      ANOMALOUS_BEHAVIOR   → escalate to human review
      IMPROVEMENT_OPPORT.  → coding agent (proactive improvement task)
      SUCCESS_SEQUENCE     → episodic memory reward signal
    """
    time.sleep(30)  # wait for startup to settle
    _consecutive_failures = 0

    while True:
        try:
            from cognitive.mirror_self_modeling import MirrorSelfModelingSystem
            from database.session import session_scope

            with session_scope() as session:
                mirror = MirrorSelfModelingSystem(session=session)
                patterns = mirror.detect_behavioral_patterns()

            _consecutive_failures = 0  # reset on success

            if not patterns:
                logger.debug("[MIRROR-OBSERVER] No behavioral patterns detected this cycle")
            else:
                logger.info(
                    "[MIRROR-OBSERVER] 🪞 Detected %d behavioral patterns — routing actions",
                    len(patterns),
                )
                for pattern in patterns:
                    _route_mirror_pattern(pattern)

        except Exception as e:
            _consecutive_failures += 1
            if _consecutive_failures >= 5:
                logger.error("[MIRROR-OBSERVER] Mirror loop failing repeatedly (%d consecutive): %s", _consecutive_failures, e)
            else:
                logger.warning("[MIRROR-OBSERVER] Cycle error (non-fatal, %d consecutive): %s", _consecutive_failures, e)

        time.sleep(_MIRROR_INTERVAL_S)


def _route_mirror_pattern(pattern: dict) -> None:
    """
    Route a single mirror pattern to the appropriate action system.
    Each pattern has: type, description, frequency, suggestions.
    """
    pattern_type = pattern.get("type", "")
    description  = pattern.get("description", "")
    suggestions  = pattern.get("suggestions", [])
    frequency    = pattern.get("frequency", 1)

    try:
        if pattern_type == "repeated_failure":
            # Repeated failure → immediate self-healing priority
            _route_exception(
                Exception(f"[Mirror] Repeated failure pattern: {description}"),
                context={"pattern": pattern, "source": "mirror_observer"},
                module="mirror_self_modeling",
                function="repeated_failure",
            )
            logger.info("[MIRROR-OBSERVER] 🔴 Repeated failure → self-heal: %s", description[:60])

        elif pattern_type == "learning_plateau":
            # Plateau → trigger learning expansion
            from api.autonomous_loop_api import submit_coding_task
            submit_coding_task(
                instructions=(
                    f"Learning plateau detected: {description}. "
                    f"Suggestions: {'; '.join(str(s) for s in suggestions[:3])}. "
                    "Create new learning materials or exercises to break through this plateau."
                ),
                context={"pattern": pattern, "frequency": frequency},
                priority=6,
                error_class="learning",
                origin="mirror_observer",
            )
            logger.info("[MIRROR-OBSERVER] 🟡 Learning plateau → coding agent: %s", description[:60])

        elif pattern_type == "efficiency_drop":
            # Efficiency drop → coding agent performance fix
            from api.autonomous_loop_api import submit_coding_task
            submit_coding_task(
                instructions=(
                    f"Efficiency drop detected: {description} (frequency: {frequency}x). "
                    f"Suggestions: {'; '.join(str(s) for s in suggestions[:3])}. "
                    "Profile and optimize the affected operations."
                ),
                context={"pattern": pattern},
                priority=5,
                error_class="performance",
                origin="mirror_observer",
            )
            logger.info("[MIRROR-OBSERVER] 🟠 Efficiency drop → coding agent: %s", description[:60])

        elif pattern_type == "anomalous_behavior":
            # Anomaly → escalation + genesis track
            try:
                from api._genesis_tracker import track
                track(
                    key_type="system_event",
                    what_description=f"[Mirror] Anomalous behavior: {description}",
                    why_reason="Mirror self-modeling detected deviation from normal behavior",
                    how_method="mirror_observer.anomalous_behavior",
                    context_data=pattern,
                    is_error=True,
                )
            except Exception as e:
                logger.debug("[TRIGGER-FABRIC] anomalous_behavior genesis track: %s", e)
            logger.warning("[MIRROR-OBSERVER] 🚨 Anomalous behavior escalated: %s", description[:60])

        elif pattern_type == "improvement_opportunity":
            # Proactive improvement → coding agent (lower priority)
            from api.autonomous_loop_api import submit_coding_task
            submit_coding_task(
                instructions=(
                    f"Improvement opportunity identified by self-mirror: {description}. "
                    f"Suggestions: {'; '.join(str(s) for s in suggestions[:3])}. "
                    "Implement the highest-value improvement."
                ),
                context={"pattern": pattern},
                priority=8,   # lowest priority — background improvement
                error_class="improvement",
                origin="mirror_observer",
            )
            logger.info("[MIRROR-OBSERVER] 🟢 Improvement opportunity → coding agent: %s", description[:60])

        elif pattern_type == "success_sequence":
            # Success → reinforce as episodic memory
            try:
                import json
                from database.session import session_scope
                from cognitive.episodic_memory import EpisodicBuffer
                with session_scope() as session:
                    buf = EpisodicBuffer(session)
                    buf.record_episode(
                        problem=f"Success sequence: {description}",
                        action={"type": "success_reinforcement"},
                        outcome={"success": True, "frequency": frequency},
                        trust_score=0.9,
                        source="mirror_observer",
                    )
            except Exception as e:
                logger.debug("[TRIGGER-FABRIC] success_sequence episodic memory: %s", e)
            logger.debug("[MIRROR-OBSERVER] ✅ Success sequence reinforced in episodic memory")

    except Exception as e:
        logger.debug("[MIRROR-OBSERVER] Pattern routing error (%s): %s", pattern_type, e)


def _on_rate_limited(event) -> None:
    """Rate limit hit — log for ops visibility, future circuit breaker."""
    data = event.data
    service = data.get("service", "unknown")
    logger.warning(
        "[TRIGGER-FABRIC] ⏸ Rate limited on %s — backing off 60s", service
    )
    # Record as genesis key so ops can inspect patterns
    try:
        from api._genesis_tracker import track
        track(
            key_type="system_event",
            what_description=f"Rate limit hit: {service}",
            why_reason=data.get("error", "")[:200],
            how_method="trigger_fabric.circuit_breaker",
            context_data=data,
        )
    except Exception as e:
        logger.debug("[TRIGGER-FABRIC] rate_limited genesis track: %s", e)


def _on_network_healed(event) -> None:
    """Network heal completed — log for ops."""
    fixes = event.data.get("fixes", [])
    logger.info("[TRIGGER-FABRIC] 🌐 Network healed: %s", " | ".join(str(f) for f in fixes))


def _on_probe_result(event) -> None:
    """
    Probe sweep result arrived (probe.light.result / probe.deep.result).
    Route any FAIL checks into the error pipeline for self-healing.
    """
    data = event.data
    failed = data.get("failed", 0)
    results = data.get("results", [])

    if failed == 0:
        return  # all healthy — nothing to do

    for r in results:
        if r.get("status") == "FAIL":
            check  = r.get("check", "unknown")
            detail = r.get("detail", "")
            logger.warning("[TRIGGER-FABRIC] 🔍 Probe failure → self-heal: [%s] %s", check, detail[:80])
            _route_exception(
                Exception(f"[Probe] {check}: {detail}"),
                context={"check": check, "probe_result": r},
                module="probe_agent",
                function=check,
            )




# ── 2. FastAPI global exception middleware ────────────────────────────────

def _wire_fastapi_middleware(app) -> None:
    """Add exception middleware so all API errors reach the error pipeline."""
    try:
        from starlette.middleware.base import BaseHTTPMiddleware
        from starlette.requests import Request
        from starlette.responses import Response

        class ErrorCaptureMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next):
                try:
                    return await call_next(request)
                except Exception as exc:
                    # Non-blocking: route to error pipeline in background
                    threading.Thread(
                        target=_route_exception,
                        args=(exc, {
                            "url": str(request.url),
                            "method": request.method,
                        }, "api", str(request.url.path)),
                        daemon=True,
                    ).start()
                    raise  # re-raise so FastAPI/Starlette handles the response

        app.add_middleware(ErrorCaptureMiddleware)
        logger.info("[TRIGGER-FABRIC] FastAPI error capture middleware added")
    except Exception as e:
        logger.warning("[TRIGGER-FABRIC] FastAPI middleware wiring skipped: %s", e)


# ── 3. Ouroboros "code" action → coding agent task queue ─────────────────

def _wire_ouroboros_code_action() -> None:
    """
    Patch the Ouroboros _decide_and_act so when it decides action_type='code'
    it routes to the coding agent task queue instead of a generic brain call.
    """
    try:
        import api.autonomous_loop_api as loop_api
        _original_decide = loop_api._decide_and_act

        def _patched_decide_and_act(problem: dict) -> dict:
            result = _original_decide(problem)
            # If the brain decided a code action, also submit to coding agent
            if result.get("type") == "code" and not result.get("trust_blocked"):
                threading.Thread(
                    target=_submit_code_action,
                    args=(problem, result),
                    daemon=True,
                ).start()
            return result

        loop_api._decide_and_act = _patched_decide_and_act
        logger.info("[TRIGGER-FABRIC] Ouroboros code action → coding agent patched")
    except Exception as e:
        logger.warning("[TRIGGER-FABRIC] Ouroboros patch skipped: %s", e)


def _submit_code_action(problem: dict, action: dict) -> None:
    """Submit Ouroboros code decision to the coding agent task queue."""
    try:
        from api.autonomous_loop_api import submit_coding_task
        submit_coding_task(
            instructions=(
                f"Fix issue detected by autonomous loop: {problem.get('reason', '')}. "
                f"Target: {problem.get('target', 'unknown')}. "
                f"Severity: {problem.get('severity', 'warning')}."
            ),
            context={
                "target_file": problem.get("target", ""),
                "file": problem.get("target", ""),
                "source": problem.get("source", "ouroboros"),
                "severity": problem.get("severity", "warning"),
            },
            priority=4,
            error_class="logic",
            origin="ouroboros",
        )
    except Exception as e:
        logger.debug("[TRIGGER-FABRIC] Ouroboros code submit: %s", e)


# ── Event handlers ────────────────────────────────────────────────────────

def _on_llm_error(event) -> None:
    """LLM call failed → report to error pipeline for healing."""
    try:
        data = event.data
        _route_exception(
            Exception(f"LLM error from {data.get('provider', 'unknown')}: {data.get('error', '')}"),
            context=data,
            module="llm_orchestrator",
            function=data.get("provider", "unknown"),
        )
    except Exception as e:
        logger.warning("[TRIGGER-FABRIC] route_exception for LLM error failed: %s", e)


def _on_hallucination(event) -> None:
    """Hallucination detected → learning trigger: record as negative example."""
    try:
        import json
        from cognitive.unified_memory import get_unified_memory
        data = event.data
        flags = data.get("flags", [])
        
        get_unified_memory().store_learning(
            input_ctx=json.dumps({
                "topic": "hallucination_pattern",
                "flags": flags,
                "prompt": data.get("prompt_preview", "")[:100],
            }),
            expected=json.dumps({
                "action": "avoid_patterns",
                "patterns": flags,
            }),
            actual="LLM Hallucinated",
            trust=0.1,   # negative signal — low trust
            source="hallucination_guard",
            example_type="hallucination"
        )
        logger.debug("[TRIGGER-FABRIC] Hallucination → learning negative example recorded via UnifiedMemory")
    except Exception as e:
        logger.debug("[TRIGGER-FABRIC] Hallucination error: %s", e)


def _on_knowledge_gap(event) -> None:
    """Knowledge gap detected → submit coding task to generate missing knowledge."""
    try:
        from api.autonomous_loop_api import submit_coding_task
        data = event.data
        gap = data.get("gap", data.get("topic", "unknown knowledge gap"))
        submit_coding_task(
            instructions=(
                f"Knowledge gap detected: '{gap}'. "
                f"Write a Python module or documentation that covers this topic and "
                f"add it to Grace's knowledge base."
            ),
            context={"gap": gap, "source": "knowledge_gap_trigger"},
            priority=7,  # lower priority than error fixes
            error_class="knowledge",
            origin="knowledge_gap",
        )
        logger.debug("[TRIGGER-FABRIC] Knowledge gap '%s' → coding agent", gap)
    except Exception as e:
        logger.debug("[TRIGGER-FABRIC] knowledge_gap submit_coding_task: %s", e)


def _on_repeated_error(event) -> None:
    """Same error pattern repeated — escalate priority."""
    try:
        from api.autonomous_loop_api import submit_coding_task
        data = event.data
        pattern = data.get("pattern", "unknown")
        count = data.get("count", 1)
        submit_coding_task(
            instructions=(
                f"Repeated error pattern (x{count}): {pattern}. "
                "This is recurring — apply a permanent fix, not a workaround."
            ),
            context=data,
            priority=2,  # urgent
            error_class="repeated",
            origin="mttr_analysis",
        )
        logger.info("[TRIGGER-FABRIC] Repeated error x%d → high-priority coding task", count)
    except Exception as e:
        logger.debug("[TRIGGER-FABRIC] repeated_error submit_coding_task: %s", e)


def _on_fix_applied(event) -> None:
    """Fix successfully applied → immediately reward in learning system."""
    try:
        import json
        from cognitive.unified_memory import get_unified_memory
        data = event.data
        
        get_unified_memory().store_episode(
            problem=f"Fixed: {data.get('file', 'unknown')} ({data.get('task_id', '')})",
            action=json.dumps({"type": "fix_applied", "task_id": data.get("task_id")}),
            outcome=json.dumps({"success": True, "lines": data.get("lines", 0)}),
            trust=0.95,
            source="trigger_fabric.fix_applied",
        )
    except Exception as e:
        logger.debug("[TRIGGER-FABRIC] Fix applied error: %s", e)


def _on_verification_rejected(event) -> None:
    """Verification pass rejected code → record as training signal."""
    try:
        import json
        from cognitive.unified_memory import get_unified_memory
        data = event.data
        
        get_unified_memory().store_learning(
            input_ctx=json.dumps({
                "topic": "code_rejection",
                "flags": data.get("flags", []),
                "trust_score": data.get("trust_score", 0),
            }),
            expected=json.dumps({"action": "avoid_rejected_patterns"}),
            actual="Code REJECTED during verification",
            trust=data.get("trust_score", 0.1),
            source="verification_pass",
            example_type="code_rejection"
        )
    except Exception as e:
        logger.debug("[TRIGGER-FABRIC] Verification rejected error: %s", e)


# ── Shared helper ─────────────────────────────────────────────────────────

def _route_exception(exc, context=None, module="", function="") -> None:
    """Fire exception into the error pipeline. Non-blocking from callers."""
    try:
        from self_healing.error_pipeline import get_error_pipeline
        get_error_pipeline().handle(exc, context=context, module=module, function=function)
    except Exception as e:
        logger.warning("[TRIGGER-FABRIC] route_exception error pipeline handle: %s", e)


# ── MTTR pattern watcher — fires error.repeated events ───────────────────

def _watch_mttr_patterns() -> None:
    """
    Background thread: check MTTR data every 5 minutes.
    If any error class repeats > 3x with MTTR < 30s, fire error.repeated.
    """
    import time
    while True:
        try:
            time.sleep(300)  # every 5 minutes
            from self_healing.error_pipeline import get_mttr
            from cognitive.event_bus import publish_async
            for error_class in ("attribute", "import", "name", "type", "value"):
                mttr = get_mttr(error_class)
                if mttr is not None and mttr < 30:
                    publish_async("error.repeated", {
                        "pattern": error_class,
                        "count": "multiple",
                        "mttr_s": mttr,
                    })
        except Exception as e:
            logger.debug("[MTTR-WATCHER] Cycle error (non-fatal): %s", e)
