"""
Invariant Validator for Grace's Cognitive Engine.

Validates that all 12 core invariants are satisfied before execution.
"""
from dataclasses import dataclass
from typing import List, Optional, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from .engine import DecisionContext


@dataclass
class ValidationResult:
    """Result of invariant validation."""
    is_valid: bool
    violations: List[str]
    warnings: List[str]


class InvariantValidator:
    """
    Validates the 12 core cognitive invariants.

    Ensures Grace operates within the defined cognitive constraints.
    """

    def validate_all(self, context: 'DecisionContext') -> ValidationResult:
        """
        Validate all invariants for a decision context.

        Args:
            context: Decision context to validate

        Returns:
            ValidationResult with any violations
        """
        violations = []
        warnings = []

        # Invariant 1: OODA Loop (validated by engine structure)
        if not context.problem_statement:
            violations.append("Invariant 1: No problem statement (OODA Observe missing)")

        if not context.goal:
            violations.append("Invariant 1: No goal defined (OODA Orient missing)")

        # Invariant 2: Ambiguity Accounting
        if context.ambiguity_ledger.has_blocking_unknowns():
            if not context.is_reversible:
                violations.append(
                    f"Invariant 2: Blocking unknowns prevent irreversible action. "
                    f"Unknowns: {[e.key for e in context.ambiguity_ledger.get_blocking_unknowns()]}"
                )
            else:
                warnings.append(
                    f"Invariant 2: Blocking unknowns exist but action is reversible. "
                    f"Unknowns: {[e.key for e in context.ambiguity_ledger.get_blocking_unknowns()]}"
                )

        # Invariant 3: Reversibility
        if not context.is_reversible and not context.reversibility_justification:
            violations.append(
                "Invariant 3: Irreversible action requires explicit justification"
            )

        # Invariant 4: Determinism
        if context.is_safety_critical and not context.requires_determinism:
            violations.append(
                "Invariant 4: Safety-critical operations must be deterministic"
            )

        # Invariant 5: Blast Radius
        if context.impact_scope == "systemic":
            if len(context.success_criteria) == 0:
                violations.append(
                    "Invariant 5: Systemic changes require detailed success criteria"
                )
            if not context.metadata.get('impact_analysis'):
                warnings.append(
                    "Invariant 5: Systemic change without impact analysis"
                )

        # Invariant 6: Observability (enforced by decision logger)
        # Checked at runtime by decision_log.py

        # Invariant 7: Simplicity
        if context.complexity_score > 0:
            if context.benefit_score == 0:
                warnings.append(
                    "Invariant 7: Complexity without measured benefit"
                )
            elif context.complexity_score > context.benefit_score:
                warnings.append(
                    f"Invariant 7: Complexity ({context.complexity_score}) "
                    f"exceeds benefit ({context.benefit_score})"
                )

        # Invariant 8: Feedback (enforced by telemetry layer)
        # Checked at runtime by telemetry system

        # Invariant 9: Bounded Recursion
        if context.recursion_depth >= context.max_recursion_depth:
            violations.append(
                f"Invariant 9: Recursion depth limit exceeded "
                f"({context.recursion_depth} >= {context.max_recursion_depth})"
            )

        if context.iteration_count >= context.max_iterations:
            violations.append(
                f"Invariant 9: Iteration limit exceeded "
                f"({context.iteration_count} >= {context.max_iterations})"
            )

        # Invariant 10: Optionality
        if not context.preserves_future_options:
            if context.future_flexibility_metric < 0.5:
                warnings.append(
                    f"Invariant 10: Low future flexibility "
                    f"({context.future_flexibility_metric})"
                )

        # Invariant 11: Time-Bounded Reasoning
        if context.decision_freeze_point:
            if datetime.utcnow() > context.decision_freeze_point:
                violations.append(
                    "Invariant 11: Decision freeze point exceeded - must decide now"
                )

        # Invariant 12: Forward Simulation
        if len(context.alternative_paths) == 0:
            warnings.append(
                "Invariant 12: No alternative paths considered (chess mode not used)"
            )
        elif context.selected_path is None:
            violations.append(
                "Invariant 12: Alternative paths generated but none selected"
            )

        is_valid = len(violations) == 0

        return ValidationResult(
            is_valid=is_valid,
            violations=violations,
            warnings=warnings
        )

    def validate_invariant(
        self,
        invariant_number: int,
        context: 'DecisionContext'
    ) -> ValidationResult:
        """
        Validate a specific invariant.

        Args:
            invariant_number: Number of invariant to validate (1-12)
            context: Decision context

        Returns:
            ValidationResult for that invariant
        """
        violations = []
        warnings = []

        if invariant_number == 1:
            if not context.problem_statement:
                violations.append("No problem statement")
            if not context.goal:
                violations.append("No goal defined")

        elif invariant_number == 2:
            if context.ambiguity_ledger.has_blocking_unknowns():
                if not context.is_reversible:
                    violations.append("Blocking unknowns prevent irreversible action")

        elif invariant_number == 3:
            if not context.is_reversible and not context.reversibility_justification:
                violations.append("Irreversible action requires justification")

        elif invariant_number == 4:
            if context.is_safety_critical and not context.requires_determinism:
                violations.append("Safety-critical operations must be deterministic")

        elif invariant_number == 5:
            if context.impact_scope == "systemic":
                if len(context.success_criteria) == 0:
                    violations.append("Systemic changes require success criteria")

        elif invariant_number == 7:
            if context.complexity_score > context.benefit_score:
                warnings.append("Complexity exceeds benefit")

        elif invariant_number == 9:
            if context.recursion_depth >= context.max_recursion_depth:
                violations.append("Recursion depth limit exceeded")
            if context.iteration_count >= context.max_iterations:
                violations.append("Iteration limit exceeded")

        elif invariant_number == 10:
            if context.future_flexibility_metric < 0.5:
                warnings.append("Low future flexibility")

        elif invariant_number == 11:
            if context.decision_freeze_point:
                if datetime.utcnow() > context.decision_freeze_point:
                    violations.append("Decision freeze point exceeded")

        elif invariant_number == 12:
            if len(context.alternative_paths) == 0:
                warnings.append("No alternative paths considered")

        is_valid = len(violations) == 0

        return ValidationResult(
            is_valid=is_valid,
            violations=violations,
            warnings=warnings
        )
