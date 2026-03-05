# GRACE 3.1 — Developer Handover Document

**Version:** 3.1.0  
**Date:** March 2026  
**Purpose:** Everything a dev team needs to understand Grace end-to-end.

---

## Table of Contents

1. [What is Grace?](#1-what-is-grace)
2. [Architecture Overview](#2-architecture-overview)
3. [Repository Structure](#3-repository-structure)
4. [Backend Deep Dive](#4-backend-deep-dive)
5. [Brain API — The Single Entry Point](#5-brain-api--the-single-entry-point)
6. [Database & Models](#6-database--models)
7. [Cognitive Engine — How Grace Thinks](#7-cognitive-engine--how-grace-thinks)
8. [Memory Systems](#8-memory-systems)
9. [Genesis Keys — Full Provenance](#9-genesis-keys--full-provenance)
10. [Internal VCS & CI/CD — No GitHub Dependency](#10-internal-vcs--cicd--no-github-dependency)
11. [Multi-Tenant Workspaces](#11-multi-tenant-workspaces)
12. [RAG & Retrieval Pipeline](#12-rag--retrieval-pipeline)
13. [Layer 1 Message Bus](#13-layer-1-message-bus)
14. [Grace OS — The 9-Layer Pipeline](#14-grace-os--the-9-layer-pipeline)
15. [MCP Servers & Tool Orchestration](#15-mcp-servers--tool-orchestration)
16. [Frontend](#16-frontend)
17. [VSCode Extension](#17-vscode-extension)
18. [Deployment](#18-deployment)
19. [Configuration Reference](#19-configuration-reference)
20. [How to Run Locally](#20-how-to-run-locally)
21. [Key Patterns & Conventions](#21-key-patterns--conventions)
22. [Authentication & Authorization](#22-authentication--authorization)
23. [Error Response Contract](#23-error-response-contract)
24. [Data Flow — Complete Chat Request](#24-data-flow--complete-chat-request)
25. [Environment Setup — Gotchas](#25-environment-setup--gotchas)
26. [Multi-Tenancy Isolation Boundaries](#26-multi-tenancy-isolation-boundaries)
27. [Concurrency Model](#27-concurrency-model)
28. [Migration Strategy](#28-migration-strategy)
29. [LLM Provider Failover](#29-llm-provider-failover)
30. [Qdrant Collection Management](#30-qdrant-collection-management)
31. [WebSocket Protocol (Voice API)](#31-websocket-protocol-voice-api)
32. [Logging & Observability](#32-logging--observability)
33. [Autonomous Loop (Ouroboros)](#33-autonomous-loop-ouroboros)
34. [Testing Strategy](#34-testing-strategy)
35. [Document Ingestion](#35-document-ingestion)
36. [LIGHTWEIGHT_MODE](#36-lightweight_mode)
37. [Backup & Disaster Recovery](#37-backup--disaster-recovery)
38. [Secret Management](#38-secret-management)
39. [Frontend State Management](#39-frontend-state-management)
40. [API Versioning](#40-api-versioning)
41. [State Machine Diagrams](#41-state-machine-diagrams)

---

## 1. What is Grace?

Grace (Genesis-driven RAG Autonomous Cognitive Engine) is a self-evolving AI platform. She is not a chatbot — she is the intelligence backbone that can power multiple independent AI systems.

**Core capabilities:**
- Multi-tier RAG retrieval with reranking
- Autonomous learning, healing, and self-improvement
- Multi-model consensus (Opus, Kimi, Qwen, Ollama models)
- Internal version control and CI/CD (no GitHub dependency)
- Multi-tenant workspaces (each AI gets its own isolated container)
- Full provenance tracking via Genesis Keys (every action is recorded)
- Graph-based contextual memory (semantic, temporal, causal, entity)
- User thinking pattern learning (adapts to each user's style)
- 10-brain domain architecture with 235+ actions
- 9-layer cognitive pipeline (L1 Runtime → L9 Deployment)

**The key mental model:**  
Grace is the brain. She can run behind Tommy AI, Rebecca AI, or any other AI system. Each gets its own workspace (isolated knowledge base, files, pipelines). Grace manages them all — fixing, healing, coding, learning for every tenant.

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CLIENTS                                       │
│   React Frontend    │    VSCode Extension    │    API Consumers       │
└─────────┬───────────┴──────────┬─────────────┴──────────┬───────────┘
          │                      │                        │
          ▼                      ▼                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend (port 8000)                       │
│                                                                      │
│  ┌─── Brain API ───────────────────────────────────────────────┐    │
│  │  POST /brain/{domain} { action, payload }                    │    │
│  │  10 domains × 235 actions                                    │    │
│  │  chat│files│govern│ai│system│data│tasks│code│deterministic│ws │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                              │                                       │
│  ┌───────────────────────────┼───────────────────────────────────┐   │
│  │               Core Services Layer                              │   │
│  │  chat_service │ files_service │ govern_service │ code_service  │   │
│  │  workspace_service │ system_service │ tasks_service            │   │
│  └───────────────────────────┼───────────────────────────────────┘   │
│                              │                                       │
│  ┌───────────────────────────┼───────────────────────────────────┐   │
│  │              Cognitive Layer                                    │   │
│  │  OODA Engine │ Consensus │ MAGMA Graphs │ Memory Mesh          │   │
│  │  Learning │ Mirror │ User Patterns │ Sandbox │ Trust Engine    │   │
│  └───────────────────────────┼───────────────────────────────────┘   │
│                              │                                       │
│  ┌───────────────────────────┼───────────────────────────────────┐   │
│  │              Infrastructure Layer                               │   │
│  │  SQLAlchemy (SQLite/PostgreSQL) │ Qdrant (vectors)             │   │
│  │  Layer 1 Message Bus │ Genesis Keys │ Internal VCS/CI          │   │
│  │  MCP Orchestrator │ Execution Bridge                           │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
          │                      │                        │
          ▼                      ▼                        ▼
┌──────────────┐    ┌──────────────────┐    ┌──────────────────────┐
│   Qdrant     │    │  Ollama (LLMs)   │    │  MCP Servers         │
│   (vectors)  │    │  mistral:7b etc  │    │  file/terminal/git   │
└──────────────┘    └──────────────────┘    └──────────────────────┘
```

---

## 3. Repository Structure

```
grace-3.1/
├── backend/                    # FastAPI Python backend (core of Grace)
│   ├── app.py                  # Main application entry point (2000 lines)
│   ├── settings.py             # All environment configuration
│   ├── requirements.txt        # Python dependencies
│   ├── Dockerfile              # Multi-stage Docker build
│   │
│   ├── api/                    # API layer (routers + brain API)
│   │   ├── brain_api_v2.py     # THE main entry point — 10 brains, 235 actions
│   │   ├── core/               # brain_controller.py (v2 routing)
│   │   ├── workspace_api.py    # Internal VCS + CI/CD REST API
│   │   ├── health.py           # Health checks
│   │   ├── auth.py             # Authentication
│   │   ├── retrieve.py         # RAG retrieval endpoints
│   │   ├── voice_api.py        # WebSocket voice
│   │   ├── _genesis_tracker.py # Fire-and-forget Genesis tracking
│   │   └── ...                 # ~20 more routers
│   │
│   ├── core/                   # Core service layer
│   │   ├── services/           # Domain services (chat, files, code, workspace, etc.)
│   │   ├── awareness/          # Self-model, time sense
│   │   ├── resilience.py       # Circuit breakers, error boundaries
│   │   └── deterministic_*.py  # Deterministic validation system
│   │
│   ├── cognitive/              # Grace's brain
│   │   ├── cognitive_engine.py # OODA decision loop
│   │   ├── consensus_engine.py # Multi-model consensus (4 layers)
│   │   ├── unified_memory.py   # Single interface for all memory
│   │   ├── mirror_self_modeling.py  # Grace observes herself
│   │   ├── user_pattern_learner.py  # Learns user thinking patterns
│   │   ├── trust_engine.py     # Trust scoring
│   │   ├── magma/              # Graph memory (semantic, temporal, causal, entity)
│   │   │   ├── relation_graphs.py      # 4 graph types + persistence
│   │   │   ├── grace_magma_system.py   # Unified entry point
│   │   │   ├── graph_persistence.py    # DB-backed graph storage
│   │   │   ├── topological_retrieval.py # Graph traversal search
│   │   │   └── rrf_fusion.py           # Multi-source ranking fusion
│   │   ├── learning_memory.py          # Learning examples + patterns
│   │   ├── episodic_memory.py          # Past experiences
│   │   ├── procedural_memory.py        # Learned skills
│   │   ├── reverse_knn.py             # Knowledge gap detection
│   │   ├── sandbox_engine.py          # Experiment sandbox
│   │   └── ...                        # ~30 more modules
│   │
│   ├── genesis/                # Genesis tracking + internal platform
│   │   ├── genesis_key_service.py     # Core key creation service
│   │   ├── internal_vcs.py            # Internal version control (replaces Git)
│   │   ├── internal_pipeline.py       # Internal CI/CD (replaces GitHub Actions)
│   │   ├── symbiotic_version_control.py # Genesis + VCS unified
│   │   ├── cicd.py                    # Async pipeline engine
│   │   ├── file_watcher.py            # Filesystem change detection
│   │   └── ...                        # archival, KB integration, etc.
│   │
│   ├── models/                 # SQLAlchemy ORM models (38 models)
│   │   ├── database_models.py         # Core: User, Chat, Document, etc.
│   │   ├── genesis_key_models.py      # GenesisKey, FixSuggestion, etc.
│   │   ├── workspace_models.py        # Workspace, Branch, FileVersion, PipelineRun
│   │   ├── memory_graph_models.py     # GraphNode/Edge, UserThinkingPattern
│   │   ├── librarian_models.py        # Tags, relationships, rules
│   │   ├── telemetry_models.py        # Operation tracking, drift detection
│   │   └── query_intelligence_models.py # Query handling, knowledge gaps
│   │
│   ├── database/               # Database infrastructure
│   │   ├── config.py           # DatabaseConfig from env
│   │   ├── connection.py       # Engine creation (SQLite WAL, PostgreSQL pools)
│   │   ├── session.py          # Session factory, get_session, session_scope
│   │   ├── base.py             # Base, BaseModel (id, created_at, updated_at)
│   │   └── migrations/         # Table creation scripts
│   │
│   ├── retrieval/              # RAG retrieval pipeline
│   │   ├── retriever.py        # DocumentRetriever (retrieve, hybrid, retrieve_and_rank)
│   │   ├── reranker.py         # Cross-encoder reranking
│   │   ├── query_intelligence.py # Multi-tier query handling
│   │   └── cognitive_retriever.py # OODA-based retrieval
│   │
│   ├── embedding/              # Embedding engine
│   │   └── embedder.py         # SentenceTransformer embeddings
│   │
│   ├── vector_db/              # Qdrant wrapper
│   │   └── client.py           # QdrantVectorDB (search, upsert, scroll)
│   │
│   ├── layer1/                 # Layer 1 message bus
│   │   ├── message_bus.py      # Async pub/sub (11 components, 6 message types)
│   │   ├── initialize.py       # Boot-time component registration
│   │   └── components/         # Connectors (genesis, rag, memory, etc.)
│   │
│   ├── grace_os/               # Grace OS kernel + 9 layers
│   │   ├── kernel/             # MessageBus, SessionManager, TrustScorekeeper
│   │   └── layers/             # L1_Runtime → L9_Deployment
│   │
│   ├── grace_mcp/              # MCP orchestrator
│   │   ├── orchestrator.py     # Multi-turn LLM + tool calling
│   │   ├── client.py           # MCP stdio client
│   │   └── builtin_tools.py    # rag_search, web_search, web_fetch
│   │
│   ├── execution/              # Code execution bridge
│   │   └── bridge.py           # File ops, Python/Bash exec, Git, tests
│   │
│   ├── llm_orchestrator/       # LLM provider management
│   │   ├── factory.py          # get_llm_client() — Ollama/OpenAI/Kimi/Opus
│   │   └── ...
│   │
│   ├── security/               # Auth, governance, middleware
│   ├── diagnostic_machine/     # 4-layer self-healing
│   ├── ml_intelligence/        # Neural trust, meta-learning, active learning
│   ├── librarian/              # Document relationship management
│   ├── ingestion/              # Document ingestion pipeline
│   ├── scraping/               # Web scraping service
│   ├── search/                 # SerpAPI integration
│   └── mcp_repos/              # Vendored MCP servers
│       ├── DesktopCommanderMCP/    # File I/O, terminal, SSH, search
│       └── mcp-servers/            # memory, filesystem, sequentialthinking
│
├── frontend/                   # React 19 + MUI 7 + Vite
│   ├── src/
│   │   ├── App.jsx             # Main app with tab layout
│   │   ├── components/         # 90+ components (15+ tabs)
│   │   ├── config/             # brain-client.js (API client)
│   │   └── store/              # Zustand state
│   ├── package.json
│   ├── vite.config.js          # Dev server + backend proxy
│   └── Dockerfile
│
├── grace-os-vscode/            # VSCode extension
│   ├── src/                    # 39 TypeScript files
│   ├── package.json            # 24 commands, 9 views, keybindings
│   └── tsconfig.json
│
├── docs/                       # 229+ documentation files
├── k8s/                        # Kubernetes manifests
├── pipelines/                  # CI/CD pipeline definitions (YAML)
├── monitoring/                 # Grafana dashboards
├── tests/                      # Integration tests
├── docker-compose.yml          # Full stack: backend + frontend + qdrant + ollama
└── .github/workflows/          # GitHub Actions CI/CD
```

---

## 4. Backend Deep Dive

### Startup Flow

When the backend starts (`uvicorn app:app`), the `lifespan()` function runs:

1. **Database**: `DatabaseConnection.initialize()` → `initialize_session_factory()` → `create_tables()`
2. **Qdrant**: `get_qdrant_client()` connects to vector DB
3. **Embedding**: Loads SentenceTransformer model (if not `SKIP_EMBEDDING_LOAD`)
4. **Auto-ingestion**: Scans knowledge base for new documents
5. **Diagnostic engine**: Starts 4-layer self-healing system
6. **Layer 1 bus**: Initializes async message bus + connectors
7. **Autonomous loop**: Starts Ouroboros self-improvement cycle
8. **File watcher**: Monitors workspace for file changes

### Middleware Stack (outer → inner)

1. `SecurityHeadersMiddleware` — security headers
2. `RateLimitMiddleware` — rate limiting
3. `RequestValidationMiddleware` — input validation
4. `CORSMiddleware` — cross-origin requests
5. `GenesisKeyMiddleware` — automatic provenance tracking

### Async Pattern

Grace uses **sync SQLAlchemy** with `run_in_executor` for async contexts. This is the established pattern throughout the codebase:

```python
async def some_async_method(self, ...):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, self._sync_implementation, ...)

def _sync_implementation(self, ...):
    with session_scope() as session:
        # sync DB work
```

FastAPI endpoints are `async def` but call sync DB code through FastAPI's thread pool.

---

## 5. Brain API — The Single Entry Point

**File:** `backend/api/brain_api_v2.py`

The Brain API is the **only entry point** for business logic. All other routers are infrastructure (health, auth, voice WebSocket).

### Routing Pattern

```
POST /brain/{domain} { "action": "...", "payload": {...} }
```

The `_call()` function routes to the appropriate handler, tracks via Genesis Keys, and returns a `BrainResponse`:

```json
{
    "brain": "code",
    "action": "projects",
    "ok": true,
    "data": { ... },
    "latency_ms": 12.3,
    "genesis_key_id": "gk-abc123"
}
```

### 10 Brain Domains — 235 Actions

| Domain | Actions | Purpose |
|--------|---------|---------|
| **chat** | 8 | Conversations, prompts, consensus, world model |
| **files** | 9 | File tree, browse, read, write, search, docs |
| **govern** | 12 | Governance, approvals, persona, trust scores |
| **ai** | 28 | Models, consensus, code generation, oracle, training, OODA |
| **system** | 115 | Health, runtime, monitoring, autonomous loop, containers, users, compliance |
| **data** | 7 | Whitelist sources, flash cache |
| **tasks** | 8 | Scheduling, time sense, planner |
| **code** | 15 | Projects, tree, read/write, code generation |
| **deterministic** | 20 | Scanning, lifecycle, event bus, coding contracts |
| **workspace** | 13 | Internal VCS, CI/CD, multi-tenant workspaces |

### Cross-Brain Calls

Any brain can call another:

```python
from api.brain_api_v2 import call_brain
result = call_brain("workspace", "snapshot", {"workspace_id": "tommy-ai", ...})
```

### Smart Routing

```
POST /brain/ask { "query": "what is the system health?" }
```

Grace auto-routes to the optimal brain + action.

### Orchestration

```
POST /brain/orchestrate { "steps": [
    { "brain": "code", "action": "read", "payload": { "path": "main.py" } },
    { "brain": "ai", "action": "generate", "payload": { "prompt": "refactor this" } }
] }
```

---

## 6. Database & Models

### Database Support

| DB | Connection | Pool | Notes |
|----|-----------|------|-------|
| **SQLite** (default) | WAL mode, `busy_timeout=30s` | `StaticPool` | Best for development |
| **PostgreSQL** | Standard | `QueuePool(5, max_overflow=10)` | Production recommended |
| **MySQL/MariaDB** | Standard | `QueuePool` | Supported |

### Session Management

```python
# FastAPI dependency injection
session = Depends(get_session)

# Context manager (services)
with session_scope() as session:
    session.query(Model).filter_by(...).all()

# Batch operations
with batch_session_scope() as session:
    session.bulk_insert_mappings(...)
```

### 38 ORM Models

**Core** (`database_models.py`): User, Conversation, Message, Embedding, Chat, ChatHistory, Document, DocumentChunk, GovernanceRule, GovernanceDocument, GovernanceDecision, LearningExample, LearningPattern, Episode, Procedure, LLMUsageStats

**Genesis** (`genesis_key_models.py`): GenesisKey, FixSuggestion, GenesisKeyArchive, UserProfile

**Workspace** (`workspace_models.py`): Workspace, Branch, FileVersion, PipelineRun

**Memory** (`memory_graph_models.py`): GraphNodeRecord, GraphEdgeRecord, UserThinkingPattern, UserInteractionLog

**Librarian** (`librarian_models.py`): LibrarianTag, DocumentTag, DocumentRelationship, LibrarianRule, LibrarianAction, LibrarianAudit

**Telemetry** (`telemetry_models.py`): OperationLog, PerformanceBaseline, DriftAlert, OperationReplay, SystemState

**Query Intelligence** (`query_intelligence_models.py`): QueryHandlingLog, KnowledgeGap, ContextSubmission

---

## 7. Cognitive Engine — How Grace Thinks

### OODA Decision Loop

Every significant decision Grace makes follows OODA:

```
OBSERVE → What happened? (gather data, context)
ORIENT  → What does it mean? (analyze, pattern match)
DECIDE  → What should we do? (evaluate options, trust score)
ACT     → Execute the decision
```

**File:** `cognitive/cognitive_engine.py`

The engine enforces 12 invariants: ambiguity detection, reversibility checks, determinism verification, blast radius assessment, etc.

### Multi-Model Consensus (4 Layers)

When Grace needs high confidence, she runs consensus across multiple LLMs:

| Layer | Name | What Happens |
|-------|------|-------------|
| 1 | Independent Deliberation | Each model (Opus, Kimi, Qwen, Ollama) answers independently |
| 2 | Consensus Formation | Responses compared; agreements emphasized, disagreements flagged |
| 3 | Alignment | Consensus aligned to Grace's world model and user context |
| 4 | Verification | Trust scoring, hallucination guard, contradiction checks |

**File:** `cognitive/consensus_engine.py`

### Trust Engine

Every piece of information has a trust score (0.0–1.0):

| Score | Level | Source Examples |
|-------|-------|----------------|
| 0.9+ | Very High | Verified, multi-source confirmed |
| 0.7–0.9 | High | Official docs, trusted APIs |
| 0.5–0.7 | Medium | Single source, unverified |
| 0.3–0.5 | Low | User input, web scrape |
| <0.3 | Uncertain | Hallucination-prone, conflicting |

---

## 8. Memory Systems

Grace has 6 interconnected memory systems:

### Memory Architecture

```
┌───────────────────────────────────────────────────────┐
│                 Unified Memory Interface                │
│            (cognitive/unified_memory.py)                │
├───────────────┬───────────────┬───────────────────────┤
│   Episodic    │  Procedural   │     Learning          │
│  "I remember  │ "I know how   │   "I learned that     │
│   when..."    │  to..."       │    X means Y"         │
├───────────────┴───────────────┴───────────────────────┤
│              Memory Mesh (integration layer)           │
│     Gap detection │ Topic clusters │ Metrics           │
├───────────────────────────────────────────────────────┤
│              MAGMA Graph Memory (persistent)           │
│  Semantic │ Temporal │ Causal │ Entity                 │
│  (concept   (event     (cause    (entity               │
│  similarity) ordering) effect)   co-occurrence)        │
├───────────────────────────────────────────────────────┤
│              Flash Cache (external references)         │
│              User Pattern Profiles                     │
└───────────────────────────────────────────────────────┘
```

### MAGMA Graphs (Persistent)

Every node and edge auto-persists to `graph_nodes` / `graph_edges` tables. On restart, `rehydrate()` restores the full graph state.

| Graph | Nodes | Edges | Auto-Links |
|-------|-------|-------|-----------|
| **Semantic** | Concepts | Similarity | Cosine > 0.7 |
| **Temporal** | Events | Before/After/Concurrent | Within 24h |
| **Causal** | Causes/Effects | Causes/Enables/Prevents | Manual + LLM |
| **Entity** | Named entities | Co-occurrence/Part-of | Context-based |

### User Thinking Pattern Learner

Observes every user interaction and builds an evolving profile:

| Pattern | Example Values |
|---------|---------------|
| Communication verbosity | verbose, moderate, concise |
| Technicality | technical, casual, mixed |
| Response preference | code_first, explanation_first |
| Problem-solving style | methodical, exploratory |
| Question depth | deep, moderate, surface |
| Topic preferences | database, async, debugging... |

Grace uses `get_adaptation_hints()` to customize system prompts per user.

---

## 9. Genesis Keys — Full Provenance

Every action in Grace creates a Genesis Key — a provenance record that tracks what happened, who did it, when, where, why, and how.

**Key structure:**
```python
GenesisKey(
    key_id="gk-abc123",
    key_type="code_change",        # what kind of action
    what_description="File written: main.py",
    who_actor="code_service",      # who/what performed it
    when_timestamp=datetime.utcnow(),
    where_component="brain.code",
    why_reason="User requested code generation",
    how_method="direct_write",
    file_path="main.py",
    session_id="session-xyz",
    user_id="aaron",
    is_error=False,
    tags=["code", "write"],
)
```

**Key types:** upload, file_op, file_ingestion, librarian, ai_response, ai_code_generation, coding_agent_action, api_request, system_event, db_change, code_change, web_fetch, error

**Tracking is automatic** — the `GenesisKeyMiddleware` tracks every API request. The `_genesis_tracker.track()` function is fire-and-forget and used throughout all services.

---

## 10. Internal VCS & CI/CD — No GitHub Dependency

### Internal Version Control

**File:** `genesis/internal_vcs.py`

Replaces Git entirely. Every file change creates a versioned snapshot in the database.

| Operation | What It Does |
|-----------|-------------|
| `snapshot(file, content, message)` | Create a new version (SHA-256 hash, unified diff) |
| `history(file)` | Get all versions of a file |
| `diff(file, v1, v2)` | Compare any two versions |
| `rollback(file, version)` | Restore to a previous version |
| `create_branch(name)` | Create a branch |
| `snapshot_directory(path)` | Version an entire directory tree |

### Internal Pipeline Runner

**File:** `genesis/internal_pipeline.py`

Replaces GitHub Actions. Runs pipeline stages as async subprocesses.

| Feature | Details |
|---------|---------|
| Stage execution | `asyncio.create_subprocess_shell` with timeout |
| YAML loading | `load_pipeline_yaml()` from disk |
| Output capture | stdout/stderr per stage |
| Artifact tracking | Per-run artifacts list |
| History | Full run history per workspace |
| Genesis integration | Every run creates a Genesis Key |

---

## 11. Multi-Tenant Workspaces

Each AI system (Tommy AI, Rebecca AI, etc.) gets its own workspace:

```
Workspace "tommy-ai"
├── knowledge_base/     ← isolated
├── data/               ← isolated
├── file versions       ← tracked by internal VCS
├── branches            ← main, dev, feature/...
└── pipeline runs       ← lint, test, build, deploy
```

Grace is the intelligence behind all of them. She fixes, heals, codes, and learns for every workspace.

**API:**
```
POST /api/workspaces                          — create workspace
POST /api/workspaces/{id}/vcs/snapshot        — version a file
POST /api/workspaces/{id}/pipelines/run       — run CI/CD pipeline
```

Or through the Brain API:
```
POST /brain/workspace { "action": "snapshot", "payload": { "workspace_id": "tommy-ai", "file_path": "main.py", "content": "..." } }
```

---

## 12. RAG & Retrieval Pipeline

### Multi-Tier Query Handling

```
User Query
    │
    ├──→ Tier 1: VectorDB (Qdrant cosine similarity)
    │    If quality > 0.6 → RAG response
    │
    ├──→ Tier 2: Model Knowledge (LLM with conversation history)
    │    If confidence > 0.7 → direct response
    │
    ├──→ Tier 3: Internet Search (SerpAPI → auto-ingest)
    │    Search web, ingest results into VectorDB
    │
    └──→ Tier 4: User Context
         Request additional information from user
```

### Retrieval Methods

| Method | How It Works |
|--------|-------------|
| `retrieve()` | Embed query → Qdrant KNN → enrich from DB |
| `retrieve_hybrid()` | Semantic + keyword boost (keyword_weight=0.3) |
| `retrieve_and_rank()` | Retrieve 3x → cross-encoder rerank → top-k |

### Graph-Based Retrieval

MAGMA provides graph traversal search alongside vector search:
- BFS, DFS, Best-First, Bidirectional, Causal Chain, Temporal Window
- RRF Fusion merges rankings from multiple sources

---

## 13. Layer 1 Message Bus

Async pub/sub system connecting all Grace components.

**File:** `layer1/message_bus.py`

### Components

GENESIS_KEYS, VERSION_CONTROL, LIBRARIAN, MEMORY_MESH, LEARNING_MEMORY, RAG, INGESTION, WORLD_MODEL, AUTONOMOUS_LEARNING, LLM_ORCHESTRATION, COGNITIVE_ENGINE

### Message Types

REQUEST, RESPONSE, EVENT, COMMAND, NOTIFICATION, TRIGGER

### API

```python
bus = get_message_bus()

# Publish event
await bus.publish("workspace.file_versioned", payload, ComponentType.VERSION_CONTROL)

# Request/response
result = await bus.request(ComponentType.RAG, "search", {"query": "..."}, timeout=5.0)

# Subscribe
bus.subscribe("genesis_keys.new_file_key", my_handler)

# Autonomous trigger
await bus.trigger("self_healing", {"component": "database"})
```

---

## 14. Grace OS — The 9-Layer Pipeline

For complex tasks, Grace runs a 9-layer pipeline:

| Layer | Name | Purpose |
|-------|------|---------|
| **L1** | Runtime | Setup environment, load context |
| **L2** | Planning | Decompose task into sub-tasks |
| **L3** | Proposer | Generate solution proposals |
| **L4** | Evaluator | Evaluate and select best proposal |
| **L5** | Simulation | Simulate the selected approach |
| **L6** | Codegen | Generate code |
| **L7** | Testing | Run tests (self-healing loop: L7→L6→L7) |
| **L8** | Verification | Verify output against requirements |
| **L9** | Deployment | Deployment gate (approval required) |

Each layer communicates via the Grace OS `MessageBus` and `TrustScorekeeper`.

---

## 15. MCP Servers & Tool Orchestration

### MCP Orchestrator

**File:** `grace_mcp/orchestrator.py`

The orchestrator enables Grace to use external tools through the Model Context Protocol:

1. LLM receives user request + available tools
2. LLM chooses which tool to call
3. Tool executes (file I/O, terminal, search, etc.)
4. Result returned to LLM
5. Loop until LLM has a final answer (max 10 turns)

### Available Tools

| Server | Tools |
|--------|-------|
| **DesktopCommanderMCP** | File read/write/edit, terminal commands, search, SSH, process management |
| **Memory** | Knowledge graph CRUD (entities, relations, observations) |
| **Filesystem** | File ops, directory tree, search |
| **Sequential Thinking** | Step-by-step reasoning |
| **Builtin** | `rag_search` (Grace KB), `web_search` (SerpAPI), `web_fetch` (URL) |

---

## 16. Frontend

**Tech:** React 19 + MUI 7 + Vite (rolldown-vite)

### Communication

The frontend talks to the backend exclusively through the Brain API:

```javascript
// frontend/src/config/brain-client.js
const result = await brainCall("code", "projects", {});
```

### Tab Layout (15+ Tabs)

ChatTab, FoldersTab, DocsTab, GovernanceTab, CodebaseTab, TasksTab, DevTab, WhitelistTab, OracleTab, BusinessIntelligenceTab, SystemHealthTab, LearningHealingTab, LabTab, APIsTab

### Key Components

- Version control UI: GitTree, DiffViewer, CommitTimeline, ModuleHistory
- Chat: ChatWindow, ConsensusChat, DirectoryChat
- Dashboards: KPIDashboard, ActivityFeed, IngestionDashboard
- Management: FileBrowser, RepositoryManager, GenesisKeyPanel

---

## 17. VSCode Extension

**24 commands**, 9 sidebar/panel views, keyboard shortcuts.

### Key Commands

| Shortcut | Command |
|----------|---------|
| `Ctrl+Shift+G` | Open Chat |
| `Ctrl+Shift+A` | Cognitive Analyze |
| `Ctrl+Shift+E` | Explain Code |
| `Ctrl+Shift+M` | Memory Query |
| `Ctrl+Shift+D` | Diagnostic Check |
| `Ctrl+Shift+H` | Ghost Ledger Toggle |
| `Ctrl+Shift+L` | View Lineage |

### Views

**Sidebar:** Dashboard, Chat, Memory Mesh, Genesis Keys, Diagnostics, Learning, Autonomous Tasks  
**Panel:** Ghost Ledger, Cognitive Output

### Configuration

`graceOS.backendUrl` (default `http://localhost:8000`), `graceOS.wsUrl`, auto-activate, telemetry, memory settings, etc.

---

## 18. Deployment

### Docker Compose (Development)

```bash
docker-compose up                    # Backend + Frontend + Qdrant
docker-compose --profile with-ollama up  # + Ollama
docker-compose --profile postgres up     # + PostgreSQL
```

| Service | Port | Image |
|---------|------|-------|
| backend | 8000 | Custom (Python 3.11) |
| frontend | 80 | Custom (nginx) |
| qdrant | 6333 | qdrant/qdrant:latest |
| ollama | 11434 | ollama/ollama:latest |
| postgres | 5432 | postgres:15-alpine |

### Kubernetes

Manifests in `k8s/deployment.yaml`:
- Namespace `grace`, ConfigMap, Secret
- Backend: 2 replicas, PVCs for data/logs
- Frontend: 2 replicas
- Ingress with TLS

### Backend Dockerfile

Multi-stage: MCP builder (Node 20) → Python builder → Runtime (Python 3.11-slim, non-root user `grace`)

---

## 19. Configuration Reference

All configuration via environment variables (`.env` file or system env):

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_TYPE` | `sqlite` | `sqlite`, `postgresql`, `mysql` |
| `DATABASE_PATH` | `data/grace.db` | SQLite path |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama server |
| `OLLAMA_LLM_DEFAULT` | `mistral:7b` | Default LLM model |
| `QDRANT_HOST` | `localhost` | Qdrant server |
| `QDRANT_PORT` | `6333` | Qdrant port |
| `EMBEDDING_DEFAULT` | `all-MiniLM-L6-v2` | Embedding model |
| `EMBEDDING_DEVICE` | `cuda` | `cuda` or `cpu` |
| `LIGHTWEIGHT_MODE` | `false` | Skip heavy components |
| `DISABLE_GENESIS_TRACKING` | `false` | Disable provenance |
| `LLM_PROVIDER` | — | `openai`, `ollama`, `kimi`, `opus` |
| `KIMI_API_KEY` | — | Kimi API key |
| `OPUS_API_KEY` | — | Opus API key |
| `SERPAPI_KEY` | — | SerpAPI key for web search |

---

## 20. How to Run Locally

### Prerequisites

- Python 3.10+
- Node.js 20+
- Docker (for Qdrant)

### Quick Start

```bash
# 1. Start Qdrant
docker run -p 6333:6333 qdrant/qdrant

# 2. Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # edit as needed
python run_migrations.py
uvicorn app:app --reload --port 8000

# 3. Frontend
cd frontend
npm install
npm run dev

# 4. (Optional) Ollama
ollama pull mistral:7b
ollama serve
```

### Docker

```bash
docker-compose up
# Frontend: http://localhost
# Backend API: http://localhost:8000
# Brain directory: http://localhost:8000/brain/directory
```

---

## 21. Key Patterns & Conventions

### Brain API Pattern

All business logic goes through brains. To add a new action:

1. Create a service function in `core/services/`
2. Add it to the brain dict in `api/brain_api_v2.py`
3. Update the directory in `_build_directory()`
4. Add Genesis tracking in the service

### Database Pattern

- Use `session_scope()` for service-layer DB access
- Use `Depends(get_session)` for FastAPI endpoints
- Use `run_in_executor` for async contexts
- All models extend `BaseModel` (auto `id`, `created_at`, `updated_at`)

### Genesis Tracking

Every mutation should track via Genesis:

```python
from api._genesis_tracker import track
track(key_type="code_change", what="File updated: main.py",
      who="code_service", tags=["code", "update"])
```

### Error Handling

- Use `try/except` with `logger.warning()` — never bare `except: pass`
- Use `ErrorBoundary` for critical paths
- Use `CircuitBreaker` for external services
- Use `GracefulDegradation` for system-wide failure modes

### Testing

```bash
cd backend
python -m pytest tests/ -v --tb=short
```

### Code Organization

- **API layer**: Thin routers, delegate to services
- **Service layer**: Business logic, sync functions
- **Cognitive layer**: Decision-making, learning, memory
- **Infrastructure layer**: DB, Qdrant, MCP, execution

---

## 22. Authentication & Authorization

### Token Format

Grace uses **cookie-based authentication**, not JWT or API keys:

| Cookie | Format | Purpose |
|--------|--------|---------|
| `genesis_id` | `GU-{uuid hex}` | User identity |
| `session_id` | `SS-{token hex}` | Session identity |

### How Clients Authenticate

**Option 1 — Cookies** (automatic for browsers):
- First request: `GenesisKeyMiddleware` assigns `genesis_id` and `session_id` cookies
- Subsequent requests: cookies are sent automatically

**Option 2 — Headers** (for API consumers):
- `X-Genesis-ID: GU-abc123...` — overrides cookie
- `X-Session-ID: SS-def456...` — overrides cookie

**Auth check** (`get_current_user` dependency):
- Only checks that `genesis_id` exists and starts with `GU-`
- Returns 401 if missing: `{"detail": "Authentication required. Please login."}`

### Roles / RBAC

**No RBAC exists.** All authenticated users have equal access. Rate limiting tiers (free/pro/admin) exist in `core/security.py` but are not enforced by auth middleware.

### Rate Limiting

| Path | Limit |
|------|-------|
| `/auth/`, `/login` | 10/minute |
| `/upload`, `/ingest` | 20/minute |
| `/chat`, `/grace/`, `/prompt` | 30/minute |
| Default | 100/minute |

**Brain-level limits** (per domain, RPM): chat: 60, ai: 30, system: 100, files: 100, govern: 50, data: 50, tasks: 100, code: 30.

On 429: response includes `Retry-After`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` headers.

### CORS Policy

Allowed origins (overridable via `CORS_ALLOWED_ORIGINS` env):
```
http://localhost:3000, http://localhost:5173, http://localhost:8000
http://127.0.0.1:3000, http://127.0.0.1:5173, http://127.0.0.1:8000
```

Methods: GET, POST, PUT, DELETE, OPTIONS, PATCH. Credentials: true. Max-age: 600s.

Custom headers allowed: `X-Genesis-ID`, `X-Session-ID`, `X-Request-ID`.

---

## 23. Error Response Contract

### Brain API Errors (HTTP 200, `ok: false`)

The Brain API **always returns 200** with the error in the body:

```json
{
    "brain": "code",
    "action": "read",
    "ok": false,
    "error": "FileNotFoundError: main.py not found",
    "latency_ms": 3.2,
    "genesis_key_id": null
}
```

Error categories in the `error` field:
- `"Unknown action 'xyz'. Available: ..."` — bad action name
- `"Rate limit exceeded — try again in 60s"` — rate limited
- `"Invalid input in field 'path'"` — validation failure
- Exception message truncated to 300 chars — runtime errors

### REST API Errors (Standard HTTP Codes)

| Code | When | Body |
|------|------|------|
| 400 | Bad request / validation | `{"detail": "message"}` |
| 401 | No `genesis_id` cookie/header | `{"detail": "Authentication required. Please login."}` |
| 404 | Resource not found | `{"detail": "message"}` |
| 409 | Conflict (e.g. workspace exists) | `{"detail": "message"}` |
| 413 | Request body > 50 MB (60 MB for chunks) | `{"detail": "Request too large. Maximum size: 50MB"}` |
| 429 | Rate limit exceeded | `{"detail": "Rate limit exceeded.", "retry_after": N}` |
| 500 | Unhandled exception | `{"detail": "Error: message"}` |
| 503 | Service unavailable (LLM, Qdrant down) | `{"detail": "message"}` |

### Retry Semantics

- **429**: Retry after `Retry-After` seconds
- **503**: Retry with exponential backoff (service may be starting)
- **500**: Do not retry (bug, not transient)
- **Brain API `ok: false`**: Application-level error; check `error` field for details

---

## 24. Data Flow — Complete Chat Request

Here's exactly what happens when a user sends `POST /brain/chat { "action": "send", "payload": { "chat_id": 5, "message": "How do I handle errors in Python?" } }`:

```
1. HTTP REQUEST arrives at FastAPI
   │
2. MIDDLEWARE CHAIN (outer → inner):
   ├── SecurityHeadersMiddleware: adds X-Content-Type-Options, X-Frame-Options, etc.
   ├── RateLimitMiddleware: checks /brain/* → 30/min limit → PASS
   ├── RequestValidationMiddleware: scans URL for injection patterns → PASS
   ├── CORSMiddleware: validates origin → PASS
   └── GenesisKeyMiddleware: reads genesis_id cookie → sets request.state.genesis_id
       creates Genesis Key: key_type=api_request, what="POST /brain/chat"
   │
3. BRAIN ROUTER: POST /brain/chat
   ├── Parses BrainRequest: action="send", payload={chat_id: 5, message: "..."}
   └── Calls _call("chat", "send", payload, _chat())
   │
4. _call() DISPATCHER:
   ├── Looks up handler: _chat()["send"] → send_prompt(payload)
   ├── Starts timer
   └── Calls handler
   │
5. send_prompt() in core/services/chat_service.py:
   ├── Loads chat from DB (session.query(Chat).get(5))
   ├── Loads conversation history (last 20 messages)
   └── Decides routing: small-talk? RAG? web search?
   │
6. MULTI-TIER QUERY HANDLING:
   │
   ├── Tier 1: VECTORDB SEARCH
   │   ├── EmbeddingModel.embed_text(["How do I handle errors..."]) → [384-dim vector]
   │   ├── QdrantVectorDB.search_vectors("documents", vector, limit=5, threshold=0.5)
   │   ├── Results enriched from DB (DocumentChunk → Document JOIN)
   │   └── If quality > 0.6 → RAG response
   │
   ├── Tier 2: MODEL KNOWLEDGE (if Tier 1 insufficient)
   │   ├── get_llm_client() → OllamaAdapter (or Kimi/Opus/Qwen)
   │   └── LLM generates response with conversation history as context
   │
   ├── Tier 3: INTERNET SEARCH (if Tier 2 confidence < 0.7)
   │   ├── SerpAPIService.search("Python error handling")
   │   └── Results auto-ingested into VectorDB for future queries
   │
   └── Tier 4: USER CONTEXT (if confidence still low)
       └── Returns knowledge gap request to user
   │
7. RESPONSE ASSEMBLY:
   ├── Build RAG prompt with retrieved chunks as context
   ├── LLM generates final response
   ├── Save assistant message to ChatHistory
   └── Genesis Key: key_type=ai_response, what="RAG retrieval: 3 chunks"
   │
8. _call() COMPLETION:
   ├── Records latency
   ├── Creates Genesis Key: key_type=api_request, what="brain/chat/send"
   └── Returns BrainResponse(ok=true, data={response, chunks, model}, latency_ms=450)
   │
9. RESPONSE TO CLIENT:
   └── HTTP 200 with BrainResponse JSON
```

---

## 25. Environment Setup — Gotchas

### Required API Keys (No Defaults)

| Variable | Required For | Impact Without |
|----------|-------------|----------------|
| `KIMI_API_KEY` | Kimi K2.5 LLM | Kimi provider unavailable; consensus runs without it |
| `OPUS_API_KEY` | Opus 4.6 / Claude | Opus provider unavailable |
| `SERPAPI_KEY` | Web search (Tier 3) | Internet search disabled; RAG-only |
| `QDRANT_API_KEY` | Qdrant Cloud only | Not needed for local Qdrant |

### Qdrant Collection Initialization

The `documents` collection is created automatically on first ingestion. Configuration:
- Vector size: **384** (for `all-MiniLM-L6-v2`) — auto-detected from embedding model
- Distance: **cosine**
- No manual setup needed; `TextIngestionService.__init__` handles it

### Embedding Model Download

- Default model: `all-MiniLM-L6-v2` (~80 MB download)
- First run: downloads from HuggingFace (1–5 min depending on connection)
- Cached at: `~/.cache/huggingface/` or `backend/models/embedding/`
- Skip with: `SKIP_EMBEDDING_LOAD=true` (disables RAG retrieval)

### CUDA vs CPU Fallback

- `EMBEDDING_DEVICE=cuda` (default) — uses GPU if available
- Auto-fallback: if CUDA OOM during retrieval, embedding model moves to CPU and retries
- Force CPU: `EMBEDDING_DEVICE=cpu`
- GPU memory: ~500 MB for embedding model, ~2 GB for reranker

### Minimum Hardware

| Mode | CPU | RAM | GPU | Disk |
|------|-----|-----|-----|------|
| Development (CPU) | 4 cores | 8 GB | None | 5 GB |
| Development (GPU) | 4 cores | 16 GB | 4 GB VRAM | 10 GB |
| Production | 8+ cores | 32 GB | 8 GB VRAM | 50 GB |

---

## 26. Multi-Tenancy Isolation Boundaries

### Isolation Model: Row-Level + Filesystem

Workspaces are isolated at **two levels**:

**1. Database — Row-Level Isolation**
- Every table with tenant data has `workspace_id` column
- Queries always filter by `workspace_id`: `session.query(FileVersion).filter_by(workspace_id=ws.id)`
- No schema-level or database-level isolation; all workspaces share one database
- Cross-workspace queries are impossible through the API (workspace_id is always scoped)

**2. Filesystem — Path Namespacing**
- Each workspace has its own `root_path` directory
- Workspace creation: `mkdir(root_path / "knowledge_base")`, `mkdir(root_path / "data")`
- File operations in `InternalVCS` resolve paths relative to `workspace.root_path`
- No symlink following; no path traversal (resolved via `Path.resolve()`)

### What's NOT Isolated

| Resource | Shared? | Notes |
|----------|---------|-------|
| Database connection | Shared | Single engine, single connection pool |
| Qdrant collection | Shared | All workspaces use `"documents"` collection |
| Embedding model | Shared | Single model instance in memory |
| LLM providers | Shared | Same Ollama/Kimi/Opus/Qwen for all |
| Layer 1 message bus | Shared | Events visible across workspaces |
| CPU/Memory | Shared | No resource quotas per workspace |

### Can Workspaces Access Each Other's Data?

**No, through the API.** Every workspace operation requires `workspace_id` and the VCS/pipeline code always scopes queries. However, at the database level there's no enforced constraint — a raw SQL query could cross boundaries. For stronger isolation in production, use separate databases per tenant.

---

## 27. Concurrency Model

### Thread Pool Executors

| Executor | Size | Location | Purpose |
|----------|------|----------|---------|
| `vcs` | 4 | `genesis/internal_vcs.py` | VCS DB operations |
| `graph-persist` | 2 | `cognitive/magma/graph_persistence.py` | Graph node/edge persistence |
| `qwen-pool` | 3 | `llm_orchestrator/qwen_pool.py` | Qwen LLM calls |
| `qwen-triad` | 6 | `cognitive/qwen_triad_orchestrator.py` | Triad orchestration |
| `agent-coord` | 4 | `cognitive/qwen_agents.py` | Agent coordination |
| `orchestrator` | 8 | `core/brain_orchestrator.py` | Brain orchestration |
| IO workers | 16 | `core/worker_pool.py` | General I/O (configurable: `GRACE_IO_WORKERS`) |
| CPU workers | 4 | `core/worker_pool.py` | CPU-bound tasks (configurable: `GRACE_CPU_WORKERS`) |
| Layer 1 connectors | 4 each | `layer1/components/*.py` | DB ops in message handlers |

### SQLite Under Load

- **WAL mode**: Multiple concurrent readers, single writer
- **`StaticPool`**: All threads share one connection — writes are serialized
- **`busy_timeout=30s`**: Writer waits up to 30s for lock before failing
- **Retry logic**: 3 retries with 0.5s backoff on "database is locked"
- **Known risk**: Under high concurrent writes, requests queue at the connection level. For production, use PostgreSQL.

### Circuit Breakers

`CircuitBreaker` protects external services:
- States: CLOSED → OPEN (after 3 failures) → HALF_OPEN (after 120s) → CLOSED (on success)
- Each external service gets its own breaker via `get_breaker("service_name")`

### Graceful Degradation

System-wide degradation levels: `FULL` → `REDUCED` → `EMERGENCY` → `READ_ONLY`

---

## 28. Migration Strategy

### How Migrations Work

Grace uses **custom Python migration scripts**, not Alembic:

1. `database/migration.py` — `create_tables()` calls `BaseModel.metadata.create_all(engine)` which creates any missing tables
2. `run_migrations.py` — imports all models (so they register with SQLAlchemy), then calls `create_all()`
3. Column migrations — individual scripts like `migrate_add_metadata_columns.py`

### Adding a New Model

1. Create the model class in `models/your_models.py`, extending `BaseModel`
2. Import it in `run_migrations.py` (add to the try/except block)
3. Import it in `database/migration.py`
4. Run `python run_migrations.py` — `create_all()` creates the new table

### Adding a New Column

1. Write a migration script: `database/migrations/add_your_column.py`
2. Use `ALTER TABLE` via `engine.execute(text("ALTER TABLE x ADD COLUMN y ..."))` with `IF NOT EXISTS` checks
3. Register in `run_migrations.py` or `run_all_migrations.py`

### Rollback

**No automated rollback.** Options:
- Restore from backup (`POST /api/runtime/backup` creates backups in `data/backups/`)
- Manual SQL to undo column additions
- `drop_tables()` exists but destroys all data

### Production Recommendation

Use PostgreSQL with proper backup/restore. For column migrations, use the `ALTER TABLE` scripts with `IF NOT EXISTS` guards. Test migrations on a copy first.

---

## 29. LLM Provider Failover

### Providers

| Provider | Config | Timeout | Model |
|----------|--------|---------|-------|
| **ollama** (default) | `OLLAMA_URL` | 120s | `mistral:7b` (configurable) |
| **openai** | `LLM_API_KEY` | 60s | `gpt-4` (configurable) |
| **kimi** | `KIMI_API_KEY` | 120s | `kimi-k2-0520` |
| **opus** | `OPUS_API_KEY` | 120s | `claude-sonnet-4-20250514` |
| **qwen** | `QWEN_*` vars | 180s | `qwen3-235b-a22b` |

### Failover Behavior

**Factory (`get_llm_client`)**: No automatic failover. Returns the single provider configured by `LLM_PROVIDER`. If that provider is down, the call fails.

**Consensus**: Runs all available providers in parallel. If one fails, consensus proceeds with the remaining models. Minimum 1 model required.

**Qwen Pool**: Internal failover within the pool — if a model hits >50% error rate after 3+ errors, it's marked unhealthy and the pool switches to the next slot (fast → code → reason).

**Task routing** (`get_llm_for_task`): For audit/document tasks, tries Opus/Kimi first, falls back to the default LLM if API keys are missing.

### What Happens When a Provider Is Down

- LLM call raises exception
- Brain API catches it, returns `ok: false` with error message
- Genesis Key tracks the error
- No automatic provider switching at the factory level

---

## 30. Qdrant Collection Management

| Setting | Value |
|---------|-------|
| Collection name | `documents` (configurable: `QDRANT_COLLECTION_NAME`) |
| Vector dimensions | 384 (for `all-MiniLM-L6-v2`); auto-detected from model |
| Distance metric | Cosine |
| Created by | `TextIngestionService.__init__()` (auto on first ingestion) |

### Chunking Strategy

| Setting | Default |
|---------|---------|
| `INGESTION_CHUNK_SIZE` | 512 characters |
| `INGESTION_CHUNK_OVERLAP` | 50 characters |
| Semantic chunking | Disabled (fallback: character-based) |

### Re-indexing

No built-in re-indexing command. To re-index:
1. `python force_reingest.py` — resets all documents to `pending`
2. Restart backend — auto-ingestion picks up pending documents
3. Or use `POST /brain/system { "action": "process_documents" }`

---

## 31. WebSocket Protocol (Voice API)

### Endpoint

`ws://localhost:8000/voice/ws/continuous`

### Client → Server Messages

```json
{"type": "start"}                              // Start session
{"type": "stop"}                               // End session
{"type": "transcript", "text": "..."}          // Send transcript
{"type": "audio", "data": "base64..."}         // Send audio for STT
{"type": "speak", "text": "...", "voice": "..."} // Request TTS
{"type": "ping"}                               // Keepalive
```

### Server → Client Messages

```json
{"type": "session_started", "message": "...", "timestamp": "..."}
{"type": "transcript_received", "original": "...", "processed": "...", "intent": "...", "timestamp": "..."}
{"type": "audio_response", "text": "...", "audio": "base64...", "format": "mp3", "timestamp": "..."}
{"type": "error", "message": "..."}
{"type": "pong"}
```

### Authentication

No authentication on the WebSocket endpoint. Any client can connect. Production should add auth middleware or token validation.

---

## 32. Logging & Observability

### Log Files

| File | Level | Format | Rotation |
|------|-------|--------|----------|
| Console (stderr) | WARNING+ | Human-readable | — |
| `logs/grace.log` | DEBUG+ | Human-readable | 10 MB × 5 |
| `logs/grace_structured.jsonl` | INFO+ | JSON | 20 MB × 3 |
| `logs/grace_audit.log` | WARNING+ | Audit format | 10 MB × 5 |

### Structured Log Fields

```json
{
    "ts": "2026-03-04T12:00:00Z",
    "level": "INFO",
    "logger": "retrieval.retriever",
    "msg": "Retrieved 3 chunks for query",
    "module": "retriever",
    "funcName": "retrieve",
    "line": 167,
    "request_id": "req-abc123",
    "user_id": "GU-xyz",
    "session_id": "SS-def"
}
```

### Request Tracing

| Mechanism | ID Format | Scope |
|-----------|-----------|-------|
| `request_id` | `req-{uuid}` | Per HTTP request (via `LoggingMiddleware`) |
| `trace_id` | `trace-{uuid}` | Per brain call (via `core/tracing.py`) |
| `correlation_id` | `corr-{uuid}` | Cross-service (via `core/logging.py`) |
| Genesis Key | `gk-{uuid}` | Per action (via `_genesis_tracker`) |

To trace a request: find `request_id` in structured logs → find `genesis_key_id` → query Genesis Keys table for full provenance.

---

## 33. Autonomous Loop (Ouroboros)

### What It Does

Runs every **30 seconds**. Cycle: TRIGGER → DIAGNOSE → DECIDE → ACT → LEARN → VERIFY.

Each cycle:
1. Runs deterministic scans on all registered components
2. Checks component health and trust scores
3. Detects orphan processes, Genesis key patterns, memory drift
4. Decides action based on trust thresholds

### Actions

| Action | Trust Threshold | What It Does |
|--------|----------------|--------------|
| HEAL | 0.5 | DB reconnect, cache clear, GC, service restart |
| LEARN | 0.4 | Record knowledge gaps, ingest into memory |
| CODE | 0.8 | (Not implemented — escalates instead) |
| ESCALATE | 0.0 | Queue for human review |

### Safety

- **No direct code edits** — the CODE path exists in design but is not implemented; most issues escalate
- HEAL actions are limited to: garbage collection, cache clearing, pool reconnection, diagnostic cycles
- All actions tracked via Genesis Keys

### How to Stop

| Method | How |
|--------|-----|
| Environment | `DISABLE_AUTONOMOUS_LOOP=true` — not started at boot |
| API | `POST /brain/system { "action": "auto_stop" }` |
| Emergency | `POST /brain/system { "action": "pause" }` — pauses entire runtime |

---

## 34. Testing Strategy

### Test Pyramid

| Level | Tests | Env Vars | What |
|-------|-------|----------|------|
| Smoke | `test_grace_system.py` Level 1 | All SKIP flags | Can all modules import? |
| Component | `test_grace_system.py` Level 2 | All SKIP flags | Does each brain return valid output? |
| Integration | `tests/test_complete_integration.py` | Minimal deps | Do components work together? |
| E2E | `tests/integration/` | Full stack | Full request lifecycle |

### Running Tests

```bash
cd backend

# Quick smoke test (no external deps)
SKIP_EMBEDDING_LOAD=true SKIP_QDRANT_CHECK=true SKIP_OLLAMA_CHECK=true \
  python -m pytest tests/test_grace_system.py -v

# Full suite
python -m pytest tests/ -v --tb=short --ignore=tests/integration

# Specific domain
python -m pytest tests/test_cognitive_engine.py -v
```

### Mocking LLM Calls

Tests avoid real LLM calls via:
- `SKIP_LLM_CHECK=true` — skips LLM connectivity checks
- `LIGHTWEIGHT_MODE=true` — disables retrieval in learning subagents
- `DISABLE_CONTINUOUS_LEARNING=true` — stops background learning
- Module-level mocks: `patch("sys.modules[...]")` with `MockLLM`
- No central LLM mock factory; each test file handles its own mocking

### Test Fixtures (`conftest.py`)

```python
@pytest.fixture(scope="session")
def app():  # FastAPI app with in-memory DB
    
@pytest.fixture(scope="session")
def client(app):  # TestClient

@pytest.fixture
def db_session():  # Database session via session_scope()
```

DB uses `:memory:` SQLite in tests.

---

## 35. Document Ingestion

### Supported Formats

| Category | Extensions |
|----------|-----------|
| **Text** | `.txt`, `.md`, `.json`, `.xml`, `.csv` |
| **Code** | `.py`, `.js`, `.jsx`, `.ts`, `.tsx`, `.java`, `.cpp`, `.c`, `.h`, `.cs`, `.php`, `.rb`, `.go`, `.rs`, `.swift`, `.kt`, `.scala`, `.sh`, `.bash`, `.sql`, `.html`, `.css`, `.scss`, `.yaml`, `.yml`, `.toml` |
| **Documents** | `.pdf`, `.docx`, `.doc`, `.xlsx`, `.xls`, `.pptx`, `.ppt` |
| **Audio** | `.mp3`, `.wav`, `.m4a`, `.flac`, `.ogg`, `.aac` |
| **Video** | `.mp4`, `.avi`, `.mov`, `.mkv`, `.webm`, `.flv` |

### Size Limits

- Upload: 50 MB per file (60 MB for chunked upload)
- Configurable via `RequestValidationMiddleware`

### Chunking

- Default: 512 characters per chunk, 50 character overlap
- Method: Character-based splitting (semantic chunking disabled by default)
- Configurable: `INGESTION_CHUNK_SIZE`, `INGESTION_CHUNK_OVERLAP`

---

## 36. LIGHTWEIGHT_MODE

When `LIGHTWEIGHT_MODE=true`:

| Component | Behavior |
|-----------|----------|
| Learning subagents | Use `NullRetriever` (no vector search) |
| Embedding model | Still loads unless `SKIP_EMBEDDING_LOAD=true` |
| Qdrant | Still connects unless `SKIP_QDRANT_CHECK=true` |
| Ollama | Still connects unless `SKIP_OLLAMA_CHECK=true` |
| Auto-ingestion | Still runs unless `SKIP_AUTO_INGESTION=true` |

For true minimal mode, set all SKIP flags:
```bash
LIGHTWEIGHT_MODE=true SKIP_EMBEDDING_LOAD=true SKIP_QDRANT_CHECK=true \
SKIP_OLLAMA_CHECK=true SKIP_AUTO_INGESTION=true DISABLE_AUTONOMOUS_LOOP=true
```

---

## 37. Backup & Disaster Recovery

### Creating Backups

```
POST /api/runtime/backup
```

- **PostgreSQL**: runs `pg_dump` → `data/backups/grace_{timestamp}.sql`
- **SQLite**: copies DB file → `data/backups/grace_{timestamp}.db`

### Workspace Snapshots

```
POST /brain/workspace { "action": "snapshot_dir", "payload": { "workspace_id": "...", "directory_path": "" } }
```

Snapshots entire workspace file tree into VCS (database-backed).

### No Automated Backup

Backups are on-demand via API. For production:
- Schedule `pg_dump` via cron
- Backup Qdrant snapshots to object storage
- Export Genesis Keys via archival service (daily JSON archives in `knowledge_base/layer_1/`)

---

## 38. Secret Management

### Development

Secrets in `.env` file (gitignored). Copy from `.env.example`.

### Kubernetes

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: grace-secrets
  namespace: grace
type: Opaque
stringData:
  DATABASE_URL: "postgresql://grace:grace@postgres-service:5432/grace"
  JWT_SECRET: "change-this-in-production"
  API_KEY: "change-this-api-key"
```

Backend deployment mounts via `envFrom: secretRef: grace-secrets`.

### Local Vault

`core/security.py` — encrypted vault at `data/.vault.enc`:
- Encrypted with Fernet using `GRACE_MASTER_KEY` env var
- API: `store_secret()`, `get_secret()`, `rotate_key()`
- No HashiCorp Vault integration

---

## 39. Frontend State Management

### Zustand Stores

| Store | Persisted? | Key State |
|-------|-----------|-----------|
| `usePreferencesStore` | Yes (`grace-preferences`) | Theme, sidebar, font, shortcuts |
| `useChatStore` | Yes (`grace-chat`, last 50) | Active chat, messages, streaming, draft |
| `useUIStore` | No | Loading, modals, toasts, search |
| `useAuthStore` | Yes (`grace-auth`) | User, tokens, genesis keys |
| `useSystemStore` | No | Connection status, health, services |

### Data Sync

- **HTTP polling only** — no WebSocket or SSE for state sync
- `brainCall(domain, action, payload)` → `fetch("POST /brain/{domain}")`
- `useConnectionStatus` polls `/api/connections/status` every **30 seconds**
- Chat messages are fetched on demand, not pushed

---

## 40. API Versioning

- **v1**: Fully removed. Does not exist in the codebase.
- **v2**: `brain_api_v2.py` is the only Brain API. `core/brain_controller.py` provides an alternative routing pattern at `/api/v2/{domain}/{action}`.
- No migration path needed — v1 was replaced before external consumers existed.

---

## 41. State Machine Diagrams

### OODA Decision Loop

```
OBSERVE ──→ ORIENT ──→ DECIDE ──→ ACT ──→ COMPLETED
   ↑                                          │
   └────────── reset() ──────────────────────┘
```

Strict sequence. Each phase validates the current state; out-of-order calls raise exceptions.

### Diagnostic Engine

```
STOPPED ──→ STARTING ──→ RUNNING ──→ PAUSED
                            │           │
                            └───→ ERROR ←┘
```

Triggers: HEARTBEAT (60s), SENSOR_FLAG, CICD_PIPELINE, MANUAL, API, WEBHOOK.

Pipeline per cycle: Sensors → Interpreters → Judgement → Action Router.

### Grace OS Session

```
initializing → setting_up → planning → executing → verifying → deploying → completed
                                                                            │
                                                                         failed
                                                                            │
                                                                        rejected
```

Maps to layers: L1 (setup) → L2 (plan) → L3 (propose) → L4 (evaluate) → L5 (simulate) → L6 (codegen) → L7 (test) → L8 (verify) → L9 (deploy gate).

---

*This document covers Grace 3.1 as of the `Aaron-new2` branch.*
