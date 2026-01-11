# Multi-LLM Orchestration System - Complete Implementation

**Version:** 1.0
**Status:** Production Ready
**Date:** 2026-01-11

---

## Executive Summary

GRACE now includes a **complete multi-LLM orchestration system** that integrates multiple open-source LLMs (DeepSeek, Qwen, Llama, etc.) with:

✅ **Read-Only Repository Access** - Full access to source code, Genesis Keys, Librarian, RAG, World Model, Memory Mesh, and training data
✅ **5-Layer Hallucination Mitigation** - Near-zero hallucination through grounding, consensus, contradiction detection, confidence scoring, and trust verification
✅ **Cognitive Framework Enforcement** - All LLMs follow GRACE's 12 OODA invariants
✅ **Genesis Key Tracking** - Every LLM interaction is tracked with Genesis Keys and version control
✅ **Layer 1 Integration** - All LLM data flows through Layer 1 (Trust & Truth Foundation)
✅ **Learning Memory Integration** - LLMs learn from experience with trust-scored training data
✅ **Complete Audit Trail** - All inputs/outputs are tracked and traced

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                       USER/GRACE INTENT                              │
│  "Does this add value? Bring knowledge? Align with intent?"         │
└────────────────────────────┬────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────────┐
│                   LLM ORCHESTRATOR                                   │
│  - Task routing                                                      │
│  - Model selection                                                   │
│  - Pipeline coordination                                             │
└────────────────────────────┬────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────────┐
│               COGNITIVE FRAMEWORK ENFORCER                           │
│  OODA Loop + 12 Invariants                                          │
│  - Observe → Orient → Decide → Act                                  │
│  - Ambiguity ledger tracking                                        │
│  - Determinism validation                                            │
│  - Blast radius assessment                                           │
└────────────────────────────┬────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────────┐
│                   MULTI-LLM CLIENT                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │DeepSeek  │  │  Qwen    │  │  Llama   │  │ Mistral  │           │
│  │ Coder    │  │2.5 Coder │  │ 3.3 70B  │  │  Small   │           │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
└────────────────────────────┬────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────────┐
│           HALLUCINATION MITIGATION PIPELINE (5 Layers)               │
│                                                                      │
│  Layer 1: Repository Grounding                                      │
│  └─ Claims must reference actual files/code                         │
│                                                                      │
│  Layer 2: Cross-Model Consensus                                     │
│  └─ Multiple LLMs must agree (similarity threshold)                 │
│                                                                      │
│  Layer 3: Contradiction Detection                                   │
│  └─ Check against existing knowledge base                           │
│                                                                      │
│  Layer 4: Confidence Scoring                                        │
│  └─ Calculate trust score based on source/quality/consensus         │
│                                                                      │
│  Layer 5: Trust System Verification                                 │
│  └─ Validate against learning memory (Layer 1 truth)                │
└────────────────────────────┬────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────────┐
│              READ-ONLY REPOSITORY ACCESS                             │
│                                                                      │
│  Source Code Repository   Genesis Keys     Librarian                │
│  RAG System              World Model       Memory Mesh              │
│  Learning Memory         Training Data     System Stats             │
│                                                                      │
│  All access is READ-ONLY and LOGGED for audit                       │
└────────────────────────────┬────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    INTEGRATION PIPELINE                              │
│                                                                      │
│  Genesis Key Assignment → Layer 1 Integration → Learning Memory     │
│                                                                      │
│  Every LLM interaction:                                             │
│  ✓ Gets Genesis Key for tracking                                   │
│  ✓ Flows through Layer 1 (Trust & Truth)                           │
│  ✓ Feeds into Learning Memory with trust scores                    │
│  ✓ Updates autonomous learning loop                                │
│  ✓ Complete audit trail                                            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Recommended Open-Source LLMs

### Tier 1: Code Generation & Debugging

1. **DeepSeek-Coder-V2-Instruct (16B/33B)**
   - Best for: Code generation, debugging, explanation
   - Context: 16K tokens
   - Installation: `ollama pull deepseek-coder:33b-instruct`

2. **Qwen2.5-Coder (7B-32B)**
   - Best for: Code understanding, generation, review
   - Context: 32K tokens
   - Installation: `ollama pull qwen2.5-coder:32b-instruct`

3. **CodeQwen1.5 (7B)**
   - Best for: Fast code queries
   - Context: 32K tokens
   - Installation: `ollama pull codeqwen:7b`

### Tier 2: Reasoning & Planning

4. **Qwen2.5 (72B)**
   - Best for: Strong reasoning, planning, following cognitive frameworks
   - Context: 32K tokens
   - Installation: `ollama pull qwen2.5:72b-instruct`

5. **DeepSeek-R1-Distill (7B-70B)**
   - Best for: Chain-of-thought reasoning
   - Context: 16K tokens
   - Installation: `ollama pull deepseek-r1:70b`

6. **Llama 3.3 (70B)**
   - Best for: General reasoning and tasks
   - Context: 8K tokens
   - Installation: `ollama pull llama3.3:70b-instruct`

### Tier 3: Fast Queries & Validation

7. **Mistral-Small (22B)**
   - Best for: Fast inference, quick validation
   - Context: 32K tokens
   - Installation: `ollama pull mistral-small:22b`

8. **Gemma 2 (9B-27B)**
   - Best for: Efficient validation tasks
   - Context: 8K tokens
   - Installation: `ollama pull gemma2:27b-instruct`

---

## Installation & Setup

### 1. Install Models

```bash
# Code generation models
ollama pull deepseek-coder:33b-instruct
ollama pull qwen2.5-coder:32b-instruct

# Reasoning models
ollama pull qwen2.5:72b-instruct
ollama pull deepseek-r1:70b

# Fast query models
ollama pull mistral-small:22b
ollama pull llama3.3:70b-instruct

# Note: Start with smaller models (7B) if resources are limited
ollama pull qwen2.5-coder:7b-instruct
ollama pull deepseek-r1:7b
```

### 2. Verify Installation

```bash
# Check available models
curl http://localhost:8000/llm/models
```

### 3. Test Basic Task

```bash
curl -X POST http://localhost:8000/llm/task \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Explain the file structure of this repository",
    "task_type": "code_explanation",
    "require_grounding": true,
    "require_verification": true,
    "user_id": "GU-test"
  }'
```

---

## API Reference

### Execute LLM Task

**Endpoint:** `POST /llm/task`

**Description:** Execute LLM task with full orchestration pipeline

**Request:**
```json
{
  "prompt": "Your question or task",
  "task_type": "code_generation|reasoning|general|etc",
  "user_id": "GU-user123",
  "require_verification": true,
  "require_consensus": true,
  "require_grounding": true,
  "enable_learning": true,
  "system_prompt": "Optional system instructions",
  "context_documents": ["Optional context"],
  "requires_determinism": false,
  "is_safety_critical": false,
  "impact_scope": "local",
  "is_reversible": true
}
```

**Response:**
```json
{
  "task_id": "llm_task_abc123",
  "success": true,
  "content": "LLM response content",
  "verification_passed": true,
  "cognitive_decision_id": "decision_xyz",
  "genesis_key_id": "GK-LLM-abc123",
  "trust_score": 0.85,
  "confidence_score": 0.82,
  "model_used": "DeepSeek Coder 33B",
  "duration_ms": 1250.5,
  "learning_example_id": "learning_example_456",
  "audit_trail": [
    {
      "step": "cognitive_enforcement",
      "decision_id": "decision_xyz",
      "timestamp": "2026-01-11T..."
    },
    {
      "step": "llm_generation",
      "model": "DeepSeek Coder 33B",
      "duration_ms": 850.2
    },
    {
      "step": "hallucination_verification",
      "is_verified": true,
      "confidence": 0.82
    },
    {
      "step": "genesis_key_assignment",
      "genesis_key_id": "GK-LLM-abc123"
    }
  ],
  "timestamp": "2026-01-11T..."
}
```

### List Available Models

**Endpoint:** `GET /llm/models`

```bash
curl http://localhost:8000/llm/models
```

**Response:**
```json
{
  "models": [
    {
      "key": "deepseek-coder-33b",
      "name": "DeepSeek Coder 33B",
      "model_id": "deepseek-coder:33b-instruct",
      "capabilities": ["code", "reasoning"],
      "context_window": 16384,
      "recommended_tasks": ["code_generation", "code_debugging"],
      "priority": 10,
      "stats": {
        "requests": 125,
        "successes": 120,
        "failures": 5,
        "avg_duration_ms": 1250.5
      }
    }
  ]
}
```

### Query Repository (Read-Only)

**Endpoint:** `POST /llm/repo/query`

**Examples:**

```bash
# Get file tree
curl -X POST http://localhost:8000/llm/repo/query \
  -H "Content-Type: application/json" \
  -d '{
    "query_type": "file_tree",
    "parameters": {"max_depth": 3}
  }'

# Read file
curl -X POST http://localhost:8000/llm/repo/query \
  -H "Content-Type: application/json" \
  -d '{
    "query_type": "read_file",
    "parameters": {"file_path": "backend/app.py"}
  }'

# Search code
curl -X POST http://localhost:8000/llm/repo/query \
  -H "Content-Type: application/json" \
  -d '{
    "query_type": "search_code",
    "parameters": {"pattern": "def.*process.*", "file_pattern": "*.py"}
  }'

# RAG query
curl -X POST http://localhost:8000/llm/repo/query \
  -H "Content-Type: application/json" \
  -d '{
    "query_type": "rag_query",
    "parameters": {"query": "authentication", "limit": 5}
  }'

# Get learning examples
curl -X POST http://localhost:8000/llm/repo/query \
  -H "Content-Type: application/json" \
  -d '{
    "query_type": "get_learning_examples",
    "parameters": {"min_trust_score": 0.8, "limit": 10}
  }'

# Get system stats
curl -X POST http://localhost:8000/llm/repo/query \
  -H "Content-Type: application/json" \
  -d '{
    "query_type": "get_system_stats",
    "parameters": {}
  }'
```

### Get Statistics

**Endpoint:** `GET /llm/stats`

```bash
curl http://localhost:8000/llm/stats
```

**Response:**
```json
{
  "stats": {
    "total_tasks": 150,
    "success_rate": 0.95,
    "avg_duration_ms": 1250.5,
    "avg_trust_score": 0.85,
    "avg_confidence_score": 0.82,
    "multi_llm_stats": {
      "deepseek-coder-33b": {
        "requests": 75,
        "successes": 72,
        "failures": 3,
        "avg_duration_ms": 1350.2
      }
    },
    "verification_stats": {
      "total_verifications": 150,
      "verification_rate": 0.88,
      "avg_confidence": 0.82,
      "layer_success_rates": {
        "repository_grounding": 0.92,
        "cross_model_consensus": 0.85,
        "contradiction_check": 0.95,
        "confidence_scoring": 0.90,
        "trust_system": 0.87
      }
    }
  }
}
```

### Get Access Log

**Endpoint:** `GET /llm/repo/access-log?limit=100`

```bash
curl http://localhost:8000/llm/repo/access-log?limit=50
```

**Response:**
```json
{
  "access_log": [
    {
      "timestamp": "2026-01-11T...",
      "operation": "read_file",
      "details": {"file_path": "backend/app.py"}
    },
    {
      "timestamp": "2026-01-11T...",
      "operation": "rag_query",
      "details": {"query": "authentication"}
    }
  ],
  "count": 50
}
```

### Get Cognitive Decisions

**Endpoint:** `GET /llm/cognitive/decisions?limit=100`

```bash
curl http://localhost:8000/llm/cognitive/decisions?limit=20
```

**Response:**
```json
{
  "decisions": [
    {
      "decision_id": "decision_abc123",
      "operation": "llm_task_code_generation",
      "ooda_phase": "act",
      "ambiguity_ledger": {
        "known": ["task_id", "task_type"],
        "inferred": ["user_intent"],
        "assumed": [],
        "unknown": []
      },
      "alternatives_count": 1,
      "reasoning_trace": [
        "Starting OODA loop for: llm_task_code_generation",
        "OBSERVE: Gathered 5 observations",
        "ORIENT: Context understood. Impact scope: local",
        "DECIDE: Selected path 'execute_llm_task' with score 0.850",
        "ACT: Executed. Success=True"
      ],
      "genesis_key_id": "GK-LLM-abc123",
      "timestamp": "2026-01-11T..."
    }
  ]
}
```

---

## Hallucination Mitigation Pipeline

### Layer 1: Repository Grounding

**What:** Verifies content references actual files and code
**How:** Extracts file references and validates they exist
**Threshold:** Configurable (can require file references or not)

### Layer 2: Cross-Model Consensus

**What:** Multiple LLMs must agree on the response
**How:** Queries 3+ models, calculates similarity, requires threshold
**Threshold:** 0.7 similarity (70% agreement)

### Layer 3: Contradiction Detection

**What:** Checks for contradictions with existing knowledge
**How:** Semantic contradiction detection against RAG system
**Threshold:** 0.7 contradiction threshold

### Layer 4: Confidence Scoring

**What:** Calculates trust score based on multiple factors
**How:** Source reliability + Content quality + Consensus score + Recency
**Threshold:** 0.6 minimum confidence

### Layer 5: Trust System Verification

**What:** Validates against learning memory (Layer 1 truth)
**How:** Checks high-trust learning examples for support
**Threshold:** 0.7 minimum trust score

**Combined Effect:** Near-zero hallucination rate
**Fallback:** If any layer fails, overall confidence is reduced

---

## Cognitive Framework Enforcement

All LLM operations follow GRACE's **12 OODA Invariants**:

1. **OODA as Primary Control Loop** - Observe → Orient → Decide → Act
2. **Explicit Ambiguity Accounting** - Known/Inferred/Assumed/Unknown ledger
3. **Reversibility Before Commitment** - Reversible actions first
4. **Determinism Where Safety Depends on It** - Critical paths are deterministic
5. **Blast Radius Minimization** - Impact scope assessment
6. **Observability Is Mandatory** - All decisions logged
7. **Simplicity Is a First-Class Constraint** - Complexity must justify itself
8. **Feedback Is Continuous** - Outcomes feed back into system
9. **Bounded Recursion** - Recursion limits enforced
10. **Optionality > Optimization** - Preserve future choices
11. **Time-Bounded Reasoning** - Planning must terminate
12. **Forward Simulation (Chess Mode)** - Evaluate multiple paths

---

## Integration with GRACE Systems

### Genesis Keys

Every LLM interaction gets a Genesis Key for tracking:
- **Entity Type:** `llm_interaction`
- **Source Path:** Task ID
- **Relationships:** Links to user, documents, learning examples
- **Immutable Hash:** Content hash
- **Semantic Tags:** Task type, model used, verification status

### Layer 1 (Trust & Truth Foundation)

All LLM data flows through Layer 1:
- **Input:** User prompts processed through Layer 1 input system
- **Processing:** LLM responses validated against Layer 1 truth
- **Output:** Verified content feeds back into Layer 1
- **Trust Scores:** All outputs trust-scored based on Layer 1 evidence

### Learning Memory

LLM interactions feed into learning memory:
- **Recording:** Each verified interaction becomes a learning example
- **Trust Scoring:** Source reliability + Outcome quality + Consistency
- **Pattern Extraction:** Multiple similar interactions → patterns
- **Autonomous Learning:** High-trust examples → training data

### Version Control

All LLM interactions are version controlled:
- **Symbiotic Git Tracking:** Changes tracked with Genesis Keys
- **Audit Trail:** Complete history of LLM operations
- **Rollback:** Can trace back to specific LLM interactions

### RAG System

LLMs have full read-only access to RAG:
- **Query:** Semantic search across documents
- **Context:** Retrieve relevant chunks for grounding
- **Verification:** Check responses against indexed knowledge

### World Model

LLMs access current system state:
- **Documents:** Total count, average confidence
- **Chunks:** Vector-indexed content
- **Learning Examples:** Trust-scored training data
- **System Health:** Ollama, Qdrant, Database status

---

## Usage Patterns

### Pattern 1: Code Generation with Verification

```python
import requests

response = requests.post('http://localhost:8000/llm/task', json={
    "prompt": "Generate a Python function to calculate Fibonacci numbers",
    "task_type": "code_generation",
    "user_id": "GU-user123",
    "require_verification": True,
    "require_consensus": True,
    "require_grounding": False,  # Not requiring file refs for new code
    "enable_learning": True
})

result = response.json()

print(f"Task ID: {result['task_id']}")
print(f"Success: {result['success']}")
print(f"Verified: {result['verification_passed']}")
print(f"Trust Score: {result['trust_score']}")
print(f"Genesis Key: {result['genesis_key_id']}")
print(f"\nGenerated Code:\n{result['content']}")
```

### Pattern 2: Code Explanation with Repository Grounding

```python
response = requests.post('http://localhost:8000/llm/task', json={
    "prompt": "Explain how the file ingestion system works in backend/api/file_ingestion.py",
    "task_type": "code_explanation",
    "user_id": "GU-user123",
    "require_grounding": True,  # Must reference actual files
    "require_verification": True,
    "system_prompt": "Provide detailed technical explanation with code references"
})

result = response.json()

# Check audit trail for file references
for step in result['audit_trail']:
    if step['step'] == 'hallucination_verification':
        print(f"Grounding verification: {step.get('details', {})}")
```

### Pattern 3: Multi-Model Consensus Reasoning

```python
response = requests.post('http://localhost:8000/llm/task', json={
    "prompt": "What is the best approach to handle authentication in this system?",
    "task_type": "reasoning",
    "user_id": "GU-user123",
    "require_consensus": True,  # Multiple models must agree
    "require_verification": True
})

result = response.json()

if result['verification_passed']:
    print(f"Consensus reached with {result['confidence_score']:.2%} confidence")
    print(f"Trust score: {result['trust_score']:.2%}")
else:
    print("Models disagreed - low confidence response")
```

### Pattern 4: Autonomous LLM as Second Brain

```python
# LLMs verify their output against system knowledge
response = requests.post('http://localhost:8000/llm/task', json={
    "prompt": "Should we add rate limiting to the API? Analyze and recommend.",
    "task_type": "reasoning",
    "user_id": "GU-grace",  # Grace's autonomous action
    "require_verification": True,
    "enable_learning": True,
    "system_prompt": """You are GRACE's second brain for analysis.

    Verify your recommendations by:
    1. Checking existing system architecture
    2. Reviewing training data for similar decisions
    3. Ensuring alignment with GRACE's cognitive framework
    4. Confirming recommendations add value and knowledge
    5. Validating against user and system intent
    """
})

result = response.json()

# Check if recommendation adds value
adds_value = result['trust_score'] > 0.7 and result['confidence_score'] > 0.7

if adds_value:
    # Store in learning memory for future reference
    learning_id = result['learning_example_id']
    print(f"Recommendation stored in learning memory: {learning_id}")
else:
    print("Recommendation did not meet trust/confidence thresholds")
```

---

## Monitoring & Maintenance

### Daily Checks

```bash
# Check model availability
curl http://localhost:8000/llm/models

# Check statistics
curl http://localhost:8000/llm/stats

# Check verification stats
curl http://localhost:8000/llm/verification/stats

# Check access log
curl http://localhost:8000/llm/repo/access-log?limit=100
```

### Performance Metrics

Monitor these key metrics:
- **Success Rate:** Should be >90%
- **Verification Rate:** Should be >80%
- **Average Trust Score:** Should be >0.7
- **Average Confidence Score:** Should be >0.7
- **Layer Success Rates:** All layers should be >80%

### Alerts

Set alerts for:
- Success rate drops below 90%
- Verification rate drops below 70%
- Average trust score drops below 0.6
- High number of contradictions detected
- Consensus failures (models disagreeing frequently)

---

## Security & Safety

### Read-Only Access

✓ **All repository access is read-only**
✓ **LLMs cannot modify code**
✓ **LLMs cannot execute commands**
✓ **LLMs cannot delete files**
✓ **All access is logged for audit**

### Genesis Key Tracking

✓ **Every LLM interaction has Genesis Key**
✓ **Complete audit trail**
✓ **Version control integration**
✓ **Traceability to user/system**

### Cognitive Enforcement

✓ **Safety-critical operations require validation**
✓ **Blast radius assessment**
✓ **Reversibility checks**
✓ **Time bounds on reasoning**

### Trust System

✓ **All outputs trust-scored**
✓ **Low-trust outputs flagged**
✓ **Learning memory integration**
✓ **Continuous feedback loop**

---

## Next Steps

1. **Install Models:** Start with 7B models if resources are limited
2. **Test API:** Run example requests to verify setup
3. **Monitor Stats:** Check `/llm/stats` regularly
4. **Review Access Log:** Ensure LLMs are accessing correct data
5. **Integrate with Frontend:** Add LLM orchestration to UI
6. **Fine-tune Thresholds:** Adjust confidence/trust thresholds as needed
7. **Add More Models:** Install additional models as resources allow

---

## Troubleshooting

### Issue: No models available

**Solution:**
```bash
# Install at least one model
ollama pull qwen2.5-coder:7b-instruct
ollama pull mistral-small:22b

# Restart GRACE
python backend/app.py
```

### Issue: Verification always failing

**Solution:** Lower thresholds in request:
```json
{
  "require_consensus": false,
  "require_grounding": false
}
```

### Issue: Slow response times

**Solution:** Use smaller/faster models:
- Use 7B models instead of 70B
- Disable consensus (single model only)
- Use Mistral-Small for quick queries

### Issue: High contradiction rate

**Solution:**
- Review RAG system for outdated data
- Check learning memory for conflicting examples
- Update training data

---

## Summary

GRACE's Multi-LLM Orchestration System provides:

✅ **Multiple LLMs** - DeepSeek, Qwen, Llama, Mistral, Gemma
✅ **Near-Zero Hallucinations** - 5-layer verification pipeline
✅ **Cognitive Framework** - 12 OODA invariants enforced
✅ **Complete Integration** - Genesis Keys, Layer 1, Learning Memory
✅ **Full Observability** - Audit trails, access logs, decision traces
✅ **Read-Only Safety** - LLMs can't modify or execute
✅ **Trust System** - All outputs trust-scored
✅ **Autonomous Learning** - Continuous improvement loop

**The LLMs are verified second brains for GRACE, ensuring their output adds value, brings knowledge, and aligns with both user and system intent.**

---

**Documentation Version:** 1.0
**Last Updated:** 2026-01-11
**Status:** Production Ready
