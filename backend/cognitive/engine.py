import uuid
from datetime import datetime, UTC
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
from .ooda import OODALoop, OODAPhase
from .ambiguity import AmbiguityLedger, AmbiguityLevel
from .invariants import InvariantValidator
from .decision_log import DecisionLogger

logger = logging.getLogger(__name__)

class DecisionType(str, Enum):
    """Types of decisions Grace can make."""
    REVERSIBLE = "reversible"
    IRREVERSIBLE = "irreversible"
    PROBABILISTIC = "probabilistic"  # DEPRECATED: Use DETERMINISTIC instead
    DETERMINISTIC = "deterministic"
    ULTRA_DETERMINISTIC = "ultra_deterministic"  # Maximum determinism with proofs


@dataclass
class DecisionContext:
    """
    Context for a decision being made.

    Tracks all information needed to enforce the 12 invariants.
    """
    decision_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    problem_statement: str = ""
    goal: str = ""
    success_criteria: List[str] = field(default_factory=list)

    # Invariant 2: Ambiguity Accounting
    ambiguity_ledger: AmbiguityLedger = field(default_factory=AmbiguityLedger)

    # Invariant 3: Reversibility
    is_reversible: bool = True
    reversibility_justification: Optional[str] = None

    # Invariant 4: Determinism
    requires_determinism: bool = False
    is_safety_critical: bool = False

    # Invariant 5: Blast Radius
    impact_scope: str = "local"  # local, component, systemic
    affected_files: List[str] = field(default_factory=list)
    affected_dependencies: List[str] = field(default_factory=list)

    # Invariant 7: Complexity
    complexity_score: float = 0.0
    benefit_score: float = 0.0
    simplicity_justification: Optional[str] = None

    # Invariant 9: Bounded Recursion
    recursion_depth: int = 0
    max_recursion_depth: int = 3
    iteration_count: int = 0
    max_iterations: int = 5

    # Invariant 10: Optionality
    preserves_future_options: bool = True
    future_flexibility_metric: float = 1.0

    # Invariant 11: Time Bounds
    planning_start: datetime = field(default_factory=lambda: datetime.now(UTC))
    planning_deadline: Optional[datetime] = None
    decision_freeze_point: Optional[datetime] = None

    # Invariant 12: Forward Simulation
    alternative_paths: List[Dict[str, Any]] = field(default_factory=list)
    selected_path: Optional[Dict[str, Any]] = None
    simulation_depth: int = 2

    # Metadata
    parent_decision_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: Dict[str, Any] = field(default_factory=dict)


class CognitiveEngine:
    """
    Central Cortex for Grace's cognitive operations.

    Enforces the 12 invariants and orchestrates decision-making
    through the OODA loop.
    """

    def __init__(
        self,
        decision_logger: Optional[DecisionLogger] = None,
        enable_strict_mode: bool = True
    ):
        """
        Initialize the cognitive engine.

        Args:
            decision_logger: Logger for decision traces
            enable_strict_mode: If True, strictly enforce all invariants
        """
        self.ooda = OODALoop()
        self.invariant_validator = InvariantValidator()
        self.decision_logger = decision_logger or DecisionLogger()
        self.enable_strict_mode = enable_strict_mode

        # Active decision contexts
        self._active_contexts: Dict[str, DecisionContext] = {}
        
        # Degradation tracking for monitoring
        self._degradation_count: Dict[str, int] = {}

    def begin_decision(
        self,
        problem_statement: str,
        goal: str,
        success_criteria: List[str],
        parent_decision_id: Optional[str] = None,
        **kwargs
    ) -> DecisionContext:
        """
        Begin a new decision process.

        Implements Invariant 1: OODA as Primary Control Loop.

        Args:
            problem_statement: Clear statement of the problem
            goal: What success looks like
            success_criteria: Measurable criteria for success
            parent_decision_id: ID of parent decision (for nested decisions)
            **kwargs: Additional context parameters

        Returns:
            DecisionContext with decision_id
        """
        context = DecisionContext(
            problem_statement=problem_statement,
            goal=goal,
            success_criteria=success_criteria,
            parent_decision_id=parent_decision_id,
            **kwargs
        )

        self._active_contexts[context.decision_id] = context

        # Log decision start
        self.decision_logger.log_decision_start(context)

        return context

    def observe(self, context: DecisionContext, observations: Dict[str, Any]) -> None:
        """
        OODA: Observe phase.

        Gather all relevant information about the problem.

        Args:
            context: Decision context
            observations: Observed facts and data
        """
        self.ooda.observe(observations)
        context.metadata['observations'] = observations

        # Update ambiguity ledger based on observations
        for key, value in observations.items():
            if value is None or value == "unknown":
                context.ambiguity_ledger.add_unknown(key, blocking=False)
            elif isinstance(value, dict) and value.get('inferred'):
                context.ambiguity_ledger.add_inferred(
                    key,
                    value.get('value'),
                    value.get('confidence', 0.5)
                )
            else:
                context.ambiguity_ledger.add_known(key, value)

    def orient(
        self,
        context: DecisionContext,
        constraints: Dict[str, Any],
        context_info: Dict[str, Any]
    ) -> None:
        """
        OODA: Orient phase.

        Understand the context, constraints, and relevant patterns.

        Args:
            context: Decision context
            constraints: Constraints on the decision
            context_info: Contextual information
        """
        self.ooda.orient(context_info, constraints)
        context.metadata['constraints'] = constraints
        context.metadata['context_info'] = context_info

        # Determine if this is safety-critical (requires determinism)
        context.is_safety_critical = constraints.get('safety_critical', False)
        context.requires_determinism = context.is_safety_critical

        # Determine impact scope (blast radius)
        context.impact_scope = constraints.get('impact_scope', 'local')

        # Check for blocking unknowns
        blocking_unknowns = context.ambiguity_ledger.get_blocking_unknowns()
        if blocking_unknowns and self.enable_strict_mode:
            if not context.is_reversible:
                raise ValueError(
                    f"Blocking unknowns prevent irreversible action: {blocking_unknowns}"
                )

    def decide(
        self,
        context: DecisionContext,
        generate_alternatives: Callable[[], List[Dict[str, Any]]],
        max_alternatives: int = 5
    ) -> Dict[str, Any]:
        """
        OODA: Decide phase.

        Generate alternatives and select the best path forward.
        Implements Invariant 12: Forward Simulation.

        Args:
            context: Decision context
            generate_alternatives: Function that generates alternative paths
            max_alternatives: Maximum number of alternatives to consider

        Returns:
            Selected path dictionary
        """
        # Generate alternative paths
        alternatives = generate_alternatives()[:max_alternatives]
        context.alternative_paths = alternatives

        # Score each alternative (with TimeSense integration)
        scored_alternatives = []
        for alt in alternatives:
            score = self._score_alternative(context, alt)
            
            # TimeSense: Get time estimates for alternative if available
            time_estimate = None
            time_awareness = {}
            if 'primitive_type' in alt or 'operation_type' in alt:
                try:
                    from timesense.integration import TimeEstimator
                    from timesense.primitives import PrimitiveType
                    
                    # Try to estimate time for this alternative
                    if 'primitive_type' in alt:
                        from timesense.integration import predict_time
                        ptype = PrimitiveType(alt['primitive_type']) if isinstance(alt['primitive_type'], str) else alt['primitive_type']
                        size = alt.get('size', 1.0)
                        time_estimate = predict_time(
                            primitive_type=ptype,
                            size=size,
                            model_name=alt.get('model_name')
                        )
                    
                    if time_estimate:
                        time_awareness = {
                            'estimated_time_ms': time_estimate.p50_ms,
                            'time_confidence': time_estimate.confidence,
                            'time_human_readable': time_estimate.human_readable()
                        }
                        
                        # Check if alternative exceeds deadline
                        if context.planning_deadline:
                            deadline_ms = (context.planning_deadline - datetime.now(UTC)).total_seconds() * 1000
                            if time_estimate.p95_ms > deadline_ms:
                                # Penalize alternatives that exceed deadline
                                score *= 0.5
                                time_awareness['exceeds_deadline'] = True
                except Exception as e:
                    # TimeSense not available or error - continue without time awareness
                    logger.warning(
                        f"[COGNITIVE ENGINE] TimeSense unavailable for decision {context.decision_id}: {e}. "
                        f"Continuing without time awareness - deadline checking disabled."
                    )
                    # Track degradation for monitoring
                    if hasattr(self, '_degradation_count'):
                        self._degradation_count['timesense_unavailable'] = \
                            self._degradation_count.get('timesense_unavailable', 0) + 1
                    else:
                        self._degradation_count = {'timesense_unavailable': 1}
            
            scored_alternatives.append({
                'alternative': alt,
                'score': score,
                'time_awareness': time_awareness,
                'breakdown': {
                    'immediate_value': alt.get('immediate_value', 0),
                    'future_options': alt.get('future_options', 0),
                    'simplicity': alt.get('simplicity', 0),
                    'reversibility': alt.get('reversibility', 0),
                }
            })

        # Sort by score
        scored_alternatives.sort(key=lambda x: x['score'], reverse=True)

        # Select best path
        best = scored_alternatives[0]
        context.selected_path = best

        # Log alternatives considered
        self.decision_logger.log_alternatives(
            context.decision_id,
            alternatives,
            best['alternative']
        )

        self.ooda.decide(best['alternative'])

        return best['alternative']

    def act(
        self,
        context: DecisionContext,
        action: Callable[[], Any],
        dry_run: bool = False
    ) -> Any:
        """
        OODA: Act phase.

        Execute the selected action with monitoring.
        Enforces reversibility and observability invariants.

        Args:
            context: Decision context
            action: Function to execute
            dry_run: If True, simulate without executing

        Returns:
            Result of action execution
        """
        # Validate all invariants before execution
        validation_result = self.invariant_validator.validate_all(context)

        if not validation_result.is_valid:
            if self.enable_strict_mode:
                raise ValueError(
                    f"Invariant validation failed: {validation_result.violations}"
                )
            else:
                # Log warnings but proceed
                for violation in validation_result.violations:
                    self.decision_logger.log_warning(
                        context.decision_id,
                        f"Invariant violation: {violation}"
                    )

        # Execute action with TimeSense tracking
        if dry_run:
            result = {"dry_run": True, "would_execute": str(action)}
        else:
            # Estimate action execution time if possible
            action_size = context.metadata.get('action_size', 1.0)
            action_primitive = context.metadata.get('action_primitive_type')
            
            try:
                # Try to track with TimeSense if primitive type is known
                if TIMESENSE_AVAILABLE and action_primitive:
                    try:
                        ptype = PrimitiveType(action_primitive) if isinstance(action_primitive, str) else action_primitive
                        with track_operation(ptype, action_size, task_id=context.decision_id):
                            result = self.ooda.act(action)
                    except Exception as e:
                        logger.debug(f"[TIMESENSE] Could not track action: {e}")
                        result = self.ooda.act(action)
                else:
                    result = self.ooda.act(action)
                
                context.metadata['action_result'] = result
                context.metadata['action_status'] = 'success'
            except Exception as e:
                context.metadata['action_result'] = None
                context.metadata['action_status'] = 'failed'
                context.metadata['action_error'] = str(e)
                raise

        # Log decision completion
        self.decision_logger.log_decision_complete(context, result)

        return result

    def _score_alternative(
        self,
        context: DecisionContext,
        alternative: Dict[str, Any]
    ) -> float:
        """
        Score an alternative path based on multiple criteria.

        Implements Invariant 10: Optionality > Optimization.
        TimeSense Integration: Includes time efficiency in scoring.

        Args:
            context: Decision context
            alternative: Alternative to score

        Returns:
            Score (higher is better)
        """
        immediate_value = alternative.get('immediate_value', 0)
        future_options = alternative.get('future_options', 0)
        simplicity = alternative.get('simplicity', 1.0)
        reversibility = alternative.get('reversibility', 1.0)

        # Weight future options heavily (Invariant 10)
        option_value_factor = 2.0

        # Penalize complexity (Invariant 7)
        complexity_penalty = 1.0 / (1.0 + alternative.get('complexity', 0))

        # Bonus for reversibility (Invariant 3)
        reversibility_bonus = 1.5 if reversibility > 0.8 else 1.0

        base_score = (
            immediate_value +
            (future_options * option_value_factor) +
            (simplicity * complexity_penalty) * reversibility_bonus
        )
        
        # TimeSense Integration: Factor in time efficiency (20% weight)
        time_efficiency_factor = 1.0
        time_confidence_factor = 1.0
        
        # Check if alternative has time estimate
        if 'estimated_time_ms' in alternative:
            estimated_time = alternative.get('estimated_time_ms', float('inf'))
            time_confidence = alternative.get('time_confidence', 0.5)
            
            # Prefer faster alternatives (inverse time relationship)
            # Normalize: 0-10s = full score, 10-60s = 0.8x, 60s+ = 0.5x
            if estimated_time < 10000:  # < 10 seconds
                time_efficiency_factor = 1.0
            elif estimated_time < 60000:  # < 1 minute
                time_efficiency_factor = 0.8
            else:  # > 1 minute
                time_efficiency_factor = 0.5
            
            # Factor in time prediction confidence
            time_confidence_factor = 0.8 + (time_confidence * 0.2)  # 0.8-1.0 range
            
            # Apply time factors (20% of score affected by time)
            score = base_score * (0.8 + (time_efficiency_factor * time_confidence_factor * 0.2))
        else:
            # No time estimate - use base score
            score = base_score

        return score

    def enforce_decision_freeze(self, context: DecisionContext) -> bool:
        """
        Check if decision freeze point has been reached.

        Implements Invariant 11: Time-Bounded Reasoning.

        Args:
            context: Decision context

        Returns:
            True if decision must be finalized now
        """
        if context.decision_freeze_point is None:
            return False

        return datetime.now(UTC) >= context.decision_freeze_point

    def check_recursion_bounds(self, context: DecisionContext) -> bool:
        """
        Check if recursion limits have been exceeded.

        Implements Invariant 9: Bounded Recursion.

        Args:
            context: Decision context

        Returns:
            True if within bounds
        """
        return (
            context.recursion_depth < context.max_recursion_depth and
            context.iteration_count < context.max_iterations
        )

    def finalize_decision(self, context: DecisionContext) -> None:
        """
        Finalize a decision and remove from active contexts.

        Args:
            context: Decision context to finalize
        """
        self.decision_logger.log_decision_finalized(context)

        if context.decision_id in self._active_contexts:
            del self._active_contexts[context.decision_id]

    def get_active_decisions(self) -> List[DecisionContext]:
        """
        Get all currently active decision contexts.

        Returns:
            List of active contexts
        """
        return list(self._active_contexts.values())

    def abort_decision(
        self,
        context: DecisionContext,
        reason: str
    ) -> None:
        """
        Abort a decision process.

        Args:
            context: Decision context to abort
            reason: Reason for aborting
        """
        context.metadata['aborted'] = True
        context.metadata['abort_reason'] = reason

        self.decision_logger.log_decision_aborted(context, reason)

        if context.decision_id in self._active_contexts:
            del self._active_contexts[context.decision_id]

    def get_degradation_metrics(self) -> Dict[str, int]:
        """
        Get current degradation metrics for monitoring.
        
        Returns:
            Dictionary mapping degradation type to count
        """
        return self._degradation_count.copy()
