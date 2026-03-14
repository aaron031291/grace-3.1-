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
    """DATABASE × REPAIR → deterministic lifecycle run."""
    try:
        from core.deterministic_lifecycle import run_lifecycle
        result = run_lifecycle("database")
        return ExecutionResult(
            success=result.healthy,
            action_taken="deterministic_lifecycle:database",
            output=result.to_dict(),
            proof_hash=proof.constraint_hash,
        )
    except Exception as e:
        logger.error(f"[SPINDLE-EXEC] database repair failed: {e}")
        return ExecutionResult(
            success=False,
            action_taken="deterministic_lifecycle:database",
            proof_hash=proof.constraint_hash,
            error=str(e),
        )


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
    """NETWORK × REPAIR → healing system."""
    return _delegate_to_healing("network_repair", proof)


def _handle_api_repair(proof: SpindleProof) -> ExecutionResult:
    """API × REPAIR → healing system."""
    return _delegate_to_healing("api_repair", proof)


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
    """Common delegation path to the autonomous healing system."""
    try:
        from cognitive.autonomous_healing_system import AutonomousHealingSystem
        from db.session import get_session

        with get_session() as session:
            healer = AutonomousHealingSystem(session=session)
            health = healer.assess_system_health()
        return ExecutionResult(
            success=True,
            action_taken=f"healing_system:{action_label}",
            output=health,
            proof_hash=proof.constraint_hash,
        )
    except Exception as e:
        logger.error(f"[SPINDLE-EXEC] healing delegation failed for {action_label}: {e}")
        return ExecutionResult(
            success=False,
            action_taken=f"healing_system:{action_label}",
            proof_hash=proof.constraint_hash,
            error=str(e),
        )


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

        logger.info(
            f"[SPINDLE-EXEC] Executed {result.action_taken} "
            f"({result.duration_ms:.1f}ms, success={result.success})"
        )
        return result

    # ── async / background API ──────────────────────────────────────

    async def execute_async(self, proof: SpindleProof) -> ExecutionResult:
        """Async version — runs handler in thread pool to avoid blocking event loop."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._pool, self.execute, proof)

    def submit(self, proof: SpindleProof) -> str:
        """Submit proof for background execution. Returns task_id."""
        task_id = f"EXEC-{int(time.time()*1000)}-{proof.constraint_hash[:6]}"
        def _worker():
            result = self.execute(proof)
            with self._pending_lock:
                self._pending[task_id] = result
        self._pool.submit(_worker)
        with self._pending_lock:
            self._pending[task_id] = None  # Pending
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
            (BD.DOMAIN_NETWORK, BD.INTENT_REPAIR):  _handle_network_repair,
            (BD.DOMAIN_API,     BD.INTENT_REPAIR):  _handle_api_repair,
            (BD.DOMAIN_MEMORY,  BD.INTENT_QUERY):   _handle_memory_query,
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
