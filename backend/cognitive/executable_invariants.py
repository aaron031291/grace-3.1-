"""
Executable Invariants System

Provides a framework for defining, registering, and checking executable invariants
including preconditions, postconditions, and state invariants.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple
import re


class InvariantType(Enum):
    """Types of executable invariants."""
    PRECONDITION = auto()
    POSTCONDITION = auto()
    INVARIANT = auto()
    STATE_INVARIANT = auto()
    TRANSITION_GUARD = auto()


@dataclass
class ExecutableInvariant:
    """An executable invariant with its predicate and metadata."""
    name: str
    description: str
    invariant_type: InvariantType
    predicate: Callable[[Dict[str, Any]], bool]
    error_message: str
    severity: str = "error"
    
    def check(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Check the invariant against the given context."""
        try:
            result = self.predicate(context)
            if result:
                return True, None
            return False, self.error_message
        except Exception as e:
            return False, f"{self.error_message} (exception: {str(e)})"


class InvariantRegistry:
    """Registry for managing and checking executable invariants."""
    
    def __init__(self):
        self._invariants: Dict[str, ExecutableInvariant] = {}
    
    def register(self, invariant: ExecutableInvariant) -> None:
        """Register an invariant by name."""
        self._invariants[invariant.name] = invariant
    
    def unregister(self, name: str) -> bool:
        """Unregister an invariant by name."""
        if name in self._invariants:
            del self._invariants[name]
            return True
        return False
    
    def get(self, name: str) -> Optional[ExecutableInvariant]:
        """Get an invariant by name."""
        return self._invariants.get(name)
    
    def check(self, name: str, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Check a specific invariant against the context."""
        invariant = self._invariants.get(name)
        if invariant is None:
            return False, f"Invariant '{name}' not found"
        return invariant.check(context)
    
    def check_all(
        self, 
        invariant_type: InvariantType, 
        context: Dict[str, Any]
    ) -> List[Tuple[str, bool, Optional[str]]]:
        """Check all invariants of a specific type."""
        results = []
        for name, invariant in self._invariants.items():
            if invariant.invariant_type == invariant_type:
                passed, error = invariant.check(context)
                results.append((name, passed, error))
        return results
    
    def check_multiple(
        self, 
        names: List[str], 
        context: Dict[str, Any]
    ) -> List[Tuple[str, bool, Optional[str]]]:
        """Check multiple invariants by name."""
        results = []
        for name in names:
            passed, error = self.check(name, context)
            results.append((name, passed, error))
        return results
    
    def list_invariants(
        self, 
        invariant_type: Optional[InvariantType] = None
    ) -> List[str]:
        """List all registered invariant names, optionally filtered by type."""
        if invariant_type is None:
            return list(self._invariants.keys())
        return [
            name for name, inv in self._invariants.items()
            if inv.invariant_type == invariant_type
        ]


class InvariantBuilder:
    """Fluent builder for creating executable invariants."""
    
    def __init__(self, name: str):
        self._name = name
        self._description: str = ""
        self._invariant_type: InvariantType = InvariantType.INVARIANT
        self._predicate: Optional[Callable[[Dict[str, Any]], bool]] = None
        self._error_message: str = f"Invariant '{name}' failed"
        self._severity: str = "error"
    
    def description(self, desc: str) -> "InvariantBuilder":
        """Set the invariant description."""
        self._description = desc
        return self
    
    def precondition(self) -> "InvariantBuilder":
        """Mark as a precondition."""
        self._invariant_type = InvariantType.PRECONDITION
        return self
    
    def postcondition(self) -> "InvariantBuilder":
        """Mark as a postcondition."""
        self._invariant_type = InvariantType.POSTCONDITION
        return self
    
    def invariant(self) -> "InvariantBuilder":
        """Mark as a general invariant."""
        self._invariant_type = InvariantType.INVARIANT
        return self
    
    def state_invariant(self) -> "InvariantBuilder":
        """Mark as a state invariant."""
        self._invariant_type = InvariantType.STATE_INVARIANT
        return self
    
    def transition_guard(self) -> "InvariantBuilder":
        """Mark as a transition guard."""
        self._invariant_type = InvariantType.TRANSITION_GUARD
        return self
    
    def of_type(self, invariant_type: InvariantType) -> "InvariantBuilder":
        """Set the invariant type directly."""
        self._invariant_type = invariant_type
        return self
    
    def check(self, predicate: Callable[[Dict[str, Any]], bool]) -> "InvariantBuilder":
        """Set the predicate function."""
        self._predicate = predicate
        return self
    
    def error(self, message: str) -> "InvariantBuilder":
        """Set the error message."""
        self._error_message = message
        return self
    
    def warning(self) -> "InvariantBuilder":
        """Set severity to warning."""
        self._severity = "warning"
        return self
    
    def severity_error(self) -> "InvariantBuilder":
        """Set severity to error."""
        self._severity = "error"
        return self
    
    def build(self) -> ExecutableInvariant:
        """Build the executable invariant."""
        if self._predicate is None:
            raise ValueError(f"Invariant '{self._name}' requires a predicate")
        
        return ExecutableInvariant(
            name=self._name,
            description=self._description,
            invariant_type=self._invariant_type,
            predicate=self._predicate,
            error_message=self._error_message,
            severity=self._severity
        )


# Global registry instance
global_registry = InvariantRegistry()


def requires_invariant(invariant_name: str, registry: Optional[InvariantRegistry] = None):
    """Decorator to check a precondition invariant before function execution."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            reg = registry or global_registry
            context = {"args": args, "kwargs": kwargs}
            if kwargs:
                context.update(kwargs)
            
            passed, error = reg.check(invariant_name, context)
            if not passed:
                invariant = reg.get(invariant_name)
                if invariant and invariant.severity == "warning":
                    import warnings
                    warnings.warn(f"Precondition warning: {error}")
                else:
                    raise AssertionError(f"Precondition failed: {error}")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def ensures_invariant(invariant_name: str, registry: Optional[InvariantRegistry] = None):
    """Decorator to check a postcondition invariant after function execution."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            reg = registry or global_registry
            context = {
                "args": args, 
                "kwargs": kwargs, 
                "result": result,
                "output": result
            }
            if kwargs:
                context.update(kwargs)
            
            passed, error = reg.check(invariant_name, context)
            if not passed:
                invariant = reg.get(invariant_name)
                if invariant and invariant.severity == "warning":
                    import warnings
                    warnings.warn(f"Postcondition warning: {error}")
                else:
                    raise AssertionError(f"Postcondition failed: {error}")
            
            return result
        return wrapper
    return decorator


def check_invariants(*invariant_names: str, registry: Optional[InvariantRegistry] = None):
    """Decorator to check multiple invariants (both pre and post based on type)."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            reg = registry or global_registry
            context = {"args": args, "kwargs": kwargs}
            if kwargs:
                context.update(kwargs)
            
            # Check preconditions
            for name in invariant_names:
                invariant = reg.get(name)
                if invariant and invariant.invariant_type == InvariantType.PRECONDITION:
                    passed, error = invariant.check(context)
                    if not passed:
                        if invariant.severity == "warning":
                            import warnings
                            warnings.warn(f"Precondition warning: {error}")
                        else:
                            raise AssertionError(f"Precondition failed: {error}")
            
            result = func(*args, **kwargs)
            
            context["result"] = result
            context["output"] = result
            
            # Check postconditions and invariants
            for name in invariant_names:
                invariant = reg.get(name)
                if invariant and invariant.invariant_type in (
                    InvariantType.POSTCONDITION, 
                    InvariantType.INVARIANT
                ):
                    passed, error = invariant.check(context)
                    if not passed:
                        if invariant.severity == "warning":
                            import warnings
                            warnings.warn(f"Invariant warning: {error}")
                        else:
                            raise AssertionError(f"Invariant failed: {error}")
            
            return result
        return wrapper
    return decorator


# Common pre-built invariants

inputs_not_empty = (
    InvariantBuilder("inputs_not_empty")
    .description("Check that inputs dictionary is not empty")
    .precondition()
    .check(lambda ctx: bool(ctx.get("inputs") or ctx.get("kwargs")))
    .error("Inputs dictionary must not be empty")
    .build()
)

output_not_none = (
    InvariantBuilder("output_not_none")
    .description("Check that output exists and is not None")
    .postcondition()
    .check(lambda ctx: ctx.get("output") is not None or ctx.get("result") is not None)
    .error("Output must not be None")
    .build()
)

trust_score_in_range = (
    InvariantBuilder("trust_score_in_range")
    .description("Check that trust score is between 0 and 1 inclusive")
    .invariant()
    .check(lambda ctx: 0 <= ctx.get("trust_score", ctx.get("score", 0)) <= 1)
    .error("Trust score must be in range [0, 1]")
    .build()
)

genesis_key_valid = (
    InvariantBuilder("genesis_key_valid")
    .description("Check that genesis key has valid format")
    .precondition()
    .check(lambda ctx: bool(
        ctx.get("genesis_key") and 
        isinstance(ctx.get("genesis_key"), str) and
        re.match(r'^[A-Za-z0-9_-]+$', ctx.get("genesis_key", ""))
    ))
    .error("Genesis key must be a valid alphanumeric string with underscores/hyphens")
    .build()
)

state_id_exists = (
    InvariantBuilder("state_id_exists")
    .description("Check that state ID exists in the state machine")
    .state_invariant()
    .check(lambda ctx: (
        ctx.get("state_id") is not None and
        ctx.get("state_machine") is not None and
        ctx.get("state_id") in ctx.get("state_machine", {}).get("states", {})
    ))
    .error("State ID must exist in the state machine")
    .build()
)


def register_common_invariants(registry: Optional[InvariantRegistry] = None) -> None:
    """Register all common pre-built invariants to a registry."""
    reg = registry or global_registry
    reg.register(inputs_not_empty)
    reg.register(output_not_none)
    reg.register(trust_score_in_range)
    reg.register(genesis_key_valid)
    reg.register(state_id_exists)


# Auto-register common invariants to global registry
register_common_invariants()


def get_invariant_registry() -> InvariantRegistry:
    """
    Get the global invariant registry instance.
    
    Returns:
        The global InvariantRegistry instance
    """
    return global_registry
