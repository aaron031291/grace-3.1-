# Enhanced Oracle Intelligence System

## Maximum Capability Implementation

The Oracle has been enhanced with:

1. **Multi-hop Reasoning Chains** with evidence links
2. **Confidence Calibration** using Expected Calibration Error (ECE)
3. **Feedback Loops** - outcomes update calibration and learning
4. **Unified Memory** - all knowledge in one format
5. **Knowledge Freshness Decay** - prioritize stale knowledge
6. **Priority Queue** - impact × uncertainty × freshness
7. **Cross-source Correlation** - boost confidence with corroboration
8. **Pattern Evolution Tracking** - detect drift
9. **LLM Orchestration** - Planner → Analyst → Critic
10. **Evidence-based Learning** - not just embedding gaps

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ENHANCED ORACLE SYSTEM                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────┐    ┌──────────────────┐    ┌───────────────┐  │
│  │ UNIFIED ORACLE  │───▶│ ENHANCED MEMORY  │───▶│ VECTOR DB     │  │
│  │ HUB             │    │ - Calibration    │    │ - Semantic    │  │
│  │ - 13 Sources    │    │ - Correlation    │    │ - Indexed     │  │
│  └─────────────────┘    │ - Priority Queue │    └───────────────┘  │
│          │              └──────────────────┘           │           │
│          │                      │                      │           │
│          ▼                      ▼                      ▼           │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              ENHANCED PROACTIVE LEARNING                     │   │
│  │                                                               │   │
│  │  ┌─────────┐    ┌──────────┐    ┌────────┐    ┌─────────┐   │   │
│  │  │ PLANNER │───▶│ ANALYST  │───▶│ CRITIC │───▶│ STORE   │   │   │
│  │  │ (LLM)   │    │ (LLM)    │    │ (LLM)  │    │         │   │   │
│  │  └─────────┘    └──────────┘    └────────┘    └─────────┘   │   │
│  │                                                               │   │
│  │  Learning Modes:                                              │   │
│  │  ├── Evidence Gap    (missing proof for claims)              │   │
│  │  ├── Staleness       (outdated knowledge)                    │   │
│  │  ├── Pattern Drift   (success rate changing)                 │   │
│  │  ├── Failure Analysis (wrong predictions)                    │   │
│  │  ├── Cross-pollinate  (connect different areas)              │   │
│  │  └── Frontier Explore (expand boundaries)                    │   │
│  └─────────────────────────────────────────────────────────────┘   │
│          │                                                         │
│          ▼                                                         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    REVERSE KNN ENGINE                        │   │
│  │  - Embedding gaps → Expansion queries                        │   │
│  │  - Same sources (GitHub, SO, arXiv, Web)                     │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Files Created

| File | Purpose |
|------|---------|
| `enhanced_oracle_memory.py` | Unified memory, calibration, correlation |
| `enhanced_proactive_learning.py` | LLM orchestration, evidence-based learning |
| `enhanced_learning_api.py` | REST API endpoints |

## Key Features

### 1. Confidence Calibration (ECE)

Instead of arbitrary confidence scores, we track accuracy per confidence bucket:

```python
# Record outcome
memory.record_outcome(memory_id="...", was_correct=True)

# Calibration adjusts future scores
# If we predict 80% but actual accuracy is 65%, we calibrate down
calibrated = calibrator.calibrate("failure", raw_confidence=0.8)
# → Returns ~0.65
```

**API:**
```bash
curl http://localhost:8000/enhanced-learning/memory/calibration
```

### 2. Cross-Source Correlation

When GitHub, StackOverflow, and research papers all say the same thing:

```python
# Multiple sources → Higher confidence
cluster.combined_confidence = 0.95  # 3 independent sources

# Knowledge items get correlation links
item.correlated_with = ["GITHUB-123", "SO-456", "ARXIV-789"]
```

**API:**
```bash
curl http://localhost:8000/enhanced-learning/memory/correlations
```

### 3. Multi-Hop Evidence Chains

Build reasoning chains with evidence:

```python
chain = await memory.retrieve_evidence_chain(
    query="async error handling best practices",
    max_hops=3
)
# Returns:
# - Step 1: Research entry on error handling
# - Step 2: Pattern from successful code
# - Step 3: Stack Overflow solution
```

**API:**
```bash
curl -X POST http://localhost:8000/enhanced-learning/memory/evidence-chain \
  -H "Content-Type: application/json" \
  -d '{"query": "caching strategies", "max_hops": 3}'
```

### 4. Priority Queue

Items prioritized by: `impact × uncertainty × staleness × usage`

```python
# Security + uncertain + stale = HIGH PRIORITY
priority = impact(0.95) × uncertainty(0.6) × staleness(0.8) × usage(1.2)
# → Priority = 0.55 (top of queue)
```

**API:**
```bash
curl http://localhost:8000/enhanced-learning/memory/priority-items
```

### 5. LLM Orchestration

Three-role pattern for knowledge acquisition:

| Role | Function |
|------|----------|
| **Planner** | Decides what queries to run, which sources |
| **Analyst** | Extracts findings and evidence links |
| **Critic** | Checks quality, adjusts confidence, approves |

```bash
curl -X POST http://localhost:8000/enhanced-learning/learning/run-cycle
```

### 6. Learning Modes

| Mode | Description | Trigger |
|------|-------------|---------|
| `evidence_gap` | Missing proof for claims | High impact + low confidence |
| `staleness` | Outdated knowledge | freshness < 0.5 |
| `pattern_drift` | Success rate changing | 20%+ drift in recent outcomes |
| `failure` | Wrong predictions | Recorded failures |
| `cross` | Connect different areas | Multi-source correlations |
| `frontier` | Expand boundaries | Sparse KNN clusters |

## API Endpoints

### Memory

| Endpoint | Description |
|----------|-------------|
| `GET /enhanced-learning/memory/stats` | Full memory statistics |
| `GET /enhanced-learning/memory/calibration` | ECE and accuracy report |
| `GET /enhanced-learning/memory/correlations` | Cross-source clusters |
| `GET /enhanced-learning/memory/priority-items` | Top priority items |
| `GET /enhanced-learning/memory/expansion-targets` | Items needing expansion |
| `POST /enhanced-learning/memory/retrieve` | Semantic search |
| `POST /enhanced-learning/memory/evidence-chain` | Multi-hop retrieval |
| `POST /enhanced-learning/memory/record-outcome` | Record prediction outcome |
| `POST /enhanced-learning/memory/save` | Persist state |

### Learning

| Endpoint | Description |
|----------|-------------|
| `GET /enhanced-learning/learning/stats` | Learning statistics |
| `POST /enhanced-learning/learning/generate-targets` | Generate learning targets |
| `POST /enhanced-learning/learning/run-cycle` | Run complete cycle |
| `POST /enhanced-learning/learning/start` | Start continuous learning |
| `POST /enhanced-learning/learning/stop` | Stop continuous learning |
| `POST /enhanced-learning/learning/record-failure` | Record failed prediction |
| `POST /enhanced-learning/learning/record-pattern` | Track pattern outcome |

### Combined

| Endpoint | Description |
|----------|-------------|
| `GET /enhanced-learning/status` | All systems status |
| `POST /enhanced-learning/initialize-all` | Initialize everything |

## Quick Start

### 1. Initialize All Systems
```bash
curl -X POST http://localhost:8000/enhanced-learning/initialize-all
```

### 2. Check Status
```bash
curl http://localhost:8000/enhanced-learning/status
```

### 3. Run Learning Cycle
```bash
curl -X POST http://localhost:8000/enhanced-learning/learning/run-cycle
```

### 4. Start Continuous Learning
```bash
curl -X POST "http://localhost:8000/enhanced-learning/learning/start?interval_seconds=300"
```

### 5. Record Outcomes (For Calibration)
```bash
curl -X POST http://localhost:8000/enhanced-learning/memory/record-outcome \
  -H "Content-Type: application/json" \
  -d '{"memory_id": "MEM-abc123", "was_correct": true}'
```

## Integration with Learning Memory

The enhanced system connects to the existing learning memory:

```python
# All ingestion flows through Oracle Hub
hub.ingest_from_learning_memory(
    training_type="error_fix",
    data={"error": "NullPointer", "fix": "Add null check"},
    trust_score=0.85
)

# Enhanced memory applies calibration
item.calibrated_confidence = calibrator.calibrate("pattern", 0.85)
# → May adjust to 0.78 based on historical accuracy

# Cross-source correlation boosts confidence
if correlated_with_github_and_stackoverflow:
    item.correlation_confidence = 0.95
```

## Summary

✅ **Calibration** - Confidence scores now mean something (ECE tracking)
✅ **Correlation** - Multi-source agreement → higher confidence  
✅ **Evidence Chains** - Multi-hop reasoning with provenance
✅ **Priority Queue** - Impact × Uncertainty × Freshness × Usage
✅ **LLM Orchestration** - Planner → Analyst → Critic pattern
✅ **6 Learning Modes** - Evidence gaps, staleness, drift, failures, cross, frontier
✅ **Pattern Evolution** - Detect when patterns stop working
✅ **Feedback Loops** - Outcomes update calibration and learning
✅ **Unified Memory** - All knowledge in one format
✅ **Freshness Decay** - Stale knowledge gets priority for refresh
