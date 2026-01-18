"""
Genesis Bound Operations

Integrates deterministic operations with Genesis Keys for complete traceability.
All operations are bound to Genesis Keys for immutable tracking.
"""
import hashlib
import json
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from contextlib import contextmanager

from genesis.genesis_key_service import GenesisKeyService, get_genesis_service
from models.genesis_key_models import GenesisKeyType

logger = logging.getLogger(__name__)


class LogicalClock:
    """
    Lamport logical clock for deterministic ordering.
    
    Uses tick-based time instead of wall-clock time for reproducibility.
    """
    
    def __init__(self, initial_tick: int = 0):
        self._tick = initial_tick
    
    @property
    def tick(self) -> int:
        return self._tick
    
    def increment(self) -> int:
        self._tick += 1
        return self._tick
    
    def update(self, received_tick: int) -> int:
        self._tick = max(self._tick, received_tick) + 1
        return self._tick
    
    def to_dict(self) -> Dict[str, Any]:
        return {"tick": self._tick}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LogicalClock":
        return cls(initial_tick=data.get("tick", 0))


class Canonicalizer:
    """
    Canonicalizes data for deterministic hashing.
    
    Ensures consistent ordering and formatting for reproducible digests.
    """
    
    @staticmethod
    def canonicalize(data: Any) -> str:
        if data is None:
            return "null"
        if isinstance(data, (bool,)):
            return "true" if data else "false"
        if isinstance(data, (int, float)):
            return str(data)
        if isinstance(data, str):
            return data
        if isinstance(data, (list, tuple)):
            items = [Canonicalizer.canonicalize(item) for item in data]
            return "[" + ",".join(items) + "]"
        if isinstance(data, dict):
            sorted_keys = sorted(data.keys())
            items = [f"{k}:{Canonicalizer.canonicalize(data[k])}" for k in sorted_keys]
            return "{" + ",".join(items) + "}"
        return str(data)
    
    @staticmethod
    def digest(data: Any, algorithm: str = "sha256") -> str:
        canonical = Canonicalizer.canonicalize(data)
        if algorithm == "sha256":
            return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        elif algorithm == "sha512":
            return hashlib.sha512(canonical.encode("utf-8")).hexdigest()
        elif algorithm == "md5":
            return hashlib.md5(canonical.encode("utf-8")).hexdigest()
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
    
    @staticmethod
    def to_json(data: Any) -> str:
        return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


class DeterministicIDGenerator:
    """
    Generates deterministic IDs based on content.
    
    Same content always produces the same ID.
    """
    
    def __init__(self, namespace: str = "grace"):
        self.namespace = namespace
    
    def generate(self, *content_parts: Any) -> str:
        combined = Canonicalizer.canonicalize({
            "namespace": self.namespace,
            "parts": list(content_parts)
        })
        digest = hashlib.sha256(combined.encode("utf-8")).hexdigest()
        return f"{self.namespace}-{digest[:16]}"
    
    def generate_from_dict(self, data: Dict[str, Any]) -> str:
        combined = Canonicalizer.canonicalize({
            "namespace": self.namespace,
            "data": data
        })
        digest = hashlib.sha256(combined.encode("utf-8")).hexdigest()
        return f"{self.namespace}-{digest[:16]}"


@dataclass
class ExecutionTrace:
    """Trace of a single operation execution."""
    operation_name: str
    inputs_digest: str
    output_digest: str
    trace_digest: str
    start_tick: int
    end_tick: int
    success: bool
    error: Optional[str] = None


class GenesisBoundOperation:
    """
    Wraps any operation and automatically creates Genesis Keys.
    
    Every execution is tracked with immutable Genesis Keys.
    """
    
    def __init__(
        self,
        operation_name: str,
        genesis_service: GenesisKeyService,
        operation_callable: Callable,
        key_type: GenesisKeyType = GenesisKeyType.SYSTEM_EVENT
    ):
        self.operation_name = operation_name
        self.genesis_service = genesis_service
        self.operation_callable = operation_callable
        self.key_type = key_type
        self.canonicalizer = Canonicalizer()
        self.id_generator = DeterministicIDGenerator(namespace="gbo")
    
    def execute(
        self,
        *args,
        logical_clock: Optional[LogicalClock] = None,
        parent_key_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Tuple[Any, str]:
        """
        Execute operation with Genesis Key tracking.
        
        Args:
            *args: Positional arguments for operation
            logical_clock: Optional logical clock (creates one if not provided)
            parent_key_id: Optional parent Genesis Key ID
            context: Optional context data
            **kwargs: Keyword arguments for operation
            
        Returns:
            Tuple of (result, genesis_key_id)
        """
        clock = logical_clock or LogicalClock()
        start_tick = clock.increment()
        
        inputs_data = {
            "args": list(args),
            "kwargs": kwargs,
            "context": context
        }
        inputs_digest = Canonicalizer.digest(inputs_data)
        
        genesis_key = self.genesis_service.create_key(
            key_type=self.key_type,
            what_description=f"Executing operation: {self.operation_name}",
            who_actor="genesis_bound_operation",
            why_reason=f"Deterministic execution of {self.operation_name}",
            how_method="GenesisBoundOperation.execute",
            input_data={
                "inputs_digest": inputs_digest,
                "operation_name": self.operation_name,
                "start_tick": start_tick
            },
            parent_key_id=parent_key_id,
            context_data=context
        )
        
        trace_steps: List[Dict[str, Any]] = []
        
        try:
            trace_steps.append({
                "step": "start",
                "tick": start_tick,
                "inputs_digest": inputs_digest
            })
            
            result = self.operation_callable(*args, **kwargs)
            
            end_tick = clock.increment()
            output_digest = Canonicalizer.digest(result)
            
            trace_steps.append({
                "step": "complete",
                "tick": end_tick,
                "output_digest": output_digest
            })
            
            trace_digest = Canonicalizer.digest(trace_steps)
            
            self.genesis_service.create_key(
                key_type=self.key_type,
                what_description=f"Completed operation: {self.operation_name}",
                who_actor="genesis_bound_operation",
                why_reason="Operation completed successfully",
                how_method="GenesisBoundOperation.execute",
                input_data={
                    "inputs_digest": inputs_digest,
                    "operation_name": self.operation_name
                },
                output_data={
                    "output_digest": output_digest,
                    "trace_digest": trace_digest,
                    "execution_ticks": end_tick - start_tick
                },
                parent_key_id=genesis_key.key_id,
                context_data=context
            )
            
            return result, genesis_key.key_id
            
        except Exception as e:
            end_tick = clock.increment()
            
            trace_steps.append({
                "step": "error",
                "tick": end_tick,
                "error": str(e)
            })
            
            trace_digest = Canonicalizer.digest(trace_steps)
            
            self.genesis_service.create_key(
                key_type=GenesisKeyType.ERROR,
                what_description=f"Operation failed: {self.operation_name}",
                who_actor="genesis_bound_operation",
                why_reason="Operation execution failed",
                how_method="GenesisBoundOperation.execute",
                is_error=True,
                error_type=type(e).__name__,
                error_message=str(e),
                input_data={
                    "inputs_digest": inputs_digest,
                    "operation_name": self.operation_name
                },
                output_data={
                    "trace_digest": trace_digest,
                    "execution_ticks": end_tick - start_tick
                },
                parent_key_id=genesis_key.key_id,
                context_data=context
            )
            
            raise


class TransitionResult(Enum):
    """Result of a state transition."""
    SUCCESS = "success"
    INVALID_TRANSITION = "invalid_transition"
    GUARD_FAILED = "guard_failed"
    ERROR = "error"


@dataclass
class StateTransition:
    """Record of a state transition."""
    transition_id: str
    from_state: str
    to_state: str
    context_digest: str
    tick: int
    genesis_key_id: str


class GenesisBoundStateMachine:
    """
    State machine that records all transitions to Genesis Keys.
    
    Every state transition is immutably recorded.
    """
    
    def __init__(
        self,
        name: str,
        genesis_service: GenesisKeyService,
        initial_state: str,
        parent_key_id: Optional[str] = None
    ):
        self.name = name
        self.genesis_service = genesis_service
        self.current_state = initial_state
        self.parent_key_id = parent_key_id
        self.transitions: Dict[Tuple[str, str], Callable[[Dict[str, Any]], bool]] = {}
        self.history: List[StateTransition] = []
        self.logical_clock = LogicalClock()
        self.id_generator = DeterministicIDGenerator(namespace="gsm")
        
        parent_key = self.genesis_service.create_key(
            key_type=GenesisKeyType.SYSTEM_EVENT,
            what_description=f"State machine created: {name}",
            who_actor="genesis_bound_state_machine",
            why_reason="Initialize state machine with Genesis Key tracking",
            how_method="GenesisBoundStateMachine.__init__",
            input_data={
                "name": name,
                "initial_state": initial_state
            },
            parent_key_id=parent_key_id
        )
        self.workflow_key_id = parent_key.key_id
    
    def add_transition(
        self,
        from_state: str,
        to_state: str,
        guard: Optional[Callable[[Dict[str, Any]], bool]] = None
    ):
        """
        Add a valid transition.
        
        Args:
            from_state: Source state
            to_state: Target state
            guard: Optional guard condition that must return True
        """
        self.transitions[(from_state, to_state)] = guard or (lambda ctx: True)
    
    def transition(
        self,
        to_state: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[TransitionResult, Optional[str]]:
        """
        Attempt a state transition.
        
        Args:
            to_state: Target state
            context: Optional context for guard evaluation
            
        Returns:
            Tuple of (result, genesis_key_id or error_message)
        """
        context = context or {}
        from_state = self.current_state
        
        transition_key = (from_state, to_state)
        if transition_key not in self.transitions:
            return TransitionResult.INVALID_TRANSITION, f"No transition from {from_state} to {to_state}"
        
        guard = self.transitions[transition_key]
        
        try:
            if not guard(context):
                return TransitionResult.GUARD_FAILED, "Guard condition returned False"
        except Exception as e:
            return TransitionResult.ERROR, f"Guard evaluation error: {e}"
        
        tick = self.logical_clock.increment()
        context_digest = Canonicalizer.digest(context)
        
        transition_id = self.id_generator.generate(
            from_state, to_state, context_digest, tick
        )
        
        genesis_key = self.genesis_service.create_key(
            key_type=GenesisKeyType.SYSTEM_EVENT,
            what_description=f"State transition: {from_state} -> {to_state}",
            who_actor="genesis_bound_state_machine",
            why_reason=f"State machine '{self.name}' transition",
            how_method="GenesisBoundStateMachine.transition",
            input_data={
                "from_state": from_state,
                "to_state": to_state,
                "context_digest": context_digest,
                "transition_id": transition_id,
                "tick": tick
            },
            parent_key_id=self.workflow_key_id,
            context_data=context
        )
        
        self.current_state = to_state
        
        transition_record = StateTransition(
            transition_id=transition_id,
            from_state=from_state,
            to_state=to_state,
            context_digest=context_digest,
            tick=tick,
            genesis_key_id=genesis_key.key_id
        )
        self.history.append(transition_record)
        
        return TransitionResult.SUCCESS, genesis_key.key_id
    
    def get_history(self) -> List[StateTransition]:
        return list(self.history)
    
    def get_state(self) -> str:
        return self.current_state


class DeterministicExecutionContext:
    """
    Scoped context for a deterministic run.
    
    All operations within context use the same clock and parent key.
    """
    
    def __init__(
        self,
        goal: str,
        genesis_service: GenesisKeyService,
        parent_key_id: Optional[str] = None
    ):
        self.goal = goal
        self.genesis_service = genesis_service
        self.parent_key_id = parent_key_id
        self.logical_clock = LogicalClock()
        self.id_generator = DeterministicIDGenerator(namespace="dex")
        self._run_key: Optional[Any] = None
        self._operations: List[str] = []
    
    @property
    def run_id(self) -> str:
        return self.id_generator.generate(self.goal)
    
    @property
    def genesis_parent_key(self) -> Optional[str]:
        return self._run_key.key_id if self._run_key else None
    
    def __enter__(self) -> "DeterministicExecutionContext":
        self._run_key = self.genesis_service.create_key(
            key_type=GenesisKeyType.SYSTEM_EVENT,
            what_description=f"Deterministic run started: {self.goal}",
            who_actor="deterministic_execution_context",
            why_reason=self.goal,
            how_method="DeterministicExecutionContext.__enter__",
            input_data={
                "run_id": self.run_id,
                "goal": self.goal,
                "start_tick": self.logical_clock.tick
            },
            parent_key_id=self.parent_key_id
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_tick = self.logical_clock.increment()
        
        if exc_type is not None:
            self.genesis_service.create_key(
                key_type=GenesisKeyType.ERROR,
                what_description=f"Deterministic run failed: {self.goal}",
                who_actor="deterministic_execution_context",
                why_reason="Execution context error",
                how_method="DeterministicExecutionContext.__exit__",
                is_error=True,
                error_type=exc_type.__name__ if exc_type else None,
                error_message=str(exc_val) if exc_val else None,
                output_data={
                    "run_id": self.run_id,
                    "end_tick": end_tick,
                    "operations_count": len(self._operations)
                },
                parent_key_id=self.genesis_parent_key
            )
        else:
            self.genesis_service.create_key(
                key_type=GenesisKeyType.SYSTEM_EVENT,
                what_description=f"Deterministic run completed: {self.goal}",
                who_actor="deterministic_execution_context",
                why_reason="Run completed successfully",
                how_method="DeterministicExecutionContext.__exit__",
                output_data={
                    "run_id": self.run_id,
                    "end_tick": end_tick,
                    "operations_count": len(self._operations)
                },
                parent_key_id=self.genesis_parent_key
            )
        
        return False
    
    def wrap_operation(
        self,
        operation_name: str,
        operation_callable: Callable,
        key_type: GenesisKeyType = GenesisKeyType.SYSTEM_EVENT
    ) -> GenesisBoundOperation:
        """
        Wrap an operation to use this context's clock and parent key.
        """
        self._operations.append(operation_name)
        return GenesisBoundOperation(
            operation_name=operation_name,
            genesis_service=self.genesis_service,
            operation_callable=operation_callable,
            key_type=key_type
        )
    
    def execute(
        self,
        operation_name: str,
        operation_callable: Callable,
        *args,
        key_type: GenesisKeyType = GenesisKeyType.SYSTEM_EVENT,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Tuple[Any, str]:
        """
        Execute an operation within this context.
        """
        bound_op = self.wrap_operation(operation_name, operation_callable, key_type)
        return bound_op.execute(
            *args,
            logical_clock=self.logical_clock,
            parent_key_id=self.genesis_parent_key,
            context=context,
            **kwargs
        )


def bind_to_genesis(
    operation: Callable,
    genesis_service: Optional[GenesisKeyService] = None,
    operation_name: Optional[str] = None,
    key_type: GenesisKeyType = GenesisKeyType.SYSTEM_EVENT
) -> GenesisBoundOperation:
    """
    Wrap an existing operation with Genesis Key tracking.
    
    Args:
        operation: The operation to wrap
        genesis_service: Optional Genesis service (uses global if not provided)
        operation_name: Optional name (uses function name if not provided)
        key_type: Type of Genesis Key to create
        
    Returns:
        GenesisBoundOperation wrapping the operation
    """
    service = genesis_service or get_genesis_service()
    name = operation_name or getattr(operation, "__name__", "anonymous_operation")
    
    return GenesisBoundOperation(
        operation_name=name,
        genesis_service=service,
        operation_callable=operation,
        key_type=key_type
    )


def create_deterministic_run(
    goal: str,
    genesis_service: Optional[GenesisKeyService] = None,
    parent_key_id: Optional[str] = None
) -> DeterministicExecutionContext:
    """
    Create a new deterministic run context.
    
    Args:
        goal: Description of the run's goal
        genesis_service: Optional Genesis service (uses global if not provided)
        parent_key_id: Optional parent key for hierarchical tracking
        
    Returns:
        DeterministicExecutionContext for use with 'with' statement
    """
    service = genesis_service or get_genesis_service()
    
    return DeterministicExecutionContext(
        goal=goal,
        genesis_service=service,
        parent_key_id=parent_key_id
    )
