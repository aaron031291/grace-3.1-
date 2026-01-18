# Transformation Library + Rule DSL Architecture in GRACE

## Overview

This document maps the Transformation Library system into GRACE's existing architecture. The system consists of:

1. **Transformation Library + Rule DSL** - AST matching and rewriting rules
2. **Outcome Ledger (magma-backed)** - Immutable logging of all transforms
3. **Pattern Miner → Rule Improvement Proposals** - Nightly job to learn from diffs

## Architecture Placement

### A) Transformation Library + Rule DSL

**Location**: `backend/cognitive/transformation_library/`

```
backend/cognitive/transformation_library/
├── __init__.py
├── rule_dsl.py              # DSL parser and rule definitions
├── ast_matcher.py           # AST pattern matching engine
├── rewrite_engine.py        # Template-based code rewriting
├── constraint_validator.py  # Pre/post-condition checking
├── proof_system.py          # Proof generation and verification
└── transformation_executor.py  # Orchestrates transform execution
```

**Integration Points**:
- Extends `backend/genesis/code_analyzer.py` - Uses existing AST parsing
- Uses `backend/cognitive/engine.py` - Cognitive engine for decision-making
- Integrates with `backend/genesis/healing_system.py` - Code healing flow

**Key Design**:
```python
# Example Rule DSL
rule = {
    "id": "bare_except_to_exception",
    "version": "1.0",
    "pattern": {
        "type": "ast",
        "match": "ExceptHandler(type=None)",
        "language": "python"
    },
    "rewrite": {
        "template": "except Exception as {name}:",
        "preserve": ["body", "name"]
    },
    "constraints": {
        "pre": ["no_nested_except"],
        "post": ["handles_exception_types", "preserves_traceback"]
    },
    "proof_required": ["type_safety", "exception_coverage"],
    "side_effects": ["improves_error_handling", "may_change_exception_caught"]
}
```

---

### B) Outcome Ledger (Magma-Backed)

**Location**: `backend/cognitive/transformation_library/outcome_ledger.py`

**Integration with Magma Memory**:
- Uses `backend/cognitive/magma_memory_system.py` for hierarchical storage
- Surface Layer: Recent transforms (hot, fluid)
- Mantle Layer: Validated patterns (warm, semi-crystallized)
- Core Layer: Proven transformations (cool, solidified)

**Ledger Schema** (stored in Magma + Database):
```python
TransformationOutcome = {
    "rule_id": str,           # e.g., "bare_except_to_exception"
    "rule_version": str,      # e.g., "1.0"
    "ast_pattern_signature": str,  # Hash of matched AST
    "before_code": str,       # Original code
    "after_code": str,        # Transformed code
    "diff_summary": str,      # Unified diff summary
    "proof_results": {
        "type_safety": "verified",
        "exception_coverage": "verified",
        "side_effects": "expected"
    },
    "rollback_status": "available",  # or "committed", "rolled_back"
    "time_to_merge": Optional[float],  # seconds if PR-based
    "magma_layer": "surface",  # or "mantle", "core"
    "temperature": 0.85,       # Activity metric
    "crystallized": 0.30,      # Validation metric
    "genesis_key_id": str,     # Link to Genesis tracking
    "timestamp": datetime
}
```

**Storage Strategy**:
- **Hot Path** (Surface): Recent transforms → Fast retrieval → `magma.get_memories_by_layer(MagmaLayer.SURFACE)`
- **Warm Path** (Mantle): Validated patterns → Pattern learning → `magma.get_memories_by_layer(MagmaLayer.MANTLE)`
- **Cold Path** (Core): Proven rules → Long-term knowledge → `magma.get_memories_by_layer(MagmaLayer.CORE)`

**Integration Points**:
- `backend/cognitive/magma_memory_system.py` - Layer classification and flow
- `backend/genesis/genesis_key_service.py` - Tracking and provenance
- `backend/database/base.py` - Persistent storage (optional, Magma is primary)

---

### C) Pattern Miner → Rule Improvement Proposals

**Location**: `backend/cognitive/transformation_library/pattern_miner.py`

**Integration with Existing Systems**:
- Extends `backend/cognitive/memory_mesh_learner.py` - Pattern detection
- Uses `backend/cognitive/mirror_self_modeling.py` - Self-reflection
- Integrates with `backend/cognitive/continuous_learning_orchestrator.py` - Scheduling

**Mining Process**:
```python
class TransformationPatternMiner:
    """
    Nightly/beat job that:
    1. Clusters successful diffs from Outcome Ledger
    2. Detects recurring manual edits (not yet automated)
    3. Proposes new rules or refinements
    4. Generates "why this rule exists" documentation
    """
    
    def mine_patterns(self):
        # 1. Get successful transforms from Outcome Ledger (Mantle/Core layers)
        successful_transforms = self.outcome_ledger.get_by_layer(
            layers=[MagmaLayer.MANTLE, MagmaLayer.CORE],
            min_crystallized=0.7
        )
        
        # 2. Cluster by AST pattern signature
        clusters = self._cluster_transforms(successful_transforms)
        
        # 3. Detect recurring manual edits (compare with manual code changes)
        manual_edits = self._detect_manual_patterns()
        
        # 4. Generate rule proposals
        proposals = self._generate_rule_proposals(clusters, manual_edits)
        
        # 5. Store in learning memory for review
        for proposal in proposals:
            self.memory_mesh.ingest_learning_experience(
                experience_type="rule_proposal",
                context={"pattern": proposal.pattern},
                action_taken={"proposed_rule": proposal.rule_dsl},
                outcome={"quality_score": proposal.quality_score}
            )
```

**Scheduling**:
- Add to `backend/cognitive/continuous_learning_orchestrator.py` - Nightly beat
- Or standalone: `backend/cognitive/transformation_library/nightly_miner.py`
- Uses same pattern as `backend/librarian/genesis_key_curator.py` (schedule library)

---

## Integration Flow

```
User Request / Autonomous Trigger
    ↓
┌─────────────────────────────────────┐
│ Transformation Library              │
│ - AST Matcher finds patterns        │
│ - Rule DSL validates match          │
│ - Rewrite Engine applies template   │
│ - Constraint Validator checks       │
│ - Proof System verifies             │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ Outcome Ledger (Magma-Backed)       │
│ - Log transform with all metadata   │
│ - Classify into Magma layer         │
│ - Link to Genesis Key               │
│ - Store in Magma memory system      │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ Pattern Miner (Nightly)             │
│ - Cluster successful transforms     │
│ - Detect manual edit patterns       │
│ - Propose new/refined rules         │
│ - Generate documentation            │
│ - Feed back to Learning Memory      │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ Memory Mesh + Learning Memory       │
│ - Store rule proposals              │
│ - Update trust scores               │
│ - Flow through Magma layers         │
└─────────────────────────────────────┘
```

---

## File Structure Summary

```
backend/
├── cognitive/
│   ├── transformation_library/          # NEW
│   │   ├── __init__.py
│   │   ├── rule_dsl.py                  # Rule DSL parser
│   │   ├── ast_matcher.py               # AST pattern matching
│   │   ├── rewrite_engine.py            # Code rewriting
│   │   ├── constraint_validator.py      # Pre/post conditions
│   │   ├── proof_system.py              # Proof generation
│   │   ├── transformation_executor.py   # Main orchestrator
│   │   ├── outcome_ledger.py            # Magma-backed ledger
│   │   ├── pattern_miner.py             # Pattern mining
│   │   └── nightly_miner.py             # Scheduled job
│   │
│   ├── magma_memory_system.py           # EXISTING - Integrate
│   ├── memory_mesh_integration.py       # EXISTING - Integrate
│   ├── memory_mesh_learner.py           # EXISTING - Extend
│   ├── continuous_learning_orchestrator.py  # EXISTING - Extend
│   └── engine.py                        # EXISTING - Use
│
├── genesis/
│   ├── code_analyzer.py                 # EXISTING - Extend
│   ├── healing_system.py                # EXISTING - Integrate
│   └── genesis_key_service.py           # EXISTING - Use
```

---

## Key Design Principles

### 1. Deterministic Transforms (Not Bigger Context Windows)
- **Focus**: Rule-based, deterministic AST transformations
- **Proof**: Every transform must pass proof gates
- **Outcome-Based Learning**: Ledger tracks what works

### 2. Magma-Backed Outcome Ledger
- **Surface**: Recent transforms (fast iteration)
- **Mantle**: Validated patterns (pattern learning)
- **Core**: Proven rules (long-term knowledge)

### 3. Compounding Advantage
- **Pattern Miner**: Discovers new rules from successful diffs
- **Rule Proposals**: Automatically generated from manual edits
- **Documentation**: "Why this rule exists" auto-generated

---

## Next Steps

1. **Create Transformation Library Core** (`backend/cognitive/transformation_library/`)
   - Rule DSL parser
   - AST matcher
   - Rewrite engine

2. **Implement Outcome Ledger** (`outcome_ledger.py`)
   - Integrate with Magma memory system
   - Link to Genesis keys
   - Store transformation outcomes

3. **Build Pattern Miner** (`pattern_miner.py`)
   - Clustering algorithm
   - Manual edit detection
   - Rule proposal generation

4. **Integrate with Existing Systems**
   - Extend `continuous_learning_orchestrator.py` for nightly mining
   - Connect to `memory_mesh_learner.py` for pattern learning
   - Use `magma_memory_system.py` for hierarchical storage

5. **Testing & Validation**
   - Unit tests for rule DSL
   - Integration tests with Magma
   - End-to-end transform → ledger → miner flow

---

## Example: Complete Flow

```python
# 1. Transform executes
from cognitive.transformation_library.transformation_executor import TransformationExecutor
from cognitive.transformation_library.rule_dsl import load_rule

executor = TransformationExecutor(session, magma_memory)
rule = load_rule("bare_except_to_exception")

result = executor.execute_transform(
    code=source_code,
    rule=rule,
    file_path="example.py"
)

# 2. Outcome logged to Magma-backed ledger
# Automatically stored in Outcome Ledger (Surface layer initially)

# 3. Nightly pattern miner discovers patterns
# Pattern miner runs, clusters successful transforms,
# detects recurring manual edits, proposes new rules

# 4. Rule proposals flow to Memory Mesh
# High-trust proposals become new rules,
# flow through Magma layers: Surface → Mantle → Core
```

---

## Benefits

1. **Deterministic**: Rule-based transforms are provable and reversible
2. **Learning**: Pattern miner discovers new rules automatically
3. **Compound Growth**: Each successful transform improves the system
4. **Immutable Log**: Magma-backed ledger provides audit trail
5. **Beyond LMs**: Focus on domain-specific rewrite knowledge, not context windows
