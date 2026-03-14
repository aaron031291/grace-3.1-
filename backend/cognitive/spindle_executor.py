"""
Spindle Executor — Dispatch Table for Z3-Verified Actions (GAP 3)

After the Spindle Z3 engine proves an action is SAT (safe),
this module maps the verified bitmask to an actual procedure and executes it.

Flow:  NLP → Braille Compiler → Z3 Proof → **SpindleExecutor** → System Effect
"""

import asyncio
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Tuple

from cognitive.braille_compiler import BrailleDictionary as BD
from cognitive.physics.spindle_proof import SpindleProof
from cognitive.spindle_checkpoint import get_checkpoint_manager
from cognitive.circuit_breaker import enter_loop, exit_loop

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
#  Execution Result
# ══════════════════════════════════════════════════════════════════════

@dataclass
class ExecutionResult:
    success: bool
    action_taken: str
    output: Any = None
    duration_ms: float = 0.0
    proof_hash: str = ""
    error: str = ""


# ══════════════════════════════════════════════════════════════════════
#  Procedure Registry
# ══════════════════════════════════════════════════════════════════════

class ProcedureRegistry:
    """Maps (domain_bit, intent_bit) tuples to handler callables."""

    def __init__(self):
        self._handlers: Dict[Tuple[int, int], Callable[..., ExecutionResult]] = {}

    def register(self, domain: int, intent: int, handler: Callable) -> None:
        key = (domain, intent)
        self._handlers[key] = handler
        logger.debug(f"[SPINDLE-EXEC] Registered handler for ({domain:#x}, {intent:#x})")

    def lookup(self, domain: int, intent: int) -> Optional[Callable]:
        return self._handlers.get((domain, intent))

    def all_keys(self) -> list:
        return list(self._handlers.keys())


# ══════════════════════════════════════════════════════════════════════
#  Default Handlers
# ══════════════════════════════════════════════════════════════════════

def _handle_database_repair(proof: SpindleProof) -> ExecutionResult:
    """DATABASE × REPAIR → HealingCoordinator (full chain with coding agent)."""
    return _delegate_to_healing("database_repair", proof)


def _handle_database_query(proof: SpindleProof) -> ExecutionResult:
    """DATABASE × QUERY → read-only pass-through (safe)."""
    return ExecutionResult(
        success=True,
        action_taken="passthrough:database_query",
        output={"note": "Read-only query permitted by Z3 proof"},
        proof_hash=proof.constraint_hash,
    )


def _handle_database_start(proof: SpindleProof) -> ExecutionResult:
    """DATABASE × START → healing system."""
    return _delegate_to_healing("database_start", proof)


def _handle_database_stop(proof: SpindleProof) -> ExecutionResult:
    """DATABASE × STOP → healing system."""
    return _delegate_to_healing("database_stop", proof)


def _handle_database_delete(proof: SpindleProof) -> ExecutionResult:
    """DATABASE × DELETE → healing system."""
    return _delegate_to_healing("database_delete", proof)


def _handle_network_repair(proof: SpindleProof) -> ExecutionResult:
    """NETWORK × REPAIR → connectivity diagnostics then healing."""
    try:
        import socket
        socket.create_connection(("127.0.0.1", 5520), timeout=2)
        # ZMQ reachable — problem is upstream, delegate to coordinator
    except OSError:
        logger.warning("[SPINDLE-EXEC] ZMQ endpoint unreachable during network repair")
    return _delegate_to_healing("network_repair", proof)


def _handle_api_repair(proof: SpindleProof) -> ExecutionResult:
    """API × REPAIR → health-check API layer then healing."""
    try:
        from api.brain_api_v2 import call_brain
        health = call_brain("system", "health", {})
        if health.get("ok"):
            return ExecutionResult(
                success=True,
                action_taken="api_repair:already_healthy",
                output=health,
                proof_hash=proof.constraint_hash,
            )
    except Exception:
        pass
    return _delegate_to_healing("api_repair", proof)


def _handle_memory_repair(proof: SpindleProof) -> ExecutionResult:
    """MEMORY × REPAIR → attempt memory mesh reconnect before escalating."""
    try:
        from cognitive.memory.memory_mesh import get_memory_mesh
        mesh = get_memory_mesh()
        mesh.query("spindle_health_check")
        return ExecutionResult(
            success=True,
            action_taken="memory_repair:mesh_healthy",
            output={"note": "Memory mesh responsive, no repair needed"},
            proof_hash=proof.constraint_hash,
        )
    except Exception:
        pass
    return _delegate_to_healing("memory_repair", proof)


def _handle_sys_conf_repair(proof: SpindleProof) -> ExecutionResult:
    """SYS_CONF × REPAIR → HealingCoordinator."""
    return _delegate_to_healing("sys_conf_repair", proof)


def _handle_memory_query(proof: SpindleProof) -> ExecutionResult:
    """MEMORY × QUERY → memory mesh lookup."""
    try:
        from cognitive.memory.memory_mesh import get_memory_mesh
        mesh = get_memory_mesh()
        results = mesh.query("spindle_executor_lookup")
        return ExecutionResult(
            success=True,
            action_taken="memory_mesh:query",
            output=results,
            proof_hash=proof.constraint_hash,
        )
    except Exception as e:
        logger.warning(f"[SPINDLE-EXEC] memory query fallback: {e}")
        return ExecutionResult(
            success=True,
            action_taken="memory_mesh:query:fallback",
            output={"note": "Memory mesh unavailable, query permitted"},
            proof_hash=proof.constraint_hash,
        )


def _delegate_to_healing(action_label: str, proof: SpindleProof) -> ExecutionResult:
    """Common delegation path through HealingCoordinator (full 7-step chain with coding agent)."""
    if not enter_loop("spindle_healing"):
        logger.warning(f"[SPINDLE-EXEC] Circuit breaker tripped — spindle_healing loop for {action_label}")
        return ExecutionResult(
            success=False,
            action_taken=f"circuit_breaker_tripped:{action_label}",
            proof_hash=proof.constraint_hash,
            error="Spindle healing circuit breaker tripped — re-healing loop detected",
        )
    try:
        from cognitive.healing_coordinator import get_coordinator
        coordinator = get_coordinator()
        problem = {
            "component": action_label.replace("_", " "),
            "description": f"Spindle Z3-verified healing request: {action_label}",
            "severity": "high",
            "proof_hash": proof.constraint_hash,
        }
        result = coordinator.resolve(problem)
        resolved = result.get("resolved", False)

        # VVT Pipeline: verify any generated code before accepting
        if resolved and result.get("resolution") in ("coding_agent", "coordinated_fix"):
            code_output = ""
            for step in result.get("steps", []):
                if step.get("step") == "code_fix" and step.get("fix"):
                    code_output = step["fix"] if isinstance(step["fix"], str) else str(step["fix"])
                    break
            if code_output:
                try:
                    from verification.deterministic_vvt_pipeline import vvt_vault
                    vvt_passed = vvt_vault.run_all_layers(
                        code_string=code_output,
                        function_name=action_label,
                    )
                    if not vvt_passed:
                        logger.warning(f"[SPINDLE-EXEC] VVT Pipeline REJECTED code fix for {action_label}")
                        resolved = False
                        result["vvt_rejected"] = True
                        result["vvt_layers"] = [
                            {"layer": r.layer_num, "name": r.layer_name, "passed": r.passed, "error": r.error}
                            for r in vvt_vault.results
                        ]
                    else:
                        logger.info(f"[SPINDLE-EXEC] VVT Pipeline APPROVED code fix for {action_label}")
                        result["vvt_approved"] = True
                except Exception as e:
                    logger.debug(f"[SPINDLE-EXEC] VVT Pipeline unavailable: {e}")

        # Persist coordination result to spindle event store
        try:
            from cognitive.spindle_event_store import get_event_store
            get_event_store().append(
                topic=f"spindle.healing.{action_label}",
                source_type="healing_coordinator",
                payload={
                    "action_label": action_label,
                    "resolved": resolved,
                    "resolution": result.get("resolution"),
                    "steps_count": len(result.get("steps", [])),
                },
                proof_hash=proof.constraint_hash,
                result="RESOLVED" if resolved else "UNRESOLVED",
            )
        except Exception as e:
            logger.debug(f"[SPINDLE-EXEC] event store write after coordination: {e}")

        return ExecutionResult(
            success=resolved,
            action_taken=f"healing_coordinator:{action_label}:{result.get('resolution', 'unresolved')}",
            output=result,
            proof_hash=proof.constraint_hash,
        )
    except Exception as e:
        logger.error(f"[SPINDLE-EXEC] healing coordination failed for {action_label}: {e}")
        # Fallback: direct health assessment if coordinator unavailable
        try:
            from cognitive.autonomous_healing_system import AutonomousHealingSystem
            from db.session import get_session
            with get_session() as session:
                healer = AutonomousHealingSystem(session=session)
                health = healer.assess_system_health()
            return ExecutionResult(
                success=True,
                action_taken=f"healing_system_fallback:{action_label}",
                output=health,
                proof_hash=proof.constraint_hash,
            )
        except Exception as e2:
            logger.error(f"[SPINDLE-EXEC] fallback healing also failed: {e2}")
            return ExecutionResult(
                success=False,
                action_taken=f"healing_system:{action_label}",
                proof_hash=proof.constraint_hash,
                error=f"coordinator: {e}; fallback: {e2}",
            )
    finally:
        exit_loop("spindle_healing")


def _handle_no_op(proof: SpindleProof) -> ExecutionResult:
    """Fallback for domain×intent combos with no specific behaviour."""
    return ExecutionResult(
        success=True,
        action_taken="no_op",
        output={"note": "No specific handler; action verified but no side-effect"},
        proof_hash=proof.constraint_hash,
    )


# ══════════════════════════════════════════════════════════════════════
#  SpindleExecutor
# ══════════════════════════════════════════════════════════════════════

class SpindleExecutor:
    """
    Dispatch table that maps Z3-verified bitmask proofs to callable procedures.

    Usage:
        executor = get_spindle_executor()
        result = executor.execute(proof)
    """

    def __init__(self):
        self.registry = ProcedureRegistry()
        self._pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="spindle-exec")
        self._pending: Dict[str, Any] = {}  # task_id -> result
        self._pending_lock = threading.Lock()
        self._exec_count = 0
        self._exec_success = 0
        self._exec_fail = 0
        self._register_defaults()
        logger.info("[SPINDLE-EXEC] SpindleExecutor initialised with default handlers")

    # ── public API ────────────────────────────────────────────────────

    def register(self, domain: int, intent: int, handler: Callable) -> None:
        """Register (or override) a handler for a domain×intent pair."""
        self.registry.register(domain, intent, handler)

    # Read-only intents that skip checkpoint wrapping
    _READONLY_INTENTS = frozenset({BD.INTENT_QUERY})

    def execute(self, proof: SpindleProof) -> ExecutionResult:
        """Look up and run the handler matching the proof's bitmask."""
        # Circuit breaker: prevent infinite healing loops
        if not enter_loop("spindle_execution"):
            logger.warning("[SPINDLE-EXEC] Circuit breaker tripped — spindle_execution loop depth exceeded")
            try:
                from ml_intelligence.kpi_tracker import get_kpi_tracker
                get_kpi_tracker().increment_kpi("spindle_executor", "circuit_breaker_trips", value=1.0)
            except Exception:
                pass
            return ExecutionResult(
                success=False,
                action_taken="circuit_breaker_tripped",
                proof_hash=proof.constraint_hash,
                error="Spindle execution circuit breaker tripped — possible infinite healing loop",
            )
        try:
            return self._execute_inner(proof)
        finally:
            exit_loop("spindle_execution")

    def _execute_inner(self, proof: SpindleProof) -> ExecutionResult:
        """Inner execution logic, protected by circuit breaker."""
        if not proof.is_valid:
            logger.warning(
                f"[SPINDLE-EXEC] Rejected proof {proof.constraint_hash}: {proof.reason}"
            )
            return ExecutionResult(
                success=False,
                action_taken="rejected",
                proof_hash=proof.constraint_hash,
                error=f"Proof invalid: {proof.reason}",
            )

        handler = self.registry.lookup(proof.domain_mask, proof.intent_mask)
        if handler is None:
            logger.warning(
                f"[SPINDLE-EXEC] No handler for "
                f"(domain={proof.domain_mask:#x}, intent={proof.intent_mask:#x})"
            )
            return ExecutionResult(
                success=False,
                action_taken="no_handler",
                proof_hash=proof.constraint_hash,
                error=(
                    f"No handler registered for "
                    f"(domain={proof.domain_mask:#x}, intent={proof.intent_mask:#x})"
                ),
            )

        # Multi-Model Consensus: require consensus for destructive operations
        _DESTRUCTIVE_INTENTS = frozenset({BD.INTENT_DELETE, BD.INTENT_STOP, BD.INTENT_GRANT})
        if proof.intent_mask in _DESTRUCTIVE_INTENTS:
            try:
                from cognitive.consensus_engine import run_consensus, get_available_models
                component_name = self._mask_to_component_name(proof.domain_mask)
                intent_name = {BD.INTENT_DELETE: "DELETE", BD.INTENT_STOP: "STOP", BD.INTENT_GRANT: "GRANT"}.get(proof.intent_mask, "UNKNOWN")
                # Use all available models: Qwen, Kimi, Opus 4.6, DeepSeek/Reasoning
                available = [m["id"] for m in get_available_models() if m["available"]]
                if not available:
                    available = ["qwen", "reasoning"]  # Minimum fallback
                consensus_result = run_consensus(
                    prompt=f"Should Spindle execute {intent_name} on {component_name}? The action has been Z3-verified as safe. Respond YES or NO with reasoning.",
                    models=available,
                    system_prompt="You are a safety reviewer for the Spindle autonomous runtime. Only approve destructive actions (DELETE/STOP/GRANT) that are clearly safe, necessary, and recoverable.",
                    source="spindle_executor",
                )
                if consensus_result.confidence < 0.5:
                    logger.warning(f"[SPINDLE-EXEC] Consensus REJECTED destructive action {intent_name} on {component_name} (confidence={consensus_result.confidence:.2f})")
                    try:
                        from ml_intelligence.kpi_tracker import get_kpi_tracker
                        get_kpi_tracker().increment_kpi("spindle_executor", "consensus_rejections", value=1.0,
                                                         metadata={"intent": intent_name, "component": component_name, "confidence": consensus_result.confidence})
                    except Exception:
                        pass
                    return ExecutionResult(
                        success=False,
                        action_taken=f"consensus_rejected:{intent_name}:{component_name}",
                        proof_hash=proof.constraint_hash,
                        error=f"Multi-model consensus rejected destructive action (confidence={consensus_result.confidence:.2f})",
                    )
                logger.info(f"[SPINDLE-EXEC] Consensus APPROVED destructive action {intent_name} on {component_name}")
            except Exception as e:
                logger.debug(f"[SPINDLE-EXEC] Consensus engine unavailable for destructive check: {e}")

        is_mutating = proof.intent_mask not in self._READONLY_INTENTS
        t0 = time.perf_counter()
        try:
            if is_mutating:
                mgr = get_checkpoint_manager()
                component = self._mask_to_component_name(proof.domain_mask)
                with mgr.checkpoint(component, proof.constraint_hash):
                    result = handler(proof)
            else:
                result = handler(proof)
        except Exception as e:
            logger.error(f"[SPINDLE-EXEC] Handler crashed: {e}", exc_info=True)
            result = ExecutionResult(
                success=False,
                action_taken="handler_crash",
                proof_hash=proof.constraint_hash,
                error=str(e),
            )
        result.duration_ms = (time.perf_counter() - t0) * 1000
        result.proof_hash = result.proof_hash or proof.constraint_hash

        self._exec_count += 1
        if result.success:
            self._exec_success += 1
        else:
            self._exec_fail += 1

        # KPI Tracking: record execution metrics for trust scoring
        try:
            from ml_intelligence.kpi_tracker import get_kpi_tracker
            tracker = get_kpi_tracker()
            component = self._mask_to_component_name(proof.domain_mask)
            tracker.increment_kpi("spindle_executor", "executions", value=1.0)
            tracker.increment_kpi("spindle_executor", "success" if result.success else "failure", value=1.0)
            tracker.increment_kpi(f"spindle_{component}", "executions", value=1.0)
            tracker.increment_kpi(f"spindle_{component}", "success" if result.success else "failure", value=1.0,
                                  metadata={"action": result.action_taken, "proof_hash": proof.constraint_hash, "duration_ms": result.duration_ms})
        except Exception:
            pass

        logger.info(
            f"[SPINDLE-EXEC] Executed {result.action_taken} "
            f"({result.duration_ms:.1f}ms, success={result.success})"
        )

        # Unified Memory: store every execution as an episode + learning example
        try:
            from cognitive.unified_memory import get_unified_memory
            mem = get_unified_memory()
            mem.store_episode(
                problem=f"Spindle execution: domain={proof.domain_mask:#x} intent={proof.intent_mask:#x}",
                action=result.action_taken,
                outcome=f"{'success' if result.success else 'failure'}: {result.error or result.action_taken}",
                trust=0.9 if result.success else 0.3,
                source="spindle_executor",
            )
            if not result.success:
                mem.store_learning(
                    input_ctx=f"Spindle {self._mask_to_component_name(proof.domain_mask)} action failed: {result.action_taken}",
                    expected="successful execution",
                    actual=result.error or "unknown failure",
                    trust=0.3,
                    source="spindle_executor",
                    example_type="spindle_failure",
                )
        except Exception as e:
            logger.debug(f"[SPINDLE-EXEC] Unified memory write failed: {e}")

        # Genesis Key: mint immutable provenance record for every execution
        try:
            from genesis.genesis_key_service import GenesisKeyService
            from models.genesis_key_models import GenesisKeyType
            gks = GenesisKeyService()
            gks.create_key(
                key_type=GenesisKeyType.SYSTEM_EVENT,
                what_description=f"Spindle execution: {result.action_taken}",
                who_actor="spindle_executor",
                where_location="cognitive.spindle_executor",
                why_reason=f"Z3-verified action (proof={proof.constraint_hash})",
                how_method="spindle_gate→z3_proof→executor",
                input_data=proof.to_dict(),
                output_data={"success": result.success, "action": result.action_taken, "duration_ms": result.duration_ms},
                tags=["spindle", "z3_verified", "execution", "success" if result.success else "failure"],
            )
        except Exception as e:
            logger.debug(f"[SPINDLE-EXEC] Genesis key minting failed: {e}")

        return result

    # ── async / background API ──────────────────────────────────────

    async def execute_async(self, proof: SpindleProof) -> ExecutionResult:
        """Async version — runs handler in thread pool to avoid blocking event loop."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._pool, self.execute, proof)

    def submit(self, proof: SpindleProof) -> str:
        """Submit proof for background execution. Returns task_id."""
        task_id = f"EXEC-{int(time.time()*1000)}-{proof.constraint_hash[:6]}"
        with self._pending_lock:
            self._pending[task_id] = None  # Mark pending BEFORE submitting
        def _worker():
            result = self.execute(proof)
            with self._pending_lock:
                self._pending[task_id] = result
        self._pool.submit(_worker)
        return task_id

    def get_result(self, task_id: str) -> Optional[ExecutionResult]:
        """Check result of a submitted task. None if still pending."""
        with self._pending_lock:
            return self._pending.get(task_id)

    @property
    def stats(self) -> Dict[str, Any]:
        """Return execution statistics."""
        with self._pending_lock:
            pending_count = sum(1 for v in self._pending.values() if v is None)
        return {
            "total_executions": self._exec_count,
            "successful": self._exec_success,
            "failed": self._exec_fail,
            "pending": pending_count,
            "registered_handlers": len(self.registry.all_keys()),
        }

    def shutdown(self):
        """Shut down the thread pool."""
        self._pool.shutdown(wait=False)

    @staticmethod
    def _mask_to_component_name(domain_mask: int) -> str:
        """Map a domain bitmask to a human-readable component name."""
        _MAP = {
            BD.DOMAIN_DATABASE: "database",
            BD.DOMAIN_API:      "api",
            BD.DOMAIN_MEMORY:   "memory",
            BD.DOMAIN_NETWORK:  "network",
            BD.DOMAIN_SYS_CONF: "sys_conf",
        }
        return _MAP.get(domain_mask, f"unknown_{domain_mask:#x}")

    # ── default registration ──────────────────────────────────────────

    def _register_defaults(self):
        """Wire up all BrailleDictionary domain×intent combos to handlers."""
        domains = [
            BD.DOMAIN_DATABASE,
            BD.DOMAIN_API,
            BD.DOMAIN_MEMORY,
            BD.DOMAIN_NETWORK,
            BD.DOMAIN_SYS_CONF,
        ]
        intents = [
            BD.INTENT_START,
            BD.INTENT_STOP,
            BD.INTENT_DELETE,
            BD.INTENT_QUERY,
            BD.INTENT_GRANT,
            BD.INTENT_REPAIR,
        ]

        # Specific handlers
        specific: Dict[Tuple[int, int], Callable] = {
            (BD.DOMAIN_DATABASE, BD.INTENT_REPAIR): _handle_database_repair,
            (BD.DOMAIN_DATABASE, BD.INTENT_QUERY):  _handle_database_query,
            (BD.DOMAIN_DATABASE, BD.INTENT_START):  _handle_database_start,
            (BD.DOMAIN_DATABASE, BD.INTENT_STOP):   _handle_database_stop,
            (BD.DOMAIN_DATABASE, BD.INTENT_DELETE):  _handle_database_delete,
            (BD.DOMAIN_NETWORK,  BD.INTENT_REPAIR):  _handle_network_repair,
            (BD.DOMAIN_API,      BD.INTENT_REPAIR):  _handle_api_repair,
            (BD.DOMAIN_MEMORY,   BD.INTENT_REPAIR):  _handle_memory_repair,
            (BD.DOMAIN_SYS_CONF, BD.INTENT_REPAIR):  _handle_sys_conf_repair,
            (BD.DOMAIN_MEMORY,   BD.INTENT_QUERY):   _handle_memory_query,
        }

        for d in domains:
            for i in intents:
                handler = specific.get((d, i), _handle_no_op)
                self.registry.register(d, i, handler)


# ══════════════════════════════════════════════════════════════════════
#  Module-level singleton
# ══════════════════════════════════════════════════════════════════════

_instance: Optional[SpindleExecutor] = None


def get_spindle_executor() -> SpindleExecutor:
    """Return (or create) the singleton SpindleExecutor."""
    global _instance
    if _instance is None:
        _instance = SpindleExecutor()
    return _instance
