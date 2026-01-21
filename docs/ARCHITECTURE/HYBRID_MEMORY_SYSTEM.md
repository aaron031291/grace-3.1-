# Grace Hybrid Memory System

## Overview

Grace's memory architecture is a **hybrid** of two advanced cognitive memory designs:

1. **Neuro-Symbolic Memory System** (Dr. Alex Carter) - Short/Long-Term Memory with Episodic, Semantic, and Procedural stores
2. **Magma Architecture** - Graph-based memory with 4 relation types and RRF fusion

This hybrid provides the best of both approaches: the cognitive organization of human-like memory with the precision of graph-based relational retrieval.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                    GRACE HYBRID NEURO-SYMBOLIC + MAGMA MEMORY                       │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  ┌──────────────────────────────────┐    ┌──────────────────────────────────┐      │
│  │     SHORT-TERM MEMORY            │    │       LONG-TERM MEMORY           │      │
│  │     (Working Memory)             │    │                                  │      │
│  │                                  │    │  ┌────────────────────────────┐  │      │
│  │  ┌────────────────────────────┐  │    │  │     EPISODIC BUFFER        │  │      │
│  │  │  Sensory Input Processor   │  │    │  │                            │  │      │
│  │  │  ════════════════════════  │  │    │  │  • Temporal Graph          │  │      │
│  │  │  Magma: Event Segmentation │  │    │  │  • JudgementDecisionMemory │  │      │
│  │  │  + Dense/Sparse Embedding  │  │    │  │  • Temporal event linking  │  │      │
│  │  └────────────────────────────┘  │    │  └────────────────────────────┘  │      │
│  │              │                   │    │              ↕                   │      │
│  │              ▼                   │    │  ┌────────────────────────────┐  │      │
│  │  ┌────────────────────────────┐  │    │  │     SEMANTIC NETWORK       │  │      │
│  │  │     Attention Module       │  │    │  │                            │  │      │
│  │  │  ════════════════════════  │  │    │  │  • Semantic Graph          │  │      │
│  │  │  Magma: Intent-Aware Router│  │    │  │  • InterpreterPatternMemory│  │      │
│  │  │  + Anchor Identification   │  │    │  │  • Concept similarity      │  │      │
│  │  └────────────────────────────┘  │    │  └────────────────────────────┘  │      │
│  │              │                   │    │              ↕                   │      │
│  │              ▼                   │    │  ┌────────────────────────────┐  │      │
│  │  ┌────────────────────────────┐  │    │  │   PROCEDURAL REPOSITORY    │  │      │
│  │  │     Context Encoder        │  │    │  │                            │  │      │
│  │  │  ════════════════════════  │  │    │  │  • ActionRouterMemory      │  │      │
│  │  │  Magma: Semantic/Temporal/ │  │    │  │  • Learned procedures      │  │      │
│  │  │  Entity/Causal Linking     │  │    │  │  • Success rate tracking   │  │      │
│  │  └────────────────────────────┘  │    │  └────────────────────────────┘  │      │
│  │              │                   │    │              │                   │      │
│  │      Attention Mechanism         │    │       Inference Engine           │      │
│  │              │                   │    │       (LLM Causal Inferencer)    │      │
│  └──────────────┼───────────────────┘    └──────────────┼───────────────────┘      │
│                 │                                        │                          │
│                 ▼                                        ▼                          │
│  ┌──────────────────────────────────────────────────────────────────────────┐      │
│  │                         VECTOR DATABASE                                   │      │
│  │  ┌────────────────────────────────────────────────────────────────────┐  │      │
│  │  │              MAGMA 4 RELATION GRAPHS + Vector Store                │  │      │
│  │  │                                                                    │  │      │
│  │  │   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │  │      │
│  │  │   │   SEMANTIC   │  │   TEMPORAL   │  │    CAUSAL    │            │  │      │
│  │  │   │    Graph     │  │    Graph     │  │    Graph     │            │  │      │
│  │  │   │              │  │              │  │              │            │  │      │
│  │  │   │ • Concepts   │  │ • Events     │  │ • Causes     │            │  │      │
│  │  │   │ • Similarity │  │ • Sequences  │  │ • Effects    │            │  │      │
│  │  │   │ • Embeddings │  │ • Time links │  │ • Inference  │            │  │      │
│  │  │   └──────────────┘  └──────────────┘  └──────────────┘            │  │      │
│  │  │                                                                    │  │      │
│  │  │   ┌──────────────┐  ┌────────────────────────────────────────┐    │  │      │
│  │  │   │    ENTITY    │  │           VECTOR STORE                 │    │  │      │
│  │  │   │    Graph     │  │                                        │    │  │      │
│  │  │   │              │  │  • Embeddings for all nodes            │    │  │      │
│  │  │   │ • Named ents │  │  • Fast similarity search              │    │  │      │
│  │  │   │ • Co-occur   │  │  • Cross-graph indexing                │    │  │      │
│  │  │   │ • Attributes │  │                                        │    │  │      │
│  │  │   └──────────────┘  └────────────────────────────────────────┘    │  │      │
│  │  └────────────────────────────────────────────────────────────────────┘  │      │
│  └──────────────────────────────────────────────────────────────────────────┘      │
│                                       │                                             │
│                                       ▼                                             │
│  ┌──────────────────────────────────────────────────────────────────────────┐      │
│  │                         RETRIEVAL LAYER                                   │      │
│  │                                                                           │      │
│  │   ┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐│      │
│  │   │ CONTEXTUAL RETRIEVAL│ │   EPISODIC BUFFER   │ │  INFERENCE ENGINE   ││      │
│  │   │ ═══════════════════ │ │ ═══════════════════ │ │ ═══════════════════ ││      │
│  │   │                     │ │                     │ │                     ││      │
│  │   │ • RRF Fusion        │ │ • Neighbor Retrieval│ │ • LLM Causal        ││      │
│  │   │ • Multi-graph merge │ │ • Multi-hop traverse│ │ • Pattern detection ││      │
│  │   │ • Weighted ranking  │ │ • Recency weighting │ │ • Chain tracing     ││      │
│  │   │ • Source diversity  │ │ • Context synthesis │ │ • Explanation gen   ││      │
│  │   └─────────────────────┘ └─────────────────────┘ └─────────────────────┘│      │
│  └──────────────────────────────────────────────────────────────────────────┘      │
│                                       │                                             │
│                                       ▼                                             │
│  ┌──────────────────────────────────────────────────────────────────────────┐      │
│  │                         QUERY FLOW                                        │      │
│  │                                                                           │      │
│  │   Semantic Query ──────► Knowledge Graph ──────► Episodic Recall          │      │
│  │   (Intent Router)        (4 Relation Graphs)     (Context Synthesizer)    │      │
│  │                                                                           │      │
│  └──────────────────────────────────────────────────────────────────────────┘      │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Mapping

### Neuro-Symbolic → Magma Implementation

| Neuro-Symbolic Component | Magma Implementation | Grace Class |
|-------------------------|---------------------|-------------|
| **SHORT-TERM MEMORY** | | |
| Sensory Input Processor | Event Segmentation | `EventSegmenter` |
| Attention Module | Intent-Aware Router | `IntentAwareRouter` |
| Context Encoder | Dense/Sparse Embedding + Linking | `SynapticIngestionPipeline` |
| Attention Mechanism | Anchor Identification | `AnchorIdentifier` |
| **LONG-TERM MEMORY** | | |
| Episodic Buffer | Temporal Graph | `TemporalGraph` + `JudgementDecisionMemory` |
| Semantic Network | Semantic Graph | `SemanticGraph` + `InterpreterPatternMemory` |
| Procedural Repository | Action Memory | `ActionRouterMemory` |
| Inference Engine | LLM Causal Inferencer | `LLMCausalInferencer` |
| **RETRIEVAL** | | |
| Contextual Retrieval | RRF Fusion | `MagmaFusion` + `AdaptiveTopologicalRetriever` |
| Episodic Buffer | Neighbor Retrieval | `NeighborRetriever` |
| Knowledge Graph | 4 Relation Graphs | `MagmaRelationGraphs` |
| Episodic Recall | Context Synthesizer | `ContextSynthesizer` |

---

## Data Flow

### Write Path (Synaptic Ingestion)

```
User Input / System Event
         │
         ▼
┌─────────────────────────────────────┐
│    SENSORY INPUT PROCESSOR          │
│    (Event Segmentation)             │
│                                     │
│    • Break into segments            │
│    • Extract entities               │
│    • Identify concepts              │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│    CONTEXT ENCODER                  │
│    (Dense/Sparse Embedding)         │
│                                     │
│    • Generate embeddings            │
│    • Semantic linking               │
│    • Temporal linking               │
│    • Entity linking                 │
│    • Causal linking                 │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│    ASYNC CONSOLIDATION              │
│                                     │
│    • Queue operations               │
│    • Neighbor retrieval             │
│    • LLM causal inference           │
│    • Background optimization        │
└─────────────────────────────────────┘
         │
         ▼
    4 RELATION GRAPHS + VECTOR STORE
```

### Read Path (Query Process)

```
User Query
         │
         ▼
┌─────────────────────────────────────┐
│    ATTENTION MODULE                 │
│    (Intent-Aware Router)            │
│                                     │
│    • Classify intent                │
│    • Identify anchors               │
│    • Select target graphs           │
│    • Choose retrieval policy        │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│    ADAPTIVE TOPOLOGICAL RETRIEVAL   │
│    (Multi-Graph Traversal)          │
│                                     │
│    • BFS / Best-first traversal     │
│    • Cross-graph retrieval          │
│    • Neighbor expansion             │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│    CONTEXTUAL RETRIEVAL             │
│    (RRF Fusion)                     │
│                                     │
│    • Merge multi-source results     │
│    • Reciprocal rank fusion         │
│    • Source-weighted scoring        │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│    EPISODIC RECALL                  │
│    (Context Synthesizer)            │
│                                     │
│    • Linearize for LLM              │
│    • Structure context              │
│    • Include metadata               │
└─────────────────────────────────────┘
         │
         ▼
    Final Response to LLM/User
```

---

## Grace Layer Integration

The hybrid memory system integrates with all 4 cognitive layers:

### Layer 1: Message Bus Integration
- `MagmaMessageBusConnector` subscribes to system events
- Auto-ingests learning experiences
- Triggers causal inference on errors
- Schedules background consolidation

### Layer 2: Interpreter Integration
- `InterpreterPatternMemory` stores detected patterns
- Finds similar past patterns
- Tracks pattern evolution over time
- Links to Semantic Graph

### Layer 3: Judgement Integration
- `JudgementDecisionMemory` stores decisions
- Finds precedents for similar situations
- Records decision outcomes
- Links to Temporal + Causal Graphs

### Layer 4: Action Router Integration
- `ActionRouterMemory` stores procedures
- Finds best procedures by success rate
- Tracks procedure statistics
- Links to Procedural Repository

---

## Security Integration

### Genesis Keys
- Every memory operation tracked with provenance
- Full audit trail for ingestion/queries
- Rollback capability through Genesis Keys

### Trust Scoring
- Neural trust-aware retrieval
- Trust-weighted result ranking
- Trust decay over time
- Feedback loop for trust updates

### Governance
- Constitutional rule enforcement
- PII detection before ingestion
- Query scope validation
- Compliance logging

---

## Usage

```python
from cognitive.magma import get_grace_magma

# Get the unified hybrid memory system
magma = get_grace_magma()

# === SHORT-TERM MEMORY OPERATIONS ===

# Sensory Input Processing (Event Segmentation)
magma.ingest("User reported database timeout errors")

# Attention (Intent-Aware Query)
results = magma.query("What causes database timeouts?")

# === LONG-TERM MEMORY OPERATIONS ===

# Episodic Buffer (Temporal/Decision Memory)
magma.store_decision("heal", "degraded", "Restart database connection")
precedents = magma.find_precedents("degraded", "high", "database issue")

# Semantic Network (Pattern Memory)
magma.store_pattern("error_cluster", "Database timeout pattern")
similar = magma.find_similar_patterns("timeout error")

# Procedural Repository (Action Memory)
magma.store_procedure("heal", "DB Reconnect", ["Stop pool", "Clear", "Restart"])
best_proc = magma.get_best_procedure("heal", "database")

# === INFERENCE OPERATIONS ===

# Causal Inference
causes = magma.why("Why do database connections fail?")

# Explanation Generation
explanation = magma.explain("What causes timeouts?")

# === RETRIEVAL OPERATIONS ===

# Contextual Retrieval with RRF Fusion
context = magma.get_context("database troubleshooting")
```

---

## File Structure

```
backend/cognitive/magma/
├── __init__.py                  # Unified exports + MagmaMemory class
├── grace_magma_system.py        # GraceMagmaSystem (unified entry point)
├── layer_integrations.py        # Layer 1-4 + Security integrations
│
├── relation_graphs.py           # 4 Relation Graphs (Semantic/Temporal/Causal/Entity)
├── intent_router.py             # Attention Module (Intent classification)
├── rrf_fusion.py                # Contextual Retrieval (RRF fusion)
├── topological_retrieval.py     # Graph traversal algorithms
├── synaptic_ingestion.py        # Sensory Input + Context Encoding
├── async_consolidation.py       # Background consolidation
└── causal_inference.py          # Inference Engine (LLM causal)
```

---

## Summary

Grace's Hybrid Memory System combines:

| Capability | From Neuro-Symbolic | From Magma |
|-----------|---------------------|------------|
| Human-like memory organization | Short/Long-term, Episodic/Semantic/Procedural | - |
| Graph-based relations | - | 4 typed graphs with edges |
| Attention mechanism | Attention Module | Intent-Aware Router |
| Multi-source fusion | - | RRF Fusion |
| Causal reasoning | Inference Engine | LLM Causal Inferencer |
| Vector similarity | Vector Database | Embedding-based retrieval |
| Temporal awareness | Episodic Buffer | Temporal Graph |
| Procedural learning | Procedural Repository | ActionRouterMemory |

**Result: A unified cognitive memory system that thinks like a human but retrieves with graph precision.**
