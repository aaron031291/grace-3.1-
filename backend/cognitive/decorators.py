"""
Decorators for integrating cognitive enforcement into Grace's operations.

These decorators wrap existing functions to automatically apply
the 12-invariant cognitive blueprint.
"""
import functools
from typing import Callable, Any, Optional, Dict, List
from datetime import datetime, timezone, timedelta

from .engine import CognitiveEngine, DecisionContext
from .ooda import OODAPhase


def cognitive_operation(
    operation_name: str,
    requires_determinism: bool = False,
    is_safety_critical: bool = False,
    impact_scope: str = "local",
    is_reversible: bool = True,
    max_recursion_depth: int = 3,
    max_iterations: int = 5,
    planning_timeout_seconds: Optional[int] = None
):
    """
    Decorator that wraps an operation with cognitive enforcement.

    Automatically applies the 12 invariants to any function.

    Args:
        operation_name: Name of the operation
        requires_determinism: If True, enforces deterministic execution
        is_safety_critical: If True, marks as safety-critical
        impact_scope: Blast radius scope (local, component, systemic)
        is_reversible: Whether operation can be reversed
        max_recursion_depth: Maximum recursion depth allowed
        max_iterations: Maximum iteration count allowed
        planning_timeout_seconds: Timeout for planning phase

    Example:
        @cognitive_operation(
            "ingest_document",
            is_reversible=True,
            impact_scope="component"
        )
        def ingest_document(filepath: str) -> dict:
            # Your implementation
            return {"status": "success"}
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Create cognitive engine
            engine = CognitiveEngine(enable_strict_mode=True)

            # Extract problem statement from kwargs or args
            problem_statement = kwargs.get(
                'problem_statement',
                f"Execute {operation_name}"
            )
            goal = kwargs.get('goal', f"Complete {operation_name} successfully")
            success_criteria = kwargs.get('success_criteria', [
                f"{operation_name} completes without errors"
            ])

            # Begin decision process
            context = engine.begin_decision(
                problem_statement=problem_statement,
                goal=goal,
                success_criteria=success_criteria,
                requires_determinism=requires_determinism,
                is_safety_critical=is_safety_critical,
                impact_scope=impact_scope,
                is_reversible=is_reversible,
                max_recursion_depth=max_recursion_depth,
                max_iterations=max_iterations
            )

            # Set planning timeout if specified
            if planning_timeout_seconds:
                context.decision_freeze_point = (
                    datetime.now(timezone.utc) + timedelta(seconds=planning_timeout_seconds)
                )

            # OBSERVE: Gather inputs
            observations = {
                'args': args,
                'kwargs': kwargs,
                'function_name': func.__name__,
                'operation_name': operation_name,
            }
            engine.observe(context, observations)

            # ORIENT: Understand constraints
            constraints = {
                'safety_critical': is_safety_critical,
                'impact_scope': impact_scope,
            }
            context_info = {
                'determinism_required': requires_determinism,
                'reversible': is_reversible,
            }
            engine.orient(context, constraints, context_info)

            # DECIDE: Choose execution path (simple case: just execute)
            def generate_alternatives() -> List[Dict[str, Any]]:
                return [{
                    'name': 'direct_execution',
                    'immediate_value': 1.0,
                    'future_options': 1.0,
                    'simplicity': 1.0,
                    'reversibility': 1.0 if is_reversible else 0.5,
                    'complexity': 0.1,
                }]

            selected_path = engine.decide(context, generate_alternatives)

            # ACT: Execute the function
            def action():
                return func(*args, **kwargs)

            result = engine.act(context, action, dry_run=False)

            # Finalize decision
            engine.finalize_decision(context)

            return result

        return wrapper
    return decorator


def with_ambiguity_tracking(func: Callable) -> Callable:
    """
    Decorator that adds ambiguity tracking to a function.

    Automatically tracks unknowns and inferred values.

    Example:
        @with_ambiguity_tracking
        def process_data(data: Optional[dict]) -> dict:
            if data is None:
                # This will be tracked as an unknown
                return {"error": "no data"}
            return {"processed": True}
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        # Get or create cognitive engine context
        # In practice, this would pull from thread-local storage
        from .engine import CognitiveEngine, DecisionContext

        engine = CognitiveEngine()

        # Check if we have an active context
        active_contexts = engine.get_active_decisions()

        if active_contexts:
            context = active_contexts[0]

            # Track None values as unknowns
            for key, value in kwargs.items():
                if value is None:
                    context.ambiguity_ledger.add_unknown(
                        key,
                        blocking=False,
                        notes=f"None value in {func.__name__}"
                    )

        result = func(*args, **kwargs)
        return result

    return wrapper


def enforce_reversibility(
    reversible: bool = True,
    justification: Optional[str] = None
):
    """
    Decorator that enforces reversibility constraints.

    Implements Invariant 3: Reversibility Before Commitment.

    Args:
        reversible: Whether the operation is reversible
        justification: Required justification if irreversible

    Example:
        @enforce_reversibility(
            reversible=False,
            justification="Database schema migration cannot be auto-reversed"
        )
        def migrate_database():
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            if not reversible and not justification:
                raise ValueError(
                    f"Irreversible operation '{func.__name__}' requires justification"
                )

            # Log irreversibility warning
            if not reversible:
                print(f"⚠ IRREVERSIBLE OPERATION: {func.__name__}")
                print(f"  Justification: {justification}")

            return func(*args, **kwargs)

        # Attach metadata
        wrapper.__cognitive_reversible__ = reversible
        wrapper.__cognitive_justification__ = justification

        return wrapper
    return decorator


def blast_radius(scope: str):
    """
    Decorator that declares the blast radius of an operation.

    Implements Invariant 5: Blast Radius Minimization.

    Args:
        scope: Impact scope (local, component, systemic)

    Example:
        @blast_radius("systemic")
        def update_schema():
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            if scope == "systemic":
                print(f"⚠ SYSTEMIC CHANGE: {func.__name__}")
                print(f"  High scrutiny required")

            return func(*args, **kwargs)

        # Attach metadata
        wrapper.__cognitive_blast_radius__ = scope

        return wrapper
    return decorator


def time_bounded(timeout_seconds: int):
    """
    Decorator that enforces time bounds on operations.

    Implements Invariant 11: Time-Bounded Reasoning.

    Args:
        timeout_seconds: Maximum execution time

    Example:
        @time_bounded(timeout_seconds=30)
        def analyze_document():
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            import os
            import sys
            
            if os.name == 'nt':
                # Windows doesn't support SIGALRM, so time_bounded is a no-op here
                return func(*args, **kwargs)
                
            import signal

            def timeout_handler(signum, frame):
                raise TimeoutError(
                    f"Operation '{func.__name__}' exceeded "
                    f"{timeout_seconds}s time bound"
                )

            # Set timeout
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout_seconds)

            try:
                result = func(*args, **kwargs)
            finally:
                # Restore old handler
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)

            return result

        return wrapper
    return decorator


def requires_determinism(func: Callable) -> Callable:
    """
    Decorator that marks a function as requiring deterministic execution.

    Implements Invariant 4: Determinism Where Safety Depends on It.

    Example:
        @requires_determinism
        def validate_critical_data():
            pass
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        # In practice, this would disable any probabilistic components
        # and enforce strict deterministic paths
        return func(*args, **kwargs)

    # Attach metadata
    wrapper.__cognitive_deterministic__ = True

    return wrapper
