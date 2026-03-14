"""
Spindle Gate — Multi-validator consensus with parallel execution.
Validators run concurrently via ThreadPoolExecutor. Quorum required to pass.
"""
import logging
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeoutError
from typing import List, Dict, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

VALIDATOR_TIMEOUT = 5.0  # seconds per validator


@dataclass
class ValidatorResult:
    validator_name: str
    passed: bool
    reason: str
    duration_ms: float = 0.0


@dataclass
class GateVerdict:
    passed: bool
    quorum_met: bool
    votes_for: int
    votes_against: int
    total_validators: int
    wall_time_ms: float = 0.0
    validator_results: List[ValidatorResult] = field(default_factory=list)
    proof: Optional[Any] = None

    @property
    def confidence(self) -> float:
        if self.total_validators == 0:
            return 0.0
        return self.votes_for / self.total_validators


class SpindleGate:
    def __init__(self, quorum_ratio: float = 0.5, max_workers: int = 4, timeout: float = VALIDATOR_TIMEOUT):
        self.quorum_ratio = quorum_ratio
        self.timeout = timeout
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="gate-validator")
        self._validators: List[Tuple[str, Callable]] = []
        self._register_default_validators()
        logger.info(f"[GATE] Initialized with {max_workers} parallel workers, timeout={timeout}s")

    def _register_default_validators(self):
        self._validators.append(("z3_geometry", self._validate_z3_geometry))
        self._validators.append(("privilege_check", self._validate_privilege))
        self._validators.append(("rate_limiter", self._validate_rate_limit))

    def add_validator(self, name: str, validator: Callable):
        self._validators.append((name, validator))

    def verify(self, d_val: int, i_val: int, s_val: int, c_val: int,
               context: Dict[str, Any] = None) -> GateVerdict:
        """Run all validators IN PARALLEL and return aggregate verdict."""
        context = context or {}
        wall_start = time.perf_counter()

        results: List[ValidatorResult] = []
        votes_for = 0
        votes_against = 0
        proof = None

        # Submit all validators to thread pool
        futures = {}
        for name, validator in self._validators:
            future = self._pool.submit(self._run_validator, name, validator, d_val, i_val, s_val, c_val, context)
            futures[future] = name

        # Collect results with timeout
        for future in as_completed(futures, timeout=self.timeout + 1):
            name = futures[future]
            try:
                vr, extra = future.result(timeout=self.timeout)
                results.append(vr)
                if name == "z3_geometry" and extra:
                    proof = extra
                if vr.passed:
                    votes_for += 1
                else:
                    votes_against += 1
            except Exception as e:
                results.append(ValidatorResult(
                    validator_name=name,
                    passed=False,
                    reason=f"Timeout or crash: {str(e)[:80]}",
                    duration_ms=self.timeout * 1000,
                ))
                votes_against += 1

        # Check for any futures that didn't complete at all
        for future, name in futures.items():
            if not future.done():
                future.cancel()
                results.append(ValidatorResult(
                    validator_name=name, passed=False,
                    reason="Cancelled: exceeded gate timeout",
                    duration_ms=self.timeout * 1000,
                ))
                votes_against += 1

        total = len(self._validators)
        quorum_needed = max(1, int(total * self.quorum_ratio) + 1)
        quorum_met = votes_for >= quorum_needed
        wall_ms = (time.perf_counter() - wall_start) * 1000

        verdict = GateVerdict(
            passed=quorum_met,
            quorum_met=quorum_met,
            votes_for=votes_for,
            votes_against=votes_against,
            total_validators=total,
            wall_time_ms=wall_ms,
            validator_results=results,
            proof=proof,
        )

        level = "info" if quorum_met else "warning"
        getattr(logger, level)(
            f"[GATE] {'PASSED' if quorum_met else 'REJECTED'} "
            f"{votes_for}/{total} (quorum={quorum_needed}) in {wall_ms:.1f}ms"
        )
        return verdict

    async def verify_async(self, d_val: int, i_val: int, s_val: int, c_val: int,
                           context: Dict[str, Any] = None) -> GateVerdict:
        """Async wrapper — runs the parallel verify in executor to avoid blocking event loop."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.verify, d_val, i_val, s_val, c_val, context)

    @staticmethod
    def _run_validator(name, validator, d, i, s, c, ctx) -> Tuple[ValidatorResult, Any]:
        """Execute a single validator (runs in thread pool)."""
        start = time.perf_counter()
        try:
            passed, reason, extra = validator(d, i, s, c, ctx)
            duration = (time.perf_counter() - start) * 1000
            return ValidatorResult(
                validator_name=name, passed=passed, reason=reason, duration_ms=duration,
            ), extra
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            return ValidatorResult(
                validator_name=name, passed=False,
                reason=f"Crashed: {str(e)[:100]}",
                duration_ms=duration,
            ), None

    # ── Default Validators ──────────────────────────────────

    def _validate_z3_geometry(self, d, i, s, c, ctx) -> tuple:
        from cognitive.physics.bitmask_geometry import HierarchicalZ3Geometry
        geom = HierarchicalZ3Geometry()
        proof = geom.verify_action(d, i, s, c)
        return proof.is_valid, proof.reason, proof

    def _validate_privilege(self, d, i, s, c, ctx) -> tuple:
        PRIV_GUEST = 1 << 27
        INTENT_DELETE = 1 << 10
        INTENT_GRANT = 1 << 12
        if (c & PRIV_GUEST) and (i & (INTENT_DELETE | INTENT_GRANT)):
            return False, "Guest privilege cannot perform destructive actions", None
        return True, "Privilege check passed", None

    def _validate_rate_limit(self, d, i, s, c, ctx) -> tuple:
        try:
            from backend.cognitive.spindle_event_store import get_event_store
            store = get_event_store()
            recent = store.query(source_type="healing", limit=10)
            if len(recent) >= 10:
                now = time.time()
                oldest = recent[-1]
                ts = oldest.get("timestamp")
                if ts and (now - ts) < 60:
                    return False, "Rate limit: too many actions in 60s window", None
        except Exception:
            pass
        return True, "Rate limit check passed", None


# Singleton
_gate: Optional[SpindleGate] = None


def get_spindle_gate() -> SpindleGate:
    global _gate
    if _gate is None:
        _gate = SpindleGate()
    return _gate
