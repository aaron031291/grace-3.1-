# GRACE System Unification Plan
## Full Diagnostic: What Works, What's Broken, What's Disconnected, and How to Unify It All

**Date**: February 16, 2026
**Branch**: `cursor/system-unification-plan-4a17`
**Total Backend Python Files**: 415
**Total Test Files**: 63
**Total Frontend Components**: 51
**Total API Routers**: 50

---

## TABLE OF CONTENTS

1. [System Architecture Overview](#1-system-architecture-overview)
2. [What IS Working](#2-what-is-working)
3. [What IS NOT Working (and Why)](#3-what-is-not-working-and-why)
4. [What's Connected vs Disconnected](#4-whats-connected-vs-disconnected)
5. [The Root Causes](#5-the-root-causes)
6. [Unification Plan: Making It One Organism](#6-unification-plan-making-it-one-organism)
7. [Execution Order](#7-execution-order)

---

## 1. SYSTEM ARCHITECTURE OVERVIEW

Grace is designed as a multi-layered AI system with the following major subsystems:

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React/Vite)                        │
│  51 UI components across 22+ tabs (Chat, Governance, Sandbox...)   │
│  State: Zustand stores (Chat, Auth, UI, System, Preferences)       │
│  API Client: api.js → http://localhost:8000                        │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTP/WebSocket/SSE
┌──────────────────────────────▼──────────────────────────────────────┐
│                     BACKEND (FastAPI on :8000)                       │
│  app.py → 50 API routers registered                                 │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    CORE INFRASTRUCTURE                        │   │
│  │  Database (SQLAlchemy/SQLite)  │  Settings  │  Security      │   │
│  │  Logging  │  Genesis Middleware │  CORS/Rate Limiting         │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                     LAYER 1: MESSAGE BUS                     │   │
│  │  Pub/Sub │ Request/Response │ Autonomous Actions              │   │
│  │  11 Component Types │ Event-Driven Architecture               │   │
│  │  STATUS: EXISTS BUT NOT INITIALIZED IN app.py                │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐               │
│  │  COGNITIVE    │ │  MEMORY      │ │  RETRIEVAL   │               │
│  │  Engine/OODA  │ │  Magma/Mesh  │ │  RAG/Tiers   │               │
│  │  Decisions    │ │  Graphs      │ │  Trust-Aware  │               │
│  │  Invariants   │ │  Relations   │ │  Reranker     │               │
│  └──────────────┘ └──────────────┘ └──────────────┘               │
│                                                                     │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐               │
│  │  DIAGNOSTIC   │ │  GENESIS     │ │  ML INTEL    │               │
│  │  4-Layer      │ │  Keys/Track  │ │  Neural Trust│               │
│  │  Sensors      │ │  Version Ctrl│ │  Bandits     │               │
│  │  Interpreters │ │  CI/CD       │ │  Meta-Learn  │               │
│  │  Judgement    │ │  Pipelines   │ │  Neuro-Symb  │               │
│  │  Action Route │ │  File Watch  │ │  Contrastive │               │
│  └──────────────┘ └──────────────┘ └──────────────┘               │
│                                                                     │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐               │
│  │  SERVICES     │ │  EXECUTION   │ │  LLM ORCH    │               │
│  │  Integration  │ │  Bridge      │ │  Multi-LLM   │               │
│  │  Autonomous   │ │  Governed    │ │  Halluc Guard│               │
│  │  Team Mgmt    │ │  Feedback    │ │  Collab      │               │
│  └──────────────┘ └──────────────┘ └──────────────┘               │
│                                                                     │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐               │
│  │  AGENT       │ │  INGESTION   │ │  SCRAPING    │               │
│  │  Grace Agent  │ │  Text/File   │ │  URL/Crawler │               │
│  │  Sub-Agents   │ │  Auto-Ingest │ │  Trafilatura │               │
│  └──────────────┘ └──────────────┘ └──────────────┘               │
└─────────────────────────────────────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                       EXTERNAL SERVICES                              │
│  Ollama (:11434)  │  Qdrant (:6333)  │  SerpAPI  │  PostgreSQL    │
│  Redis (optional)  │  Git/GitHub                                    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. WHAT IS WORKING

These modules import and function correctly at the code/logic level:

| Module | Status | Notes |
|--------|--------|-------|
| `cognitive/engine.py` | **WORKS** | OODA loop, invariants, decision engine - pure Python logic |
| `cognitive/magma/` (10 files) | **WORKS** | Relation graphs, intent router, RRF fusion, causal inference - all pure Python |
| `cognitive/ooda.py` | **WORKS** | OODA loop implementation |
| `cognitive/ambiguity.py` | **WORKS** | Ambiguity ledger |
| `cognitive/invariants.py` | **WORKS** | Invariant validator |
| `cognitive/decision_log.py` | **WORKS** | Decision logger |
| `cognitive/continuous_learning_orchestrator.py` | **WORKS** | Continuous learning loop (threaded) |
| `cognitive/mirror_self_modeling.py` | **WORKS** | Self-modeling |
| `layer1/message_bus.py` | **WORKS** | Pub/Sub, Request/Response, Autonomous Actions |
| `core/registry.py` | **WORKS** | Component registry with lifecycle management |
| `core/base_component.py` | **WORKS** | Base component class |
| `agent/grace_agent.py` | **WORKS** | Grace agent framework |
| `services/grace_systems_integration.py` | **WORKS** | Systems integration service |
| `services/grace_autonomous_engine.py` | **WORKS** | Autonomous engine |
| `security/config.py` | **WORKS** | Security configuration |
| `embedding/__init__.py` | **WORKS** | Embedding model loader (lazy) |
| `ollama_client/client.py` | **WORKS** | Ollama HTTP client |
| `logging_config.py` | **WORKS** | Logging setup |

**Summary**: ~30% of core logic modules work as standalone Python. These are the "brain" components that don't depend on heavy external libraries.

---

## 3. WHAT IS NOT WORKING (AND WHY)

### 3A. MISSING PYTHON DEPENDENCIES (CRITICAL)

**Every single API router (all 50) fails to import** because core dependencies are not installed:

| Missing Package | Blocks | Impact |
|----------------|--------|--------|
| `fastapi` | ALL 50 API routers | **Entire backend API cannot start** |
| `starlette` | Security middleware, Genesis middleware | No security layer |
| `sqlalchemy` | Database (session, connection, models, migration) | No data persistence |
| `python-dotenv` | Settings, LLM Orchestrator | No config loading |
| `qdrant-client` | Vector DB, Ingestion, Retriever, RAG | No vector search, no document storage |
| `torch` | ML Intelligence (15 modules) | No neural trust, no neuro-symbolic |
| `trafilatura` | SerpAPI/Web scraping | No web research |
| `sentence-transformers` | Embedding model (production) | No embedding generation |
| `pydantic` | ALL request/response models | No data validation |

**Root cause**: `requirements.txt` lists packages but `pip install` was never run. The system requires a Python virtual environment with all 79 dependencies installed.

### 3B. FRONTEND NOT BUILT

| Issue | Impact |
|-------|--------|
| `node_modules/` missing | Frontend cannot build or run |
| `zustand` not in `package.json` | Store module imports `zustand` but it's not declared as a dependency |
| No `package-lock.json` | Dependency versions not locked |
| `nginx.conf` exists but never tested | Production deployment untested |

### 3C. MODULES THAT EXIST BUT ARE NEVER CALLED

These are fully implemented modules that **nobody calls** from the main application:

| Module | What It Does | Why It's Disconnected |
|--------|-------------|----------------------|
| `layer1/initialize.py` → `initialize_layer1()` | Initializes ALL Layer 1 components, connects message bus, creates connectors | **Never called from `app.py` lifespan** |
| `core/registry.py` → `get_component_registry()` | Central component registry with lifecycle management | **Never used anywhere except tests** |
| `cognitive/magma/` → `get_grace_magma()` | Unified memory system (Magma) | **Only used in `ide_bridge_api.py`, not in main app** |
| `services/grace_systems_integration.py` | Connects Planning/Todos to all subsystems | **Only used in test files** |
| `services/grace_autonomous_engine.py` | Autonomous task execution | **Only used in test files** |
| `services/grace_team_management.py` | Sub-agent team management | **Only used in test files** |
| `diagnostic_machine/diagnostic_engine.py` | 4-layer diagnostic orchestrator | **API router registered but engine never initialized** |
| `execution/governed_bridge.py` | Governed execution with governance checks | **Never called from any API** |
| `cognitive/active_learning_system.py` | Active learning | **Exists but no integration point** |
| `cognitive/autonomous_healing_system.py` | Self-healing | **Exists but not wired to diagnostic machine** |

---

## 4. WHAT'S CONNECTED VS DISCONNECTED

### 4A. WHAT IS ACTUALLY CONNECTED (end-to-end)

These pathways work when dependencies are installed:

```
Frontend ChatTab → POST /chat → app.py → multi_tier_integration → retriever → Qdrant
Frontend ChatTab → POST /chats/{id}/prompt → app.py → conversation history → multi_tier → Qdrant
Frontend RAGTab → POST /ingest → ingest_router → ingestion service → Qdrant
Frontend → GET /health → Ollama health check
Frontend → CRUD /chats → Database (SQLAlchemy)
Frontend → Genesis Keys → genesis_key_service → Database
File Watcher → genesis/file_watcher → auto-tracking (background thread)
Auto-Ingestion → file_manager → scan_directory → Qdrant (background thread)
Continuous Learning → cognitive/continuous_learning_orchestrator (background thread)
```

### 4B. WHAT IS DISCONNECTED

#### The Layer 1 Message Bus is an Orphan
The message bus (`layer1/message_bus.py`) is the centerpiece of the architecture. It has:
- 11 component types defined
- Pub/Sub system
- Request/Response system
- Autonomous action triggers
- 9 connectors written (memory mesh, genesis keys, RAG, ingestion, LLM orchestration, version control, neuro-symbolic, knowledge base, data integrity)

**BUT**: `initialize_layer1()` is never called from `app.py`. The message bus is created as a singleton but no components ever register with it. Result: **the entire nervous system of the application sits idle**.

#### The Component Registry is Unused
`core/registry.py` implements a full component lifecycle manager with:
- Registration, discovery by role/capability/tag
- Dependency-aware startup/shutdown
- Health monitoring
- Message bus integration

**BUT**: Not a single component is ever registered. The registry exists but manages nothing.

#### Magma Memory is Isolated
`cognitive/magma/` is a sophisticated memory system with:
- 4 relation graphs (Semantic, Temporal, Causal, Entity)
- Intent-aware query routing
- RRF fusion
- Causal inference
- Layer integrations (Layers 1-4)

**BUT**: `get_grace_magma()` is only called from `ide_bridge_api.py`. The main chat endpoint doesn't use Magma. The layer integrations are never activated.

#### Services Are Test-Only
`services/grace_systems_integration.py`, `grace_autonomous_engine.py`, `grace_team_management.py` are complete integration services but they are **only imported in test files**. No API router or startup code uses them.

#### Diagnostic Machine Has No Brain
The diagnostic machine has a full 4-layer architecture:
- Sensors → Interpreters → Judgement → Action Router
- The `diagnostic_engine.py` orchestrates all layers

**BUT**: The API (`diagnostic_machine/api.py`) is registered as a router, but the `DiagnosticEngine` is never instantiated in `app.py`'s lifespan. The diagnostic API creates its own instances per-request instead of sharing a running engine.

#### Cognitive Engine is Headless
`cognitive/engine.py` implements the Central Cortex (OODA loops, invariants, decisions). **BUT**: Nothing in the main application initializes it or feeds it decisions. The cognitive tab in the frontend calls `/cognitive/*` endpoints, but these are thin wrappers that don't leverage the full engine.

#### Execution Bridge Goes Nowhere
`execution/bridge.py` and `execution/governed_bridge.py` handle executing actions with governance checks. **BUT**: No API router calls them. The agent (`agent/grace_agent.py`) has its own execution logic that doesn't use the governed bridge.

#### Frontend WebSocket/SSE Never Connects
- `api/websocket.py` and `api/streaming.py` exist as routers
- The frontend has WebSocket code in 4 components (GracePlanningTab, APITab, IngestionDashboard, GraceTodosTab)
- **BUT**: There's no shared WebSocket connection manager in the frontend. Each component independently creates connections. The `useSystemStore` tracks `wsConnected` but nothing sets it.

#### Frontend Missing Dependency
The store (`frontend/src/store/index.js`) imports `zustand` but it's not listed in `package.json` dependencies. The store won't work without it.

---

## 5. THE ROOT CAUSES

### Root Cause 1: No Dependency Installation Pipeline
The `requirements.txt` file lists packages without versions (except `filelock==3.13.1`). There's a `Dockerfile` that runs `pip install` but no local setup script. Nobody ran `pip install -r requirements.txt` in the current environment.

### Root Cause 2: No Unified Startup Orchestrator
`app.py` does these things at startup:
1. Database init ✓
2. Embedding model preload ✓
3. Ollama health check ✓
4. Qdrant health check ✓
5. File watcher (background thread) ✓
6. ML Intelligence init ✓
7. Auto-ingestion (background thread) ✓
8. Continuous learning (background thread) ✓

What it does NOT do:
- Initialize Layer 1 Message Bus and register components
- Initialize Component Registry
- Initialize Magma Memory
- Initialize Diagnostic Engine
- Initialize Cognitive Engine (Central Cortex)
- Initialize Services (Systems Integration, Autonomous Engine)
- Initialize Execution Bridge
- Connect subsystems to each other

### Root Cause 3: Subsystems Built in Isolation
Each subsystem was developed as a standalone module:
- Cognitive engine doesn't know about the message bus
- Diagnostic machine doesn't know about Magma memory
- The agent doesn't use the governed execution bridge
- ML Intelligence doesn't feed into the cognitive engine
- Services integration exists but nothing triggers its events

### Root Cause 4: No Shared Event/State Architecture
Despite the message bus existing, there is no shared event flow:
- When a document is ingested, Magma should learn from it
- When the diagnostic machine detects an issue, the healing system should respond
- When the agent makes a decision, it should go through the cognitive engine
- When ML Intelligence updates trust scores, the retriever should reflect them

None of these event flows are wired.

### Root Cause 5: Frontend Has No Real-Time Connection
The frontend polls `/health` every 30 seconds. It has WebSocket code scattered in individual components but:
- No central WebSocket manager
- No event bus on the frontend
- No real-time push from backend to frontend
- System health doesn't reflect actual subsystem status

---

## 6. UNIFICATION PLAN: MAKING IT ONE ORGANISM

### Phase 1: Foundation (Get It Running)

**Goal**: Make the system startable and functional end-to-end.

#### 1.1 Pin and Install Dependencies
```bash
# Backend: Create proper requirements with versions
pip install fastapi uvicorn sqlalchemy python-dotenv qdrant-client \
    pydantic sentence-transformers torch trafilatura aiohttp \
    python-multipart websockets httpx requests PyYAML \
    scikit-learn scipy psutil watchdog schedule

# Frontend: Add missing dependency and install
cd frontend
npm install zustand
npm install
```

#### 1.2 Create Local Setup Script
Create `setup.sh` that:
- Creates Python venv
- Installs backend dependencies
- Installs frontend dependencies
- Creates `.env` from `.env.example`
- Creates data directories
- Runs database migrations

#### 1.3 Verify Basic Startup
- `app.py` starts without import errors
- `/health` endpoint responds
- `/docs` shows all 50 routers
- Frontend builds and loads
- Frontend connects to backend

---

### Phase 2: Wire the Nervous System (Layer 1 Message Bus)

**Goal**: Connect all subsystems through the message bus so they can communicate.

#### 2.1 Add Layer 1 Initialization to app.py Lifespan
```python
# In app.py lifespan, AFTER database and services are ready:
from layer1.initialize import initialize_layer1

layer1_system = initialize_layer1(
    session=session,
    kb_path=settings.KNOWLEDGE_BASE_PATH,
    enable_neuro_symbolic=True,
    enable_knowledge_base=True,
)
```

#### 2.2 Register Core Components with Component Registry
```python
from core.registry import get_component_registry
registry = get_component_registry()
registry.set_message_bus(layer1_system.message_bus)

# Register all major subsystems as components
# Each gets a BaseComponent wrapper with health checks
```

#### 2.3 Connect Magma Memory to the Message Bus
```python
from cognitive.magma import get_grace_magma, create_magma_layer_integrations

magma = get_grace_magma()
magma_integrations = create_magma_layer_integrations(magma, message_bus)
```

#### 2.4 Wire the Diagnostic Engine
```python
from diagnostic_machine.diagnostic_engine import DiagnosticEngine

diagnostic_engine = DiagnosticEngine()
# Register sensors that pull from message bus events
# Connect action router to the execution bridge
```

---

### Phase 3: Create Event Flows (The Circulatory System)

**Goal**: Define the event flows that make subsystems react to each other.

#### 3.1 Ingestion → Learning Flow
```
Document uploaded → Ingestion Service → MESSAGE_BUS("ingestion.complete")
  → Magma Memory (index in relation graphs)
  → Learning Memory (extract patterns)
  → Genesis Keys (track provenance)
  → Continuous Learning (trigger learning cycle)
```

#### 3.2 Query → Intelligence Flow
```
User query → Multi-Tier Handler → MESSAGE_BUS("query.started")
  → Magma Memory (intent-aware retrieval)
  → Trust Scorer (filter by trust)
  → Cognitive Engine (apply invariants)
  → LLM Orchestrator (generate response)
  → MESSAGE_BUS("query.complete")
  → Learning Memory (learn from interaction)
```

#### 3.3 Diagnostic → Healing Flow
```
Diagnostic heartbeat (60s) → Sensors collect data → MESSAGE_BUS("diagnostic.scan")
  → Interpreters (pattern analysis) → MESSAGE_BUS("diagnostic.interpreted")
  → Judgement (decision) → MESSAGE_BUS("diagnostic.judgement")
  → Action Router → Governed Bridge → Execute action
  → MESSAGE_BUS("healing.executed")
  → Magma Memory (store healing pattern)
```

#### 3.4 Agent → Execution Flow
```
Agent receives task → Cognitive Engine (evaluate via OODA)
  → MESSAGE_BUS("agent.decision")
  → Governed Bridge (governance check)
  → Execute action
  → MESSAGE_BUS("agent.executed")
  → Feedback → Learning Memory
```

---

### Phase 4: Unify the Frontend (The Skin)

**Goal**: Create a single, coherent frontend experience with real-time updates.

#### 4.1 Add Missing Dependencies
```json
{
  "dependencies": {
    "zustand": "^4.5.0"
  }
}
```

#### 4.2 Create Central WebSocket Manager
```javascript
// src/services/websocket.js
class GraceWebSocket {
  connect() { /* single persistent connection to backend */ }
  subscribe(event, handler) { /* event-based subscriptions */ }
  send(event, data) { /* send events to backend */ }
}
```

#### 4.3 Connect System Store to Real Backend Health
```javascript
// Poll /api/system/health which returns ALL subsystem statuses
// Update useSystemStore.services with real data
// Show health in header (not just Ollama status)
```

#### 4.4 Wire Frontend Tabs to Backend Events
- Chat: Real-time streaming via SSE
- Monitoring: Live diagnostic data via WebSocket
- Cognitive: Live decision feed
- Sandbox: Live experiment status

---

### Phase 5: Create the Unified Startup (The Heartbeat)

**Goal**: Single startup sequence that brings all systems online in the right order.

#### 5.1 Startup Sequence (Order Matters)

```
1. Load Settings & Environment
2. Initialize Database & Run Migrations
3. Initialize Component Registry
4. Initialize Layer 1 Message Bus
5. Initialize Magma Memory System
6. Initialize Cognitive Engine (Central Cortex)
7. Connect to Qdrant (Vector DB)
8. Connect to Ollama (LLM)
9. Pre-load Embedding Model
10. Initialize Ingestion Service
11. Initialize Retrieval System (Trust-Aware)
12. Initialize ML Intelligence
13. Initialize LLM Orchestrator
14. Initialize Diagnostic Engine (4-Layer)
15. Initialize Agent Framework
16. Initialize Governed Execution Bridge
17. Initialize Services (Systems Integration)
18. Register ALL components with Registry
19. Wire ALL event flows through Message Bus
20. Start Background Workers:
    a. File Watcher
    b. Auto-Ingestion
    c. Continuous Learning
    d. Diagnostic Heartbeat (60s)
21. Start API server (FastAPI/Uvicorn)
22. Component Registry → start_all() → health_check_all()
```

#### 5.2 Graceful Shutdown Sequence

```
1. Stop accepting new requests
2. Complete in-flight requests
3. Stop background workers
4. Component Registry → stop_all() (reverse priority order)
5. Close database connections
6. Close Qdrant connection
7. Log final state
```

---

### Phase 6: Make It Observable (The Nervous Feedback)

**Goal**: Full observability so you can see the organism working.

#### 6.1 Unified Health Endpoint
```
GET /api/system/health → {
  "overall": "healthy",
  "score": 0.95,
  "components": {
    "database": {"status": "active", "latency_ms": 2},
    "qdrant": {"status": "active", "collections": 3},
    "ollama": {"status": "active", "models": 2},
    "message_bus": {"status": "active", "messages_total": 1523},
    "magma_memory": {"status": "active", "nodes": 45000},
    "cognitive_engine": {"status": "active", "decisions": 89},
    "diagnostic_engine": {"status": "active", "last_scan": "2s ago"},
    "agent": {"status": "idle"},
    "ingestion": {"status": "active", "queued": 0},
    "ml_intelligence": {"status": "active", "trust_scores": 12000}
  }
}
```

#### 6.2 Event Stream Dashboard
Real-time view of events flowing through the message bus, showing which components are talking to each other.

---

## 7. EXECUTION ORDER

### Immediate (Day 1-2): Get It Running
- [ ] Install all Python dependencies (backend)
- [ ] Add `zustand` to `package.json` and install frontend deps
- [ ] Create `setup.sh` for local development
- [ ] Verify `app.py` starts without errors
- [ ] Verify frontend builds and connects to backend
- [ ] Pin dependency versions in `requirements.txt`

### Week 1: Wire the Nervous System
- [ ] Add `initialize_layer1()` call to `app.py` lifespan
- [ ] Add `get_component_registry()` initialization to `app.py` lifespan
- [ ] Add `get_grace_magma()` initialization to `app.py` lifespan
- [ ] Add `DiagnosticEngine` initialization to `app.py` lifespan
- [ ] Initialize Cognitive Engine (Central Cortex) in `app.py` lifespan
- [ ] Connect `services/grace_systems_integration.py` to main app
- [ ] Verify all 11 message bus components register successfully

### Week 2: Create Event Flows
- [ ] Wire Ingestion → Learning flow through message bus
- [ ] Wire Query → Intelligence flow (Magma + Trust + Cognitive)
- [ ] Wire Diagnostic → Healing flow
- [ ] Wire Agent → Governed Execution flow
- [ ] Test event propagation end-to-end

### Week 3: Unify Frontend
- [ ] Install `zustand`, verify stores work
- [ ] Create central WebSocket manager
- [ ] Connect System Store to real health endpoint
- [ ] Add real-time event subscriptions to key tabs
- [ ] Test frontend ↔ backend WebSocket communication

### Week 4: Polish and Observe
- [ ] Create unified `/api/system/health` endpoint
- [ ] Create event stream dashboard (monitoring tab)
- [ ] Run full integration test suite
- [ ] Document the unified architecture
- [ ] Load test the connected system

---

## APPENDIX A: COMPLETE FILE MAP

### Backend Modules (by subsystem)

| Subsystem | Files | Status |
|-----------|-------|--------|
| `api/` | 50 routers | All fail (missing fastapi) |
| `cognitive/` | 31 files | Core logic works, not wired |
| `cognitive/magma/` | 10 files | Works standalone, not initialized |
| `genesis/` | 29 files | Partially connected (file watcher, middleware) |
| `layer1/` | 14 files | Message bus works, never initialized |
| `diagnostic_machine/` | 12 files | Engine exists, not instantiated |
| `ml_intelligence/` | 15 files | All fail (missing torch) |
| `llm_orchestrator/` | 9 files | Fails (missing dotenv) |
| `retrieval/` | 7 files | Fails (missing qdrant-client) |
| `database/` | 16 files | Fails (missing sqlalchemy) |
| `models/` | Multiple | Fails (missing sqlalchemy) |
| `security/` | 7 files | Config works, middleware fails (starlette) |
| `services/` | 3 files | Works standalone, test-only usage |
| `execution/` | 5 files | Works standalone, never called |
| `agent/` | 2 files | Works standalone, not connected |
| `ingestion/` | Multiple | Fails (missing qdrant-client) |
| `embedding/` | Multiple | Lazy loader works, model needs torch |
| `scraping/` | 5 files | Fails (missing trafilatura) |
| `search/` | Multiple | Fails (missing trafilatura) |
| `core/` | 4 files | Works, never used in production |
| `vector_db/` | Multiple | Fails (missing qdrant-client) |

### Frontend Components (by tab)

| Tab | Component | Backend Endpoint |
|-----|-----------|-----------------|
| Chat | ChatTab, ChatList, ChatWindow, DirectoryChat | `/chat`, `/chats`, `/chats/{id}/prompt` |
| Governance | GovernanceTab | `/governance` |
| Sandbox | SandboxTab | `/sandbox` |
| Insights | InsightsTab | Multiple |
| Code Base | CodeBaseTab, FileBrowser | `/codebase` |
| Documents | RAGTab, IngestionDashboard | `/ingest`, `/retrieve` |
| Research | ResearchTab, WebScraper, SearchInternetButton | `/scrape` |
| APIs | APITab | `/` (API docs) |
| Librarian | LibrarianTab | `/librarian` |
| Cognitive | CognitiveTab | `/cognitive` |
| Monitoring | MonitoringTab | `/monitoring`, `/diagnostics` |
| Version Control | VersionControl + 4 sub-components | `/api/version-control` |
| Orchestration | OrchestrationTab | `/llm` |
| ML Intelligence | MLIntelligenceTab | `/ml-intelligence` |
| Experiment | ExperimentTab | `/sandbox` |
| Genesis Keys | GenesisKeyTab, GenesisKeyPanel, GenesisLogin | `/genesis` |
| Learning | LearningTab | `/learning-memory`, `/training` |
| Whitelist | WhitelistTab | `/whitelist` |
| Connectors | ConnectorsTab | `/knowledge-base` |
| Telemetry | TelemetryTab | `/telemetry` |
| Notion/Tasks | NotionTab | `/notion` |
| Todos | GraceTodosTab | `/grace-todos` |
| Planning | GracePlanningTab | `/grace-planning` |
| KPI | KPIDashboard | `/kpi` |
| Voice | PersistentVoicePanel, VoiceButton | `/voice` |
| Repository | RepositoryManager | `/repositories` |
| CI/CD | CICDDashboard | `/cicd` |

---

## APPENDIX B: THE ORGANISM METAPHOR

When unified, Grace should function like a living organism:

| Body Part | Grace Equivalent | Current State |
|-----------|-----------------|---------------|
| **Nervous System** | Layer 1 Message Bus | Built but disconnected |
| **Brain** | Cognitive Engine + Magma Memory | Built but isolated |
| **Immune System** | Diagnostic Machine + Healing | Built but not running |
| **Eyes/Ears** | Ingestion + Scraping + Sensors | Partially working |
| **Mouth** | LLM Orchestrator + Chat API | Working (when deps installed) |
| **Skeleton** | Database + Models + Settings | Needs dependencies |
| **Muscles** | Execution Bridge + Agent | Built but unused |
| **DNA** | Genesis Keys + Version Control | Partially connected |
| **Learning** | ML Intelligence + Continuous Learning | ML needs torch |
| **Skin** | Frontend UI | Needs zustand + npm install |
| **Blood** | Events flowing through Message Bus | No flow exists yet |
| **Heart** | Startup Orchestrator | Incomplete - most organs not started |

**The organism has all its organs built, but they've never been connected to the circulatory system (message bus), the heart barely pumps (startup only initializes ~40% of systems), and the nervous system (event flows) has never fired a signal.**

The unification plan above connects every organ, starts the heart, and gets the blood flowing.
