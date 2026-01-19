# Grace Cognitive Blueprint Integration Guide

This guide shows how to integrate the 12-invariant cognitive blueprint into Grace's existing systems.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     COGNITIVE ENGINE                            │
│  backend/cognitive/                                             │
│  ├── engine.py          (Central Cortex - OODA orchestration)  │
│  ├── ooda.py            (OODA Loop implementation)             │
│  ├── ambiguity.py       (Ambiguity accounting)                 │
│  ├── invariants.py      (Invariant validation)                 │
│  ├── decision_log.py    (Decision logging)                     │
│  └── decorators.py      (Integration helpers)                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   EXISTING GRACE SYSTEMS                        │
│  • Ingestion Pipeline (backend/ingestion/)                     │
│  • Retrieval System (backend/retrieval/)                       │
│  • Telemetry (backend/telemetry/)                              │
│  • API Endpoints (backend/api/)                                │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start: Using Decorators

The easiest way to integrate cognitive enforcement is through decorators:

### Example 1: Simple Operation

```python
from cognitive.decorators import cognitive_operation

@cognitive_operation(
    "process_document",
    is_reversible=True,
    impact_scope="local"
)
def process_document(filepath: str) -> dict:
    """Process a document with cognitive enforcement."""
    # Your implementation
    result = extract_text(filepath)
    return {"status": "success", "chunks": len(result)}
```

### Example 2: Safety-Critical Operation

```python
from cognitive.decorators import (
    cognitive_operation,
    requires_determinism,
    enforce_reversibility
)

@cognitive_operation(
    "update_database_schema",
    requires_determinism=True,
    is_safety_critical=True,
    is_reversible=False,
    impact_scope="systemic"
)
@requires_determinism
@enforce_reversibility(
    reversible=False,
    justification="Database schema changes cannot be auto-reversed"
)
def update_database_schema(migration_script: str) -> dict:
    """Update database schema with strict enforcement."""
    # Your implementation
    execute_migration(migration_script)
    return {"status": "migrated"}
```

### Example 3: Time-Bounded Operation

```python
from cognitive.decorators import cognitive_operation, time_bounded

@cognitive_operation(
    "analyze_large_dataset",
    is_reversible=True,
    impact_scope="component"
)
@time_bounded(timeout_seconds=60)
def analyze_large_dataset(data: list) -> dict:
    """Analyze dataset with time bounds."""
    # Implementation must complete within 60 seconds
    results = perform_analysis(data)
    return {"analysis": results}
```

## Advanced: Using the Cognitive Engine Directly

For complex decision-making, use the cognitive engine directly:

```python
from cognitive import CognitiveEngine, DecisionContext
from cognitive.decorators import with_ambiguity_tracking

def ingest_document_with_rag(filepath: str) -> dict:
    """
    Ingest a document using full cognitive enforcement.

    This example demonstrates all 12 invariants in action.
    """
    # Initialize cognitive engine
    engine = CognitiveEngine(enable_strict_mode=True)

    # ==================== INVARIANT 1: OODA LOOP ====================
    # Begin decision with clear problem statement
    context = engine.begin_decision(
        problem_statement=f"Ingest document {filepath} into knowledge base",
        goal="Successfully parse, chunk, embed, and store document",
        success_criteria=[
            "Document parsed without errors",
            "All chunks embedded successfully",
            "Metadata stored in database",
            "Vector store updated"
        ]
    )

    # ==================== INVARIANT 2: AMBIGUITY ACCOUNTING ====================
    # OBSERVE: Gather information
    observations = {
        'filepath': filepath,
        'file_exists': os.path.exists(filepath),
        'file_size': os.path.getsize(filepath) if os.path.exists(filepath) else None,
        'mime_type': get_mime_type(filepath) if os.path.exists(filepath) else None,
    }
    engine.observe(context, observations)

    # Track ambiguity
    context.ambiguity_ledger.add_known('filepath', filepath)

    if observations['file_exists']:
        context.ambiguity_ledger.add_known('file_size', observations['file_size'])
        context.ambiguity_ledger.add_inferred(
            'chunk_count_estimate',
            observations['file_size'] // 1000,
            confidence=0.6,
            notes="Rough estimate based on file size"
        )
    else:
        context.ambiguity_ledger.add_unknown(
            'file_content',
            blocking=True,  # Can't proceed without file
            notes="File does not exist"
        )

    # ==================== INVARIANT 3: REVERSIBILITY ====================
    context.is_reversible = True  # We can delete the ingested document

    # ==================== INVARIANT 4: DETERMINISM ====================
    context.requires_determinism = False  # Embeddings can be probabilistic
    context.is_safety_critical = False

    # ==================== INVARIANT 5: BLAST RADIUS ====================
    context.impact_scope = "component"  # Affects knowledge base component
    context.affected_files = [filepath]
    context.affected_dependencies = ['vector_db', 'database', 'embedding_model']

    # ORIENT: Understand constraints
    constraints = {
        'max_file_size': 100 * 1024 * 1024,  # 100MB
        'supported_formats': ['.pdf', '.txt', '.md', '.docx'],
        'safety_critical': False,
        'impact_scope': 'component'
    }

    context_info = {
        'vector_db_available': check_qdrant_connection(),
        'embedding_model_loaded': check_embedding_model(),
        'database_available': check_database_connection()
    }

    engine.orient(context, constraints, context_info)

    # Check for blocking unknowns
    if context.ambiguity_ledger.has_blocking_unknowns():
        engine.abort_decision(
            context,
            f"Blocking unknowns: {context.ambiguity_ledger.get_blocking_unknowns()}"
        )
        return {"status": "failed", "reason": "blocking unknowns"}

    # ==================== INVARIANT 7: SIMPLICITY ====================
    context.complexity_score = 3.0  # Moderate complexity (parse + embed + store)
    context.benefit_score = 5.0  # High benefit (adds knowledge to system)

    # ==================== INVARIANT 9: BOUNDED RECURSION ====================
    context.max_recursion_depth = 2  # Allow recursive directory traversal
    context.max_iterations = 5  # Max retries for embedding

    # ==================== INVARIANT 10: OPTIONALITY ====================
    context.preserves_future_options = True  # Can re-ingest or delete
    context.future_flexibility_metric = 0.9

    # ==================== INVARIANT 12: FORWARD SIMULATION ====================
    # DECIDE: Generate alternative execution paths
    def generate_alternatives():
        return [
            {
                'name': 'direct_ingestion',
                'immediate_value': 1.0,
                'future_options': 0.9,
                'simplicity': 1.0,
                'reversibility': 1.0,
                'complexity': 0.3,
                'steps': ['parse', 'chunk', 'embed', 'store']
            },
            {
                'name': 'staged_ingestion_with_validation',
                'immediate_value': 0.8,
                'future_options': 1.0,
                'simplicity': 0.7,
                'reversibility': 1.0,
                'complexity': 0.5,
                'steps': ['parse', 'validate', 'chunk', 'validate', 'embed', 'store']
            },
            {
                'name': 'async_ingestion',
                'immediate_value': 0.6,
                'future_options': 1.0,
                'simplicity': 0.5,
                'reversibility': 1.0,
                'complexity': 0.7,
                'steps': ['queue', 'parse_async', 'chunk_async', 'embed_async', 'store']
            }
        ]

    selected_path = engine.decide(context, generate_alternatives)

    # ==================== INVARIANT 6: OBSERVABILITY ====================
    # ==================== INVARIANT 8: FEEDBACK ====================
    # ACT: Execute with monitoring and feedback
    def action():
        # Actual ingestion logic
        result = execute_ingestion_pipeline(
            filepath=filepath,
            strategy=selected_path['name'],
            steps=selected_path['steps']
        )

        # Update context with results
        context.metadata['ingestion_result'] = result

        return result

    result = engine.act(context, action, dry_run=False)

    # ==================== INVARIANT 11: TIME-BOUNDED REASONING ====================
    # Decision was bounded by initial setup (no infinite planning)

    # Finalize decision
    engine.finalize_decision(context)

    return result
```

## Integration Points

### 1. Ingestion Pipeline

Modify [backend/ingestion/service.py](backend/ingestion/service.py):

```python
from cognitive.decorators import cognitive_operation, blast_radius

@cognitive_operation(
    "ingest_file",
    is_reversible=True,
    impact_scope="component"
)
@blast_radius("component")
def ingest_file(filepath: str, **kwargs) -> dict:
    # Existing ingestion logic
    pass
```

### 2. Retrieval System

Modify [backend/retrieval/retriever.py](backend/retrieval/retriever.py):

```python
from cognitive.decorators import cognitive_operation

@cognitive_operation(
    "retrieve_documents",
    requires_determinism=False,  # Semantic search is probabilistic
    is_reversible=True,
    impact_scope="local"
)
def retrieve(query: str, limit: int = 5) -> list:
    # Existing retrieval logic
    pass
```

### 3. API Endpoints

Modify [backend/app.py](backend/app.py) chat endpoint:

```python
from cognitive import CognitiveEngine

@app.post("/chats/{chat_id}/prompt")
async def send_prompt(chat_id: int, request: PromptRequest):
    engine = CognitiveEngine()

    context = engine.begin_decision(
        problem_statement=f"Generate response to: {request.content}",
        goal="Provide accurate response using only knowledge base",
        success_criteria=[
            "Response based on retrieved context",
            "No hallucination",
            "Sources cited"
        ]
    )

    # Observe: Collect query and context
    engine.observe(context, {
        'query': request.content,
        'chat_id': chat_id,
    })

    # Orient: Check RAG availability
    engine.orient(context, {
        'safety_critical': False,
        'impact_scope': 'local'
    }, {
        'rag_available': True,
        'model_loaded': True
    })

    # Decide & Act with existing logic
    # ... rest of implementation
```

## Enforcement Checklist

Before any significant action, validate:

```python
from cognitive import CognitiveEngine, DecisionContext
from cognitive.invariants import InvariantValidator

def validate_before_action(context: DecisionContext):
    """Run full invariant validation."""
    validator = InvariantValidator()
    result = validator.validate_all(context)

    if not result.is_valid:
        print("❌ INVARIANT VIOLATIONS:")
        for violation in result.violations:
            print(f"  - {violation}")
        return False

    if result.warnings:
        print("⚠ WARNINGS:")
        for warning in result.warnings:
            print(f"  - {warning}")

    return True
```

## Decision Logging and Observability

All decisions are automatically logged:

```python
from cognitive import DecisionLogger

# Initialize logger (done automatically by engine)
logger = DecisionLogger(log_dir="./logs/decisions")

# Get decision report
report = logger.generate_decision_report(decision_id)
print(report)

# Get all decisions for a specific operation
logs = logger.get_decision_log(decision_id)
```

Log format (JSONL):

```json
{
  "event": "decision_start",
  "decision_id": "abc-123",
  "timestamp": "2026-01-11T10:30:00Z",
  "problem_statement": "Ingest document.pdf",
  "goal": "Successfully ingest document",
  "success_criteria": ["parsed", "chunked", "embedded"]
}
```

## Testing Cognitive Enforcement

Create tests that validate invariant enforcement:

```python
import pytest
from cognitive import CognitiveEngine

def test_blocking_unknowns_prevent_irreversible_action():
    """Test that blocking unknowns halt irreversible operations."""
    engine = CognitiveEngine(enable_strict_mode=True)

    context = engine.begin_decision(
        problem_statement="Delete database",
        goal="Remove all data",
        success_criteria=["Database deleted"],
        is_reversible=False  # IRREVERSIBLE
    )

    # Add blocking unknown
    context.ambiguity_ledger.add_unknown(
        'backup_exists',
        blocking=True
    )

    # Should raise error due to blocking unknown + irreversible
    with pytest.raises(ValueError, match="Blocking unknowns"):
        engine.orient(context, {}, {})
```

## Monitoring Dashboard

Create a dashboard to visualize cognitive operations:

```python
# Get all active decisions
engine = CognitiveEngine()
active = engine.get_active_decisions()

print(f"Active Decisions: {len(active)}")
for context in active:
    print(f"  - {context.decision_id}: {context.problem_statement}")
    print(f"    Ambiguity: {context.ambiguity_ledger.summary()}")
    print(f"    Phase: {context.metadata.get('phase', 'unknown')}")
```

## Next Steps

1. **Add to existing functions**: Apply decorators to existing Grace operations
2. **Create integration tests**: Validate cognitive enforcement works correctly
3. **Monitor decision logs**: Review logs to ensure proper enforcement
4. **Tune thresholds**: Adjust complexity scores, timeouts, etc. based on usage
5. **Expand enforcement**: Add more specific invariant checks for domain logic

## Benefits

- **Prevents philosophical drift**: 12 orthogonal invariants, no overlap
- **Enforces accountability**: All decisions logged with full rationale
- **Ensures reversibility**: Irreversible actions require justification
- **Bounds complexity**: Complexity must justify itself with benefit
- **Tracks ambiguity**: Explicit accounting of what is known vs unknown
- **Time-bounded**: Planning must terminate, no infinite analysis
- **Forward simulation**: Multiple paths considered, best selected
- **Observability**: Every decision is inspectable and traceable
