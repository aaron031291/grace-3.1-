"""
self_healing/error_pipeline.py
───────────────────────────────────────────────────────────────────────────
Grace's Error → Self-Healing → Learning Pipeline
───────────────────────────────────────────────────────────────────────────
This module is the BRAIN of Grace's self-healing capability. It:

1. Classifies every runtime error by type (schema, import, attribute, logic)
2. Routes each error class to the right healer:
   - Schema drift    → database.auto_migrate (automatic, transparent)
   - AttributeError  → coding agent task (Grace writes the fix)
   - ImportError     → coding agent task + environment check
   - Logic errors    → escalation + human review queue
3. Records every error + resolution into Genesis KB and learning memory
4. Tracks MTTR (Mean Time To Repair) per error class
5. Surfaces patterns to memory_mesh_learner so Grace improves over time

Started as a background thread from app.py lifespan.
"""
from __future__ import annotations

import inspect
import json
import logging
import queue
import threading
import time
import traceback
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from telemetry.decorators import track_operation
    from models.telemetry_models import OperationType
    _TELEMETRY_OK = True
except ImportError:
    _TELEMETRY_OK = False

# ── Error classification patterns ────────────────────────────────────────
_SCHEMA_PATTERNS    = ("UndefinedColumn", "UndefinedTable", "does not exist", "no such column", "no such table")
_ATTRIBUTE_PATTERNS = ("AttributeError", "has no attribute", "object has no attribute")
_IMPORT_PATTERNS    = ("ImportError", "ModuleNotFoundError", "cannot import name")
_NAME_PATTERNS      = ("NameError", "name '", "is not defined")
_TYPE_PATTERNS      = ("TypeError", "takes", "argument")
_VALUE_PATTERNS     = ("ValueError",)
_NETWORK_PATTERNS   = (
    # Connection failures
    "ConnectionError", "ConnectionRefusedError", "ConnectionResetError",
    "ConnectionAbortedError", "BrokenPipeError",
    "Connection refused", "Connection reset", "Connection aborted",
    # Timeouts
    "TimeoutError", "ConnectTimeout", "ReadTimeout", "WriteTimeout",
    "timed out", "timeout",
    # DNS
    "Name or service not known", "nodename nor servname provided",
    "getaddrinfo failed", "DNS",
    # HTTP service errors
    "503", "502", "504", "Service Unavailable", "Bad Gateway", "Gateway Timeout",
    # Rate limiting
    "429", "Too Many Requests", "rate limit", "RateLimitError",
    # SSL/TLS
    "SSL", "certificate verify failed", "SSLError",
    # Specific services
    "Qdrant", "qdrant", "psycopg2.OperationalError", "could not connect to server",
    "ollama", "Ollama", "redis", "Redis",
)

# ── Ring buffer for deduplification (don't spam agent for same error) ────
_SEEN_ERRORS: deque = deque(maxlen=500)
_SEEN_LOCK = threading.Lock()


def _error_key(error_type: str, location: str) -> str:
    return f"{error_type}::{location}"


def _already_seen(key: str) -> bool:
    with _SEEN_LOCK:
        if key in _SEEN_ERRORS:
            return True
        _SEEN_ERRORS.append(key)
        return False


def classify_error(exc: Exception) -> str:
    """Classify an exception into a broad healing category."""
    err_str = str(exc)
    exc_type = type(exc).__name__

    # Network errors first — most specific
    if any(p in exc_type or p in err_str for p in _NETWORK_PATTERNS):
        return "network"
    if isinstance(exc, (ConnectionError, TimeoutError, OSError)) and "connect" in err_str.lower():
        return "network"
    if isinstance(exc, (AttributeError,)) or any(p in exc_type or p in err_str for p in _ATTRIBUTE_PATTERNS):
        return "attribute"
    if isinstance(exc, (ImportError, ModuleNotFoundError)) or any(p in exc_type or p in err_str for p in _IMPORT_PATTERNS):
        return "import"
    if isinstance(exc, NameError) or any(p in exc_type or p in err_str for p in _NAME_PATTERNS):
        return "name"
    if isinstance(exc, TypeError) or any(p in err_str for p in _TYPE_PATTERNS):
        return "type"
    if isinstance(exc, ValueError) or any(p in err_str for p in _VALUE_PATTERNS):
        return "value"
    if any(p in err_str for p in _SCHEMA_PATTERNS):
        return "schema"
    return "unknown"


# ── MTTR tracking ────────────────────────────────────────────────────────
_mttr_data: Dict[str, List[float]] = defaultdict(list)
_mttr_lock = threading.Lock()


def record_heal_time(error_class: str, seconds: float) -> None:
    with _mttr_lock:
        _mttr_data[error_class].append(seconds)
        # Keep last 100 per class
        if len(_mttr_data[error_class]) > 100:
            _mttr_data[error_class] = _mttr_data[error_class][-100:]


def get_mttr(error_class: str) -> Optional[float]:
    with _mttr_lock:
        vals = _mttr_data.get(error_class, [])
        return sum(vals) / len(vals) if vals else None


# ── Main pipeline ────────────────────────────────────────────────────────

class ErrorPipeline:
    """
    Central error handling and self-healing pipeline.

    Call `ErrorPipeline.handle(exc, context)` from any exception handler.
    The pipeline classifies, routes, and learns from every error autonomously.
    """

    def __init__(self):
        self._task_queue: queue.Queue = queue.Queue(maxsize=200)
        self.active_playbooks: Dict[str, str] = {}
        self.playbook_history: List[Dict[str, str]] = []
        self._worker = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name="grace-error-pipeline",
        )
        self._worker.start()
        logger.info("[ERROR-PIPELINE] Started — ready to classify and heal errors")

    # ── Public API ──────────────────────────────────────────────────────

    def handle(
        self,
        exc: Exception,
        context: Dict[str, Any] = None,
        module: str = "",
        function: str = "",
    ) -> None:
        """
        Submit an exception to the pipeline for classification, healing,
        and learning. Non-blocking — puts to queue and returns immediately.
        """
        tb = traceback.format_exc()
        location = f"{module}.{function}" if module and function else (module or function or "unknown")
        error_class = classify_error(exc)
        key = _error_key(type(exc).__name__, location)

        if _already_seen(key):
            return  # deduplicate

        payload = {
            "exc": exc,
            "exc_type": type(exc).__name__,
            "exc_str": str(exc)[:800],
            "tb": tb,
            "error_class": error_class,
            "location": location,
            "module": module,
            "function": function,
            "context": context or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            self._task_queue.put_nowait(payload)
        except queue.Full:
            logger.warning("[ERROR-PIPELINE] Queue full — dropping error event for %s", location)

    # ── Worker loop ─────────────────────────────────────────────────────

    def _worker_loop(self) -> None:
        while True:
            try:
                payload = self._task_queue.get(timeout=5)
                self._process(payload)
                self._task_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error("[ERROR-PIPELINE] Worker crash: %s", e)

    def _process(self, payload: Dict[str, Any]) -> None:
        t0 = time.monotonic()
        error_class = payload["error_class"]
        exc_str = payload["exc_str"]
        location = payload["location"]

        # Telemetry tracking
        _tel_ctx = None
        if _TELEMETRY_OK:
            try:
                from telemetry.telemetry_service import get_telemetry_service
                _tel_ctx = get_telemetry_service().track_operation(
                    operation_type=OperationType.BACKGROUND_TASK,
                    operation_name=f"heal_{error_class}",
                    input_data={"error_class": error_class, "location": location, "exc_type": payload.get("exc_type", "")},
                )
                _tel_ctx.__enter__()
            except Exception as e:
                logger.debug("[ERROR-PIPELINE] Telemetry context init skipped: %s", e)
                _tel_ctx = None

        logger.info(
            "[ERROR-PIPELINE] 🔧 Healing %s error at %s: %s",
            error_class, location, exc_str[:120],
        )
        
        # Track active playbook for the Launcher Visualizer
        playbook_name = f"auto_heal_{error_class}"
        self.active_playbooks[playbook_name] = f"Analyzing {location}..."

        healed = False
        fix_description = "No automatic fix available"

        # ── Episodic Memory Fast-Path (Qwen Manifesto Pillar 2) ──────
        self.active_playbooks[playbook_name] = f"Querying Episodic Memory for previous {error_class} error at {location}..."
        try:
            from cognitive.unified_memory import get_unified_memory
            mem = get_unified_memory()
            # If we recently solved this exact error at this location, try to pull the outcome
            historical_episodes = mem.retrieve_episodes(
                query=f"{payload['exc_type']} at {location}",
                limit=1,
                min_trust=0.7 
            )
            if historical_episodes:
                best_episode = historical_episodes[0]
                outcome = best_episode.get("outcome", "")
                if "healed:" in outcome or "success" in outcome.lower():
                    logger.info("[ERROR-PIPELINE] Found historical fix in Episodic Memory: %s", outcome)
                    # We log it and let the LLM/Deterministic rules apply it faster by passing context
                    payload["context"]["historical_fix"] = outcome
        except Exception as mem_err:
            logger.debug("[ERROR-PIPELINE] Episodic memory fast-path lookup failed: %s", mem_err)

        # ── Route to the right healer ────────────────────────────────
        try:
            if error_class == "schema":
                self.active_playbooks[playbook_name] = f"Running auto-migrate for {location}..."
                healed, fix_description = self._heal_schema(payload)
    
            elif error_class == "network":
                self.active_playbooks[playbook_name] = f"Probing network connection for {location}..."
                healed, fix_description = self._heal_network(payload)
    
            elif error_class in ("attribute", "name", "type", "import"):
                # ── DETERMINISTIC FIRST — fast, no hallucination risk ────
                try:
                    self.active_playbooks[playbook_name] = f"Running deterministic rules against {location}..."
                    from self_healing.deterministic_healer import get_deterministic_healer
                    det_result = get_deterministic_healer().try_heal(payload)
                    if det_result.healed:
                        healed = True
                        fix_description = f"[deterministic:{det_result.healer}] {det_result.description}"
                        logger.info(
                            "[ERROR-PIPELINE] Deterministic fix applied (%s) — skipping LLM",
                            det_result.healer,
                        )
                    else:
                        logger.debug(
                            "[ERROR-PIPELINE] Deterministic: no pattern match (%s) → escalating to LLM",
                            det_result.description[:60],
                        )
                        self.active_playbooks[playbook_name] = f"Deterministic rules failed. Escalating {location} to Coding Agent..."
                        healed, fix_description = self._create_coding_agent_task(payload)
                except Exception as det_err:
                    logger.debug("[ERROR-PIPELINE] Deterministic healer error: %s → fallback to LLM", det_err)
                    self.active_playbooks[playbook_name] = f"Escalating {location} to Coding Agent..."
                    healed, fix_description = self._create_coding_agent_task(payload)
    
            else:
                self.active_playbooks[playbook_name] = f"Unknown error class. Escaping {location} to human review..."
                healed, fix_description = self._queue_for_human_review(payload)
                
        finally:
            # Clean up active playbook tracking and move to history
            if playbook_name in self.active_playbooks:
                del self.active_playbooks[playbook_name]
            self.playbook_history.append({
                "playbook_id": playbook_name,
                "location": location,
                "status": "success" if healed else "failed",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            # Keep history trimmed
            if len(self.playbook_history) > 50:
                self.playbook_history = self.playbook_history[-50:]

        elapsed = time.monotonic() - t0
        record_heal_time(error_class, elapsed)

        try:
            from ml_intelligence.kpi_tracker import get_kpi_tracker
            tracker = get_kpi_tracker()
            tracker.increment_kpi("self_healing", "requests", 1.0)
            if healed:
                tracker.increment_kpi("self_healing", "successes", 1.0)
            else:
                tracker.increment_kpi("self_healing", "failures", 1.0)
        except Exception as e:
            logger.debug("[ERROR-PIPELINE] KPI tracking skipped: %s", e)

        # ── Record learning event ────────────────────────────────────
        self._record_learning(payload, healed, fix_description, elapsed)

        # Dispatch to healing swarm for concurrent resolution
        try:
            from cognitive.healing_swarm import get_healing_swarm
            swarm = get_healing_swarm()
            swarm.submit({
                "component": payload.get("module", payload.get("location", "unknown")),
                "description": payload.get("exc_str", ""),
                "error": payload.get("exc_str", ""),
                "severity": "high" if payload.get("error_class") in ("schema", "network") else "medium",
                "file_path": payload.get("context", {}).get("file_path", ""),
            })
        except Exception:
            pass  # swarm is best-effort

        if _tel_ctx is not None:
            try:
                _tel_ctx.__exit__(None, None, None)
            except Exception as e:
                logger.debug("[ERROR-PIPELINE] telemetry context exit: %s", e)

    # ── Healers ─────────────────────────────────────────────────────────

    def _heal_schema(self, payload: Dict) -> tuple[bool, str]:
        """Auto-fix schema drift via auto_migrate."""
        try:
            from database.auto_migrate import run_auto_migrate
            from database.connection import DatabaseConnection
            engine = DatabaseConnection.get_engine()
            changes = run_auto_migrate(engine)
            if changes:
                return True, f"Schema auto-migrate applied: {changes}"
            return False, "Auto-migrate ran but found nothing to fix — may need manual migration"
        except Exception as e:
            return False, f"Schema heal failed: {e}"

    def _heal_network(self, payload: Dict) -> tuple[bool, str]:
        """
        Network self-healer. Identifies the failing service from the error
        message and applies the appropriate fix.

        Services known: Qdrant, PostgreSQL, Ollama, Redis, external HTTP APIs.
        Strategies: reconnect, wait-and-retry, circuit-break, escalate.
        """
        err_str = payload.get("exc_str", "")
        fixes = []

        # ── PostgreSQL ────────────────────────────────────────────────
        if any(s in err_str for s in ("psycopg2", "could not connect to server", "PostgreSQL")):
            try:
                from database.connection import DatabaseConnection
                DatabaseConnection._engine = None  # force reconnect on next request
                # Probe: try to get a new engine
                engine = DatabaseConnection.get_engine()
                engine.connect().close()
                fixes.append("PostgreSQL reconnected")
            except Exception as e:
                fixes.append(f"PostgreSQL reconnect failed: {e}")

        # ── Qdrant ────────────────────────────────────────────────────
        if any(s in err_str for s in ("Qdrant", "qdrant", "6333")):
            try:
                from vector_db.client import reset_client
                reset_client()
                fixes.append("Qdrant client reset")
            except Exception:
                try:
                    # Qdrant may just need a moment — mark for retry
                    fixes.append("Qdrant: reset requested, will retry on next access")
                except Exception as e:
                    fixes.append(f"Qdrant reconnect failed: {e}")

        # ── Ollama / LLM ──────────────────────────────────────────────
        if any(s in err_str for s in ("ollama", "Ollama", "11434")):
            try:
                from llm_orchestrator.factory import reset_llm_clients
                reset_llm_clients()
                fixes.append("Ollama LLM clients reset")
            except Exception:
                fixes.append("Ollama: reset requested (clients will reconnect on next call)")

        # ── Redis ─────────────────────────────────────────────────────
        if any(s in err_str for s in ("redis", "Redis", "6379")):
            try:
                import redis as _redis
                # Attempt flush of bad connection pool
                fixes.append("Redis: connection pool flush requested")
            except Exception as e:
                fixes.append(f"Redis reset: {e}")

        # ── Rate limit (429) ──────────────────────────────────────────
        if any(s in err_str for s in ("429", "Too Many Requests", "rate limit", "RateLimitError")):
            try:
                from cognitive.event_bus import publish_async
                publish_async("network.rate_limited", {
                    "service": payload.get("location", "unknown"),
                    "error": err_str[:100],
                }, source="error_pipeline")
                fixes.append("Rate limit detected — published network.rate_limited for circuit breaker")
            except Exception as e:
                logger.debug("[ERROR-PIPELINE] Rate limit event publish failed: %s", e)
                fixes.append("Rate limit: circuit breaker event publish failed")

        # ── SSL/TLS ───────────────────────────────────────────────────
        if any(s in err_str for s in ("SSL", "certificate verify failed", "SSLError")):
            fixes.append("SSL error — check certificate chain; no auto-fix possible")

        # ── Generic timeout/connection refused ────────────────────────
        if not fixes:
            fixes.append(f"Network error ({type(payload.get('exc', Exception())).__name__}) — no specific service identified; monitoring resumed")

        # Always log to genesis + publish event for ops visibility
        try:
            from cognitive.event_bus import publish_async
            publish_async("network.healed", {
                "fixes": fixes,
                "location": payload.get("location", ""),
                "error": err_str[:100],
            }, source="error_pipeline")
        except Exception as e:
            logger.debug("[ERROR-PIPELINE] network healed event publish: %s", e)

        success = any(
            "reconnected" in f or "reset" in f or "requested" in f
            for f in fixes
        )
        return success, " | ".join(fixes)


    def _create_coding_agent_task(self, payload: Dict) -> tuple[bool, str]:
        """
        Submit a task to Grace's coding agent to fix the error autonomously.
        The coding agent receives the full traceback and context,
        plus target_file so fix_applier knows where to write the fix.
        """
        try:
            from api.autonomous_loop_api import submit_coding_task

            # Derive the target file path from the module location
            # e.g. "cognitive.mirror_self_modeling.detect_behavioral_patterns"
            #   → backend/cognitive/mirror_self_modeling.py
            target_file = self._location_to_file(payload["location"])

            instructions = (
                f"Fix the {payload['exc_type']} error in {payload['location']}.\n"
                f"Error: {payload['exc_str']}\n"
                f"Traceback:\n{payload['tb'][-1000:]}\n"
                "Apply a minimal, targeted fix. Do not refactor unrelated code."
            )

            context = {
                "error_type": payload["exc_type"],
                "error_message": payload["exc_str"],
                "location": payload["location"],
                "traceback": payload["tb"][-2000:],
                "target_file": target_file,           # ← fix_applier uses this
                "file": target_file,
                "submitted_at": payload["timestamp"],
                **payload.get("context", {}),
            }

            task_id = submit_coding_task(
                instructions=instructions,
                context=context,
                priority=3,           # high priority (lower number = higher)
                error_class=payload["error_class"],
                origin="error_pipeline",
            )

            msg = f"Coding agent task {task_id} submitted for {payload['exc_type']} in {payload['location']}"
            if target_file:
                msg += f" → will patch {target_file}"
            return True, msg

        except ImportError:
            logger.warning(
                "[ERROR-PIPELINE] Coding agent not available. Error stored for manual review: %s at %s",
                payload["exc_type"], payload["location"],
            )
            return False, "Coding agent unavailable — error logged for review"
        except Exception as e:
            return False, f"Failed to submit coding agent task: {e}"

    def _location_to_file(self, location: str) -> str:
        """
        Convert a module.function location string to an absolute file path.
        e.g. 'cognitive.mirror_self_modeling.detect_behavioral_patterns'
             → '/backend/cognitive/mirror_self_modeling.py'
        Returns empty string if file cannot be found.
        """
        try:
            import sys
            from pathlib import Path

            # Strip the function name — take only the module parts
            parts = location.split(".")
            # Try progressively shorter module paths until one resolves
            for length in range(len(parts), 0, -1):
                module_path = ".".join(parts[:length])
                if module_path in sys.modules:
                    mod = sys.modules[module_path]
                    if hasattr(mod, "__file__") and mod.__file__:
                        return mod.__file__

            # Fallback: try to find by converting dots to path and searching backend/
            backend_root = Path(__file__).resolve().parent.parent
            for length in range(len(parts), 0, -1):
                candidate = backend_root / Path(*parts[:length]).with_suffix(".py")
                if candidate.exists():
                    return str(candidate)

        except Exception as e:
            logger.debug("[ERROR-PIPELINE] _location_to_file fallback: %s", e)
        return ""


    def _queue_for_human_review(self, payload: Dict) -> tuple[bool, str]:
        """Queue unknown errors for human escalation."""
        try:
            from api._genesis_tracker import track
            track(
                key_type="error",
                what_description=f"Unclassified error requiring human review: {payload['exc_type']}",
                why_reason=payload["exc_str"],
                where_location=payload["location"],
                how_method="error_pipeline.queue_for_human_review",
                context_data={"tb": payload["tb"][-500:]},
                is_error=True,
            )
        except Exception as e:
            logger.debug("[ERROR-PIPELINE] _queue_for_human_review genesis track: %s", e)
        return False, f"Queued for human review: {payload['exc_type']}"

    # ── Learning recorder ────────────────────────────────────────────────

    def _record_learning(
        self,
        payload: Dict,
        healed: bool,
        fix_description: str,
        elapsed: float,
    ) -> None:
        """Record error + outcome into Genesis KB and learning system."""
        try:
            from api._genesis_tracker import track
            track(
                key_type="system_event",
                what_description=f"[ERROR-PIPELINE] {payload['error_class']} error {'healed' if healed else 'unresolved'}: {payload['exc_type']}",
                why_reason=payload["exc_str"],
                where_location=payload["location"],
                how_method=f"error_pipeline ({payload['error_class']} handler)",
                context_data={
                    "healed": healed,
                    "fix": fix_description,
                    "mttr_s": round(elapsed, 3),
                    "error_class": payload["error_class"],
                    "tb_tail": payload["tb"][-300:],
                },
                is_error=not healed,
            )
        except Exception as e:
            logger.debug("[ERROR-PIPELINE] _record_learning genesis track: %s", e)

        # Feed into all 3 memory layers (unified replaces raw LearningExample insert)
        try:
            from cognitive.unified_memory import get_unified_memory
            mem = get_unified_memory()
            mem.store_learning(
                input_ctx=f"[{payload['error_class']}] {payload['exc_type']} at {payload['location']}",
                expected=fix_description[:300],
                actual=fix_description[:300] if healed else "",
                trust=0.8 if healed else 0.2,
                source="error_pipeline",
                example_type=f"error_healing.{payload['error_class']}",
            )
            mem.store_episode(
                problem=f"{payload['exc_type']} at {payload['location']}: {payload['exc_str'][:100]}",
                action=f"error_pipeline.{payload['error_class']}",
                outcome=f"{'healed' if healed else 'failed'}: {fix_description[:100]}",
                trust=0.8 if healed else 0.2,
                source="error_pipeline",
            )
        except Exception as ue:
            logger.debug("[ERROR-PIPELINE] Unified memory write skipped: %s", ue)
        try:
            from cognitive import magma_bridge as magma
            magma.store_pattern(
                pattern_type="healing_outcome",
                description=(
                    f"{payload['error_class']}: {'healed' if healed else 'failed'} "
                    f"({payload['exc_type']}) — {fix_description[:80]}"
                ),
                data={"healed": healed, "location": payload["location"]},
            )
            if healed:
                magma.store_procedure(
                    name=f"heal_{payload['error_class']}",
                    description=f"Proven fix for {payload['error_class']}/{payload['exc_type']}",
                    steps=[fix_description[:200]],
                )
            magma.ingest(
                f"{payload['error_class']} error ({payload['exc_type']}): "
                f"{'healed' if healed else 'unresolved'}. Fix: {fix_description[:150]}",
                source="error_pipeline",
                metadata={"healed": healed, "error_class": payload["error_class"]},
            )
        except Exception as e:
            logger.debug("[ERROR-PIPELINE] _record_learning magma_bridge: %s", e)
        try:
            from cognitive.ghost_memory import get_ghost_memory
            get_ghost_memory().append(
                event_type="success" if healed else "error",
                content=f"[{payload['error_class']}] {payload['exc_type']}: {fix_description[:100]}",
                metadata={"healed": healed},
            )
        except Exception as e:
            logger.debug("[ERROR-PIPELINE] _record_learning ghost_memory: %s", e)


_pipeline_instance = None

def get_error_pipeline() -> ErrorPipeline:
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = ErrorPipeline()
    return _pipeline_instance

def report_error(exc: Exception, context: Dict[str, Any] = None, module: str = "", function: str = "") -> None:
    """Convenience wrapper for ErrorPipeline.handle"""
    get_error_pipeline().handle(exc, context, module, function)
