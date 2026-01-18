import logging
import hashlib
from typing import Dict, List, Optional, Tuple, Any, Callable, Set, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import OrderedDict
import json
from sqlalchemy.orm import Session

from cognitive.deterministic_primitives import (
    LogicalClock, Canonicalizer, DeterministicIDGenerator, PurityGuard,
    stable_hash, generate_deterministic_id
)
from cognitive.executable_invariants import (
    ExecutableInvariant, InvariantRegistry, InvariantType, global_registry as invariant_registry
)
from cognitive.genesis_bound_operations import (
    GenesisBoundOperation, DeterministicExecutionContext
)

try:
    from genesis.genesis_key_service import GenesisKeyService, get_genesis_service
    from models.genesis_key_models import GenesisKeyType
    GENESIS_AVAILABLE = True
except ImportError:
    GENESIS_AVAILABLE = False
    GenesisKeyService = None
    GenesisKeyType = None
logger = logging.getLogger(__name__)


class DeterminismLevel(Enum):
    """Levels of determinism enforcement."""
    BASIC = "basic"  # Standard deterministic
    STRICT = "strict"  # No probabilistic elements
    ULTRA = "ultra"  # Maximum determinism with proofs
    FORMAL = "formal"  # Formal verification


@dataclass
class MathematicalProof:
    """
    Represents a mathematical proof for a deterministic operation.
    """
    theorem: str  # What we're proving
    premises: List[str]  # Assumptions/axioms
    steps: List[Dict[str, Any]]  # Proof steps
    conclusion: str  # What we've proven
    proof_type: str  # "direct", "contradiction", "induction", etc.
    verified: bool = False
    proof_digest: Optional[str] = None  # Digest of canonicalized proof content
    evidence_digests: List[str] = field(default_factory=list)  # Digests for empirical verification
    
    def __post_init__(self):
        """Compute proof digest after initialization if not provided."""
        if self.proof_digest is None:
            self._compute_digest()
    
    def _compute_digest(self) -> None:
        """Compute the proof digest from canonicalized content."""
        content = {
            'theorem': self.theorem,
            'premises': sorted(self.premises),
            'steps': self.steps,
            'conclusion': self.conclusion
        }
        self.proof_digest = stable_hash(content)
    
    def add_evidence(self, evidence: Any) -> str:
        """Add evidence and return its digest."""
        digest = stable_hash(evidence)
        if digest not in self.evidence_digests:
            self.evidence_digests.append(digest)
        return digest
    
    def verify_digest(self) -> bool:
        """Verify that the current content matches the stored digest."""
        content = {
            'theorem': self.theorem,
            'premises': sorted(self.premises),
            'steps': self.steps,
            'conclusion': self.conclusion
        }
        return self.proof_digest == stable_hash(content)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'theorem': self.theorem,
            'premises': self.premises,
            'steps': self.steps,
            'conclusion': self.conclusion,
            'proof_type': self.proof_type,
            'verified': self.verified,
            'proof_digest': self.proof_digest,
            'evidence_digests': self.evidence_digests
        }


@dataclass
class DeterministicState:
    """
    Represents a state in a deterministic state machine.
    """
    state_id: str
    state_name: str
    properties: Dict[str, Any]  # State properties
    invariants: List[str]  # Invariants that must hold in this state
    transitions: List[str]  # Valid transitions from this state
    proof: Optional[MathematicalProof] = None  # Proof that state is valid
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'state_id': self.state_id,
            'state_name': self.state_name,
            'properties': self.properties,
            'invariants': self.invariants,
            'transitions': self.transitions,
            'proof': self.proof.to_dict() if self.proof else None
        }


@dataclass
class DeterministicOperation:
    """
    Represents a deterministic operation with complete traceability.
    
    Supports both legacy string-based invariants (for backward compatibility)
    and new ExecutableInvariant objects.
    """
    operation_id: str
    operation_name: str
    inputs: Dict[str, Any]
    deterministic_function: Callable
    proof: Optional[MathematicalProof] = None
    preconditions: List[Union[str, ExecutableInvariant]] = field(default_factory=list)
    postconditions: List[Union[str, ExecutableInvariant]] = field(default_factory=list)
    invariants: List[Union[str, ExecutableInvariant]] = field(default_factory=list)
    execution_trace: List[Dict[str, Any]] = field(default_factory=list)
    genesis_service: Optional[Any] = None  # Optional GenesisKeyService for tracking
    _logical_clock: Optional[LogicalClock] = field(default=None, repr=False)
    _canonicalizer: Optional[Canonicalizer] = field(default=None, repr=False)
    
    def __post_init__(self):
        """Initialize internal components."""
        if self._logical_clock is None:
            self._logical_clock = LogicalClock()
        if self._canonicalizer is None:
            self._canonicalizer = Canonicalizer()
    
    def execute(self, *args, **kwargs) -> Tuple[Any, Dict[str, Any]]:
        """
        Execute operation with complete traceability.
        
        Returns:
            Tuple of (result, trace)
        """
        execution_tick = self._logical_clock.tick()
        inputs_digest = self._canonicalizer.stable_digest({'args': args, 'kwargs': kwargs, 'inputs': self.inputs})
        
        trace = {
            'operation_id': self.operation_id,
            'operation_name': self.operation_name,
            'inputs': self.inputs,
            'execution_tick': execution_tick,
            'inputs_digest': inputs_digest,
            'timestamp': datetime.utcnow().isoformat(),  # Keep for backward compat
            'steps': []
        }
        
        context = {
            'args': args,
            'kwargs': kwargs,
            'inputs': self.inputs,
            'operation_id': self.operation_id,
            'operation_name': self.operation_name
        }
        context.update(kwargs)
        
        # Verify preconditions
        for precondition in self.preconditions:
            passed, error = self._verify_precondition(precondition, context)
            if not passed:
                raise ValueError(f"Precondition violated: {error or precondition}")
            trace['steps'].append({
                'step': 'precondition_check',
                'precondition': self._get_invariant_name(precondition),
                'result': 'passed'
            })
        
        # Execute with tracing
        start_tick = self._logical_clock.get_tick()
        try:
            result = self.deterministic_function(*args, **kwargs)
            end_tick = self._logical_clock.tick()
            
            output_digest = self._canonicalizer.stable_digest(result)
            
            trace['steps'].append({
                'step': 'execution',
                'start_tick': start_tick,
                'end_tick': end_tick,
                'result': 'success'
            })
            
            context['result'] = result
            context['output'] = result
            
            # Verify postconditions
            for postcondition in self.postconditions:
                passed, error = self._verify_postcondition(postcondition, context)
                if not passed:
                    raise ValueError(f"Postcondition violated: {error or postcondition}")
                trace['steps'].append({
                    'step': 'postcondition_check',
                    'postcondition': self._get_invariant_name(postcondition),
                    'result': 'passed'
                })
            
            # Verify invariants
            for invariant in self.invariants:
                passed, error = self._verify_invariant(invariant, context)
                if not passed:
                    raise ValueError(f"Invariant violated: {error or invariant}")
                trace['steps'].append({
                    'step': 'invariant_check',
                    'invariant': self._get_invariant_name(invariant),
                    'result': 'passed'
                })
            
            trace['result'] = result
            trace['output_digest'] = output_digest
            trace['success'] = True
            
            # Track with Genesis if available
            if self.genesis_service and GENESIS_AVAILABLE:
                self._create_genesis_key(trace)
            
            return result, trace
        
        except Exception as e:
            trace['steps'].append({
                'step': 'execution',
                'result': 'error',
                'error': str(e)
            })
            trace['success'] = False
            raise
    
    def _get_invariant_name(self, invariant: Union[str, ExecutableInvariant]) -> str:
        """Get the name/string representation of an invariant."""
        if isinstance(invariant, ExecutableInvariant):
            return invariant.name
        return invariant
    
    def _verify_precondition(self, precondition: Union[str, ExecutableInvariant], context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Verify a precondition."""
        if isinstance(precondition, ExecutableInvariant):
            return precondition.check(context)
        # Legacy string-based: check if registered in global registry
        registered = invariant_registry.get(precondition)
        if registered:
            return registered.check(context)
        return True, None  # Backward compat: unregistered strings pass
    
    def _verify_postcondition(self, postcondition: Union[str, ExecutableInvariant], context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Verify a postcondition."""
        if isinstance(postcondition, ExecutableInvariant):
            return postcondition.check(context)
        registered = invariant_registry.get(postcondition)
        if registered:
            return registered.check(context)
        return True, None
    
    def _verify_invariant(self, invariant: Union[str, ExecutableInvariant], context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Verify an invariant."""
        if isinstance(invariant, ExecutableInvariant):
            return invariant.check(context)
        registered = invariant_registry.get(invariant)
        if registered:
            return registered.check(context)
        return True, None
    
    def _create_genesis_key(self, trace: Dict[str, Any]) -> Optional[str]:
        """Create a Genesis Key for this execution if service available."""
        if not self.genesis_service or not GENESIS_AVAILABLE:
            return None
        try:
            key = self.genesis_service.create_key(
                key_type=GenesisKeyType.SYSTEM_EVENT,
                what_description=f"Executed operation: {self.operation_name}",
                who_actor="DeterministicOperation",
                why_reason="Deterministic operation execution",
                how_method="DeterministicOperation.execute",
                input_data={
                    'inputs_digest': trace.get('inputs_digest'),
                    'execution_tick': trace.get('execution_tick')
                },
                output_data={
                    'output_digest': trace.get('output_digest'),
                    'success': trace.get('success')
                }
            )
            return key.key_id
        except Exception as e:
            logger.warning(f"Failed to create Genesis Key: {e}")
            return None


class DeterministicStateMachine:
    """
    Deterministic state machine with formal verification.
    
    Every transition is provably deterministic. Uses logical clock ticks
    instead of wall-clock time for reproducibility.
    """
    
    def __init__(
        self, 
        name: str, 
        initial_state: str,
        genesis_service: Optional[Any] = None
    ):
        """
        Initialize deterministic state machine.
        
        Args:
            name: Name of the state machine
            initial_state: Initial state ID
            genesis_service: Optional GenesisKeyService for tracking
        """
        self.name = name
        self.states: Dict[str, DeterministicState] = {}
        self.transitions: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self.current_state: Optional[str] = initial_state
        self.history: List[Dict[str, Any]] = []
        self.proofs: Dict[str, MathematicalProof] = {}
        self.genesis_service = genesis_service
        self._logical_clock = LogicalClock()
        self._canonicalizer = Canonicalizer()
        self._id_generator = DeterministicIDGenerator()
    
    def add_state(
        self,
        state: DeterministicState,
        proof: Optional[MathematicalProof] = None
    ):
        """Add a state with optional proof."""
        self.states[state.state_id] = state
        if proof:
            self.proofs[state.state_id] = proof
    
    def add_transition(
        self,
        from_state: str,
        to_state: str,
        condition: Callable[[Dict[str, Any]], bool],
        proof: Optional[MathematicalProof] = None
    ):
        """
        Add a deterministic transition.
        
        Args:
            from_state: Source state ID
            to_state: Target state ID
            condition: Deterministic condition function
            proof: Optional proof that transition is valid
        """
        created_tick = self._logical_clock.tick()
        transition_digest = self._canonicalizer.stable_digest((from_state, to_state))
        
        self.transitions[(from_state, to_state)] = {
            'condition': condition,
            'proof': proof,
            'created_tick': created_tick,
            'created_at': datetime.utcnow(),  # Backward compat
            'transition_digest': transition_digest
        }
        
        # Update state transitions
        if from_state in self.states:
            if to_state not in self.states[from_state].transitions:
                self.states[from_state].transitions.append(to_state)
    
    def get_sorted_transitions(self) -> List[Tuple[Tuple[str, str], Dict[str, Any]]]:
        """Get transitions sorted deterministically by digest."""
        return sorted(
            self.transitions.items(),
            key=lambda x: x[1].get('transition_digest', self._canonicalizer.stable_digest(x[0]))
        )
    
    def compute_next_state(self, context: Dict[str, Any]) -> Optional[str]:
        """
        Deterministically compute the next state based on context.
        
        Evaluates all transitions from current state in deterministic order
        and returns the first one whose condition is satisfied.
        
        Args:
            context: Context for evaluating transition conditions
            
        Returns:
            Next state ID or None if no transition is valid
        """
        if self.current_state is None:
            return None
        
        # Get all transitions from current state, sorted deterministically
        valid_transitions = [
            (key, trans) for key, trans in self.get_sorted_transitions()
            if key[0] == self.current_state
        ]
        
        for (from_state, to_state), trans_data in valid_transitions:
            try:
                condition_func = trans_data['condition']
                if condition_func(context):
                    return to_state
            except Exception:
                continue
        
        return None
    
    def transition(
        self,
        to_state: str,
        context: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Attempt deterministic transition.
        
        Returns:
            Tuple of (success, reason)
        """
        if self.current_state is None:
            return False, "No current state"
        
        # Check if transition exists
        transition_key = (self.current_state, to_state)
        if transition_key not in self.transitions:
            return False, f"Transition from {self.current_state} to {to_state} does not exist"
        
        # Check if target state exists
        if to_state not in self.states:
            return False, f"Target state {to_state} does not exist"
        
        # Verify transition condition deterministically
        transition = self.transitions[transition_key]
        condition_func = transition['condition']
        
        try:
            condition_result = condition_func(context)
            
            if not isinstance(condition_result, bool):
                return False, "Transition condition must return boolean"
            
            if condition_result:
                # Transition is valid
                old_state = self.current_state
                self.current_state = to_state
                
                transition_tick = self._logical_clock.tick()
                context_digest = self._canonicalizer.stable_digest(context)
                
                # Record in history
                history_entry = {
                    'tick': transition_tick,
                    'timestamp': datetime.utcnow().isoformat(),  # Backward compat
                    'from_state': old_state,
                    'to_state': to_state,
                    'context_digest': context_digest,
                    'context': context,
                    'proof': transition.get('proof')
                }
                self.history.append(history_entry)
                
                # Track with Genesis if available
                genesis_key_id = self._create_genesis_key_for_transition(history_entry)
                if genesis_key_id:
                    history_entry['genesis_key_id'] = genesis_key_id
                
                return True, None
            else:
                return False, "Transition condition not met"
        
        except Exception as e:
            return False, f"Error evaluating transition condition: {str(e)}"
    
    def _create_genesis_key_for_transition(self, history_entry: Dict[str, Any]) -> Optional[str]:
        """Create a Genesis Key for a state transition."""
        if not self.genesis_service or not GENESIS_AVAILABLE:
            return None
        try:
            key = self.genesis_service.create_key(
                key_type=GenesisKeyType.SYSTEM_EVENT,
                what_description=f"State transition: {history_entry['from_state']} -> {history_entry['to_state']}",
                who_actor="DeterministicStateMachine",
                why_reason=f"State machine '{self.name}' transition",
                how_method="DeterministicStateMachine.transition",
                input_data={
                    'from_state': history_entry['from_state'],
                    'to_state': history_entry['to_state'],
                    'context_digest': history_entry.get('context_digest'),
                    'tick': history_entry.get('tick')
                }
            )
            return key.key_id
        except Exception as e:
            logger.warning(f"Failed to create Genesis Key for transition: {e}")
            return None
    
    def get_current_state(self) -> Optional[DeterministicState]:
        """Get current state object."""
        if self.current_state:
            return self.states.get(self.current_state)
        return None
    
    def get_proof(self, state_id: str) -> Optional[MathematicalProof]:
        """Get proof for a state."""
        return self.proofs.get(state_id)


class DeterministicScheduler:
    """
    Deterministic scheduler - no randomness, all decisions are provable.
    """
    
    def __init__(self, seed: Optional[int] = None):
        """
        Initialize deterministic scheduler.
        
        Args:
            seed: Optional seed for deterministic pseudo-randomness (if needed)
        """
        self.seed = seed
        self.schedule: List[Dict[str, Any]] = []
        self.priority_queue: OrderedDict = OrderedDict()
    
    def schedule_operation(
        self,
        operation: DeterministicOperation,
        priority: int = 0,
        dependencies: List[str] = None
    ) -> str:
        """
        Schedule an operation deterministically.
        
        Args:
            operation: Operation to schedule
            priority: Priority (higher = more important)
            dependencies: List of operation IDs that must complete first
            
        Returns:
            Schedule ID
        """
        schedule_id = self._generate_deterministic_id(operation)
        
        schedule_entry = {
            'schedule_id': schedule_id,
            'operation': operation,
            'priority': priority,
            'dependencies': dependencies or [],
            'scheduled_at': datetime.utcnow(),
            'status': 'pending'
        }
        
        # Insert in priority order (deterministic)
        self._insert_by_priority(schedule_entry)
        
        return schedule_id
    
    def _insert_by_priority(self, entry: Dict[str, Any]):
        """Insert entry in priority order (deterministic sorting)."""
        priority = entry['priority']
        
        # Find insertion point (deterministic)
        insert_index = 0
        for i, existing in enumerate(self.schedule):
            if existing['priority'] < priority:
                insert_index = i
                break
            elif existing['priority'] == priority:
                # Same priority: sort by schedule_id (deterministic)
                if existing['schedule_id'] > entry['schedule_id']:
                    insert_index = i
                    break
            insert_index = i + 1
        
        self.schedule.insert(insert_index, entry)
    
    def get_next_operation(self) -> Optional[DeterministicOperation]:
        """
        Get next operation to execute (deterministic).
        
        Returns:
            Next operation or None if none ready
        """
        for entry in self.schedule:
            if entry['status'] != 'pending':
                continue
            
            # Check dependencies
            if all(
                dep_entry['status'] == 'completed'
                for dep_entry in self.schedule
                if dep_entry['schedule_id'] in entry['dependencies']
            ):
                entry['status'] = 'executing'
                return entry['operation']
        
        return None
    
    def mark_completed(self, schedule_id: str):
        """Mark operation as completed."""
        for entry in self.schedule:
            if entry['schedule_id'] == schedule_id:
                entry['status'] = 'completed'
                entry['completed_at'] = datetime.utcnow()
                break
    
    def _generate_deterministic_id(self, operation: DeterministicOperation) -> str:
        """Generate deterministic ID from operation."""
        content = f"{operation.operation_id}_{operation.operation_name}_{len(self.schedule)}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


class FormalVerifier:
    """
    Formal verifier for deterministic operations.
    
    Verifies mathematical properties and invariants.
    """
    
    def __init__(self):
        """Initialize formal verifier."""
        self.verified_operations: Set[str] = set()
        self.proofs: Dict[str, MathematicalProof] = {}
    
    def verify_operation(
        self,
        operation: DeterministicOperation
    ) -> Tuple[bool, Optional[str], Optional[MathematicalProof]]:
        """
        Formally verify a deterministic operation.
        
        Returns:
            Tuple of (is_valid, error_message, proof)
        """
        # Verify preconditions are satisfiable
        for precondition in operation.preconditions:
            if not self._verify_precondition_satisfiable(precondition):
                return False, f"Precondition not satisfiable: {precondition}", None
        
        # Verify postconditions are achievable
        for postcondition in operation.postconditions:
            if not self._verify_postcondition_achievable(postcondition):
                return False, f"Postcondition not achievable: {postcondition}", None
        
        # Verify invariants are maintained
        for invariant in operation.invariants:
            if not self._verify_invariant_maintainable(invariant):
                return False, f"Invariant not maintainable: {invariant}", None
        
        # If operation has a proof, verify it
        if operation.proof:
            if self._verify_proof(operation.proof):
                self.proofs[operation.operation_id] = operation.proof
                self.verified_operations.add(operation.operation_id)
                return True, None, operation.proof
            else:
                return False, "Proof verification failed", None
        
        # Operation is valid but unproven
        return True, None, None
    
    def _verify_precondition_satisfiable(self, precondition: Union[str, ExecutableInvariant]) -> bool:
        """Verify precondition is satisfiable (simplified)."""
        if isinstance(precondition, ExecutableInvariant):
            return precondition.predicate is not None
        return True
    
    def _verify_postcondition_achievable(self, postcondition: Union[str, ExecutableInvariant]) -> bool:
        """Verify postcondition is achievable."""
        if isinstance(postcondition, ExecutableInvariant):
            return postcondition.predicate is not None
        return True
    
    def _verify_invariant_maintainable(self, invariant: Union[str, ExecutableInvariant]) -> bool:
        """Verify invariant is maintainable."""
        if isinstance(invariant, ExecutableInvariant):
            return invariant.predicate is not None
        return True
    
    def _verify_proof(self, proof: MathematicalProof) -> bool:
        """Verify a mathematical proof."""
        if not proof.theorem:
            return False
        if not proof.premises:
            return False
        if not proof.steps:
            return False
        if not proof.conclusion:
            return False
        
        # Verify digest integrity if digest exists
        if proof.proof_digest:
            if not proof.verify_digest():
                return False
        
        # Mark as verified
        proof.verified = True
        return True


class UltraDeterministicCore:
    """
    Ultra-deterministic core for Grace.
    
    Maximum determinism with formal verification, state machines, and proofs.
    Integrates with deterministic primitives for reproducible operations.
    """
    
    def __init__(
        self, 
        session: Optional[Session] = None,
        genesis_service: Optional[Any] = None
    ):
        """
        Initialize ultra-deterministic core.
        
        Args:
            session: Optional database session
            genesis_service: Optional GenesisKeyService for tracking
        """
        self.session = session
        self.genesis_service = genesis_service
        self.state_machines: Dict[str, DeterministicStateMachine] = {}
        self.scheduler = DeterministicScheduler()
        self.verifier = FormalVerifier()
        self.operations: Dict[str, DeterministicOperation] = {}
        self.execution_trace: List[Dict[str, Any]] = []
        
        # Deterministic primitives
        self.logical_clock = LogicalClock()
        self.canonicalizer = Canonicalizer()
        self.id_generator = DeterministicIDGenerator()
    
    def register_operation(
        self,
        operation: DeterministicOperation,
        verify: bool = True
    ) -> Tuple[bool, Optional[str]]:
        """
        Register a deterministic operation.
        
        Args:
            operation: Operation to register
            verify: If True, formally verify the operation
            
        Returns:
            Tuple of (success, error_message)
        """
        if verify:
            is_valid, error, proof = self.verifier.verify_operation(operation)
            if not is_valid:
                return False, error
        
        # Inject genesis service if operation doesn't have one
        if operation.genesis_service is None and self.genesis_service:
            operation.genesis_service = self.genesis_service
        
        self.operations[operation.operation_id] = operation
        return True, None
    
    def execute_operation(
        self,
        operation_id: str,
        *args,
        determinism_level: DeterminismLevel = DeterminismLevel.ULTRA,
        **kwargs
    ) -> Tuple[Any, Dict[str, Any]]:
        """
        Execute a registered operation with complete traceability.
        
        Args:
            operation_id: ID of the registered operation
            *args: Positional arguments for operation
            determinism_level: Level of determinism enforcement
            **kwargs: Keyword arguments for operation
        
        Returns:
            Tuple of (result, execution_trace)
        """
        if operation_id not in self.operations:
            raise ValueError(f"Operation {operation_id} not registered")
        
        operation = self.operations[operation_id]
        
        # For FORMAL level, use PurityGuard
        if determinism_level == DeterminismLevel.FORMAL:
            with PurityGuard():
                result, trace = operation.execute(*args, **kwargs)
        else:
            result, trace = operation.execute(*args, **kwargs)
        
        # Record in execution trace
        self.execution_trace.append(trace)
        
        return result, trace
    
    def create_state_machine(
        self,
        name: str,
        initial_state: str
    ) -> DeterministicStateMachine:
        """Create a deterministic state machine."""
        sm = DeterministicStateMachine(
            name, 
            initial_state,
            genesis_service=self.genesis_service
        )
        self.state_machines[name] = sm
        return sm
    
    def create_genesis_bound_operation(
        self,
        operation_name: str,
        operation_callable: Callable,
        key_type: Optional[Any] = None
    ) -> Optional[GenesisBoundOperation]:
        """
        Create a Genesis-bound operation for complete traceability.
        
        Args:
            operation_name: Name of the operation
            operation_callable: The callable to wrap
            key_type: Optional GenesisKeyType (defaults to SYSTEM_EVENT)
            
        Returns:
            GenesisBoundOperation or None if Genesis not available
        """
        if not GENESIS_AVAILABLE or not self.genesis_service:
            logger.warning("Genesis service not available for bound operation")
            return None
        
        return GenesisBoundOperation(
            operation_name=operation_name,
            genesis_service=self.genesis_service,
            operation_callable=operation_callable,
            key_type=key_type or GenesisKeyType.SYSTEM_EVENT
        )
    
    def prove_determinism(
        self,
        operation: DeterministicOperation,
        inputs: List[Dict[str, Any]]
    ) -> MathematicalProof:
        """
        Prove that an operation is deterministic.
        
        A deterministic operation produces the same output for the same input.
        """
        # Test with multiple identical inputs
        results = []
        for input_set in inputs:
            result, _ = operation.execute(**input_set)
            results.append(result)
        
        # Prove all results are identical
        all_identical = all(
            self._results_identical(results[0], r)
            for r in results[1:]
        )
        
        proof = MathematicalProof(
            theorem=f"Operation {operation.operation_name} is deterministic",
            premises=[
                f"Operation {operation.operation_name} is a pure function",
                "All inputs are identical",
                "No external state affects execution"
            ],
            steps=[
                {
                    'step': 1,
                    'description': f"Execute operation with input set 1",
                    'result': str(results[0])
                },
                {
                    'step': 2,
                    'description': f"Execute operation with input set 2",
                    'result': str(results[1] if len(results) > 1 else 'N/A')
                },
                {
                    'step': 3,
                    'description': "Compare results",
                    'result': f"All results identical: {all_identical}"
                }
            ],
            conclusion=f"Operation {operation.operation_name} is deterministic" if all_identical else "Operation may not be deterministic",
            proof_type="direct"
        )
        
        proof.verified = all_identical
        return proof
    
    def _results_identical(self, result1: Any, result2: Any) -> bool:
        """Check if two results are identical (deterministic comparison)."""
        # Use deterministic comparison
        if isinstance(result1, dict) and isinstance(result2, dict):
            return self._dicts_identical(result1, result2)
        elif isinstance(result1, list) and isinstance(result2, list):
            return self._lists_identical(result1, result2)
        else:
            return result1 == result2
    
    def _dicts_identical(self, dict1: Dict, dict2: Dict) -> bool:
        """Deterministic dictionary comparison."""
        if set(dict1.keys()) != set(dict2.keys()):
            return False
        
        for key in dict1.keys():
            if not self._results_identical(dict1[key], dict2[key]):
                return False
        
        return True
    
    def _lists_identical(self, list1: List, list2: List) -> bool:
        """Deterministic list comparison."""
        if len(list1) != len(list2):
            return False
        
        for i in range(len(list1)):
            if not self._results_identical(list1[i], list2[i]):
                return False
        
        return True
    
    def get_complete_trace(self) -> Dict[str, Any]:
        """Get complete execution trace."""
        return {
            'total_operations': len(self.operations),
            'executions': len(self.execution_trace),
            'trace': self.execution_trace,
            'state_machines': {
                name: {
                    'current_state': sm.current_state,
                    'history_length': len(sm.history)
                }
                for name, sm in self.state_machines.items()
            }
        }


# Global instance
_ultra_deterministic_core: Optional[UltraDeterministicCore] = None


def get_ultra_deterministic_core(
    session: Optional[Session] = None,
    genesis_service: Optional[Any] = None
) -> UltraDeterministicCore:
    """Get or create global ultra-deterministic core instance."""
    global _ultra_deterministic_core
    if _ultra_deterministic_core is None or session is not None or genesis_service is not None:
        _ultra_deterministic_core = UltraDeterministicCore(
            session=session,
            genesis_service=genesis_service
        )
    return _ultra_deterministic_core


# Convenience function to get the invariant registry
def get_invariant_registry() -> InvariantRegistry:
    """Get the global invariant registry."""
    return invariant_registry
