# Third-Party LLM Integration System
## Automatic Handshake & Integration

**Status:** ✅ Complete
**Version:** 1.0
**Date:** 2026-01-11

---

## 🎯 Overview

When a third-party LLM (Gemini, GPT-4, Claude, etc.) connects to GRACE, it **immediately** receives:

1. ✅ **Complete System Architecture** - Layer 1, Layer 2, all systems
2. ✅ **All Rules & Governance** - Three-Pillar Governance Framework
3. ✅ **Available APIs & Scripts** - Repository access, Layer 1, Genesis Keys
4. ✅ **Integration Protocols** - How to work with GRACE
5. ✅ **Hallucination Prevention** - 6-layer validation rules
6. ✅ **Layer 1 Trust System** - Deterministic trust scoring
7. ✅ **Cognitive Framework** - OODA Loop + 12 Invariants

**Result:** Seamless integration - LLM understands GRACE immediately!

---

## 🚀 Quick Start

### Register Gemini

```python
from backend.llm_orchestrator.third_party_llm_client import get_third_party_llm_client

client = get_third_party_llm_client()

# Register with automatic handshake
llm_id = client.register_gemini(
    api_key="your-gemini-api-key",
    model_name="gemini-pro"
)

# Use immediately
response = client.generate(
    llm_id=llm_id,
    prompt="What is GRACE's trust scoring formula?"
)
```

### Register OpenAI

```python
llm_id = client.register_openai(
    api_key="your-openai-api-key",
    model_name="gpt-4"
)
```

### Register Anthropic Claude

```python
llm_id = client.register_anthropic(
    api_key="your-anthropic-api-key",
    model_name="claude-3-opus-20240229"
)
```

---

## 📡 REST API

### Register Gemini

```bash
POST /third-party-llm/register/gemini
{
    "api_key": "your-api-key",
    "model_name": "gemini-pro",
    "base_url": null  # optional
}
```

**Response:**
```json
{
    "success": true,
    "llm_id": "gemini_gemini-pro_1234567890",
    "handshake_passed": true,
    "capabilities": {
        "handshake_acknowledged": true,
        "integration_test_passed": true,
        "can_provide_sources": true,
        "can_provide_trust_scores": true,
        "understands_ooda": true,
        "understands_invariants": true
    },
    "errors": []
}
```

### Generate Response

```bash
POST /third-party-llm/generate
{
    "llm_id": "gemini_gemini-pro_1234567890",
    "prompt": "What is GRACE's trust scoring formula?",
    "system_prompt": null,  # optional, uses system context if not provided
    "temperature": 0.7,
    "max_tokens": 4096
}
```

### List Integrated LLMs

```bash
GET /third-party-llm/list
```

---

## 🔄 Handshake Process

### Step 1: System Context Provided

When LLM connects, it immediately receives complete system context:

```
# GRACE System Integration Guide
# Version: 3.1

## System Architecture
- Layer 1: Trust & Truth Foundation (Deterministic)
- Layer 2: Intelligent Processing (Neural/AI)
- Complete governance framework
- Hallucination prevention (6 layers)
- Genesis Key tracking

## Hallucination Prevention (6 LAYERS)
1. Repository Grounding
2. Cross-Model Consensus
3. Contradiction Detection
4. Confidence Scoring
5. Trust System Verification
6. External Verification

## Cognitive Framework (OODA + 12 Invariants)
- OODA Loop: Observe → Orient → Decide → Act
- 12 Invariants (mandatory)

## Available APIs
- Repository Access (read-only)
- Layer 1 Access (trust system)
- Genesis Key System (audit trail)
- Learning Memory

## Response Format Requirements
- Content
- Sources (file paths)
- Trust Score
- Evidence
- Invariants considered
- Ambiguity ledger

... (complete documentation)
```

### Step 2: Acknowledgment

LLM must acknowledge:
- Understanding of system architecture
- Agreement to follow all rules
- Capability to provide required response format

### Step 3: Integration Test

LLM is tested with sample query:
- Response format compliance
- Source citation
- Trust scoring
- Invariant acknowledgment

### Step 4: Production Use

Once integrated, all responses are:
- ✅ Validated through 6-layer hallucination prevention
- ✅ Tracked with Genesis Keys
- ✅ Scored for trust
- ✅ Logged for audit

---

## 🛡️ What LLM Receives

### System Architecture

- **Layer 1**: Trust & Truth Foundation (deterministic)
- **Layer 2**: Intelligent Processing (neural/AI)
- **Integration Rule**: Layer 1 controls Layer 2

### Hallucination Prevention (6 Layers)

1. **Repository Grounding** - Must reference actual files
2. **Cross-Model Consensus** - Multiple models must agree
3. **Contradiction Detection** - Must not contradict knowledge
4. **Confidence Scoring** - Must have high confidence
5. **Trust System Verification** - Must align with Layer 1
6. **External Verification** - Critical claims must be verifiable

### Cognitive Framework

- **OODA Loop**: Observe → Orient → Decide → Act
- **12 Invariants**: Mandatory for all operations

### Available APIs

```python
# Repository Access (Read-Only)
repo_access.read_file(file_path: str) -> str
repo_access.search_code(pattern: str) -> List[Dict]
repo_access.get_learning_examples(min_trust_score: float) -> List[Dict]

# Layer 1 Access (Trust System)
layer1.get_knowledge(topic: str, min_trust_score: float) -> Dict
layer1.validate_against_trust_system(content: str) -> Dict

# Genesis Key System (Audit Trail)
genesis.create_genesis_key(what, when, who, why, how) -> str
```

### Response Format

Every response MUST include:
1. **Content** - Actual response
2. **Sources** - File paths/documents referenced
3. **Trust Score** - Confidence (0-1)
4. **Evidence** - Layer 1 evidence
5. **Invariants** - Which OODA invariants considered
6. **Ambiguity Ledger** - Known/Inferred/Assumed/Unknown

---

## ✅ Integration Checklist

Before LLM can be used in production:

- [x] System context provided
- [x] Handshake acknowledged
- [x] Integration test passed
- [x] Response format correct
- [x] Source citation working
- [x] Trust scoring working
- [x] OODA invariants acknowledged

---

## 🔐 Security & Governance

### All LLM Operations Are:

- ✅ **Tracked** - Genesis Keys for every operation
- ✅ **Validated** - 6-layer hallucination prevention
- ✅ **Scored** - Trust scores calculated
- ✅ **Audited** - Complete audit trail
- ✅ **Governed** - Three-Pillar Governance Framework

### Determinism Preserved

Even with third-party LLMs:
- ✅ Layer 1 validates deterministically
- ✅ Trust scores are mathematical
- ✅ Decisions are evidence-based
- ✅ Fallback to Layer 1 if validation fails

**See:** `DETERMINISM_WITH_THIRD_PARTY_LLMS.md`

---

## 📊 Example: Gemini Integration

```python
from backend.llm_orchestrator.third_party_llm_client import get_third_party_llm_client

# Initialize client
client = get_third_party_llm_client()

# Register Gemini (automatic handshake)
llm_id = client.register_gemini(
    api_key="your-api-key",
    model_name="gemini-pro"
)

# Use immediately
response = client.generate(
    llm_id=llm_id,
    prompt="What is GRACE's trust scoring formula?"
)

# Response includes:
# - Content (answer)
# - Sources (if any)
# - Trust score
# - Evidence
# - Invariants considered
# - Ambiguity ledger
```

---

## 🎯 Key Features

### Automatic Handshake

- ✅ System context provided immediately
- ✅ Rules acknowledged automatically
- ✅ Integration test runs automatically
- ✅ Capabilities determined automatically

### Seamless Integration

- ✅ Works with existing hallucination prevention
- ✅ Works with existing trust system
- ✅ Works with existing governance
- ✅ Works with existing audit trail

### Enterprise Ready

- ✅ Complete audit trail (Genesis Keys)
- ✅ Deterministic validation (Layer 1)
- ✅ Governance compliance
- ✅ Security hardened

---

## 📝 Files Created

1. **`backend/llm_orchestrator/third_party_llm_integration.py`**
   - Handshake protocol
   - System context provider
   - Integration manager

2. **`backend/llm_orchestrator/third_party_llm_client.py`**
   - API clients (Gemini, OpenAI, Anthropic)
   - Response handling
   - Error handling

3. **`backend/api/third_party_llm_api.py`**
   - REST API endpoints
   - Registration endpoints
   - Generation endpoints

---

## 🚀 Next Steps

1. **Register your LLM** - Use API or Python client
2. **Automatic handshake** - System context provided
3. **Start using** - LLM understands GRACE immediately!

---

## ✅ Summary

**Third-party LLM integration is now automatic:**

- ✅ **Handshake** - Complete system context provided
- ✅ **Integration** - All rules and APIs explained
- ✅ **Validation** - 6-layer hallucination prevention
- ✅ **Tracking** - Genesis Keys for audit trail
- ✅ **Governance** - Three-Pillar Framework
- ✅ **Determinism** - Layer 1 validation preserved

**When a new LLM connects, it immediately understands GRACE!** 🎉
