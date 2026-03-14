"""
Spindle Gate — Multi-validator consensus for formal verification.
Runs the base Z3 geometry check + additional constraint validators.
Requires quorum (majority) to pass.
"""
import logging
import time
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ValidatorResult:
    """Result from a single validator in the gate."""
    validator_name: str
    passed: bool
    reason: str
    duration_ms: float = 0.0


@dataclass
class GateVerdict:
    """Aggregate verdict from all validators."""
    passed: bool
    quorum_met: bool
    votes_for: int
    votes_against: int
    total_validators: int
    validator_results: List[ValidatorResult] = field(default_factory=list)
    proof: Optional[Any] = None  # SpindleProof

    @property
    def confidence(self) -> float:
        if self.total_validators == 0:
            return 0.0
        return self.votes_for / self.total_validators


class SpindleGate:
    """
    Multi-validator consensus gate for Spindle verification.
    Validators vote SAT/UNSAT. Action passes only if quorum is met.
    """

    def __init__(self, quorum_ratio: float = 0.5):
        self.quorum_ratio = quorum_ratio  # Fraction needed to pass (0.5 = majority)
        self._validators: List[tuple] = []  # (name, callable)
        self._register_default_validators()

    def _register_default_validators(self):
        """Register the built-in validators."""
        # V1: Base Z3 geometry (the core physics rules)
        self._validators.append(("z3_geometry", self._validate_z3_geometry))
        # V2: Privilege escalation check
        self._validators.append(("privilege_check", self._validate_privilege))
        # V3: Rate limiting / duplicate action check
        self._validators.append(("rate_limiter", self._validate_rate_limit))

    def add_validator(self, name: str, validator: Callable):
        """Add a custom validator to the gate."""
        self._validators.append((name, validator))

    def verify(self, d_val: int, i_val: int, s_val: int, c_val: int,
               context: Dict[str, Any] = None) -> GateVerdict:
        """
        Run all validators and return aggregate verdict.
        """
        context = context or {}
        results = []
        votes_for = 0
        votes_against = 0
        proof = None

        for name, validator in self._validators:
            start = time.time()
            try:
                passed, reason, extra = validator(d_val, i_val, s_val, c_val, context)
                duration = (time.time() - start) * 1000

                if name == "z3_geometry" and extra:
                    proof = extra  # Capture the SpindleProof from the primary validator

                results.append(ValidatorResult(
                    validator_name=name,
                    passed=passed,
                    reason=reason,
                    duration_ms=duration,
                ))

                if passed:
                    votes_for += 1
                else:
                    votes_against += 1

            except Exception as e:
                duration = (time.time() - start) * 1000
                results.append(ValidatorResult(
                    validator_name=name,
                    passed=False,
                    reason=f"Validator crashed: {str(e)[:100]}",
                    duration_ms=duration,
                ))
                votes_against += 1

        total = len(self._validators)
        quorum_needed = max(1, int(total * self.quorum_ratio) + 1)
        quorum_met = votes_for >= quorum_needed

        verdict = GateVerdict(
            passed=quorum_met,
            quorum_met=quorum_met,
            votes_for=votes_for,
            votes_against=votes_against,
            total_validators=total,
            validator_results=results,
            proof=proof,
        )

        if quorum_met:
            logger.info(f"[GATE] PASSED {votes_for}/{total} validators (quorum={quorum_needed})")
        else:
            logger.warning(f"[GATE] REJECTED {votes_for}/{total} validators (quorum={quorum_needed})")

        return verdict

    # ── Default Validators ──────────────────────────────────

    def _validate_z3_geometry(self, d, i, s, c, ctx) -> tuple:
        """Primary Z3 SMT verification."""
        from cognitive.physics.bitmask_geometry import HierarchicalZ3Geometry
        geom = HierarchicalZ3Geometry()
        proof = geom.verify_action(d, i, s, c)
        return proof.is_valid, proof.reason, proof

    def _validate_privilege(self, d, i, s, c, ctx) -> tuple:
        """Check that privilege level is appropriate for the action."""
        PRIV_GUEST = 1 << 27
        INTENT_DELETE = 1 << 10
        INTENT_GRANT = 1 << 12

        # Guests cannot delete or grant
        if (c & PRIV_GUEST) and (i & (INTENT_DELETE | INTENT_GRANT)):
            return False, "Guest privilege cannot perform destructive actions", None
        return True, "Privilege check passed", None

    def _validate_rate_limit(self, d, i, s, c, ctx) -> tuple:
        """Basic rate limiting — prevent action storms."""
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
            pass  # If store unavailable, don't block

        return True, "Rate limit check passed", None


# Singleton
_gate: Optional[SpindleGate] = None


def get_spindle_gate() -> SpindleGate:
    global _gate
    if _gate is None:
        _gate = SpindleGate()
    return _gate
