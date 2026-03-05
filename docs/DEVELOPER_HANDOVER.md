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

*This document covers Grace 3.1 as of commit `589ccd10` on the `Aaron-new2` branch.*
