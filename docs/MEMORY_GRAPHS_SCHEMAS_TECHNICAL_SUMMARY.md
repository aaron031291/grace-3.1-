# Memory, Graphs & Database Schemas — Complete Technical Summary

---

## Part 1: Memory Systems

GRACE has 7 distinct memory systems that form a hierarchy from volatile to permanent.

### 1.1 Ghost Memory (`cognitive/ghost_memory.py`)

**What**: Per-task in-memory scratch buffer. Lives only during a task execution. Volatile.

**Class**: `GhostMemory`
- `start_task(task_id)` — begin tracking
- `append(key, value)` — add context during execution
- `get_context()` — retrieve accumulated context
- `complete_task()` — save to procedural memory and playbook, then clear
- `evolve_playbook()` — refine playbook from completed tasks

**Lifetime**: Single task. On `complete_task()`, saves to `Procedure` via `store_procedure()`.

**When used**: Coding pipeline, multi-step reasoning, any task that builds context incrementally.

---

### 1.2 Episodic Memory (`cognitive/episodic_memory.py`)

**What**: Records of past problems, actions taken, and outcomes. "What happened last time we saw this problem?"

**Table**: `episodes`

| Column | Type | Purpose |
|--------|------|---------|
| `problem` | Text | What the problem was |
| `action` | Text (JSON) | What action was taken |
| `outcome` | Text (JSON) | What the result was |
| `predicted_outcome` | Text (JSON) | What was expected |
| `prediction_error` | Float | How wrong the prediction was |
| `trust_score` | Float | Reliability of this episode |
| `source` | String | Where this came from |
| `genesis_key_id` | String | Genesis Key link |
| `decision_id` | String | Decision that produced this |
| `embedding` | Text (JSON) | Vector for semantic recall |
| `episode_metadata` | Text (JSON) | Extra data |

**Class**: `EpisodicBuffer`
- `record_episode(problem, action, outcome, predicted_outcome, trust_score, source, genesis_key_id)` — store an episode
- `recall_similar(problem, k=5, min_trust=0.5)` — find similar past episodes (semantic or text-based)
- `generate_episode_embedding(episode)` — create embedding for semantic recall
- `recall_by_topic(conversation_id, topic, k=3)` — topic-based recall

**When used**: Autonomous loop checks episodic memory before deciding what action to take. If a similar problem was solved before, it reuses the solution.

---

### 1.3 Learning Memory (`cognitive/learning_memory.py`)

**What**: Curated input/output training examples with trust scores. "What did we learn and how reliable is it?"

**Table**: `learning_examples`

| Column | Type | Purpose |
|--------|------|---------|
| `example_type` | String | Category (e.g., "code_fix", "query_response") |
| `input_context` | Text (JSON) | Input that was given |
| `expected_output` | Text (JSON) | What should have happened |
| `actual_output` | Text (JSON) | What actually happened |
| `trust_score` | Float | Composite trust score (0-1) |
| `source` | String | Where this came from |
| `genesis_key_id` | String | Genesis Key link |
| `times_referenced` | Integer | How often this was used |
| `times_validated` | Integer | Successful validations |
| `times_invalidated` | Integer | Failed validations |
| `file_path` | String | Associated file |
| `episodic_episode_id` | Integer | Link to episode |
| `procedure_id` | Integer | Link to procedure |

**Table**: `learning_patterns`

| Column | Type | Purpose |
|--------|------|---------|
| `pattern_name` | String | Name of the pattern |
| `pattern_type` | String | Type (e.g., "success", "failure") |
| `preconditions` | Text (JSON) | When this pattern applies |
| `actions` | Text (JSON) | What to do |
| `expected_outcomes` | Text (JSON) | What should happen |
| `trust_score` | Float | Reliability |
| `success_rate` | Float | Historical success rate |
| `sample_size` | Integer | Number of examples |

**Class**: `LearningMemoryManager`
- `ingest_learning_data(learning_type, learning_data, source, user_id, genesis_key_id)` — ingest new example
- `get_training_data(min_trust_score=0.7, example_type, limit=100)` — get high-trust examples for training
- `update_trust_on_usage(example_id, outcome_success)` — update trust after use
- `decay_trust_scores()` — time-based trust decay

**Class**: `TrustScorer`
- `calculate_trust_score(source, outcome_quality, consistency_score, validation_history, age_days)` — composite trust
- `update_trust_on_validation(example, validation_result)` — adjust on validate/invalidate

---

### 1.4 Procedural Memory (`cognitive/procedural_memory.py`)

**What**: Learned step-by-step procedures. "We've done this before — here's the exact sequence."

**Table**: `procedures`

| Column | Type | Purpose |
|--------|------|---------|
| `name` | String | Procedure name |
| `goal` | Text | What this achieves |
| `procedure_type` | String | Type (general, domain-specific) |
| `steps` | Text (JSON) | Ordered steps |
| `preconditions` | Text (JSON) | When this applies |
| `trust_score` | Float | Reliability |
| `success_rate` | Float | Historical success rate |
| `usage_count` | Integer | Times used |
| `success_count` | Integer | Times succeeded |
| `supporting_examples` | Text (JSON) | Evidence |
| `embedding` | Text (JSON) | Vector for semantic search |

**Class**: `ProceduralRepository`
- `create_procedure(goal, action_sequence, preconditions, supporting_examples)` — create procedure
- `find_procedure(goal, context)` — semantic or text search for matching procedure
- `suggest_procedure(goal, context, min_success_rate=0.6)` — suggest best procedure
- `update_success_rate(procedure_id, succeeded)` — update after use
- `classify_query(query)` — determine query type

---

### 1.5 Memory Mesh (`cognitive/memory_mesh_integration.py`)

**What**: The integration layer that connects Learning, Episodic, and Procedural memory. When an experience is ingested, it flows to the right memory type based on trust thresholds.

**Class**: `MemoryMeshIntegration`
- `ingest_learning_experience(experience_type, context, action_taken, outcome, expected_outcome, source, user_id, genesis_key_id)` — main ingestion point

**Flow**:
```
ingest_learning_experience()
    │
    ├─→ LearningMemoryManager.ingest_learning_data()
    │       → Creates LearningExample (always)
    │
    ├─→ if trust ≥ 0.7:
    │       EpisodicBuffer.record_episode()
    │       → Creates Episode
    │
    └─→ if trust ≥ 0.8 AND type in ('success', 'pattern'):
            ProceduralRepository.create_procedure()
            → Creates Procedure
```

- `feedback_loop_update(learning_example_id, actual_outcome, success)` — update trust from real outcomes
- `get_training_dataset(experience_type, min_trust_score, max_examples)` — export for training
- `get_memory_mesh_stats()` — stats across all three memory types

**Supporting modules**:
- `MemoryMeshCache` — caching layer for frequent queries
- `MemoryMeshMetrics` — performance tracking (latency, throughput, cache hit rates)
- `MemoryMeshSnapshot` — immutable snapshots for versioning and comparison
- `MemoryMeshLearner` — identifies knowledge gaps, high-value topics, failure patterns
- `GenesisMemoryChain` — builds learning narratives from Genesis Key chains

---

### 1.6 Unified Memory (`core/memory/unified_memory.py` and `cognitive/unified_memory.py`)

Two implementations:

**Facade** (`core/memory/unified_memory.py`):
Wraps LearningMemoryManager, EpisodicBuffer, MemoryMeshIntegration, and MemoryMeshLearner into a single API:
- `ingest_experience()` → routes to mesh
- `recall_similar()` → queries episodic
- `get_learning_suggestions()` → queries learner
- `get_training_data()` → queries learning memory

**Raw SQL** (`cognitive/unified_memory.py`):
Direct SQLite queries with Magma bridge and Flash cache integration:
- `store_episode()`, `store_learning()`, `store_procedure()`
- `recall_episodes()`, `recall_learnings()`, `recall_procedures()`
- `search_all()` — cross-memory search

### 1.7 Memory Reconciler (`cognitive/memory_reconciler.py`)

**What**: Keeps FlashCache, Ghost Memory, and Unified Memory consistent.

**Class**: `MemoryReconciler`
- `atomic_get(key)` — read from all memory tiers
- `atomic_set(key, value)` — write to all tiers
- `atomic_evict(key)` — remove from all tiers
- `reconcile()` — sync all tiers

---

### Memory Hierarchy Summary

```
Volatile                                              Permanent
┌──────────┐   ┌──────────┐   ┌───────────┐   ┌──────────┐   ┌──────────────┐
│  Ghost   │──→│ Episodic │──→│ Learning  │──→│Procedural│──→│ Knowledge    │
│  Memory  │   │  Memory  │   │  Memory   │   │  Memory  │   │  Base (RAG)  │
│          │   │          │   │           │   │          │   │              │
│ Per-task │   │ Episodes │   │ Examples  │   │ Step-by- │   │ Files, docs  │
│ scratch  │   │ trust≥0.7│   │ all trust │   │ step     │   │ vectors      │
│ buffer   │   │          │   │           │   │ trust≥0.8│   │              │
└──────────┘   └──────────┘   └───────────┘   └──────────┘   └──────────────┘
     │              │               │               │               │
     └──────────────┴───────────────┴───────────────┘               │
                    Memory Mesh (integration)                       │
                           │                                        │
                    ┌──────┴──────┐                                 │
                    │   Unified   │                                 │
                    │   Memory    │                                 │
                    └─────────────┘                                 │
                           │                                        │
                    ┌──────┴──────┐                                 │
                    │  Reconciler │──────────────────────────────────┘
                    │  (sync all) │
                    └─────────────┘
```

---

## Part 2: MAGMA System

MAGMA (Memory-Augmented Graph-based Memory Architecture) is the graph-based knowledge layer.

### 2.1 Four Relation Graphs

All graphs use the same base structure (`BaseRelationGraph`):

**Nodes** (`GraphNode`): `id`, `node_type`, `content`, `embedding`, `metadata`, `genesis_key_id`, `trust_score`

**Edges** (`GraphEdge`): `id`, `source_id`, `target_id`, `relation_type`, `weight`, `confidence`, `metadata`, `genesis_key_id`

| Graph | Purpose | Relation Types | Key Methods |
|-------|---------|---------------|-------------|
| **SemanticGraph** | Concept relationships (similarity, hierarchy, part-of) | `SIMILAR_TO`, `IS_A`, `PART_OF`, `RELATED_TO`, `SYNONYM`, `ANTONYM`, `DEFINED_BY` | `add_concept()`, `find_related_concepts()`, auto-links by cosine similarity |
| **TemporalGraph** | Event sequences (before, after, during, caused) | `BEFORE`, `AFTER`, `DURING`, `CAUSED`, `FOLLOWED_BY`, `CONCURRENT` | `add_event()`, `get_events_in_range()`, `get_event_sequence()` |
| **CausalGraph** | Cause-effect chains | `CAUSES`, `ENABLES`, `PREVENTS`, `CORRELATES`, `TRIGGERS`, `INHIBITS` | `add_causal_link()`, `get_causes()`, `get_effects()`, `trace_causal_chain()` |
| **EntityGraph** | Entity co-occurrence and relationships | `CO_OCCURS`, `INTERACTS`, `DEPENDS_ON`, `CONTAINS`, `CREATED_BY`, `MODIFIED_BY` | `add_entity()`, `link_entities()`, `record_co_occurrence()`, `get_entity_cluster()` |

**`MagmaRelationGraphs`**: Container for all 4 graphs with `cross_graph_search()` for multi-graph queries.

### 2.2 Query Pipeline

```
Query Text
    │
    ▼
IntentAwareRouter
    ├── IntentClassifier: classify query type (FACTUAL, EXPLANATION, CAUSAL, HOW_TO, etc.)
    ├── AnchorIdentifier: extract key entities/concepts from query
    ├── GraphSelector: choose which graphs to search
    └── RetrievalPolicySelector: choose traversal strategy
    │
    ▼
AdaptiveTopologicalRetriever
    ├── GraphTraverser: BFS, DFS, best-first, bidirectional
    └── Traversal policies: BFS, DFS, BEST_FIRST, BIDIRECTIONAL,
        ADAPTIVE, SEMANTIC_SPREAD, CAUSAL_CHAIN, TEMPORAL_WINDOW
    │
    ▼
MagmaFusion (result merging)
    ├── RRF (Reciprocal Rank Fusion)
    ├── WeightedRRF
    ├── CombSUM, CombMNZ
    ├── Borda
    └── Interleaving
    │
    ▼
ContextSynthesizer → formatted context for LLM
```

### 2.3 Ingestion Pipeline

```
Content
    │
    ▼
SynapticIngestionPipeline
    ├── EventSegmenter: split into sentences/paragraphs/concepts/entities
    ├── SemanticLinker → SemanticGraph (cosine similarity linking)
    ├── TemporalLinker → TemporalGraph (timestamp-based linking)
    ├── EntityLinker → EntityGraph (entity co-occurrence)
    └── CausalLinker → CausalGraph (causal pattern detection)
    │
    ▼
AsyncOperationQueue (priority-based background processing)
    │
    ▼
ConsolidationWorker (periodic cleanup: prune weak edges, update importance)
```

### 2.4 Causal Inference

`CausalPatternDetector`: Regex-based detection of causal language ("because", "therefore", "caused by", etc.)

`LLMCausalInferencer`: When patterns alone aren't enough, uses LLM to infer causal relationships. Stores verified claims in `CausalGraph`. Can trace causal chains and produce explanations.

### 2.5 Layer Integrations

MAGMA integrates with the 4-layer diagnostic machine:

| Layer | Integration | Purpose |
|-------|------------|---------|
| Layer 1 (Sensors) | `MagmaMessageBusConnector` | Subscribe to events, ingest into graphs |
| Layer 2 (Interpreters) | `InterpreterPatternMemory` | Store and recall diagnostic patterns |
| Layer 3 (Judgement) | `JudgementDecisionMemory` | Store decisions, find precedents |
| Layer 4 (Action Router) | `ActionRouterMemory` | Store procedures, find best healing action |

Plus: `MagmaGenesisIntegration` (Genesis Key tracking), `MagmaTrustIntegration` (trust-based filtering), `MagmaGovernanceIntegration` (governance checks on queries/ingestion).

### 2.6 Unified Entry Point

`GraceMagmaSystem` (`cognitive/magma/grace_magma_system.py`):

```python
from cognitive.magma.grace_magma_system import get_grace_magma

magma = get_grace_magma()
magma.ingest("The retriever failed because Qdrant was down", content_type="log")
context = magma.get_context("Why did retrieval fail?")
explanation = magma.why("What caused the Qdrant outage?")
```

Key methods:
- `ingest(content, content_type, timestamp, genesis_key_id)` — ingest into all graphs
- `query(query_text, max_results)` — intent-aware multi-graph search
- `get_context(query_text, max_length)` — synthesized context for LLM
- `why(question)` — causal chain explanation
- `store_pattern()`, `find_similar_patterns()` — pattern memory
- `store_decision()`, `find_precedents()` — decision memory
- `store_procedure()`, `find_procedures()`, `get_best_procedure()` — procedure memory

---

## Part 3: Other Graph Systems

### 3.1 Topic Relationship Graph (`cognitive/predictive_context_loader.py`)

**Purpose**: Predict related topics for context prefetching.

**Class**: `TopicRelationshipGraph`
- `get_related_topics(topic, depth=2)` — find related topics
- `learn_relationship(topic1, topic2)` — learn new relationship from usage

Uses static relationships (Python→debugging, FastAPI→REST, etc.) plus dynamically learned ones.

### 3.2 Document Relationship Manager (`librarian/relationship_manager.py`)

**Purpose**: Detect relationships between documents (similar content, version chains, citations).

**Class**: `RelationshipManager`
- `detect_relationships()` — auto-detect similarity, versions, citations
- `create_relationship(source_id, target_id, type, confidence)` — manual relationship
- `get_document_relationships(document_id)` — get all relationships for a document
- `get_dependency_graph()` — full document dependency graph

**Table**: `document_relationships` (source_document_id, target_document_id, relationship_type, confidence, strength)

### 3.3 MCP Knowledge Graph (`mcp_repos/mcp-servers/src/memory/index.ts`)

**Purpose**: Persistent knowledge graph for MCP memory server.

**Class**: `KnowledgeGraphManager`
- `createEntities()`, `createRelations()`, `addObservations()`
- `readGraph()`, `searchNodes()`, `openNodes()`

Stored as JSON file. Entities have types and observations. Relations link entities.

### 3.4 Component Registry Topology (`core/registry.py`)

**Purpose**: Topological sort of components for startup ordering based on dependency graph.

`_dependency_order()` — returns components in dependency-safe order.

---

## Part 4: Complete Database Schema

### 42 Tables Across 8 Model Modules

#### Core Data (database_models.py) — 16 tables

| Table | Purpose |
|-------|---------|
| `users` | User accounts |
| `conversations` | Chat conversations (legacy) |
| `messages` | Conversation messages (legacy) |
| `embeddings` | Stored embeddings |
| `chats` | Active chats |
| `chat_history` | Chat messages |
| `documents` | Ingested documents |
| `document_chunks` | Document chunks with embeddings |
| `governance_rules` | Governance rules |
| `governance_documents` | Governance document files |
| `governance_decisions` | Governance decisions and approvals |
| `learning_examples` | Learning memory examples |
| `learning_patterns` | Extracted learning patterns |
| `episodes` | Episodic memory |
| `procedures` | Procedural memory |
| `llm_usage_stats` | LLM call tracking |

#### Genesis Keys (genesis_key_models.py) — 4 tables

| Table | Purpose |
|-------|---------|
| `genesis_key` | Provenance records (5W1H) |
| `fix_suggestion` | Fix proposals for errors |
| `genesis_key_archive` | Daily archives |
| `user_profile` | User tracking profiles |

#### Notion/Task Management (notion_models.py) — 4 tables

| Table | Purpose |
|-------|---------|
| `notion_profile` | Team member profiles |
| `notion_task` | Tasks with full lifecycle |
| `task_history` | Task change history |
| `task_template` | Reusable task templates |

#### Librarian (librarian_models.py) — 6 tables

| Table | Purpose |
|-------|---------|
| `librarian_tags` | Hierarchical tags |
| `document_tags` | Tag assignments to documents |
| `document_relationships` | Document-to-document relationships |
| `librarian_rules` | Auto-categorization rules |
| `librarian_actions` | Actions taken on documents |
| `librarian_audit` | Audit trail for actions |

#### Telemetry (telemetry_models.py) — 5 tables

| Table | Purpose |
|-------|---------|
| `operation_log` | Operation traces |
| `performance_baseline` | Performance baselines |
| `drift_alert` | Performance drift alerts |
| `operation_replay` | Operation replay records |
| `system_state` | System health snapshots |

#### Query Intelligence (query_intelligence_models.py) — 3 tables

| Table | Purpose |
|-------|---------|
| `query_handling_log` | Query processing log |
| `knowledge_gaps` | Detected knowledge gaps |
| `context_submissions` | User-submitted context |

#### Scraping (scraping/models.py) — 2 tables

| Table | Purpose |
|-------|---------|
| `scraping_jobs` | Web scraping jobs |
| `scraped_pages` | Scraped page content |

#### File Intelligence (migration-only) — 4 tables

| Table | Purpose |
|-------|---------|
| `file_intelligence` | AI analysis of files |
| `file_relationships` | File-to-file relationships |
| `processing_strategies` | File processing strategies |
| `file_health_checks` | File system health checks |

---

## Part 5: How Everything Connects

### Data Flow: Experience → Memory → Knowledge → Action

```
1. EXPERIENCE OCCURS
   (user query, AI response, code fix, error, healing action)
        │
2. GENESIS KEY CREATED (track everything)
        │
3. MEMORY MESH INGESTION
        │
   ┌────┴────────────────────────────────────────────────────┐
   │                                                          │
   ▼                                                          ▼
Learning Memory                              MAGMA Graphs
(LearningExample)                    ┌──────────────────────────┐
   │                                 │ SemanticGraph (concepts)  │
   │ trust ≥ 0.7                     │ TemporalGraph (events)    │
   ▼                                 │ CausalGraph (cause-effect)│
Episodic Memory                      │ EntityGraph (entities)    │
(Episode)                            └──────────────────────────┘
   │
   │ trust ≥ 0.8
   ▼
Procedural Memory
(Procedure)

4. RETRIEVAL (when information needed)
        │
   ┌────┴─────────────────────┐
   │                           │
   ▼                           ▼
RAG (Qdrant vectors)     MAGMA (graph traversal)
   │                           │
   └───────────┬───────────────┘
               ▼
         Context for LLM

5. DETERMINISTIC VALIDATION
   (memory mesh stats, schema checks, trust verification)

6. SELF-HEALING
   Error → recall similar episode → use procedure → fix → update trust
```

### Memory ↔ Genesis Key Integration

Every memory record links back to Genesis Keys:
- `LearningExample.genesis_key_id` — which key produced this learning
- `Episode.genesis_key_id` — which key this episode relates to
- `GraphNode.genesis_key_id` — which key created this graph node
- `GraphEdge.genesis_key_id` — which key created this edge

This creates full traceability: from any memory record, you can trace back to the exact action that created it.

### Memory ↔ Diagnostic Machine

The diagnostic machine uses memory for intelligent healing:
- **Layer 2 (Interpreters)**: `InterpreterPatternMemory` stores and recalls diagnostic patterns via MAGMA
- **Layer 3 (Judgement)**: `JudgementDecisionMemory` stores past decisions and finds precedents
- **Layer 4 (Action Router)**: `ActionRouterMemory` stores healing procedures and finds the best one for a given problem

### Memory ↔ Autonomous Loop

The Ouroboros loop uses episodic memory to avoid repeating mistakes:
- `_recall_similar_episode(problem_text)` — checks if this problem was seen before
- If found, uses the past action and outcome to guide the current decision
- Records every cycle outcome as a new episode for future reference

---

## Part 6: Known Schema Issues

| Issue | Location | Impact |
|-------|----------|--------|
| Dual model definitions for memory tables | `database_models.py` vs `cognitive/*.py` | Both use `extend_existing=True` but have different columns; runtime behavior depends on import order |
| `MemoryMeshConnector` field name mismatches | `layer1/components/memory_mesh_connector.py` | Uses `ex.experience_type` (should be `example_type`), `proc.times_used` (should be `usage_count`) |
| Memory mesh learner field names | `cognitive/memory_mesh_learner.py` | Uses `LearningExample.metadata` (should be `example_metadata`) |
| `CognitiveMesh` procedure field | `core/cognitive_mesh.py` | Uses `proc.pattern_name` (should be `proc.name`) |
| MAGMA graphs are in-memory only | `cognitive/magma/relation_graphs.py` | All graph data stored in Python dicts — lost on restart unless snapshotted |
| No migration for LLM usage stats | `database_models.py` | `llm_usage_stats` table not in main migration |
| FK reference inconsistency | `file_health_checks` | References `genesis_key.id` (auto-increment); `fix_suggestion` references `genesis_key.key_id` (UUID) |
| Index name collision | `migration_memory_mesh_indexes.py` | References table `genesis_keys` (plural) but model defines `genesis_key` (singular) |
