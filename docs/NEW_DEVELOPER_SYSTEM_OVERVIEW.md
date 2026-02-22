# Grace 3.1 - New Developer System Overview

**Welcome to the Grace codebase.** This document is designed to give you a clear, logical path into the system. Read it top-to-bottom. By the end, you will understand what Grace is, how it is structured, how the pieces connect, and where to look when you need to change something.

---

## Table of Contents

1. [What is Grace?](#1-what-is-grace)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Repository Layout](#3-repository-layout)
4. [The Three Applications](#4-the-three-applications)
5. [Backend Deep Dive](#5-backend-deep-dive)
6. [Frontend Deep Dive](#6-frontend-deep-dive)
7. [VSCode Extension Deep Dive](#7-vscode-extension-deep-dive)
8. [Core Concepts You Must Understand](#8-core-concepts-you-must-understand)
9. [Data Flow: How a User Query Travels Through the System](#9-data-flow-how-a-user-query-travels-through-the-system)
10. [Infrastructure and DevOps](#10-infrastructure-and-devops)
11. [How to Run the System Locally](#11-how-to-run-the-system-locally)
12. [Configuration Reference](#12-configuration-reference)
13. [Where to Find Things (Quick Reference)](#13-where-to-find-things-quick-reference)
14. [Common Tasks for New Developers](#14-common-tasks-for-new-developers)
15. [Glossary](#15-glossary)

---

## 1. What is Grace?

Grace is a **Neuro-Symbolic AI system** -- not just a chatbot. It combines:

- **Neural** components (LLM inference via Ollama, vector embeddings, pattern recognition)
- **Symbolic** components (explicit knowledge graphs, trust scores, logic-based reasoning, deterministic rules)

The result is an AI that can:
- Chat with users using knowledge from ingested documents (RAG)
- Learn autonomously from new data
- Monitor and heal itself when things break
- Track every operation with full audit trails (Genesis Keys)
- Run experiments in a sandboxed environment
- Manage code via version control with cognitive awareness
- Operate as a VSCode extension for in-IDE intelligence

**Think of Grace as an AI operating system**, not just an API.

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          USER INTERFACES                                │
│                                                                         │
│   ┌──────────────┐    ┌──────────────────┐    ┌──────────────────┐    │
│   │   Frontend    │    │  VSCode Extension │    │   API Clients    │    │
│   │  (React/Vite) │    │   (Grace OS)      │    │   (curl, etc.)   │    │
│   │  Port 5173    │    │   TypeScript      │    │                  │    │
│   └──────┬───────┘    └────────┬─────────┘    └────────┬─────────┘    │
│          │                     │                        │               │
└──────────┼─────────────────────┼────────────────────────┼───────────────┘
           │                     │                        │
           ▼                     ▼                        ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      BACKEND (FastAPI - Port 8000)                      │
│                                                                         │
│   ┌─────────────────────────────────────────────────────────────┐      │
│   │                     API Layer (~50 routers)                  │      │
│   │  Chat, Ingest, Retrieve, Genesis, Cognitive, Learning, ...  │      │
│   └─────────────────────────┬───────────────────────────────────┘      │
│                             │                                           │
│   ┌─────────────┬───────────┼───────────┬───────────────────┐          │
│   │  Cognitive   │  Genesis  │  Retrieval │   ML Intelligence │          │
│   │  Engine      │  Keys     │  (Multi-   │   (Trust Scoring, │          │
│   │  (OODA Loop) │  (Audit)  │   Tier)    │    Bandits, etc.) │          │
│   └─────────────┴───────────┴───────────┴───────────────────┘          │
│                                                                         │
│   ┌─────────────────────────────────────────────────────────────┐      │
│   │               Layer 1 Communication Mesh (Message Bus)       │      │
│   │   Connects: RAG, Genesis, KPI, LLM, Memory, Ingestion, ...  │      │
│   └─────────────────────────────────────────────────────────────┘      │
│                                                                         │
└──────────┬──────────────────────┬───────────────────────┬───────────────┘
           │                      │                       │
           ▼                      ▼                       ▼
┌──────────────────┐  ┌──────────────────┐   ┌──────────────────────┐
│   SQLite/PostgreSQL │  │   Qdrant Vector DB │   │   Ollama (LLM)       │
│   (Structured Data) │  │   (Embeddings)     │   │   (mistral:7b, etc.) │
│   Port: file/5432   │  │   Port 6333        │   │   Port 11434         │
└──────────────────┘  └──────────────────┘   └──────────────────────┘
```

**Three external services Grace depends on:**

| Service | Purpose | Default Port |
|---------|---------|-------------|
| **Ollama** | Runs LLM models locally (mistral:7b default) | 11434 |
| **Qdrant** | Vector database for document embeddings | 6333 |
| **SQLite/PostgreSQL** | Relational database for structured data | File-based / 5432 |

---

## 3. Repository Layout

```
grace-3.1/
│
├── backend/                    # Python FastAPI backend (THE CORE)
│   ├── app.py                  # Main FastAPI application entry point
│   ├── settings.py             # All configuration (env vars)
│   ├── logging_config.py       # Logging setup
│   │
│   ├── api/                    # ~50 API route modules (REST endpoints)
│   ├── cognitive/              # Brain of Grace (OODA, learning, memory, healing)
│   │   └── magma/              # Deep memory system (Magma Memory)
│   ├── layer1/                 # Communication mesh (message bus between systems)
│   │   └── components/         # Connectors: RAG, Genesis, KPI, LLM, Memory...
│   ├── genesis/                # Audit trail & version tracking system
│   ├── retrieval/              # Document retrieval (multi-tier: VectorDB→Model→Context)
│   ├── embedding/              # Text-to-vector embedding models
│   ├── ingestion/              # Document ingestion pipeline (file→chunks→vectors)
│   ├── llm_orchestrator/       # Multi-LLM management and routing
│   ├── ml_intelligence/        # ML features (trust scoring, bandits, meta-learning)
│   ├── diagnostic_machine/     # 4-layer self-diagnostic system
│   ├── file_manager/           # File handling, health monitoring, intelligence
│   ├── librarian/              # Document categorization, tagging, relationships
│   ├── confidence_scorer/      # Confidence scoring and contradiction detection
│   ├── vector_db/              # Qdrant vector database client
│   ├── ollama_client/          # Ollama LLM client wrapper
│   ├── database/               # Database connection, models, migrations
│   ├── models/                 # SQLAlchemy ORM models
│   ├── security/               # Auth, CORS, rate limiting, governance
│   ├── services/               # High-level service orchestration
│   ├── search/                 # Internet search (SerpAPI integration)
│   ├── scraping/               # Web scraping service
│   ├── execution/              # Action execution bridge with governance
│   ├── telemetry/              # System telemetry and monitoring
│   ├── version_control/        # Git service integration
│   ├── cache/                  # Redis cache layer
│   ├── utils/                  # Shared utilities
│   ├── scripts/                # Startup and maintenance scripts
│   ├── tests/                  # Test suite
│   ├── data/                   # SQLite database files
│   └── knowledge_base/         # Ingested document storage
│
├── frontend/                   # React (Vite) web UI
│   ├── src/
│   │   ├── App.jsx             # Main app with 23 tab-based views
│   │   ├── components/         # ~40 React components (one per feature tab)
│   │   ├── config/api.js       # API endpoint configuration
│   │   └── store/              # State management
│   ├── package.json            # React 19, MUI, Vite
│   └── index.html              # Entry point
│
├── grace-os-vscode/            # VSCode extension (TypeScript)
│   ├── src/
│   │   ├── extension.ts        # Extension entry point
│   │   ├── core/               # Core systems (scheduler, ledger, status bar)
│   │   ├── bridges/            # IDE↔Backend communication
│   │   ├── panels/             # Chat panel, dashboard
│   │   ├── providers/          # Cognitive, diagnostic, genesis, memory providers
│   │   ├── systems/            # 12 subsystems (Magma, OODA, Security, etc.)
│   │   └── test/               # Extension tests
│   └── package.json            # Grace OS v3.1.0, VSCode ^1.85
│
├── k8s/                        # Kubernetes deployment manifests
├── monitoring/                 # Grafana dashboard config
├── pipelines/                  # CI/CD pipeline definitions
├── .github/                    # GitHub workflows, issue templates
├── docs/                       # Architecture documentation
├── knowledge_base/             # Top-level knowledge base directory
├── qdrant_storage/             # Qdrant persistent storage
├── tests/                      # Integration tests
├── tools/                      # Utility tools
├── benchmarks/                 # Performance benchmarks
│
├── start.sh                    # Start backend + frontend (Linux/Mac)
├── start.bat                   # Start backend + frontend (Windows)
├── verify_system.sh            # System verification script
└── *.md                        # Extensive documentation files
```

---

## 4. The Three Applications

### 4.1 Backend (Python/FastAPI)

**Location:** `backend/`
**Language:** Python 3.x
**Framework:** FastAPI with Uvicorn
**Port:** 8000

This is the brain. Everything runs through here. The backend has approximately **50 API routers** registered in `app.py`, covering every feature of the system.

**Key entry points:**
- `backend/app.py` -- FastAPI app definition, all router registrations, startup lifecycle
- `backend/settings.py` -- All configuration loaded from environment variables

### 4.2 Frontend (React/Vite)

**Location:** `frontend/`
**Language:** JavaScript (JSX)
**Framework:** React 19 + Vite + Material UI
**Port:** 5173

A tab-based single-page application with **23 feature tabs**:

| Tab | Component | What It Does |
|-----|-----------|-------------|
| Chat | `ChatTab.jsx` | Main conversation interface with RAG |
| Governance | `GovernanceTab.jsx` | Three-pillar governance framework |
| Sandbox | `SandboxTab.jsx` | Experimentation environment |
| Insights | `InsightsTab.jsx` | System insights and analytics |
| Code Base | `CodeBaseTab.jsx` | File browser, code search, analysis |
| Documents | `RAGTab.jsx` | Document upload, ingestion, retrieval |
| Research | `ResearchTab.jsx` | Research tools and resources |
| APIs | `APITab.jsx` | API testing and exploration |
| Librarian | `LibrarianTab.jsx` | Document categorization and tagging |
| Cognitive | `CognitiveTab.jsx` | OODA loop visualization, decisions |
| Monitoring | `MonitoringTab.jsx` | System health and metrics |
| Version Control | `VersionControl.jsx` | Git integration and history |
| Task Manager | `NotionTab.jsx` | Kanban-style task board |
| Grace Todos | `GraceTodosTab.jsx` | Autonomous task management |
| Planning | `GracePlanningTab.jsx` | Concept-to-execution workflow |
| Genesis Keys | `GenesisKeyTab.jsx` | Audit trail viewer |
| Learning | `LearningTab.jsx` | Autonomous learning dashboard |
| ML Intelligence | `MLIntelligenceTab.jsx` | ML features dashboard |
| Whitelist | `WhitelistTab.jsx` | Human-approved learning entries |
| Experiments | `ExperimentTab.jsx` | Sandbox experiments |
| Connectors | `ConnectorsTab.jsx` | External knowledge source integrations |
| Orchestration | `OrchestrationTab.jsx` | Multi-LLM orchestration |
| Telemetry | `TelemetryTab.jsx` | System telemetry dashboard |
| Web Scraper | `WebScraper.jsx` | URL scraping and crawling |

All API calls go through `frontend/src/config/api.js` which centralizes the backend URL (`http://localhost:8000` by default).

### 4.3 VSCode Extension (Grace OS)

**Location:** `grace-os-vscode/`
**Language:** TypeScript
**Platform:** VSCode Extension API (^1.85)
**Version:** 3.1.0

Brings Grace into the IDE. Key features:
- **Chat Panel** -- Talk to Grace from VSCode
- **Memory Mesh** -- Query and store knowledge
- **Genesis Keys** -- Track code changes with full audit
- **Ghost Ledger** -- Line-by-line change tracking
- **Diagnostic Machine** -- Real-time system health
- **Cognitive Analysis** -- Analyze, explain, refactor code
- **Autonomous Scheduler** -- Background task management
- **Magma Memory** -- Deep memory ingestion and consolidation

---

## 5. Backend Deep Dive

The backend is the most complex part. Here is how to think about its subsystems:

### 5.1 Subsystem Map

```
┌──────────────────────────────────────────────────────────────────────┐
│                        BACKEND SUBSYSTEMS                            │
│                                                                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐   │
│  │   API LAYER      │  │  DATA LAYER       │  │  AI/ML LAYER    │   │
│  │                  │  │                  │  │                 │   │
│  │  api/ (50 routes)│  │  database/        │  │  cognitive/     │   │
│  │  app.py          │  │  models/          │  │  ml_intelligence│   │
│  │  security/       │  │  vector_db/       │  │  llm_orchestr.  │   │
│  │                  │  │  embedding/       │  │  retrieval/     │   │
│  └──────────────────┘  │  ingestion/       │  │  confidence_sc. │   │
│                        │  cache/           │  │  librarian/     │   │
│  ┌──────────────────┐  └──────────────────┘  └─────────────────┘   │
│  │   INFRA LAYER    │                                                │
│  │                  │  ┌──────────────────┐  ┌─────────────────┐   │
│  │  genesis/        │  │  COMMUNICATION   │  │  SELF-MGMT      │   │
│  │  telemetry/      │  │                  │  │                 │   │
│  │  version_control/ │  │  layer1/         │  │  diagnostic_m.  │   │
│  │  search/         │  │  (message bus +  │  │  cognitive/     │   │
│  │  scraping/       │  │   connectors)    │  │   healing       │   │
│  │  execution/      │  │                  │  │   mirror        │   │
│  └──────────────────┘  └──────────────────┘  │   learning      │   │
│                                               └─────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

### 5.2 Key Subsystems Explained

#### API Layer (`api/`)

About 50 Python files, each defining a FastAPI router. All are registered in `app.py`. Key ones:

| File | Prefix | Purpose |
|------|--------|---------|
| `api/ingest.py` | `/ingest` | Document ingestion |
| `api/retrieve.py` | `/retrieve` | Document retrieval/search |
| `api/genesis_keys.py` | `/genesis` | Genesis Key CRUD |
| `api/cognitive.py` | `/cognitive` | Cognitive engine endpoints |
| `api/layer1.py` | `/layer1` | Layer 1 mesh operations |
| `api/llm_orchestration.py` | `/llm` | Multi-LLM management |
| `api/ml_intelligence_api.py` | `/ml` | ML Intelligence features |
| `api/voice_api.py` | `/voice` | Speech-to-text / Text-to-speech |
| `api/agent_api.py` | `/agent` | Software engineering agent |
| `api/grace_todos_api.py` | `/grace-todos` | Autonomous task management |
| `api/grace_planning_api.py` | `/grace-planning` | Planning workflow |
| `api/streaming.py` | `/stream` | SSE streaming responses |
| `api/websocket.py` | `/ws` | WebSocket real-time updates |
| `api/health.py` | `/health` | Comprehensive health checks |
| `api/scraping.py` | `/scrape` | Web scraping |

#### Cognitive Engine (`cognitive/`)

The "brain" of Grace. Implements the OODA (Observe-Orient-Decide-Act) loop and all learning systems.

| File | What It Does |
|------|-------------|
| `engine.py` | Core cognitive engine |
| `ooda.py` | OODA loop implementation |
| `ambiguity.py` | Ambiguity detection and handling |
| `memory_mesh_integration.py` | Memory mesh operations |
| `mirror_self_modeling.py` | Self-observation and improvement |
| `autonomous_healing_system.py` | Self-healing (AVN/AVM-based) |
| `learning_subagent_system.py` | 8-process learning pipeline |
| `continuous_learning_orchestrator.py` | Background continuous learning |
| `predictive_context_loader.py` | Predictive context loading |
| `episodic_memory.py` | Episode-based memory |
| `procedural_memory.py` | Procedure memory |

**Magma Memory** (`cognitive/magma/`) is the deep memory subsystem:
- `grace_magma_system.py` -- Core Magma memory system
- `relation_graphs.py` -- Knowledge relationship graphs
- `causal_inference.py` -- Causal reasoning
- `topological_retrieval.py` -- Advanced retrieval
- `synaptic_ingestion.py` -- Memory ingestion
- `async_consolidation.py` -- Background memory consolidation

#### Genesis Keys (`genesis/`)

The audit trail system. Every operation in Grace creates a "Genesis Key" that records **what, where, when, who, how, and why**.

| File | What It Does |
|------|-------------|
| `genesis_key_service.py` | Core Genesis Key CRUD |
| `middleware.py` | Auto-tracking middleware (every API call) |
| `file_watcher.py` | File system change monitoring |
| `autonomous_triggers.py` | Auto-trigger actions from keys |
| `comprehensive_tracker.py` | Detailed tracking |
| `daily_organizer.py` | Daily key organization |
| `directory_hierarchy.py` | Directory-level tracking |
| `healing_system.py` | Healing via Genesis patterns |

#### Layer 1 Communication Mesh (`layer1/`)

An internal message bus that connects all subsystems. Think of it as the "nervous system."

- `message_bus.py` -- Pub/sub message bus
- `initialize.py` -- Starts all connectors
- `components/` -- Individual connectors for each subsystem:
  - `rag_connector.py` -- RAG retrieval events
  - `genesis_keys_connector.py` -- Genesis key events
  - `kpi_connector.py` -- KPI metric events
  - `llm_orchestration_connector.py` -- LLM events
  - `memory_mesh_connector.py` -- Memory events
  - `ingestion_connector.py` -- Ingestion events
  - `version_control_connector.py` -- Version control events
  - `data_integrity_connector.py` -- Data integrity events
  - `neuro_symbolic_connector.py` -- Neuro-symbolic events
  - `knowledge_base_connector.py` -- KB events

#### Retrieval System (`retrieval/`)

Multi-tier query handling:

```
User Query
    │
    ▼
Tier 1: Vector DB (Qdrant) ─── Found? → Generate response with RAG context
    │ (no match)
    ▼
Tier 2: Model Knowledge ────── LLM answers from training data
    │ (low confidence)
    ▼
Tier 3: User Context Request ─ Ask user to provide more info
```

Key files:
- `retriever.py` -- Base retrieval logic
- `multi_tier_integration.py` -- Tier fallback orchestration
- `cognitive_retriever.py` -- Cognitive-aware retrieval
- `trust_aware_retriever.py` -- Trust-score-weighted retrieval
- `reranker.py` -- Result reranking
- `query_intelligence.py` -- Query analysis and routing

#### Diagnostic Machine (`diagnostic_machine/`)

A 4-layer self-diagnostic system:

```
Layer 1: Sensors       → Collect raw telemetry
Layer 2: Interpreters  → Analyze patterns
Layer 3: Judgement      → Make diagnostic decisions
Layer 4: Action Router  → Execute fixes or escalate
```

#### ML Intelligence (`ml_intelligence/`)

Advanced ML features:
- `neural_trust_scorer.py` -- Neural network-based trust scoring
- `multi_armed_bandit.py` -- Exploration/exploitation for routing
- `meta_learning.py` -- Learning to learn
- `active_learning_sampler.py` -- Strategic data selection
- `neuro_symbolic_reasoner.py` -- Hybrid reasoning
- `contrastive_learning.py` -- Contrastive learning for embeddings
- `uncertainty_quantification.py` -- Confidence calibration

### 5.3 Database Architecture

**Relational (SQLite/PostgreSQL):**
- `database/config.py` -- Supports SQLite, PostgreSQL, MySQL, MariaDB
- `database/connection.py` -- Connection management with pooling
- `database/session.py` -- Session factory (thread-safe)
- `database/migration.py` -- Table creation
- `models/database_models.py` -- SQLAlchemy ORM models (Chats, Messages, Documents, Genesis Keys, etc.)

Default: SQLite at `backend/data/grace.db`

**Vector (Qdrant):**
- `vector_db/client.py` -- Qdrant client wrapper
- Collection: `documents` (stores document chunk embeddings)

**Embedding:**
- `embedding/embedder.py` -- Embedding model management
- Default model: `qwen_4b` (SentenceTransformer)

### 5.4 Startup Lifecycle

When `app.py` runs, the following happens in order:

1. **Logging configured** (`logging_config.py`)
2. **Database initialized** (connection, session factory, tables created)
3. **Embedding model pre-loaded** (unless `SKIP_EMBEDDING_LOAD=true`)
4. **Ollama connection checked** (unless `SKIP_OLLAMA_CHECK=true`)
5. **Qdrant connection checked** (unless `SKIP_QDRANT_CHECK=true`)
6. **File watcher started** (Genesis tracking, unless `DISABLE_GENESIS_TRACKING=true`)
7. **ML Intelligence initialized**
8. **Auto-ingestion started** (scans `knowledge_base/`, unless `SKIP_AUTO_INGESTION=true`)
9. **Continuous learning activated** (unless `DISABLE_CONTINUOUS_LEARNING=true`)
10. **Security middleware applied** (CORS, rate limiting, request validation)
11. **Genesis Key middleware applied** (tracks all API calls)
12. **All 50 routers registered**

---

## 6. Frontend Deep Dive

### 6.1 Technology Stack

- **React 19** with hooks (no class components)
- **Vite** (via rolldown-vite) for bundling
- **Material UI (MUI)** for UI components
- **@dnd-kit** and **@hello-pangea/dnd** for drag-and-drop
- **Axios** for HTTP requests

### 6.2 Architecture

The frontend is a simple, flat architecture:

```
App.jsx
  ├── State: activeTab (which tab is shown)
  ├── Health check polling (every 30s)
  ├── Voice message handling
  ├── Sidebar navigation (23 tabs)
  └── Main content area (renders active tab component)
```

Each tab is a self-contained component in `frontend/src/components/`. Each component manages its own state and API calls.

### 6.3 API Communication

All API calls use the centralized config in `frontend/src/config/api.js`:

```javascript
import { API_BASE_URL, API_ENDPOINTS } from './config/api';

// Example: fetch health
const response = await fetch(API_ENDPOINTS.health);
```

The `API_BASE_URL` defaults to `http://localhost:8000` and can be overridden with the `VITE_API_BASE_URL` environment variable.

---

## 7. VSCode Extension Deep Dive

### 7.1 Architecture

```
extension.ts (entry point)
    │
    ├── core/
    │   ├── GraceOSCore.ts          # Central coordinator
    │   ├── GraceStatusBar.ts       # Status bar items
    │   ├── GhostLedger.ts          # Line-change tracking
    │   └── AutonomousScheduler.ts  # Background task scheduler
    │
    ├── bridges/
    │   ├── IDEBridge.ts            # IDE ↔ Backend HTTP
    │   └── WebSocketBridge.ts      # Real-time WebSocket
    │
    ├── panels/
    │   ├── GraceChatPanel.ts       # Chat webview
    │   └── GraceDashboardPanel.ts  # Dashboard webview
    │
    ├── providers/
    │   ├── CognitiveIDEProvider.ts  # Code analysis
    │   ├── DiagnosticProvider.ts    # Diagnostic tree view
    │   ├── GenesisKeyProvider.ts    # Genesis key tree view
    │   ├── LearningProvider.ts      # Learning tree view
    │   ├── MemoryMeshProvider.ts    # Memory tree view
    │   └── InlineCodeIntelligence.ts # Inline suggestions
    │
    └── systems/                     # 12 subsystems
        ├── DeepMagmaMemory.ts
        ├── DiagnosticMachine.ts
        ├── EnterpriseAgent.ts
        ├── IngestionPipeline.ts
        ├── NeuralSymbolicAI.ts
        ├── OracleMLIntelligence.ts
        ├── ProactiveLearning.ts
        ├── SandboxLab.ts
        ├── SecurityLayer.ts
        ├── SelfHealingSystem.ts
        ├── TimeSenseOODA.ts
        └── ClarityFramework.ts
```

### 7.2 Communication

The extension communicates with the backend via:
1. **HTTP** (`IDEBridge.ts`) -- Standard REST calls to `http://localhost:8000`
2. **WebSocket** (`WebSocketBridge.ts`) -- Real-time updates via `ws://localhost:8000/ws`

Both URLs are configurable in VSCode settings under `graceOS.backendUrl` and `graceOS.wsUrl`.

---

## 8. Core Concepts You Must Understand

### 8.1 Genesis Keys

Every significant operation creates a "Genesis Key" -- a structured audit record containing:
- **What** happened
- **Where** it happened (file, endpoint, system)
- **When** it happened (timestamp)
- **Who** initiated it (user, system, agent)
- **How** it was done (method, parameters)
- **Why** it was done (trigger, context)

Genesis Keys are the foundation for:
- Full audit trails
- Autonomous triggers (one key can trigger another action)
- Learning from past operations
- Debugging and forensics

### 8.2 OODA Loop

Grace's cognitive decision-making follows the **OODA** loop:
- **Observe**: What is the actual problem/input?
- **Orient**: What context matters? What are the constraints?
- **Decide**: What is the plan? What alternatives exist?
- **Act**: Execute with monitoring

This is implemented in `backend/cognitive/ooda.py` and enforced throughout the system.

### 8.3 Multi-Tier Query Handling

When a user asks a question:
1. **Tier 1 (VectorDB)**: Search Qdrant for relevant document chunks
2. **Tier 2 (Model Knowledge)**: If nothing found, use the LLM's training knowledge
3. **Tier 3 (Context Request)**: If still uncertain, ask the user for more info

Implemented in `backend/retrieval/multi_tier_integration.py`.

### 8.4 Trust Scores

Every piece of knowledge has a trust score (0.0 to 1.0) based on:
- Source reliability
- Consistency with other knowledge
- Age and freshness
- Validation results

Higher trust = more weight in responses.

### 8.5 Memory Mesh

Grace's memory has multiple layers:
- **Episodic Memory** -- What happened (events, interactions)
- **Procedural Memory** -- How to do things (processes)
- **Semantic Memory** -- What things mean (concepts, relationships)
- **Magma Memory** -- Deep, consolidated long-term memory

### 8.6 Continuous Learning Pipeline

Grace runs a background learning loop:
```
Ingest Data → Study (3 agents) → Practice (2 agents) → Mirror Observes
     → Detect Patterns → Generate Improvements → Trigger New Learning → Repeat
```

### 8.7 Self-Healing

When issues are detected:
1. Anomaly detected (7 types: error spikes, memory leaks, etc.)
2. Health level assessed (HEALTHY → DEGRADED → WARNING → CRITICAL → FAILING)
3. Healing action selected based on trust level
4. Action executed (buffer clear → process restart → emergency shutdown)
5. Outcome logged, trust scores updated

---

## 9. Data Flow: How a User Query Travels Through the System

Here is the exact path a message takes from the user typing in the chat to receiving a response:

```
1. User types message in Frontend (ChatTab.jsx)
          │
          ▼
2. HTTP POST to /chats/{id}/prompt (backend/app.py)
          │
          ▼
3. Greeting detector checks if it's small talk
   ├── YES → Generate simple response via Ollama, return
   └── NO → Continue to multi-tier handling
          │
          ▼
4. Conversation context loaded (last 10 messages from DB)
          │
          ▼
5. Multi-tier handler created (retrieval/multi_tier_integration.py)
          │
          ▼
6. Tier 1: Qdrant vector search
   ├── Embedding model converts query to vector
   ├── Qdrant searches for similar document chunks
   ├── Results reranked and scored
   └── If good results found → Build RAG prompt → Send to Ollama → Return
          │ (no results)
          ▼
7. Tier 2: LLM model knowledge
   ├── Send query directly to Ollama
   ├── Check confidence of response
   └── If confident → Return
          │ (low confidence)
          ▼
8. Tier 3: Request user context
   └── Return message asking user for more information
          │
          ▼
9. Response saved to database (ChatHistory)
          │
          ▼
10. Genesis Key created (tracks the entire interaction)
          │
          ▼
11. Response returned to Frontend → Displayed to user
```

---

## 10. Infrastructure and DevOps

### Kubernetes

- `k8s/deployment.yaml` -- Kubernetes deployment specs
- `k8s/services.yaml` -- Service definitions

### CI/CD

- `.github/workflows/ci.yml` -- Continuous integration
- `.github/workflows/cd.yml` -- Continuous deployment
- `pipelines/grace-ci.yaml` -- Grace-specific CI pipeline
- `pipelines/grace-deploy.yaml` -- Deployment pipeline

### Monitoring

- `monitoring/grafana-dashboard.json` -- Pre-built Grafana dashboard

### Docker

- `frontend/Dockerfile` -- Frontend container
- `frontend/nginx.conf` -- Nginx config for production frontend

---

## 11. How to Run the System Locally

### Prerequisites

1. **Python 3.10+** with pip
2. **Node.js 18+** with npm
3. **Ollama** installed and running (`ollama serve`)
4. **Qdrant** running (Docker: `docker run -p 6333:6333 qdrant/qdrant`)

### Quick Start

```bash
# 1. Clone and enter repo
cd grace-3.1

# 2. Backend setup
cd backend
python -m venv venv
source venv/bin/activate          # Linux/Mac
# venv\Scripts\activate           # Windows
pip install -r requirements.txt   # (if exists, otherwise install manually)
cp .env.example .env              # Configure environment
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000

# 3. Frontend setup (new terminal)
cd frontend
npm install
npm run dev                       # Starts on http://localhost:5173

# 4. Or use the unified start script
./start.sh                        # Linux/Mac
start.bat                         # Windows
```

### Verify Everything Works

```bash
# Check backend health
curl http://localhost:8000/health

# Check API docs
open http://localhost:8000/docs

# Open frontend
open http://localhost:5173
```

---

## 12. Configuration Reference

All configuration is in `backend/settings.py`, loaded from environment variables. Create a `.env` file in `backend/` to customize:

### Core Services

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_URL` | `http://localhost:11434` | Ollama LLM service URL |
| `OLLAMA_LLM_DEFAULT` | `mistral:7b` | Default LLM model |
| `QDRANT_HOST` | `localhost` | Qdrant vector DB host |
| `QDRANT_PORT` | `6333` | Qdrant port |
| `DATABASE_TYPE` | `sqlite` | Database type (sqlite, postgresql, mysql, mariadb) |
| `DATABASE_PATH` | `backend/data/grace.db` | SQLite file path |

### Embedding

| Variable | Default | Description |
|----------|---------|-------------|
| `EMBEDDING_DEFAULT` | `qwen_4b` | Embedding model name |
| `EMBEDDING_DEVICE` | `cuda` | Device (cuda or cpu) |

### Feature Flags (set to `true` to disable)

| Variable | Default | Description |
|----------|---------|-------------|
| `SKIP_EMBEDDING_LOAD` | `false` | Skip loading embedding model |
| `SKIP_OLLAMA_CHECK` | `false` | Skip Ollama connectivity check |
| `SKIP_QDRANT_CHECK` | `false` | Skip Qdrant connectivity check |
| `SKIP_AUTO_INGESTION` | `false` | Skip auto-ingesting knowledge_base/ |
| `DISABLE_GENESIS_TRACKING` | `false` | Disable Genesis Key audit trail |
| `DISABLE_CONTINUOUS_LEARNING` | `false` | Disable background learning |
| `LIGHTWEIGHT_MODE` | `false` | Minimal startup (testing) |

### Error Suppression

| Variable | Default | Description |
|----------|---------|-------------|
| `SUPPRESS_INGESTION_ERRORS` | `false` | Suppress ingestion errors |
| `SUPPRESS_GENESIS_ERRORS` | `false` | Suppress genesis tracking errors |
| `SUPPRESS_QDRANT_ERRORS` | `false` | Suppress Qdrant errors |
| `SUPPRESS_EMBEDDING_ERRORS` | `false` | Suppress embedding errors |

---

## 13. Where to Find Things (Quick Reference)

| "I need to..." | Look here |
|-----------------|-----------|
| Add a new API endpoint | `backend/api/` (create file, register in `app.py`) |
| Change how chat responses work | `backend/app.py` (chat endpoint) + `backend/retrieval/` |
| Modify the frontend UI | `frontend/src/components/` |
| Add a new frontend tab | `frontend/src/App.jsx` + new component |
| Change database schema | `backend/models/database_models.py` + `backend/database/migration.py` |
| Modify document ingestion | `backend/ingestion/service.py` |
| Change embedding model | `backend/settings.py` (`EMBEDDING_DEFAULT`) + `backend/embedding/` |
| Fix Genesis Key tracking | `backend/genesis/` |
| Modify cognitive engine | `backend/cognitive/engine.py` |
| Update VSCode extension | `grace-os-vscode/src/` |
| Add a Kubernetes config | `k8s/` |
| Modify CI/CD | `.github/workflows/` or `pipelines/` |
| Change security settings | `backend/security/` |
| Update LLM configuration | `backend/ollama_client/client.py` + `backend/settings.py` |
| Modify search behavior | `backend/search/` + `backend/retrieval/` |
| Change vector DB settings | `backend/vector_db/client.py` + `backend/settings.py` |
| Add a web scraping feature | `backend/scraping/` |
| Understand how systems communicate | `backend/layer1/` (message bus) |

---

## 14. Common Tasks for New Developers

### Task 1: Add a New API Endpoint

1. Create a new file in `backend/api/`, e.g., `my_feature_api.py`
2. Define a FastAPI router:
   ```python
   from fastapi import APIRouter
   router = APIRouter(prefix="/my-feature", tags=["My Feature"])

   @router.get("/status")
   async def get_status():
       return {"status": "ok"}
   ```
3. Register it in `backend/app.py`:
   ```python
   from api.my_feature_api import router as my_feature_router
   app.include_router(my_feature_router)
   ```
4. Test: `curl http://localhost:8000/my-feature/status`

### Task 2: Add a New Frontend Tab

1. Create `frontend/src/components/MyFeatureTab.jsx` and `MyFeatureTab.css`
2. Import and add it to `frontend/src/App.jsx`:
   ```jsx
   import MyFeatureTab from "./components/MyFeatureTab";
   // In the sidebar nav, add a button
   // In the main content, add: {activeTab === "my-feature" && <MyFeatureTab />}
   ```

### Task 3: Modify How Documents Are Ingested

1. Core logic: `backend/ingestion/service.py`
2. File handling: `backend/file_manager/file_handler.py`
3. API endpoint: `backend/api/file_ingestion.py`
4. Auto-ingestion on startup: `backend/app.py` (see `run_auto_ingestion()`)

### Task 4: Change the LLM Model

1. Pull the model in Ollama: `ollama pull llama3:8b`
2. Update `backend/.env`: `OLLAMA_LLM_DEFAULT=llama3:8b`
3. Restart the backend

### Task 5: Run Tests

```bash
# Backend tests
cd backend
python -m pytest tests/ -v

# Frontend lint
cd frontend
npm run lint

# VSCode extension tests
cd grace-os-vscode
npm run test:all
```

---

## 15. Glossary

| Term | Meaning |
|------|---------|
| **Genesis Key** | An audit record tracking what/where/when/who/how/why for every operation |
| **OODA Loop** | Observe-Orient-Decide-Act -- Grace's cognitive decision cycle |
| **RAG** | Retrieval-Augmented Generation -- answering questions using retrieved document context |
| **Memory Mesh** | Grace's multi-layered memory system (episodic, procedural, semantic, magma) |
| **Magma Memory** | Deep, consolidated long-term memory with relationship graphs |
| **Layer 1** | The internal message bus connecting all subsystems |
| **Multi-Tier** | The fallback system: VectorDB -> Model Knowledge -> User Context |
| **Trust Score** | 0.0-1.0 score indicating how reliable a piece of knowledge is |
| **Qdrant** | Open-source vector database used for embedding storage and search |
| **Ollama** | Local LLM runtime (runs models like Mistral, Llama locally) |
| **Sandbox** | Safe execution environment for experiments |
| **Mirror** | Grace's self-observation system for detecting patterns and improving |
| **Ghost Ledger** | Line-by-line change tracking in the VSCode extension |
| **Cognitive Blueprint** | The 12 invariant rules that govern Grace's decision-making |
| **Librarian** | Document categorization, tagging, and relationship detection system |
| **Diagnostic Machine** | 4-layer self-diagnostic system (sensors, interpreters, judgement, action) |
| **Neuro-Symbolic** | Combining neural networks (pattern matching) with symbolic AI (logic rules) |
| **Whitelist** | Human-approved knowledge entries that feed into Grace's learning |
| **KPI** | Key Performance Indicators tracked across the system |

---

## Getting Help

- **API Documentation**: `http://localhost:8000/docs` (Swagger UI, auto-generated)
- **Architecture docs**: `docs/ARCHITECTURE/` directory
- **Existing documentation**: See the many `*.md` files in the repo root
- **Key reference docs**:
  - `COGNITIVE_BLUEPRINT.md` -- How Grace thinks (12 core invariants)
  - `GRACE_NEUROSYMBOLIC_ARCHITECTURE.md` -- Neural + Symbolic design
  - `COMPLETE_SYSTEM_SUMMARY.md` -- Full system capabilities
  - `DEPLOYMENT_GUIDE.md` -- Production deployment
  - `SETUP_GUIDE.md` -- Setup instructions

---

*This document was created to give you a structured path into the Grace codebase. Start with the high-level architecture, explore the backend subsystems that interest you, and use the quick reference table to find things fast. Welcome to the team.*
