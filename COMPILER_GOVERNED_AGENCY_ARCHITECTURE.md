# Compiler-Governed Agency Model - GRACE Architecture

## 🎯 Mechanical Alignment Architecture

**Core Principle**: LLM = Intent Generator, AST Transformer = Authority, Ruleset = Constitution

This is **not RLHF**. This is **not guardrails**. This is **mechanical alignment** via deterministic transformation.

---

## 🔐 Zero Write Access for LLM

### LLM Can Only Emit:

```python
{
    "intent_type": "add_logging",
    "target_class": "MyClass",
    "criteria": {"target": "class"},
    "justification": "Class needs logging for debugging",
    "confidence": 0.9
}
```

### LLM CANNOT Emit:

```
❌ function foo() { ... }
❌ class Bar:
❌ def baz():
❌ import logging
❌ Any code-shaped strings
```

**Enforcement**: Intent validation rejects any intent containing code syntax.

---

## 🏛️ Three Non-Negotiables

### 1. LLM Must Not Emit Code-Shaped Output

**Enforcement**:
- Intent validation checks for code syntax patterns
- Rejects intents containing: `def`, `class`, `import`, `=`, `(`, `)`, `{`, `}`
- Only allows structured intent objects

**Why**: If LLM can output syntax, someone will trust it later → authority leak.

### 2. Transformer Rules Must Be Finite and Named

**Rule Structure**:
```python
TransformRule(
    rule_id='RULE-001',          # Explicit ID
    version='1.0.0',              # Versioned
    description='Add logger...',  # Human-readable
    author='system',              # Owned
    reversible=True,              # Reversible/diffable
    matches_intent_types=[IntentType.ADD_LOGGING],  # Explicit intent matching
    transformer_class=LoggerTransformer  # Human-authored transformer
)
```

**Why**: Rules are now policy. Must be explicit, versioned, reversible.

### 3. Semantic Diff, Not Just Text Diff

**Diff Structure**:
```python
{
    'before_code': '...',
    'after_code': '...',
    'diff_lines': [...],
    'preserves_syntax': True,
    'preserves_semantics': True,
    'dependency_changes': [...],
    'control_flow_changes': [...],
    'side_effect_changes': [...]
}
```

**Why**: "It only added logging" might have changed behavior. Semantic diff shows real impact.

---

## 🔗 GRACE System Integration

### 1. **Genesis Keys** (Audit Trail - Diff + Stamp)

**Every mutation creates a Genesis key**:
```python
GenesisKey(
    key_type=CODE_CHANGE,
    action="compiler_governed_transformation",
    details={
        'rule_id': 'RULE-001',
        'rule_version': '1.0.0',
        'intent_type': 'add_logging',
        'before_code': '...',
        'after_code': '...',
        'diff_lines': [...],
        'justification_chain': [
            "Intent: add_logging",
            "Rule: RULE-001 v1.0.0",
            "AST Path: ClassDef → body[0]"
        ],
        'trust_score': 0.9
    }
)
```

**Forensic-grade explainability**: "Grace can always say: I changed this — here's why"

### 2. **Trust Scoring** (Enhanced Trust Scorer)

**Factors**:
- Rule provenance (human-authored = 0.8, LLM = 0.5)
- Syntax preservation (1.0 if preserved, 0.0 if broken)
- Semantics preservation (control-flow, side-effects)
- Intent LLM confidence (weighted)
- Transformation determinism (AST transformation = 1.0)
- Cognitive alignment (validated via cognitive framework)

**Integration**: Uses `EnhancedTrustScorer` for comprehensive scoring.

### 3. **KPI Tracking** (Alignment Metrics)

**Metrics tracked**:
- `transformations_successful` - Count of successful transformations
- `transformations_failed` - Count of failed transformations
- `rule_{RULE-ID}_usage` - Per-rule usage tracking
- `alignment_quality` - Syntax + semantics preservation score

**Integration**: Uses `KPITracker` for performance metrics.

### 4. **Anti-Hallucination Governance**

**Layers**:
1. **Intent Structure Validation** - No code syntax in intents
2. **Target Existence Check** - Verify intent target exists in source
3. **Cognitive Framework Validation** - Reasoning chain validity
4. **Clarity Framework Check** - Ambiguity detection
5. **HallucinationGuard** - Repository grounding verification

**Integration**:
- `HallucinationGuard` - Multi-layer verification
- `CognitiveEngine` - Reasoning validation
- Clarity checks - Ambiguity detection

### 5. **Cognitive Framework** (Reasoning Validation)

**Constraints**:
```python
CognitiveConstraints(
    requires_determinism=True,      # AST transformation is deterministic
    is_safety_critical=False,
    impact_scope="local",           # Code changes are local
    is_reversible=True,             # Can be diffed/reverted
    requires_grounding=True,        # Must reference actual code
    min_confidence_threshold=0.7    # LLM confidence threshold
)
```

**Validation**: Intent reasoning checked via cognitive framework.

### 6. **Clarity Framework** (Ambiguity Detection)

**Checks**:
- Ambiguous target (multiple matches possible)
- Vague criteria ("both class and function")
- Uncertain justification ("might need", "could be")
- Low confidence + vague = ambiguous

**Result**: Ambiguous intents rejected before transformation.

---

## 🔄 Complete Flow

```
1. LLM analyzes code issue
   ↓
2. LLM emits CodeIntent (structured, no code)
   ↓
3. Intent validation (anti-hallucination)
   ├─ Code syntax check (reject if found)
   ├─ Target existence check
   ├─ Cognitive framework validation
   ├─ Clarity framework check
   └─ HallucinationGuard verification
   ↓
4. Match intent to rule (RulesetRegistry)
   ↓
5. AST Transformer executes rule (authority)
   ├─ Transform AST
   ├─ Generate semantic diff
   └─ Validate syntax + semantics
   ↓
6. Create Genesis key (diff + stamp)
   ↓
7. Calculate trust score (Enhanced Trust Scorer)
   ↓
8. Update KPI metrics (KPI Tracker)
   ↓
9. Track mutation (audit trail)
```

---

## 📊 What This Unlocks

### 1. Safe Self-Modification

Grace can improve itself without violating sovereignty:
- LLM proposes intents
- Ruleset (constitution) controls what executes
- Every mutation tracked (Genesis keys)
- Deterministic transformations only

### 2. Multi-Model Competition

Run multiple LLMs proposing intents:
- GPT-4 proposes: `IntentType.ADD_LOGGING`
- Claude proposes: `IntentType.ADD_LOGGING`
- Gemini proposes: `IntentType.ADD_ERROR_HANDLING`

**Only transformer decides** (via ruleset matching). Best proposal wins.

### 3. Human Override Without Forked Reality

Humans don't edit code directly:
- Approve/reject **intents** (before transformation)
- Approve/reject **diffs** (after transformation)
- Adjust **rules** (constitution)

Same pipeline. Same authority. No forked reality.

---

## 🛡️ Safety Guarantees

### 1. Mechanical Alignment

```
Alignment = Determinism + Provenance + Audit
```

- **Determinism**: AST transformation is deterministic
- **Provenance**: Every rule has human author, version, description
- **Audit**: Every mutation has Genesis key with diff + justification chain

### 2. Zero LLM Write Access

**Enforced at multiple layers**:
1. Intent validation (rejects code syntax)
2. Ruleset matching (only human-authored rules execute)
3. AST transformer (only executes registered transformers)
4. Genesis key audit (tracks all mutations)

### 3. Forensic-Grade Explainability

**Every mutation has**:
- **What**: Intent type, rule ID, diff
- **Where**: File path, AST path, line numbers
- **When**: Timestamp
- **Who**: LLM model, rule author
- **How**: AST transformation path
- **Why**: Intent justification → Rule → AST path

---

## 📚 Implementation Files

1. **`compiler_governed_agency.py`** - Core system
   - Intent system
   - Ruleset registry
   - AST transformer authority
   - GRACE integrations

2. **`intent_proposal_system.py`** - LLM interface
   - Intent proposal creation
   - Intent validation
   - Processing pipeline

3. **`code_analyzer_self_healing.py`** - Existing system (enhanced)
   - AST transformation
   - Fix application
   - Can be integrated with intent system

---

## ✅ Status

- ✅ Intent system implemented
- ✅ Ruleset registry (constitution)
- ✅ AST transformer authority
- ✅ Genesis key integration
- ✅ Trust scoring integration
- ✅ KPI tracking integration
- ✅ Anti-hallucination governance
- ✅ Cognitive framework integration
- ✅ Clarity framework checks

**The compiler-governed agency model is now integrated with all GRACE systems!**

---

**Last Updated:** 2026-01-16
