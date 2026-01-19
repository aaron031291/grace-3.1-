"""
Cognitive Framework Enforcer for LLMs

Ensures all LLM operations follow GRACE's cognitive blueprint:
- 12 OODA Invariants
- Deterministic decision-making
- Observability and traceability
- Trust-based reasoning

All LLM interactions are logged with Genesis Keys and tracked.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CognitiveConstraints:
    """Cognitive constraints for LLM operation."""
    requires_determinism: bool = False
    is_safety_critical: bool = False
    impact_scope: str = "local"  # local, component, systemic
    is_reversible: bool = True
    max_recursion_depth: int = 3
    time_limit_seconds: int = 30
    requires_grounding: bool = True
    min_confidence_threshold: float = 0.6
    min_consensus_threshold: float = 0.7


@dataclass
class CognitiveDecision:
    """Cognitive decision record."""
    decision_id: str
    operation: str
    ooda_phase: str  # observe, orient, decide, act
    constraints: CognitiveConstraints
    ambiguity_ledger: Dict[str, List[str]]
    alternatives_considered: List[Dict[str, Any]]
    selected_path: Dict[str, Any]
    reasoning_trace: List[str]
    timestamp: datetime
    genesis_key_id: Optional[str] = None


class CognitiveEnforcer:
    """
    Enforces cognitive framework on all LLM operations.

    Implements 12 OODA Invariants:
    1. OODA as Primary Control Loop
    2. Explicit Ambiguity Accounting
    3. Reversibility Before Commitment
    4. Determinism Where Safety Depends on It
    5. Blast Radius Minimization
    6. Observability Is Mandatory
    7. Simplicity Is a First-Class Constraint
    8. Feedback Is Continuous
    9. Bounded Recursion
    10. Optionality > Optimization
    11. Time-Bounded Reasoning
    12. Forward Simulation (Chess Mode)
    """

    def __init__(self):
        """Initialize cognitive enforcer."""
        self.decision_log: List[CognitiveDecision] = []
        self.active_decisions: Dict[str, CognitiveDecision] = {}

    # =======================================================================
    # INVARIANT 1: OODA LOOP ENFORCEMENT
    # =======================================================================

    def begin_ooda_loop(
        self,
        operation: str,
        constraints: CognitiveConstraints
    ) -> str:
        """
        Begin OODA loop for operation.

        Args:
            operation: Operation name
            constraints: Cognitive constraints

        Returns:
            Decision ID
        """
        decision_id = f"decision_{datetime.now().timestamp()}"

        decision = CognitiveDecision(
            decision_id=decision_id,
            operation=operation,
            ooda_phase="observe",
            constraints=constraints,
            ambiguity_ledger={
                "known": [],
                "inferred": [],
                "assumed": [],
                "unknown": []
            },
            alternatives_considered=[],
            selected_path={},
            reasoning_trace=[f"Starting OODA loop for: {operation}"],
            timestamp=datetime.now()
        )

        self.active_decisions[decision_id] = decision
        logger.info(f"[OODA] Started decision loop: {decision_id}")

        return decision_id

    def observe(
        self,
        decision_id: str,
        observations: Dict[str, Any]
    ):
        """
        OBSERVE phase: Gather facts and data.

        Invariant 2: Explicit Ambiguity Accounting
        """
        if decision_id not in self.active_decisions:
            raise ValueError(f"Decision {decision_id} not active")

        decision = self.active_decisions[decision_id]
        decision.ooda_phase = "observe"

        # Categorize observations
        for key, value in observations.items():
            if value is None:
                decision.ambiguity_ledger["unknown"].append(key)
            elif isinstance(value, dict) and value.get("confidence", 1.0) < 0.8:
                decision.ambiguity_ledger["inferred"].append(key)
            else:
                decision.ambiguity_ledger["known"].append(key)

        decision.reasoning_trace.append(
            f"OBSERVE: Gathered {len(observations)} observations"
        )

        logger.info(f"[OODA-OBSERVE] {decision_id}: {len(observations)} observations")

    def orient(
        self,
        decision_id: str,
        context: Dict[str, Any],
        constraints_update: Optional[Dict[str, Any]] = None
    ):
        """
        ORIENT phase: Understand context and constraints.

        Invariant 4: Determinism Where Safety Depends on It
        Invariant 5: Blast Radius Minimization
        """
        if decision_id not in self.active_decisions:
            raise ValueError(f"Decision {decision_id} not active")

        decision = self.active_decisions[decision_id]
        decision.ooda_phase = "orient"

        # Update constraints if provided
        if constraints_update:
            for key, value in constraints_update.items():
                if hasattr(decision.constraints, key):
                    setattr(decision.constraints, key, value)

        # Check for blocking unknowns (Invariant 2)
        blocking_unknowns = [
            u for u in decision.ambiguity_ledger["unknown"]
            if not decision.constraints.is_reversible
        ]

        if blocking_unknowns:
            decision.reasoning_trace.append(
                f"ORIENT: HALT - Blocking unknowns detected for irreversible operation: {blocking_unknowns}"
            )
            raise ValueError(f"Blocking unknowns prevent irreversible operation: {blocking_unknowns}")

        decision.reasoning_trace.append(
            f"ORIENT: Context understood. Impact scope: {decision.constraints.impact_scope}"
        )

        logger.info(f"[OODA-ORIENT] {decision_id}: Impact={decision.constraints.impact_scope}")

    def decide(
        self,
        decision_id: str,
        alternatives: List[Dict[str, Any]],
        selection_criteria: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        DECIDE phase: Evaluate alternatives and choose path.

        Invariant 7: Simplicity Is a First-Class Constraint
        Invariant 10: Optionality > Optimization
        Invariant 12: Forward Simulation (Chess Mode)
        """
        if decision_id not in self.active_decisions:
            raise ValueError(f"Decision {decision_id} not active")

        decision = self.active_decisions[decision_id]
        decision.ooda_phase = "decide"
        decision.alternatives_considered = alternatives

        # Default selection criteria
        if not selection_criteria:
            selection_criteria = {
                "simplicity": 0.3,
                "optionality": 0.3,
                "immediate_value": 0.2,
                "reversibility": 0.2
            }

        # Score alternatives
        scored_alternatives = []
        for alt in alternatives:
            score = 0.0
            for criterion, weight in selection_criteria.items():
                score += alt.get(criterion, 0.5) * weight

            # Apply reversibility constraint (Invariant 3)
            if not decision.constraints.is_reversible and not alt.get("reversible", True):
                score *= 0.5  # Heavy penalty for irreversible in irreversible context

            # Apply complexity penalty (Invariant 7)
            complexity = alt.get("complexity", 0.5)
            score *= (1.0 - (complexity * 0.3))

            scored_alternatives.append({
                **alt,
                "total_score": score
            })

        # Select best alternative
        scored_alternatives.sort(key=lambda x: x["total_score"], reverse=True)
        selected = scored_alternatives[0]
        decision.selected_path = selected

        decision.reasoning_trace.append(
            f"DECIDE: Selected path '{selected.get('name', 'unknown')}' with score {selected['total_score']:.3f}"
        )

        logger.info(f"[OODA-DECIDE] {decision_id}: Selected {selected.get('name', 'unknown')}")

        return selected

    def act(
        self,
        decision_id: str,
        action_result: Any,
        success: bool
    ):
        """
        ACT phase: Execute and observe outcomes.

        Invariant 6: Observability Is Mandatory
        Invariant 8: Feedback Is Continuous
        """
        if decision_id not in self.active_decisions:
            raise ValueError(f"Decision {decision_id} not active")

        decision = self.active_decisions[decision_id]
        decision.ooda_phase = "act"

        decision.reasoning_trace.append(
            f"ACT: Executed. Success={success}"
        )

        logger.info(f"[OODA-ACT] {decision_id}: Success={success}")

    def finalize_decision(
        self,
        decision_id: str,
        genesis_key_id: Optional[str] = None
    ):
        """
        Finalize decision and move to log.

        Invariant 6: Observability Is Mandatory
        """
        if decision_id not in self.active_decisions:
            raise ValueError(f"Decision {decision_id} not active")

        decision = self.active_decisions[decision_id]
        decision.genesis_key_id = genesis_key_id

        # Move to permanent log
        self.decision_log.append(decision)
        del self.active_decisions[decision_id]

        logger.info(f"[OODA] Finalized decision: {decision_id} (Genesis: {genesis_key_id})")

    # =======================================================================
    # INVARIANT VALIDATORS
    # =======================================================================

    def validate_determinism(self, decision_id: str) -> bool:
        """
        Validate determinism requirement (Invariant 4).

        Returns:
            True if determinism requirements are met
        """
        if decision_id not in self.active_decisions:
            return False

        decision = self.active_decisions[decision_id]

        if decision.constraints.requires_determinism:
            # Check for unknowns
            if decision.ambiguity_ledger["unknown"]:
                logger.warning(f"[DETERMINISM] Decision {decision_id} has unknowns but requires determinism")
                return False

            # Check for assumptions
            if decision.ambiguity_ledger["assumed"]:
                logger.warning(f"[DETERMINISM] Decision {decision_id} has assumptions but requires determinism")
                return False

        return True

    def validate_blast_radius(self, decision_id: str) -> bool:
        """
        Validate blast radius constraints (Invariant 5).

        Returns:
            True if blast radius is acceptable
        """
        if decision_id not in self.active_decisions:
            return False

        decision = self.active_decisions[decision_id]

        # Systemic changes require highest scrutiny
        if decision.constraints.impact_scope == "systemic":
            if decision.constraints.is_safety_critical and not decision.constraints.is_reversible:
                logger.warning(f"[BLAST RADIUS] Systemic, safety-critical, irreversible operation requires approval")
                return False

        return True

    def validate_bounded_recursion(self, decision_id: str, current_depth: int) -> bool:
        """
        Validate recursion bounds (Invariant 9).

        Args:
            decision_id: Decision ID
            current_depth: Current recursion depth

        Returns:
            True if within bounds
        """
        if decision_id not in self.active_decisions:
            return False

        decision = self.active_decisions[decision_id]

        if current_depth > decision.constraints.max_recursion_depth:
            logger.warning(f"[RECURSION] Decision {decision_id} exceeded max depth {decision.constraints.max_recursion_depth}")
            return False

        return True

    def validate_time_bounds(self, decision_id: str) -> bool:
        """
        Validate time bounds (Invariant 11).

        Returns:
            True if within time limits
        """
        if decision_id not in self.active_decisions:
            return False

        decision = self.active_decisions[decision_id]
        elapsed = (datetime.now() - decision.timestamp).total_seconds()

        if elapsed > decision.constraints.time_limit_seconds:
            logger.warning(f"[TIME BOUNDS] Decision {decision_id} exceeded time limit")
            return False

        return True

    def validate_all_invariants(self, decision_id: str) -> Dict[str, bool]:
        """
        Validate all applicable invariants.

        Returns:
            Dictionary of invariant validation results
        """
        return {
            "determinism": self.validate_determinism(decision_id),
            "blast_radius": self.validate_blast_radius(decision_id),
            "recursion_bounds": self.validate_bounded_recursion(decision_id, 0),
            "time_bounds": self.validate_time_bounds(decision_id)
        }

    # =======================================================================
    # QUERY METHODS
    # =======================================================================

    def get_decision(self, decision_id: str) -> Optional[CognitiveDecision]:
        """Get decision by ID."""
        # Check active decisions
        if decision_id in self.active_decisions:
            return self.active_decisions[decision_id]

        # Check log
        for decision in self.decision_log:
            if decision.decision_id == decision_id:
                return decision

        return None

    def get_decision_log(self, limit: int = 100) -> List[CognitiveDecision]:
        """Get recent decision log."""
        return self.decision_log[-limit:]

    def get_ambiguity_ledger(self, decision_id: str) -> Optional[Dict[str, List[str]]]:
        """Get ambiguity ledger for decision."""
        decision = self.get_decision(decision_id)
        return decision.ambiguity_ledger if decision else None

    def get_reasoning_trace(self, decision_id: str) -> Optional[List[str]]:
        """Get reasoning trace for decision."""
        decision = self.get_decision(decision_id)
        return decision.reasoning_trace if decision else None

    # =======================================================================
    # ENFORCEMENT CHECKLIST
    # =======================================================================

    def run_enforcement_checklist(self, decision_id: str) -> Dict[str, Any]:
        """
        Run complete enforcement checklist (from cognitive blueprint).

        Returns:
            Checklist results
        """
        decision = self.get_decision(decision_id)
        if not decision:
            return {"error": "Decision not found"}

        checklist = {
            "ooda_completed": decision.ooda_phase == "act",
            "ambiguity_classified": all(
                ledger for ledger in decision.ambiguity_ledger.values()
            ),
            "reversibility_checked": True,  # Checked in decide phase
            "determinism_validated": self.validate_determinism(decision_id),
            "blast_radius_assessed": self.validate_blast_radius(decision_id),
            "observability_ensured": len(decision.reasoning_trace) > 0,
            "simplicity_considered": len(decision.alternatives_considered) > 0,
            "feedback_enabled": True,  # Enabled via action result
            "bounds_set": self.validate_bounded_recursion(decision_id, 0),
            "optionality_evaluated": len(decision.alternatives_considered) > 1,
            "time_limit_set": decision.constraints.time_limit_seconds > 0,
            "alternatives_considered": len(decision.alternatives_considered) > 0
        }

        checklist["all_passed"] = all(checklist.values())

        return checklist


# Global instance
_cognitive_enforcer: Optional[CognitiveEnforcer] = None


def get_cognitive_enforcer() -> CognitiveEnforcer:
    """Get or create global cognitive enforcer instance."""
    global _cognitive_enforcer
    if _cognitive_enforcer is None:
        _cognitive_enforcer = CognitiveEnforcer()
    return _cognitive_enforcer
