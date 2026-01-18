# Clarity Framework - Grace-Aligned Coding Agent Cognitive Framework

## Overview

The **Clarity Framework** is a Grace-aligned cognitive coding agent designed to compete with Claude, ChatGPT, and Gemini by using **template-first deterministic code generation** with minimal LLM dependency.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CLARITY FRAMEWORK                                    │
│                   Grace-Aligned Coding Agent                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │
│   │   OBSERVE   │───►│   ORIENT    │───►│   DECIDE    │───►│     ACT     │ │
│   │             │    │             │    │             │    │             │ │
│   │ Parse Intent│    │Consult Oracle│   │Select Approach│  │Generate Code│ │
│   │ Extract Req │    │Match Templates│  │Calculate Trust│  │   Verify    │ │
│   └─────────────┘    └─────────────┘    └─────────────┘    └──────┬──────┘ │
│         │                                                         │        │
│         │                    ┌─────────────┐                     │        │
│         │                    │    LEARN    │◄────────────────────┘        │
│         │                    │             │                              │
│         │                    │Update Memory│                              │
│         │                    │Store Outcome│                              │
│         │                    └─────────────┘                              │
│         │                          │                                      │
│         ▼                          ▼                                      │
│   ┌─────────────────────────────────────────────────────────────────────┐ │
│   │                        GRACE INTEGRATION                             │ │
│   ├─────────────┬─────────────┬─────────────┬─────────────┬─────────────┤ │
│   │Genesis Keys │ Unified     │ Memory Mesh │ Trust       │Hallucination│ │
│   │  Tracking   │  Oracle     │  Learning   │  Scorer     │   Guard     │ │
│   └─────────────┴─────────────┴─────────────┴─────────────┴─────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Key Features

### 1. Template-First Code Generation
- **50+ built-in templates** covering common patterns
- **Deterministic synthesis** - same input = same output
- **No LLM hallucination** - templates are verified patterns
- **Oracle-boosted matching** - templates enhanced by Oracle insights

### 2. Grace Architecture Integration

| Component | Purpose | Integration |
|-----------|---------|-------------|
| **Genesis Keys** | Track all operations | Every task creates keys |
| **Unified Oracle** | Intelligence source | Consulted for patterns |
| **Memory Mesh** | Learning feedback | Stores outcomes |
| **Trust Scorer** | Autonomy decisions | Gates code application |
| **Hallucination Guard** | LLM verification | Checks LLM outputs |

### 3. Multi-Layer Verification
```
Layer 1: Syntax Validation     ✓ Python compile check
Layer 2: AST Parsing           ✓ Abstract syntax tree
Layer 3: Import Resolution     ✓ Standard library check
Layer 4: Security Scanning     ✓ Dangerous pattern detection
Layer 5: Test Execution        ✓ Run provided test cases
Layer 6: Anti-Hallucination    ✓ LLM output verification
```

### 4. Trust-Based Autonomy
```
Trust Score ≥ 0.85  →  AUTONOMOUS    (auto-apply)
Trust Score ≥ 0.60  →  SUPERVISED    (sandbox + confirm)
Trust Score < 0.60  →  BLOCKED       (do not apply)
```

### 5. Self-Healing Loop
```
Generate → Verify → [Failed?] → Heal → Generate → Verify → ...
                                  ↓
                          Try next template
                                  ↓
                          LLM escalation (last resort)
```

## Architecture

### Core Components

```python
ClarityFramework
├── ClarityTemplateCompiler      # Deterministic code synthesis
├── ClarityVerificationGate      # Multi-layer verification
├── ClarityTrustManager          # Trust-based autonomy
├── ClarityGenesisTracker        # Genesis Key integration
├── ClarityOracleLiaison         # Oracle Hub interface
└── ClarityMemoryLearner         # Memory Mesh updates
```

### OODA Loop Processing

```python
# OBSERVE: Parse intent from user request
intent = ClarityIntent(
    task_type="code_generation",
    language="python",
    desired_behavior="Write function to filter even numbers",
    target_symbols=["filter_even"]
)

# ORIENT: Consult Oracle, match templates
oracle_consultation = oracle.consult(intent)
template_matches = compiler.match_templates(intent, oracle_boost)

# DECIDE: Select approach, calculate trust
selected_template = template_matches[0]

# ACT: Generate code, verify
code = compiler.synthesize(selected_template, params)
verification = gate.verify(code, test_cases)
trust = manager.calculate_trust(template, verification)

# LEARN: Update memory mesh
memory.learn_from_outcome(state, success=verification.passed)
```

## Usage

### Python API

```python
from cognitive.clarity_framework import get_clarity_framework

# Initialize
framework = get_clarity_framework()

# Solve a task
result = framework.solve(
    description="Write a function that returns the factorial of n",
    language="python",
    test_cases=["assert factorial(5) == 120", "assert factorial(0) == 1"],
    function_name="factorial"
)

print(result)
# {
#     "success": True,
#     "code": "def factorial(n):\n    if n <= 1:\n        return 1\n    result = 1\n    for i in range(2, n + 1):\n        result *= i\n    return result",
#     "llm_used": False,
#     "template_used": "Factorial",
#     "oracle_consulted": True,
#     "trust_score": 0.94,
#     "trust_gate": "autonomous",
#     "genesis_keys": ["GK-abc123"],
#     "verification": {
#         "passed": True,
#         "syntax_valid": True,
#         "tests_passed": True,
#         "anti_hallucination": True
#     }
# }
```

### REST API

```bash
# Solve a task
POST /api/clarity/solve
{
    "description": "Write a function that checks if a number is prime",
    "test_cases": ["assert is_prime(7) == True", "assert is_prime(4) == False"],
    "function_name": "is_prime"
}

# Batch solve
POST /api/clarity/batch-solve
{
    "tasks": [
        {"description": "...", "test_cases": [...]},
        {"description": "...", "test_cases": [...]}
    ],
    "parallel": true
}

# Get KPI Dashboard
GET /api/clarity/kpi-dashboard

# List templates
GET /api/clarity/templates

# Grace integration status
GET /api/clarity/grace-status
```

## Template Categories

| Category | Templates | Description |
|----------|-----------|-------------|
| `list_operations` | 9 | filter, map, reduce, find, sort, group, unique, flatten, max/min |
| `string_operations` | 7 | split/join, extract, replace, reverse, palindrome, count |
| `math_operations` | 7 | factorial, fibonacci, prime, gcd, lcm, power, sum_digits |
| `algorithms` | 4 | binary_search, merge_sort, quick_sort, bubble_sort |
| `data_structures` | 3 | dict_merge, dict_invert, dict_filter |
| `validation` | 2 | email, phone |

## KPI Metrics

### Performance Tracking

```python
dashboard = framework.get_kpi_dashboard()
# {
#     "summary": {
#         "total_tasks": 100,
#         "template_solved": 85,
#         "template_coverage_pct": 85.0,
#         "llm_independence_rate": 85.0,
#         "verification_pass_rate": 92.0,
#         "avg_trust_score": 0.87
#     },
#     "grace_integration": {
#         "genesis_tracking": True,
#         "oracle_connected": True,
#         "memory_mesh_active": True
#     },
#     "competing_metrics": {
#         "llm_independence_rate": 85.0,
#         "autonomous_rate": 72.0,
#         "template_hit_rate": 90.0
#     }
# }
```

### Key Metrics

| Metric | Target | Description |
|--------|--------|-------------|
| **LLM Independence Rate** | >80% | Tasks solved without LLM |
| **Template Hit Rate** | >85% | Template match success |
| **Verification Pass Rate** | >90% | Code passes all checks |
| **Autonomous Rate** | >70% | Auto-applied without review |
| **Self-Healing Success** | >60% | Recovery from failures |

## Competing with LLMs

### Advantages Over Pure LLM

1. **Deterministic** - Same input = same output (no randomness)
2. **No Hallucination** - Templates are verified patterns
3. **Faster** - No API latency for template-based solutions
4. **Cheaper** - No LLM API costs for 80%+ of tasks
5. **Auditable** - Genesis Keys track every operation
6. **Learnable** - Memory Mesh improves over time

### When LLM Fallback is Used

- Complex novel problems with no matching template
- Multi-step reasoning required
- Domain-specific knowledge needed
- All templates fail verification

### LLM Output Verification

When LLM fallback is used, outputs go through:
1. **Syntax validation** - Must compile
2. **AST parsing** - Must be valid Python
3. **Security check** - No dangerous patterns
4. **Test execution** - Must pass test cases
5. **Anti-hallucination check** - No placeholder code
6. **Hallucination Guard** - Cross-verification (if enabled)

## Genesis Key Tracking

Every Clarity operation creates Genesis Keys:

```
GK-task_start       → Task initiated
GK-intent_parsed    → Intent extracted
GK-oracle_consulted → Oracle queried
GK-template_matched → Template selected
GK-code_generated   → Code synthesized
GK-verification     → Verification complete
GK-code_applied     → Code applied
GK-healing_attempt  → Self-healing tried
GK-learning_stored  → Outcome recorded
GK-task_complete    → Task finished
```

## Memory Mesh Integration

### Learning Flow

```
Task Outcome
     ↓
[Success/Failure]
     ↓
Memory Mesh Ingest
     ↓
┌────────────────────┐
│  Learning Memory   │ ← Trust-scored examples
├────────────────────┤
│  Episodic Memory   │ ← High-trust experiences
├────────────────────┤
│ Procedural Memory  │ ← Extracted procedures
└────────────────────┘
     ↓
Template Stats Updated
     ↓
Future Tasks Improved
```

### Feedback Loop

```python
# After task completion
memory_learner.learn_from_outcome(
    state=task_state,
    success=verification.passed
)

# Updates:
# - Template success rates
# - Pattern confidence
# - Procedure effectiveness
```

## Configuration

```python
framework = ClarityFramework(
    session=db_session,                    # Database session
    knowledge_base_path=Path("kb"),        # Knowledge base location
    enable_llm_fallback=True,              # Allow LLM when templates fail
    max_parallel_agents=4                  # Parallel processing threads
)
```

## Files

| File | Purpose |
|------|---------|
| `backend/cognitive/clarity_framework.py` | Main framework implementation |
| `backend/api/clarity_api.py` | REST API endpoints |
| `CLARITY_FRAMEWORK_ARCHITECTURE.md` | This documentation |

## Related Grace Components

- **Enterprise Coding Agent** - Full enterprise features
- **Unified Oracle Hub** - Intelligence source
- **Memory Mesh Integration** - Learning system
- **Genesis Key Service** - Operation tracking
- **Hallucination Guard** - LLM verification
- **Enhanced Trust Scorer** - Trust calculations

## Roadmap

### Phase 1 (Complete)
- ✅ Core template compiler
- ✅ Multi-layer verification
- ✅ Trust-based autonomy
- ✅ Genesis Key tracking
- ✅ Oracle integration
- ✅ Memory Mesh learning

### Phase 2 (Planned)
- [ ] AST-based transforms
- [ ] Template DSL
- [ ] Proof-carrying patches
- [ ] Cross-language support

### Phase 3 (Future)
- [ ] Template auto-generation from GitHub
- [ ] Federated template learning
- [ ] Real-time Oracle streaming
- [ ] Multi-repository support
