# Deterministic Logic Improvements

## Summary

All deterministic logic has been enhanced with proper primitives, eliminating hidden nondeterminism and adding real enforcement.

## New Files Created

### 1. `backend/cognitive/deterministic_primitives.py`
Core utilities for deterministic operations:

| Class | Purpose |
|-------|---------|
| **LogicalClock** | Monotonic tick counter (replaces `datetime.utcnow()`) |
| **Canonicalizer** | Stable JSON serialization + SHA256 hashing |
| **DeterministicIDGenerator** | Content-based IDs (replaces `uuid.uuid4()`) |
| **PurityGuard** | Context manager blocking nondeterministic calls |

```python
# Example usage
from cognitive.deterministic_primitives import LogicalClock, Canonicalizer, DeterministicIDGenerator

clock = LogicalClock()
tick = clock.tick()  # 1, 2, 3... (monotonic, no wall-clock)

canon = Canonicalizer()
digest = canon.stable_digest({'b': 2, 'a': 1})  # Same hash regardless of key order

gen = DeterministicIDGenerator()
id = gen.generate_id("EC", goal, constraints)  # Deterministic from content
```

### 2. `backend/cognitive/executable_invariants.py`
Real enforcement of pre/post conditions:

| Class | Purpose |
|-------|---------|
| **ExecutableInvariant** | Invariant with actual predicate function |
| **InvariantRegistry** | Register and check invariants by name |
| **InvariantBuilder** | Fluent API for building invariants |

```python
# Example usage
from cognitive.executable_invariants import ExecutableInvariant, InvariantType

invariant = ExecutableInvariant(
    name="trust_in_range",
    description="Trust score must be 0-1",
    invariant_type=InvariantType.POSTCONDITION,
    predicate=lambda ctx: 0 <= ctx.get('trust', 0) <= 1,
    error_message="Trust score out of range"
)

passed, error = invariant.check({'trust': 0.85})  # (True, None)
```

**Built-in Invariants:**
- `inputs_not_empty`
- `output_not_none`
- `trust_score_in_range`
- `genesis_key_valid`
- `state_id_exists`

### 3. `backend/cognitive/genesis_bound_operations.py`
Automatic Genesis Key tracking for operations:

| Class | Purpose |
|-------|---------|
| **GenesisBoundOperation** | Wraps operations with Genesis Key creation |
| **GenesisBoundStateMachine** | State machine with transition tracking |
| **DeterministicExecutionContext** | Scoped context for deterministic runs |

```python
# Example usage
from cognitive.genesis_bound_operations import DeterministicExecutionContext

with DeterministicExecutionContext(goal="fix bug", genesis_service=svc) as ctx:
    # All operations within context:
    # - Share same logical clock
    # - Link to parent Genesis Key
    # - Record input/output digests
    result = ctx.execute_operation(my_function, inputs)
```

## Files Updated

### `backend/cognitive/ultra_deterministic_core.py`
- `DeterministicOperation` now uses logical ticks instead of timestamps
- `_verify_precondition/postcondition/invariant` actually execute predicates
- Added `inputs_digest` and `output_digest` tracking
- `MathematicalProof` includes `proof_digest` for verification
- `DeterministicStateMachine` has `compute_next_state()` for deterministic transitions

### `backend/cognitive/deterministic_alternatives.py`
- `DeterministicSampler` uses `Canonicalizer` for stable hashing (fixes dict/set instability)
- `DeterministicRandomReplacement` has `stream_id` for counter persistence
- Fixed O(n²) → O(n) in `deterministic_sample()` using digest-based sets
- Added `DeterministicTraceStore` for efficient trace storage

### `backend/grace_os/deterministic_pipeline.py`
- `ExecutionContract.contract_id` is now content-based (not UUID)
- `PreCommitScore` uses `computed_tick` instead of `computed_at`
- Added `PipelineRun` dataclass for tracking complete runs
- `DeterministicCodePipeline` uses `DeterministicExecutionContext`

### `backend/cognitive/deterministic_stability_proof.py`
- `StabilityProof` includes `proof_digest` and `evidence_hashes`
- Added checks for logical clock consistency
- Added canonicalization stability verification
- Added Genesis Key chain verification
- Creates Genesis Key for each stability proof

## Issues Fixed

| Issue | Solution |
|-------|----------|
| `datetime.utcnow()` in traces | Replaced with `LogicalClock.tick()` |
| `uuid.uuid4()` in IDs | Replaced with content-based `DeterministicIDGenerator` |
| `str(item)` unstable hashing | Replaced with `Canonicalizer.stable_digest()` |
| Stub verifications (`return True`) | Real predicate execution via `ExecutableInvariant` |
| Counter not persisted | Added `stream_id` + `persist_counter()` |
| No Genesis Key binding | Added `GenesisBoundOperation` wrapper |

## Verification

All improvements pass verification:

```
LogicalClock: 1 < 2 < 3 ✓
Canonicalizer: same hash for different dict order ✓
DeterministicIDGenerator: same content = same ID ✓
PurityGuard: blocks datetime.utcnow ✓
ExecutableInvariant: predicate actually executes ✓
```

## Usage Guidelines

### For New Code
1. Use `LogicalClock` instead of `datetime.utcnow()` for ordering
2. Use `DeterministicIDGenerator` instead of `uuid.uuid4()` for IDs
3. Use `Canonicalizer.stable_digest()` for hashing complex objects
4. Wrap operations with `GenesisBoundOperation` for tracking
5. Define invariants as `ExecutableInvariant` with predicates

### For Formal Verification
Use `PurityGuard` to enforce purity:

```python
from cognitive.deterministic_primitives import PurityGuard

with PurityGuard():
    # This will raise RuntimeError if any nondeterministic
    # operation is called (datetime, uuid, random)
    result = deterministic_computation(inputs)
```

## Test File
`backend/tests/test_deterministic_improvements.py` - 43 test cases covering all improvements
