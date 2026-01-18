"""
Executable Invariants System

Provides a framework for defining, registering, and checking executable invariants
including preconditions, postconditions, and state invariants.

Built-in Invariants (automatically registered):
-----------------------------------------------
Basic Type Checks:
    - "not_null" / "not_none": Checks result is not None
    - "is_string": Checks result is a string
    - "is_dict": Checks result is a dict
    - "is_list": Checks result is a list

Content Checks:
    - "non_empty": Checks result is not empty (string/list/dict)
    - "is_positive": Checks numeric result > 0
    - "is_non_negative": Checks numeric result >= 0

Legacy Invariants:
    - "inputs_not_empty": Checks inputs dict is not empty (precondition)
    - "output_not_none": Checks output is not None (postcondition)
    - "trust_score_in_range": Checks trust score is in [0, 1]
    - "genesis_key_valid": Checks genesis key format
    - "state_id_exists": Checks state ID exists in state machine

Parameterized Invariants (create via factory functions):
--------------------------------------------------------
    - has_keys(*keys): Creates invariant checking dict has required keys
    - type_is(expected_type): Creates invariant checking result is of type
    - length_at_least(min_length): Creates invariant checking length >= min_length

Example Usage:
    from cognitive.executable_invariants import (
        global_registry, has_keys, type_is, length_at_least
    )
    
    # Use built-in invariant by name
    passed, error = global_registry.check("not_none", {"result": my_value})
    
    # Create and register parameterized invariant
    my_invariant = has_keys("id", "name", "value")
    global_registry.register(my_invariant)
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


# --- New Built-in Invariants ---

def _get_result(ctx: Dict[str, Any]) -> Any:
    """Helper to get result from context (supports 'result' or 'output' keys)."""
    return ctx.get("result", ctx.get("output"))


not_none = (
    InvariantBuilder("not_none")
    .description("Check that result is not None")
    .postcondition()
    .check(lambda ctx: _get_result(ctx) is not None)
    .error("Result must not be None")
    .build()
)

not_null = (
    InvariantBuilder("not_null")
    .description("Check that result is not None (alias for not_none)")
    .postcondition()
    .check(lambda ctx: _get_result(ctx) is not None)
    .error("Result must not be null/None")
    .build()
)

non_empty = (
    InvariantBuilder("non_empty")
    .description("Check that result is not empty (works for string, list, dict)")
    .postcondition()
    .check(lambda ctx: (
        (result := _get_result(ctx)) is not None and
        (len(result) > 0 if hasattr(result, '__len__') else bool(result))
    ))
    .error("Result must not be empty")
    .build()
)

is_string = (
    InvariantBuilder("is_string")
    .description("Check that result is a string")
    .postcondition()
    .check(lambda ctx: isinstance(_get_result(ctx), str))
    .error("Result must be a string")
    .build()
)

is_dict = (
    InvariantBuilder("is_dict")
    .description("Check that result is a dict")
    .postcondition()
    .check(lambda ctx: isinstance(_get_result(ctx), dict))
    .error("Result must be a dict")
    .build()
)

is_list = (
    InvariantBuilder("is_list")
    .description("Check that result is a list")
    .postcondition()
    .check(lambda ctx: isinstance(_get_result(ctx), list))
    .error("Result must be a list")
    .build()
)

is_positive = (
    InvariantBuilder("is_positive")
    .description("Check that numeric result is greater than 0")
    .postcondition()
    .check(lambda ctx: (
        (result := _get_result(ctx)) is not None and
        isinstance(result, (int, float)) and
        result > 0
    ))
    .error("Result must be a positive number (> 0)")
    .build()
)

is_non_negative = (
    InvariantBuilder("is_non_negative")
    .description("Check that numeric result is greater than or equal to 0")
    .postcondition()
    .check(lambda ctx: (
        (result := _get_result(ctx)) is not None and
        isinstance(result, (int, float)) and
        result >= 0
    ))
    .error("Result must be a non-negative number (>= 0)")
    .build()
)


# --- Parameterized Invariant Factory Functions ---

def has_keys(*keys: str) -> ExecutableInvariant:
    """
    Create an invariant that checks if the result dict has all required keys.
    
    Args:
        *keys: Required key names
        
    Returns:
        ExecutableInvariant that checks for required keys
        
    Example:
        inv = has_keys("id", "name", "value")
        global_registry.register(inv)
    """
    key_list = list(keys)
    name = f"has_keys_{'+'.join(key_list)}"
    
    def check_keys(ctx: Dict[str, Any]) -> bool:
        result = _get_result(ctx)
        if not isinstance(result, dict):
            return False
        return all(k in result for k in key_list)
    
    return (
        InvariantBuilder(name)
        .description(f"Check that result dict has keys: {key_list}")
        .postcondition()
        .check(check_keys)
        .error(f"Result dict must have keys: {key_list}")
        .build()
    )


def type_is(expected_type: type) -> ExecutableInvariant:
    """
    Create an invariant that checks if the result is of the expected type.
    
    Args:
        expected_type: The expected type (e.g., str, int, dict)
        
    Returns:
        ExecutableInvariant that checks the type
        
    Example:
        inv = type_is(int)
        global_registry.register(inv)
    """
    type_name = expected_type.__name__
    name = f"type_is_{type_name}"
    
    return (
        InvariantBuilder(name)
        .description(f"Check that result is of type {type_name}")
        .postcondition()
        .check(lambda ctx: isinstance(_get_result(ctx), expected_type))
        .error(f"Result must be of type {type_name}")
        .build()
    )


def length_at_least(min_length: int) -> ExecutableInvariant:
    """
    Create an invariant that checks if the result has at least the specified length.
    
    Args:
        min_length: Minimum required length
        
    Returns:
        ExecutableInvariant that checks the length
        
    Example:
        inv = length_at_least(5)
        global_registry.register(inv)
    """
    name = f"length_at_least_{min_length}"
    
    def check_length(ctx: Dict[str, Any]) -> bool:
        result = _get_result(ctx)
        if result is None:
            return False
        if not hasattr(result, '__len__'):
            return False
        return len(result) >= min_length
    
    return (
        InvariantBuilder(name)
        .description(f"Check that result has length >= {min_length}")
        .postcondition()
        .check(check_length)
        .error(f"Result must have length >= {min_length}")
        .build()
    )


def register_common_invariants(registry: Optional[InvariantRegistry] = None) -> None:
    """
    Register all common pre-built invariants to a registry.
    
    Registers the following invariants:
        - inputs_not_empty (precondition)
        - output_not_none (postcondition)
        - trust_score_in_range (invariant)
        - genesis_key_valid (precondition)
        - state_id_exists (state_invariant)
        - not_none / not_null (postcondition)
        - non_empty (postcondition)
        - is_string (postcondition)
        - is_dict (postcondition)
        - is_list (postcondition)
        - is_positive (postcondition)
        - is_non_negative (postcondition)
    
    Args:
        registry: Optional registry to use (defaults to global_registry)
    """
    reg = registry or global_registry
    # Legacy invariants
    reg.register(inputs_not_empty)
    reg.register(output_not_none)
    reg.register(trust_score_in_range)
    reg.register(genesis_key_valid)
    reg.register(state_id_exists)
    # New invariants
    reg.register(not_none)
    reg.register(not_null)
    reg.register(non_empty)
    reg.register(is_string)
    reg.register(is_dict)
    reg.register(is_list)
    reg.register(is_positive)
    reg.register(is_non_negative)


# Auto-register common invariants to global registry
register_common_invariants()


def get_invariant_registry() -> InvariantRegistry:
    """
    Get the global invariant registry instance.
    
    Returns:
        The global InvariantRegistry instance
    """
    return global_registry
