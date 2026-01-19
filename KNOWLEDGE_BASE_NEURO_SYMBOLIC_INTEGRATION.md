# Knowledge Base & Neuro-Symbolic AI Integration

## Overview

The Knowledge Base Ingestion and Data Integrity Verification systems have been fully integrated into Grace's neuro-symbolic AI architecture through Layer 1 connectors. This enables autonomous knowledge base management with trust-aware embeddings and integrity verification.

---

## 🎯 Integration Components

### 1. **Knowledge Base Ingestion Connector**
**Location:** `backend/layer1/components/knowledge_base_connector.py`

**Purpose:**
- Connects AI Research Repository Ingestion to Layer 1 message bus
- Enables autonomous repository ingestion
- Supports trust-aware embedding generation (optional)
- Provides event-driven ingestion triggers

**Key Features:**
- ✅ Autonomous repository ingestion on detection
- ✅ Post-ingestion automatic verification triggers
- ✅ Trust-aware embedding support (when neuro-symbolic enabled)
- ✅ Progress tracking and event publishing
- ✅ Integration with neuro-symbolic trust system

**Usage:**
```python
from layer1.components import create_knowledge_base_ingestion_connector

connector = create_knowledge_base_ingestion_connector(
    ai_research_path="/path/to/ai_research",
    message_bus=message_bus,
    use_trust_aware=True,  # Enable trust-aware embeddings
    trust_weight=0.3,
    min_trust_threshold=0.3,
)
```

### 2. **Data Integrity Verification Connector**
**Location:** `backend/layer1/components/data_integrity_connector.py`

**Purpose:**
- Connects Data Integrity Verification System to Layer 1 message bus
- Enables autonomous integrity checking
- Calculates trust scores based on integrity
- Integrates with neuro-symbolic trust system

**Key Features:**
- ✅ Autonomous post-ingestion verification
- ✅ Periodic integrity checks
- ✅ Trust score calculation from integrity results
- ✅ Comprehensive integrity reporting
- ✅ Integration with neuro-symbolic reasoner

**Usage:**
```python
from layer1.components import create_data_integrity_connector

connector = create_data_integrity_connector(
    ai_research_path="/path/to/ai_research",
    database_path="/path/to/database.db",
    message_bus=message_bus,
    enable_trust_scoring=True,  # Enable trust score updates
)
```

---

## 🔗 Layer 1 Integration

### Initialization

The knowledge base connectors are integrated into Layer 1 initialization:

```python
from layer1.initialize import initialize_layer1

layer1 = initialize_layer1(
    session=db_session,
    kb_path="/path/to/knowledge_base",
    enable_neuro_symbolic=True,  # Enable neuro-symbolic features
    enable_knowledge_base=True,  # Enable knowledge base connectors
    ai_research_path="/path/to/ai_research",  # Optional
    database_path="/path/to/database.db",  # Optional
    trust_weight=0.3,
    min_trust_threshold=0.3,
)
```

### Automatic Features

When enabled, the following autonomous actions are triggered:

1. **New Repository Detection** → Auto-ingest
   - Trigger: `file.new_repository_detected`
   - Action: Ingest repository with trust-aware embeddings

2. **Ingestion Complete** → Auto-verify
   - Trigger: `knowledge_base.ingestion_complete`
   - Action: Run integrity verification

3. **Integrity Verified** → Update Trust Scores
   - Trigger: `knowledge_base.integrity_verified`
   - Action: Update trust scores based on integrity results

4. **Periodic Integrity Check**
   - Trigger: `system.periodic_check`
   - Action: Run periodic integrity verification

---

## 🔄 Message Bus Events

### Ingestion Events

- `knowledge_base.ingestion_started` - Ingestion started
- `knowledge_base.ingestion_complete` - Ingestion completed
- `knowledge_base.ingestion_all_started` - Batch ingestion started
- `knowledge_base.ingestion_all_complete` - Batch ingestion completed

### Integrity Events

- `knowledge_base.verification_started` - Verification started
- `knowledge_base.integrity_verified` - Verification completed
- `knowledge_base.trust_scores_updated` - Trust scores updated

### Request Handlers

- `knowledge_base.ingest_repository` - Ingest single repository
- `knowledge_base.ingest_all` - Ingest all repositories
- `knowledge_base.verify_integrity` - Verify data integrity
- `knowledge_base.get_ingestion_status` - Get ingestion status
- `knowledge_base.get_integrity_report` - Get integrity report

---

## 🧠 Neuro-Symbolic Integration

### Trust-Aware Embeddings

When `use_trust_aware=True` is enabled:

1. **Ingestion Phase:**
   - AI Research documents are ingested with trust-aware embeddings
   - High-trust sources (e.g., official docs) get higher trust scores
   - Trust scores influence embedding similarity calculations

2. **Retrieval Phase:**
   - Documents with high trust scores are prioritized
   - Trust-weighted similarity search
   - Low-trust documents are filtered out (below threshold)

3. **Reasoning Phase:**
   - Neuro-symbolic reasoner uses trust scores in joint inference
   - High-trust facts inform symbolic reasoning
   - Neural patterns validated against trusted knowledge

### Integrity-Based Trust Scoring

When `enable_trust_scoring=True` is enabled:

1. **After Verification:**
   - High integrity → High trust (0.9)
   - Issues found → Medium trust (0.5)
   - Critical failures → Low trust (0.3)

2. **Trust Propagation:**
   - Integrity trust scores propagate to embeddings
   - Used in neuro-symbolic reasoning
   - Influence retrieval ranking

---

## 📊 Integration Flow

```
┌─────────────────────┐
│  Repository Clone   │
│  (GitHub → Disk)    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Ingestion Connector│
│  - Detect repo      │
│  - Auto-ingest      │
│  - Trust-aware      │
│    embeddings       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Integrity Connector │
│  - Verify data      │
│  - Check hashes     │
│  - Calculate trust  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Neuro-Symbolic      │
│  - Trust-weighted   │
│    retrieval        │
│  - Joint inference  │
│  - Rule generation  │
└─────────────────────┘
```

---

## 🚀 Usage Examples

### Example 1: Manual Ingestion

```python
from layer1.message_bus import get_message_bus, Message, MessageType

message_bus = get_message_bus()

# Ingest single repository
result = await message_bus.send_request(
    "knowledge_base.ingest_repository",
    payload={
        "repo_path": "/path/to/repo",
        "category": "frameworks",
    }
)

print(f"Ingested: {result['success']}")
print(f"Stats: {result['stats']}")
```

### Example 2: Manual Verification

```python
# Verify integrity
result = await message_bus.send_request(
    "knowledge_base.verify_integrity",
    payload={
        "category": "frameworks",  # Optional filter
        "detailed": True,
    }
)

print(f"All checks passed: {result['all_checks_passed']}")
print(f"Report: {result['report']}")
```

### Example 3: Neuro-Symbolic Query with Trust-Aware KB

```python
# Query with neuro-symbolic reasoning
# (Uses trust-aware retrieval from ingested knowledge base)
result = await message_bus.send_request(
    "neuro_symbolic.reason",
    payload={
        "query": "How does Kubernetes handle container orchestration?",
        "context": {},
        "limit": 5,
        "min_overall_trust": 0.7,  # Only high-trust results
    }
)

print(f"Fused results: {len(result['fused_results'])}")
print(f"Confidence: {result['fusion_confidence']:.2f}")
```

---

## 📝 Configuration

### Environment Variables

```bash
# Knowledge Base Paths
AI_RESEARCH_PATH=/path/to/ai_research
DATABASE_PATH=/path/to/database.db

# Trust Configuration
TRUST_WEIGHT=0.3
MIN_TRUST_THRESHOLD=0.3

# Neuro-Symbolic
ENABLE_NEURO_SYMBOLIC=true
ENABLE_KNOWLEDGE_BASE=true
```

### Layer 1 Configuration

```python
layer1_config = {
    "enable_neuro_symbolic": True,
    "enable_knowledge_base": True,
    "trust_weight": 0.3,
    "min_trust_threshold": 0.3,
}
```

---

## ✅ Verification

### Check Integration

```python
from layer1.initialize import initialize_layer1

layer1 = initialize_layer1(
    session=db_session,
    kb_path="/path/to/kb",
    enable_knowledge_base=True,
)

# Check connectors are initialized
assert layer1.knowledge_base_ingestion is not None
assert layer1.data_integrity is not None

# Check autonomous actions
actions = layer1.get_autonomous_actions()
kb_actions = [a for a in actions if 'knowledge_base' in a.get('trigger_topic', '')]
print(f"Knowledge base autonomous actions: {len(kb_actions)}")
```

---

## 🎉 Benefits

1. **Autonomous Management**
   - No manual intervention needed
   - Automatic ingestion and verification
   - Self-healing integrity checks

2. **Trust-Aware Knowledge**
   - High-trust sources prioritized
   - Integrity-based trust scoring
   - Trust-weighted retrieval

3. **Neuro-Symbolic Integration**
   - Trust-aware embeddings
   - Integrity-informed reasoning
   - Joint neural + symbolic inference

4. **Complete Integration**
   - Seamless Layer 1 integration
   - Event-driven architecture
   - Message bus coordination

---

## 📚 Related Documentation

- **Ingestion:** `backend/scripts/ingest_ai_research_repos.py`
- **Verification:** `backend/scripts/verify_data_integrity.py`
- **Layer 1:** `backend/layer1/initialize.py`
- **Neuro-Symbolic:** `NEUROSYMBOLIC_AI_ROADMAP.md`
- **Knowledge Base:** `COMPLETE_KNOWLEDGE_BASE_SUMMARY.md`

---

**Status:** ✅ **FULLY INTEGRATED**

All knowledge base ingestion and verification systems are now integrated into Grace's neuro-symbolic AI architecture through Layer 1 connectors.
