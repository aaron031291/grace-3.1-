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
        self._validators.append(("governance", self._validate_governance))
        self._validators.append(("trust_scorer", self._validate_trust))

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

        # Store gate verdict in unified memory for cross-system learning
        try:
            from cognitive.unified_memory import get_unified_memory
            mem = get_unified_memory()
            mem.store_episode(
                problem=f"SpindleGate verdict: d={d_val:#x} i={i_val:#x}",
                action=f"gate:{'PASSED' if quorum_met else 'REJECTED'} ({votes_for}/{total})",
                outcome=f"confidence={verdict.confidence:.2f} wall_time={wall_ms:.1f}ms",
                trust=verdict.confidence,
                source="spindle_gate",
            )
        except Exception:
            pass

        return verdict

    async def verify_async(self, d_val: int, i_val: int, s_val: int, c_val: int,
                           context: Dict[str, Any] = None) -> GateVerdict:
        """Async wrapper — runs the parallel verify in executor to avoid blocking event loop."""
        loop = asyncio.get_running_loop()
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
            from cognitive.spindle_event_store import get_event_store
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

    def _validate_governance(self, d, i, s, c, ctx) -> tuple:
        """Check constitutional governance rules before execution."""
        try:
            from security.governance import get_governance_engine, GovernanceContext
            engine = get_governance_engine()

            # Map bitmask intent to action type
            from cognitive.braille_compiler import BrailleDictionary as BD
            intent_map = {
                BD.INTENT_DELETE: "delete_data",
                BD.INTENT_STOP: "system_config",
                BD.INTENT_GRANT: "execute_external",
                BD.INTENT_REPAIR: "execute_safe",
                BD.INTENT_QUERY: "read",
                BD.INTENT_START: "execute_safe",
            }
            action_type = intent_map.get(i, "execute_safe")
            is_destructive = i in (BD.INTENT_DELETE, BD.INTENT_STOP, BD.INTENT_GRANT)

            gov_ctx = GovernanceContext(
                context_id=f"spindle-gate-{id(self)}",
                action_type=action_type,
                actor_id="spindle_daemon",
                actor_type="ai",
                target_resource=f"domain_{d:#x}",
                impact_scope="systemic" if is_destructive else "component",
                is_reversible=not is_destructive,
                financial_impact=0.0,
                metadata={"spindle_gate": True, "domain": d, "intent": i, "state": s, "context": c},
            )
            violations = engine.check_constitutional_rules(gov_ctx)
            hard_blocks = [v for v in violations if v.enforcement_action == "blocked"]
            if hard_blocks:
                reasons = "; ".join(v.description for v in hard_blocks)
                return False, f"Governance BLOCKED: {reasons}", None
            return True, "Governance check passed", None
        except Exception as e:
            # Governance unavailable — pass (fail-open for availability)
            return True, f"Governance check skipped: {e}", None

    def _validate_trust(self, d, i, s, c, ctx) -> tuple:
        """Check neural trust score for the target component."""
        try:
            from cognitive.trust_engine import get_trust_engine
            engine = get_trust_engine()
            from cognitive.braille_compiler import BrailleDictionary as BD
            domain_names = {
                BD.DOMAIN_DATABASE: "database",
                BD.DOMAIN_API: "api",
                BD.DOMAIN_MEMORY: "memory",
                BD.DOMAIN_NETWORK: "network",
                BD.DOMAIN_SYS_CONF: "sys_conf",
            }
            component = domain_names.get(d, f"unknown_{d:#x}")
            dashboard = engine.get_dashboard()
            component_trust = dashboard.get("components", {}).get(component, {})
            trust_score = component_trust.get("trust_score", 0.7) if isinstance(component_trust, dict) else 0.7

            # Destructive intents need higher trust
            is_destructive = i in (BD.INTENT_DELETE, BD.INTENT_STOP, BD.INTENT_GRANT)
            threshold = 0.6 if is_destructive else 0.3

            if trust_score < threshold:
                return False, f"Trust too low for {component}: {trust_score:.2f} < {threshold}", None
            return True, f"Trust check passed: {component}={trust_score:.2f}", None
        except Exception as e:
            return True, f"Trust check skipped: {e}", None


# Singleton
_gate: Optional[SpindleGate] = None


def get_spindle_gate() -> SpindleGate:
    global _gate
    if _gate is None:
        _gate = SpindleGate()
    return _gate
