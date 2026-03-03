# GraceOS Complete System Breakdown — Developer Handover

**Branch:** `Aaron-new2`
**Date:** 2026-03-03
**Purpose:** Full architectural decomposition of the GraceOS system for new developer onboarding

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Tech Stack](#2-tech-stack)
3. [Repository Structure](#3-repository-structure)
4. [Chunk 1: Backend — FastAPI Core](#chunk-1-backend--fastapi-core)
5. [Chunk 2: Brain API — The Nervous System](#chunk-2-brain-api--the-nervous-system)
6. [Chunk 3: GraceOS 9-Layer Kernel](#chunk-3-graceos-9-layer-kernel)
7. [Chunk 4: Cognitive Engine](#chunk-4-cognitive-engine)
8. [Chunk 5: MAGMA Memory System](#chunk-5-magma-memory-system)
9. [Chunk 6: Diagnostic Machine](#chunk-6-diagnostic-machine)
10. [Chunk 7: ML Intelligence](#chunk-7-ml-intelligence)
11. [Chunk 8: Genesis Key System](#chunk-8-genesis-key-system)
12. [Chunk 9: Scale Infrastructure (Aaron-new2)](#chunk-9-scale-infrastructure-aaron-new2)
13. [Chunk 10: Frontend — React UI](#chunk-10-frontend--react-ui)
14. [Chunk 11: VSCode Extension](#chunk-11-vscode-extension)
15. [Chunk 12: MCP Servers](#chunk-12-mcp-servers)
16. [Chunk 13: Infrastructure & DevOps](#chunk-13-infrastructure--devops)
17. [Chunk 14: Database Layer](#chunk-14-database-layer)
18. [Chunk 15: Security](#chunk-15-security)
19. [Data Flow Diagrams](#data-flow-diagrams)
20. [File Index](#file-index)

---

## 1. System Overview

**GRACE** = Genesis-driven RAG Autonomous Cognitive Engine

GraceOS is a self-evolving AI platform built around Retrieval-Augmented Generation with autonomous cognitive capabilities. It is a full-stack system (Python backend + React frontend + VSCode extension) that can:

- Chat with users using multi-model LLM orchestration (Kimi, Qwen, DeepSeek, Claude)
- Ingest, index, and retrieve documents using vector search (Qdrant)
- Autonomously learn from interactions and self-heal
- Track full provenance of every operation via Genesis Keys
- Run an 8-layer coding pipeline that writes, tests, and deploys code
- Execute a 4-layer diagnostic machine for self-monitoring
- Enforce governance rules and constitutional AI principles
- Manage projects, files, tasks, and CI/CD pipelines

---

## 2. Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.11+, FastAPI, SQLAlchemy, Qdrant, PyTorch, sentence-transformers |
| **Frontend** | React 19, Vite (rolldown), Material UI 7, Zustand, Axios |
| **VSCode Extension** | TypeScript, VSCode API |
| **LLMs** | Ollama (Qwen 2.5, DeepSeek R1 — local), Kimi K2.5 (cloud), Claude (cloud) |
| **Vector DB** | Qdrant (local or cloud) |
| **Relational DB** | SQLite (default), PostgreSQL (production) |
| **Infra** | Docker, Docker Compose, Kubernetes |
| **MCP** | Model Context Protocol servers (Git, Filesystem, Memory, etc.) |

---

## 3. Repository Structure

```
/workspace
├── backend/                  # Python FastAPI backend (THE CORE)
│   ├── app.py                # FastAPI entry point (~1900 lines)
│   ├── settings.py           # Central configuration
│   ├── api/                  # API routers (20+ modules)
│   ├── core/                 # Core services, worker pool, security, memory
│   ├── cognitive/            # Cognitive engine (70+ files)
│   ├── grace_os/             # 9-layer kernel
│   ├── diagnostic_machine/   # 4-layer diagnostic system
│   ├── ml_intelligence/      # Neural trust, meta-learning
│   ├── genesis/              # Genesis Key tracking (30 files)
│   ├── database/             # SQLAlchemy, sessions, migrations
│   ├── models/               # ORM data models
│   ├── retrieval/            # RAG retrieval
│   ├── ingestion/            # Document ingestion
│   ├── embedding/            # Embedding models
│   ├── vector_db/            # Qdrant client
│   ├── agent/                # Software engineering agent
│   ├── grace_mcp/            # MCP orchestrator
│   ├── execution/            # Code execution bridge
│   ├── file_manager/         # File intelligence
│   ├── llm_orchestrator/     # LLM orchestration
│   ├── security/             # Auth, middleware, governance
│   └── mcp_repos/            # MCP server implementations
├── frontend/                 # React 19 SPA
│   ├── src/
│   │   ├── App.jsx           # Root component, view routing
│   │   ├── main.jsx          # Entry point
│   │   ├── components/       # 52 JSX components
│   │   ├── store/            # Zustand state stores
│   │   ├── api/              # API clients
│   │   ├── hooks/            # Custom React hooks
│   │   └── config/           # API configuration
│   ├── package.json
│   └── vite.config.js
├── grace-os-vscode/          # VSCode extension
│   ├── src/
│   │   ├── extension.ts      # Extension entry
│   │   ├── core/             # GraceOSCore, GhostLedger
│   │   ├── panels/           # Dashboard, Chat webviews
│   │   ├── providers/        # Tree data providers
│   │   ├── systems/          # Neural, MAGMA, Diagnostic
│   │   ├── bridges/          # IDE + WebSocket bridges
│   │   └── commands/         # Command registration
│   └── package.json
├── docs/                     # 234+ documentation files
├── tests/                    # Integration tests
├── tools/                    # Maintenance scripts
├── knowledge_base/           # System knowledge docs
├── k8s/                      # Kubernetes manifests
├── pipelines/                # CI/CD definitions
├── monitoring/               # Grafana dashboard
└── docker-compose.yml        # Full-stack orchestration
```

---

## Chunk 1: Backend — FastAPI Core

### 1.1 Entry Point: `backend/app.py`

The main FastAPI application. ~1900 lines. Handles:

| Sub-chunk | What it does |
|-----------|-------------|
| **1.1.1 Lifespan** | Initializes database, Qdrant, embedding model, diagnostic engine, genesis tracker, coding pipeline, autonomous loop, worker pools on startup. Shuts them down on exit. |
| **1.1.2 Router Registration** | Mounts all API routers: brain, health, auth, voice, stream, completion, connection |
| **1.1.3 Runtime Endpoints** | `/api/runtime/*` — model listing, status, hot reload, pause/resume, security, resilience, workers, connectivity |
| **1.1.4 Middleware** | CORS, security headers, rate limiting, request validation, Genesis key tracking |

### 1.2 Settings: `backend/settings.py`

Central configuration loaded from environment variables:
- LLM endpoints (Ollama, Kimi, Claude)
- Database paths and credentials
- Qdrant connection
- Feature flags
- API keys

### 1.3 Core Services: `backend/core/services/`

8 service modules that implement business logic for each brain domain:

| Service | File | Purpose |
|---------|------|---------|
| **ChatService** | `chat_service.py` | Chat CRUD, message handling |
| **FilesService** | `files_service.py` | File operations, uploads |
| **GovernService** | `govern_service.py` | Governance rules, persona |
| **CodeService** | `code_service.py` | Code analysis, generation |
| **DataService** | `data_service.py` | Data operations |
| **ProjectService** | `project_service.py` | Project management, containers |
| **TasksService** | `tasks_service.py` | Task management |
| **SystemService** | `system_service.py` | System operations |

---

## Chunk 2: Brain API — The Nervous System

### 2.1 Architecture

The Brain API is the single entry point for ALL frontend-to-backend communication. Every action in the system routes through it.

```
Frontend → POST /brain/{domain} → { action, payload }
                                        ↓
                              brain_api_v2.py routes to handler
                                        ↓
                              core/services/{domain}_service.py
```

### 2.2 Brain Domains (8 domains, 207+ actions)

| Domain | Actions (sample) | File |
|--------|-----------------|------|
| **chat** | `send`, `history`, `list`, `delete`, `search`, `rename`, `export`, `consensus`, `forensic` | `core/services/chat_service.py` |
| **files** | `list`, `read`, `write`, `delete`, `upload`, `download`, `tree`, `search`, `move` | `core/services/files_service.py` |
| **govern** | `rules`, `add_rule`, `persona`, `compliance`, `approval`, `frameworks` | `core/services/govern_service.py` |
| **ai** | `models`, `status`, `trust`, `train`, `predict`, `embeddings` | Various ML/cognitive |
| **system** | `health`, `metrics`, `trust`, `mine_keys`, `worker_pool`, `llm_cache`, `api_costs`, `memory_pressure`, `db_info` | System-level ops |
| **data** | `ingest`, `retrieve`, `search`, `collections`, `sync` | Ingestion/retrieval |
| **tasks** | `list`, `create`, `update`, `assign`, `complete` | Task management |
| **code** | `analyze`, `generate`, `refactor`, `test`, `pipeline`, `blueprint` | Coding pipeline |

### 2.3 Brain API Files

| File | Purpose |
|------|---------|
| `api/brain_api_v2.py` | WebSocket-based brain router. Routes `{domain}/{action}` to handlers. Builds action directory. |
| `api/core/brain_controller.py` | REST-based brain router at `/api/v2/{domain}/{action}` |
| `api/health_api.py` | `/health` endpoint |
| `api/auth.py` | `/auth/login`, `/auth/logout`, `/auth/session` |
| `api/voice_api.py` | `/voice` WebSocket for voice chat |
| `api/stream_api.py` | `/api/stream` SSE streaming |
| `api/completion_api.py` | `/api/complete` inline code completion |
| `api/connection_api.py` | `/api/connections` connection validation |

### 2.4 Autonomous Loop (Ouroboros)

The system has a background autonomous loop (`api/autonomous_loop_api.py`) that:
1. Scans for triggers (errors, stale data, knowledge gaps)
2. Executes healing, learning, or analysis actions
3. Logs everything via Genesis Keys
4. Runs on a configurable interval

---

## Chunk 3: GraceOS 9-Layer Kernel

**Location:** `backend/grace_os/`

The kernel is organized into three tiers: **Kernel** (infrastructure), **Knowledge** (persistent memory), and **Layers** (9 processing stages).

### 3.1 Kernel Infrastructure

| Sub-chunk | File | Purpose |
|-----------|------|---------|
| **3.1.1 Message Protocol** | `kernel/message_protocol.py` | `LayerMessage` and `LayerResponse` dataclasses — the wire format for all inter-layer communication. Fields: `from_layer`, `to_layer`, `message_type`, `payload`, `trace_id`, `priority`, `max_depth` |
| **3.1.2 Message Bus** | `kernel/message_bus.py` | Central routing with `send()` (point-to-point) and `broadcast()` (fan-out). Exponential-backoff retries (3x, starting at 100ms). Cycle detection via `max_depth`. |
| **3.1.3 Layer Registry** | `kernel/layer_registry.py` | Dynamic discovery. Each layer registers on `start()` with its `capabilities` and `status` (healthy/degraded/offline). `query_capabilities()` finds layers by capability. |
| **3.1.4 Trust Scorekeeper** | `kernel/trust_scorekeeper.py` | Tracks trust scores per layer per session. Weighted aggregation (L7/L8 at 1.2x, L5 at 1.1x, L1 at 0.8x). Time decay (1%/sec). Threshold gates: deploy=85, warn=70, abort=50. |
| **3.1.5 Event System** | `kernel/event_system.py` | Pub/sub observability. Events: `MESSAGE_SENT`, `MESSAGE_RECEIVED`, `RESPONSE_RETURNED`, `LAYER_STARTED`, `LAYER_STOPPED`, `TRUST_UPDATED`, `SESSION_STARTED`, `TOOL_CALLED`. |
| **3.1.6 Session Manager** | `kernel/session_manager.py` | Orchestrates the full L1-L9 pipeline for each user request. Creates `SessionState`, drives messages through all layers, collects trust scores. |

### 3.2 Knowledge Layer

| Sub-chunk | File | Purpose |
|-----------|------|---------|
| **3.2.1 OracleDB** | `knowledge/oracle_db.py` | Dict-backed JSON-serializable persistent store. Categories: `task_results`, `error_patterns`, `conventions`, `trust_history`, `file_deps`. |
| **3.2.2 Project Conventions** | `knowledge/project_conventions.py` | Learned style rules. Used by L6 (Codegen) for style enforcement and L8 (Verification) for consistency checking. Tracks enforcement counts. |
| **3.2.3 Error Patterns** | `knowledge/error_patterns.py` | Error-to-fix mappings with fuzzy matching (SequenceMatcher, threshold 0.6). Records success rates. Used by L7 (Testing) for self-healing. |

### 3.3 The 9 Layers

All layers extend `GraceLayer(BaseLayer)` which provides `call_llm()`, `call_tool()`, and `build_response()`.

#### Layer 1: Runtime (`layers/l1_runtime/`)
- **Capabilities:** environment_management, dependency_resolution, state_snapshot, resource_limiting
- **Messages:** `SETUP_ENVIRONMENT`, `SNAPSHOT_STATE`, `TEARDOWN_ENVIRONMENT`
- **What it does:** Creates isolated execution environments, captures state snapshots for rollback, resolves dependencies
- **Trust weight:** 0.8x

#### Layer 2: Planning (`layers/l2_planning/`)
- **Capabilities:** task_decomposition, planning, intent_parsing
- **Messages:** `DECOMPOSE_TASK`, `REPLAN_TASK`
- **What it does:** Uses LLM to break user prompts into a JSON task list with `id`, `description`, `dependency_ids`, `type`
- **Trust weight:** 1.0x

#### Layer 3: Proposer (`layers/l3_proposer/`)
- **Capabilities:** propose_solutions, strategy_generation, diversity_enforcement
- **Messages:** `PROPOSE_SOLUTIONS`, `REQUEST_MORE_PROPOSALS`
- **What it does:** Generates 3+ diverse solution proposals per task. Provides fallback proposals on parse failure.
- **Trust weight:** 0.9x

#### Layer 4: Evaluator (`layers/l4_evaluator/`)
- **Capabilities:** evaluate_proposals, comparative_scoring, tradeoff_analysis
- **Messages:** `EVALUATE_PROPOSALS`
- **What it does:** Scores proposals on correctness, performance, maintainability, risk (0-100 each). Minimum score: 70. If below, sends `REQUEST_MORE_PROPOSALS` back to L3.
- **Trust weight:** 1.0x
- **Feedback loop:** L4 → L3 (request more proposals if score < 70)

#### Layer 5: Simulation (`layers/l5_simulation/`)
- **Capabilities:** static_analysis, symbolic_execution, impact_analysis, edge_case_detection
- **Messages:** `SIMULATE_PROPOSAL`, `ANALYZE_IMPACT`
- **What it does:** Pre-flight analysis without running code. Detects risks, edge cases, dependency impacts, contradictions. Returns `recommendation`: proceed/caution/block.
- **Trust weight:** 1.1x (highest tier)

#### Layer 6: Codegen (`layers/l6_codegen/`)
- **Capabilities:** code_generation, file_editing, style_enforcement
- **Messages:** `EXECUTE_TASK`, `FIX_CODE`
- **What it does:** Generates code via LLM, writes files via MCP tools. Consults `ProjectConventions` for style.
- **Trust weight:** 1.0x
- **Feedback loop:** L7 → L6 (fix code on test failure)

#### Layer 7: Testing (`layers/l7_testing/`)
- **Capabilities:** test_execution, test_generation, build_validation
- **Messages:** `VERIFY_TASK`
- **What it does:** Runs tests via MCP terminal tools (`pytest`). On failure, sends `FIX_CODE` back to L6 with error trace.
- **Trust weight:** 1.2x (highest tier)
- **Feedback loop:** L7 → L6 (self-healing)

#### Layer 8: Verification (`layers/l8_verification/`)
- **Capabilities:** requirement_verification, fact_checking, security_scanning, consistency_checking
- **Messages:** `VERIFY_OUTPUT`, `FACT_CHECK`
- **What it does:** Post-generation QA. Validates requirements coverage, scans for security issues (injection, hardcoded secrets), checks consistency, scores readability. Security flags force `verified=false`.
- **Trust weight:** 1.2x (highest tier)

#### Layer 9: Deployment (`layers/l9_deployment/`)
- **Capabilities:** trust_aggregation, policy_enforcement, commit_planning, rollback_planning
- **Messages:** `DEPLOYMENT_CHECK`
- **What it does:** Final gate. Aggregates all layer trust scores. Policies: tests must pass, verification clean, no security flags, trust >= 85. On rejection, sends `REPLAN_TASK` to L2.
- **Trust weight:** 1.0x
- **Feedback loop:** L9 → L2 (full re-plan on rejection)

### 3.4 Pipeline Flow Diagram

```
User Prompt
  │
  ▼
L1: Setup Environment ──── snapshot for rollback
  │
  ▼
L2: Decompose ──────────── break into tasks
  │
  ▼ (per task)
  ┌────────────────────────────────────────┐
  │ L3: Propose (3+ solutions) ◄── L4 can │
  │   │                         request    │
  │   ▼                         more       │
  │ L4: Evaluate (score, select best) ─────┘
  │   │
  │   ▼
  │ L5: Simulate (pre-flight risk)
  │   │
  │   ▼
  │ L6: Codegen (write code) ◄──── L7 can
  │   │                          send fix
  │   ▼                          requests
  │ L7: Test (run pytest) ────────────────┘
  │   │
  │   ▼
  │ L8: Verify (QA + security scan)
  └────────────────────────────────────────┘
  │
  ▼
L9: Deploy Gate ──── trust >= 85? ──── Yes → Commit Plan
                         │
                         No → REPLAN (back to L2)
```

---

## Chunk 4: Cognitive Engine

**Location:** `backend/cognitive/`
**Size:** 70+ Python files

The cognitive engine is the brain of the system. It implements a 12-invariant cognitive blueprint.

### 4.1 OODA Loop (Primary Control Loop)

| Sub-chunk | File | Purpose |
|-----------|------|---------|
| **4.1.1 OODA Controller** | `ooda.py` | `OODALoop` class with strict phase sequencing: OBSERVE → ORIENT → DECIDE → ACT → COMPLETED. Calling out of order raises ValueError. |
| **4.1.2 Cognitive Engine** | `engine.py` | Central cortex. Manages `DecisionContext` lifecycle: `begin_decision()` → `observe()` → `orient()` → `decide()` → `act()`. Validates all 12 invariants. |
| **4.1.3 Invariant Validator** | `invariants.py` | Validates 12 cognitive invariants before every execution (see table below). |
| **4.1.4 Ambiguity Ledger** | `ambiguity.py` | Tracks facts as Known/Inferred/Assumed/Unknown. Blocks irreversible actions when blocking unknowns exist. |
| **4.1.5 Decision Logger** | `decision_log.py` | Full audit trail in JSONL files. Logs all alternatives, outcomes, violations. |

### 4.2 The 12 Invariants

| # | Name | Enforcement |
|---|------|-------------|
| 1 | OODA as Primary Loop | Strict phase sequencing |
| 2 | Ambiguity Accounting | AmbiguityLedger blocks on unknowns |
| 3 | Reversibility | Justification required for irreversible actions |
| 4 | Determinism | Safety-critical ops must be deterministic |
| 5 | Blast Radius | Systemic changes need success criteria |
| 6 | Observability | DecisionLogger logs everything |
| 7 | Simplicity | Complexity must justify benefit |
| 8 | Feedback | FeedbackLoop records all outcomes |
| 9 | Bounded Recursion | CircuitBreaker with per-loop depth limits |
| 10 | Optionality > Optimization | Future options weighted 2x |
| 11 | Time-Bounded Reasoning | Decision freeze points enforced |
| 12 | Forward Simulation | Alternatives scored before deciding |

### 4.3 9-Stage Cognitive Pipeline

| Stage | Name | What it does |
|-------|------|-------------|
| 1 | TimeSense | Temporal context (business hours, time-of-day) |
| 2 | OODA | Observe project files, orient with episodic/procedural/MAGMA memory |
| 3 | Ambiguity | Detect assumptions, resolve via consensus if blocking |
| 4 | Invariants | Validate all 12 invariants |
| 5 | Trust Pre-Check | Filter context by trust threshold (0.6) |
| 6 | Generate | LLM call with enriched prompt |
| 7 | Contradiction | Language mismatch, semantic contradiction, import verification |
| 8 | Hallucination | 7-layer verification: grounding, contradiction, quality, trust, internal, structural, cross-model |
| 9 | Genesis | Provenance tracking via Genesis Keys |

### 4.4 Consensus Engine (Knights of the Roundtable)

4-model multi-model deliberation protocol:

| Model | Provider | Strength |
|-------|----------|----------|
| Claude Opus 4.6 | Anthropic (cloud) | Deep reasoning, architecture |
| Kimi K2.5 | Moonshot (cloud) | Long context (262K tokens) |
| Qwen 2.5 | Ollama (local) | Code generation, fast |
| DeepSeek R1 | Ollama (local) | Chain-of-thought |

**4 Layers of Deliberation:**
1. **Independent Deliberation** — each model answers independently (parallel)
2. **Consensus Formation** — responses compared, synthesized, agreements/disagreements identified
3. **Alignment** — consensus aligned to user context or Grace's internal needs
4. **Verification** — trust scoring, hallucination guard, contradiction detection

### 4.5 Central Orchestrator

File: `central_orchestrator.py` — Singleton "nervous system"

| Sub-chunk | What it manages |
|-----------|----------------|
| **4.5.1 Event Bus** | `event_bus.py` — in-process pub/sub with wildcard topic matching |
| **4.5.2 Circuit Breaker** | `circuit_breaker.py` — prevents recursive loop explosions. 40+ named system loops with per-loop depth limits. |
| **4.5.3 Loop Orchestrator** | `loop_orchestrator.py` — composes multiple loops into 8 pre-defined composites (CODE_WRITE, HEAL_AND_LEARN, etc.) |

### 4.6 Memory Systems

| Sub-chunk | File | Purpose |
|-----------|------|---------|
| **4.6.1 Episodic Memory** | `episodic_memory.py` | Concrete past experiences: problem → action → outcome |
| **4.6.2 Procedural Memory** | `procedural_memory.py` | Learned skills with success rates |
| **4.6.3 Flash Cache** | `flash_cache.py` | Fast keyword-indexed external references |
| **4.6.4 Ghost Memory** | `ghost_memory.py` | Ephemeral task-scoped memory (resets on task completion) |
| **4.6.5 Unified Memory** | `unified_memory.py` | Single access point across all memory types |

### 4.7 Learning Systems

| Sub-chunk | File | Purpose |
|-----------|------|---------|
| **4.7.1 Intelligence Layer** | `intelligence_layer.py` | ML (pattern recognition) + DL (feature vectors) + Neuro-Symbolic (rule promotion). Patterns with >90% success auto-promote to deterministic rules. |
| **4.7.2 ML Trainer** | `ml_trainer.py` | Collects training signals from circuit breaker loop executions |
| **4.7.3 Active Learning** | `active_learning_system.py` | Uncertainty sampling for efficient learning |
| **4.7.4 Continuous Learning** | `continuous_learning_orchestrator.py` | Background learning orchestration |
| **4.7.5 Idle Learner** | `idle_learner.py` | Learning during system idle periods |
| **4.7.6 Proactive Learner** | `proactive_learner.py` | Proactive knowledge gap discovery |

### 4.8 Self-Healing

| Sub-chunk | File | Purpose |
|-----------|------|---------|
| **4.8.1 Core Healing** | `self_healing.py` | Database/Qdrant/LLM reconnection primitives |
| **4.8.2 Healing Coordinator** | `healing_coordinator.py` | Orchestrates healing across components |
| **4.8.3 Autonomous Healing** | `autonomous_healing_loop.py` | The "13th loop" — full autonomous healing with rollback |
| **4.8.4 Proactive Healing** | `proactive_healing_engine.py` | Heals before problems manifest |
| **4.8.5 Immune System** | `immune_system.py` | AVN: adaptive scanning, anomaly detection, playbook-based healing, vaccination |

### 4.9 Code Generation

| Sub-chunk | File | Purpose |
|-----------|------|---------|
| **4.9.1 File Generator** | `file_generator.py` | Generates files from LLM output |
| **4.9.2 Grace Compiler** | `grace_compiler.py` | Validates and compiles generated code |
| **4.9.3 Code Sandbox** | `code_sandbox.py` | Isolated code execution |
| **4.9.4 Blueprint Engine** | `blueprint_engine.py` | Multi-model design → build → verify loop |
| **4.9.5 Qwen Coding Net** | `qwen_coding_net.py` | Qwen-based coding agent with ghost memory |

### 4.10 40+ Named System Loops (Circuit Breaker)

Organized into 7 categories:

| Category | Loops |
|----------|-------|
| **Homeostasis** | healing, trust, resource balance, system health, cognitive load, performance optimization |
| **Learning** | autonomous, memory mesh, consensus refinement, user intent, feedback optimization |
| **Healing** | cognitive, pipeline self-repair, autonomous (13th loop) |
| **Trust** | genesis trust, external API reliability, model drift detection |
| **Knowledge** | integration, cognitive consensus, live integration, knowledge graph |
| **Safety** | API validation, security compliance, sandbox, trigger validation, emergency response, ethics governance |
| **Coding** | code generation safety, blueprint build, qwen coding net |

---

## Chunk 5: MAGMA Memory System

**Location:** `backend/cognitive/magma/`

MAGMA = Memory Architecture for Graph-based Memory Augmentation

### 5.1 Four Relation Graphs

| Graph | Relation Types | Purpose |
|-------|---------------|---------|
| **Semantic** | similarity, parent/child, synonym | Meaning-based connections |
| **Temporal** | before/after, concurrent, sequence | Time-based event linking |
| **Causal** | causes, enables, prevents | Cause-effect reasoning |
| **Entity** | instance-of, part-of, co-occurs | Entity relationship tracking |

### 5.2 MAGMA Sub-chunks

| Sub-chunk | File | Purpose |
|-----------|------|---------|
| **5.2.1 GraceMagmaSystem** | `grace_magma_system.py` | THE single entry point for all memory operations. Integrates Layers 1-4 + security. |
| **5.2.2 Relation Graphs** | `relation_graphs.py` | Four graph types with BFS path-finding |
| **5.2.3 Intent Router** | `intent_router.py` | Query analysis: intent classification (17 types), anchor identification, graph selection, retrieval policy |
| **5.2.4 RRF Fusion** | `rrf_fusion.py` | 5 fusion methods: RRF, Weighted RRF, CombSUM, CombMNZ, Interleaving |
| **5.2.5 Topological Retrieval** | `topological_retrieval.py` | Graph traversal: BFS, DFS, Best-First, Bidirectional, Adaptive, Causal Chain, Temporal Window |
| **5.2.6 Synaptic Ingestion** | `synaptic_ingestion.py` | Write pipeline: Event segmentation → Embedding → Semantic/Temporal/Entity/Causal linking |
| **5.2.7 Async Consolidation** | `async_consolidation.py` | Background queue: priority-based async operations, graph pruning, importance updates |
| **5.2.8 Causal Inference** | `causal_inference.py` | LLM-powered cause-effect reasoning with pattern detection |
| **5.2.9 Layer Integrations** | `layer_integrations.py` | Connectors: L1 Message Bus, L2 Pattern Memory, L3 Decision Memory, L4 Action Memory |
| **5.2.10 MAGMA Bridge** | `magma_bridge.py` | Simplified facade connecting MAGMA to every other Grace system |

### 5.3 MAGMA Data Flow

```
Content In ──► SynapticIngestionPipeline
                 ├── EventSegmenter (sentence/paragraph/entity/concept)
                 ├── SemanticLinker (embedding + cosine similarity)
                 ├── TemporalLinker (time-based linking)
                 ├── EntityLinker (co-occurrence tracking)
                 └── CausalLinker (cause-effect patterns)
                         │
                         ▼
              4 Relation Graphs (populated)
                         │
Query In ──► IntentAwareRouter
                 ├── IntentClassifier (17 intent types)
                 ├── AnchorIdentifier (concept/entity/time/action)
                 ├── GraphSelector (intent → target graphs)
                 └── RetrievalPolicySelector (7 policies)
                         │
                         ▼
              AdaptiveTopologicalRetriever
                 ├── BFS / Best-First / Bidirectional
                 └── Policy-driven exploration
                         │
                         ▼
              MagmaFusion (RRF / Weighted RRF / CombSUM)
                         │
                         ▼
              ContextSynthesizer (text for LLM)
```

---

## Chunk 6: Diagnostic Machine

**Location:** `backend/diagnostic_machine/`
**Architecture:** 4-layer pipeline

### 6.1 Layers

| Layer | File | Purpose |
|-------|------|---------|
| **Layer 1: Sensors** | `sensors.py` | Collects raw data from tests, logs, metrics, agent outputs, Genesis Keys, Mirror |
| **Layer 2: Interpreters** | `interpreters.py` | Pattern analysis, anomaly detection, 12 invariant checks, clarity classification |
| **Layer 3: Judgement** | `judgement.py` | Health scoring (0-100), confidence scoring, risk vectors, drift analysis, forensic analysis |
| **Layer 4: Action Router** | `action_router.py` | Routes decisions to actions: Alert, Heal, Freeze, Learn, CI/CD, Escalate |

### 6.2 Supporting Modules

| Sub-chunk | File | Purpose |
|-----------|------|---------|
| **6.2.1 Diagnostic Engine** | `diagnostic_engine.py` | Main orchestrator. 60s heartbeat, manages diagnostic cycles. |
| **6.2.2 Healing Executor** | `healing.py` | 10 reversible actions: DB reconnect, vector DB reset, cache clear, GC, log rotation, config reload, service restart |
| **6.2.3 Cognitive Integration** | `cognitive_integration.py` | Bridges diagnostic insights into learning memory, decision logs, Memory Mesh |
| **6.2.4 Notifications** | `notifications.py` | Multi-channel: Webhook, Slack, Email, Console with retry and priority routing |
| **6.2.5 Realtime** | `realtime.py` | WebSocket connection manager for live diagnostic streaming |
| **6.2.6 Trend Analysis** | `trend_analysis.py` | Time-series storage, linear regression trends, volatility, predictive alerting |
| **6.2.7 API** | `api.py` | 25+ endpoints: `/trigger`, `/health`, `/healing/execute`, `/ws`, `/trends`, `/avn/alerts` |

### 6.3 Diagnostic Flow

```
SensorLayer.collect_all()  ──►  InterpreterLayer.interpret()
      ↓                              ↓
   Raw Data                   Patterns/Anomalies/
   (tests, logs,              Invariant Checks
    metrics, agents)
                                     ↓
JudgementLayer.judge()  ──►  ActionRouter.route()
      ↓                              ↓
   Health Score              Alert / Heal / Freeze /
   Risk Vectors              Learn / Log
   Drift Analysis
```

---

## Chunk 7: ML Intelligence

**Location:** `backend/ml_intelligence/`

### 7.1 Core Components

| Sub-chunk | File | Key Classes | Purpose |
|-----------|------|-------------|---------|
| **7.1.1 Neural Trust Scorer** | `neural_trust_scorer.py` | `NeuralTrustScorer`, `TrustScorerNetwork` | Deep learning trust scoring with attention, MC dropout, experience replay, adversarial robustness |
| **7.1.2 Trust-Aware Embeddings** | `trust_aware_embedding.py` | `TrustAwareEmbeddingModel` | Enhances embeddings with symbolic trust scores; trust-weighted similarity |
| **7.1.3 Meta-Learning** | `meta_learning.py` | `MAML`, `HyperparameterOptimizer`, `TaskSimilarityDetector` | MAML, Reptile algorithms; hyperparameter optimization; task similarity detection |
| **7.1.4 Neuro-Symbolic Reasoner** | `neuro_symbolic_reasoner.py` | `NeuroSymbolicReasoner` | Unified neural + symbolic reasoning with bidirectional cross-informing |
| **7.1.5 Rule Generator** | `neural_to_symbolic_rule_generator.py` | `NeuralToSymbolicRuleGenerator` | Converts neural patterns (clusters) into explicit symbolic rules |
| **7.1.6 Multi-Armed Bandit** | `multi_armed_bandit.py` | `MultiArmedBandit` | UCB1, Thompson Sampling, Epsilon-Greedy, Exp3 for learning topic selection |
| **7.1.7 Contrastive Learning** | `contrastive_learning.py` | `ContrastiveLearner` | NT-Xent, Triplet, Supervised Contrastive losses; hard negative mining |
| **7.1.8 Active Learning Sampler** | `active_learning_sampler.py` | `ActiveLearningSampler` | 7 sampling strategies: Uncertainty, Entropy, Margin, Committee, Expected Model Change, Diversity, Core-Set |
| **7.1.9 Uncertainty Quantification** | `uncertainty_quantification.py` | `UncertaintyQuantifier` | Bayesian NNs, MC Dropout, Deep Ensembles, Conformal Prediction |
| **7.1.10 Online Learning** | `online_learning_pipeline.py` | `OnlineLearningPipeline` | Streaming mini-batch updates, EWC for catastrophic forgetting prevention |
| **7.1.11 Integration Orchestrator** | `integration_orchestrator.py` | `MLIntelligenceOrchestrator` | Main coordinator. Initializes and combines all ML components. Unified APIs for trust/topic/uncertainty/training. |

---

## Chunk 8: Genesis Key System

**Location:** `backend/genesis/`
**Size:** 30 files

Genesis Keys are universal identifiers tracking WHAT, WHERE, WHEN, WHY, WHO, and HOW for every operation.

### 8.1 Core Tracking

| Sub-chunk | File | Purpose |
|-----------|------|---------|
| **8.1.1 Genesis Key Service** | `genesis_key_service.py` | Central service: creates Genesis Keys with 6W metadata, user profiles, fix suggestions, rollback |
| **8.1.2 Comprehensive Tracker** | `comprehensive_tracker.py` | Tracks ALL inputs: user inputs, AI responses, agent actions, API calls, web fetches, DB changes |
| **8.1.3 KB Integration** | `kb_integration.py` | Auto-populates keys into `knowledge_base/layer_1/genesis_key/` by user/session |
| **8.1.4 Middleware** | `middleware.py` | FastAPI middleware: assigns Genesis IDs to users, tracks all API requests/responses |
| **8.1.5 Tracking Middleware** | `tracking_middleware.py` | Decorators for tracking file/DB operations; `SessionTracker` context manager |

### 8.2 Version Control

| Sub-chunk | File | Purpose |
|-----------|------|---------|
| **8.2.1 Symbiotic VC** | `symbiotic_version_control.py` | Every file change creates BOTH a Genesis Key AND a version entry atomically, with rollback |
| **8.2.2 File Version Tracker** | `file_version_tracker.py` | File-level version tracking with `FILE-` prefix keys, SHA256 hashing, diffs |
| **8.2.3 Git-Genesis Bridge** | `git_genesis_bridge.py` | Bidirectional: post-commit hooks create Genesis Keys; Genesis Keys can auto-commit to Git |
| **8.2.4 Directory Hierarchy** | `directory_hierarchy.py` | `DIR-` prefix Genesis Keys for every directory with parent-child relationships |
| **8.2.5 Repo Scanner** | `repo_scanner.py` | Full repo scanning: assigns Genesis Keys to all directories and files |
| **8.2.6 File Watcher** | `file_watcher.py` | Real-time file system watcher using `watchdog`: auto-creates keys on file create/modify/delete |

### 8.3 CI/CD Pipeline System

| Sub-chunk | File | Purpose |
|-----------|------|---------|
| **8.3.1 Genesis CI/CD** | `cicd.py` | Self-hosted CI/CD: pipeline definitions, stage execution (checkout/install/lint/test/build/security/deploy) |
| **8.3.2 CI/CD Versioning** | `cicd_versioning.py` | Version control for pipeline configurations; every mutation tracked |
| **8.3.3 Adaptive CI/CD** | `adaptive_cicd.py` | Trust scores per pipeline, KPI tracking, LLM-based recommendations |
| **8.3.4 Autonomous CI/CD** | `autonomous_cicd_engine.py` | Monitors events, decides when/what to test/deploy, autonomy levels (0-5) |
| **8.3.5 Intelligent Orchestrator** | `intelligent_cicd_orchestrator.py` | ML-based test selection (6 strategies), webhook processing, closed-loop feedback |

### 8.4 Data Pipeline

| Sub-chunk | File | Purpose |
|-----------|------|---------|
| **8.4.1 Pipeline Integration** | `pipeline_integration.py` | 7-stage: L1 Input → Genesis Key → Version Control → Librarian → Immutable Memory → RAG → World Model |
| **8.4.2 Layer 1 Integration** | `layer1_integration.py` | Processes 8 input types through full pipeline; triggers autonomous actions |
| **8.4.3 Cognitive L1** | `cognitive_layer1_integration.py` | Wraps Layer 1 with OODA enforcement and 12 invariant validation |
| **8.4.4 Librarian Pipeline** | `librarian_pipeline.py` | Full ingestion: receive → Genesis Key → index → file → memorize → publish |
| **8.4.5 Whitelist Pipeline** | `whitelist_learning_pipeline.py` | 15-stage pipeline for human-approved data with trust verification |

### 8.5 Autonomous & Archival

| Sub-chunk | File | Purpose |
|-----------|------|---------|
| **8.5.1 Autonomous Engine** | `autonomous_engine.py` | Event/schedule/condition triggers, priority queues, trust scores per action |
| **8.5.2 Trigger Pipeline** | `autonomous_triggers.py` | Genesis Key creation triggers: study, practice loops, prefetch, multi-LLM verification, mirror |
| **8.5.3 Archival** | `archival_service.py` | Daily archival at 2 AM: collects keys, generates reports (type breakdown, error analysis) |
| **8.5.4 Daily Organizer** | `daily_organizer.py` | Exports keys to Layer 1, creates daily Markdown summaries |
| **8.5.5 Realtime Events** | `realtime.py` | Instant callbacks on key creation, alert rules (error spike/burst), streaming aggregation |

---

## Chunk 9: Scale Infrastructure (Aaron-new2)

**These are the 8 commits specific to the Aaron-new2 branch** that add production-scale infrastructure.

### 9.1 Worker Pool (REWRITE)

**File:** `backend/core/worker_pool.py`
**Commit:** `cc2565d7`

**Before:** Simple `ThreadPoolExecutor` with per-user request tracking
**After:** Full `ManagedPool` architecture:

| Sub-chunk | What |
|-----------|------|
| **9.1.1 ManagedPool class** | Thread pool with backpressure, metrics, task naming. Rejects tasks when queue depth exceeds `MAX_QUEUE_DEPTH` (200). |
| **9.1.2 TaskMetrics** | Tracks submitted/completed/failed/cancelled counts, rolling average latency (last 200 tasks). |
| **9.1.3 IO Pool** | `get_io_pool()` — 16 workers for DB queries, HTTP calls, file ops. Singleton. |
| **9.1.4 CPU Pool** | `get_cpu_pool()` — 4 workers for code analysis, AST parsing, embeddings. Singleton. |
| **9.1.5 Convenience functions** | `submit_io()`, `submit_cpu()`, `pool_status()`, `shutdown_all()` |
| **9.1.6 Timeout guards** | Per-task timeout with daemon thread watchdog |

**Config env vars:** `GRACE_IO_WORKERS`, `GRACE_CPU_WORKERS`, `GRACE_MAX_QUEUE_DEPTH`

### 9.2 Memory Injector (EXPANSION)

**File:** `backend/core/memory_injector.py`
**Commits:** `2f82f838`, `788928eb`

**Before:** 8 hardcoded context sections, flat char budget
**After:** 18 priority-ordered sections with adaptive budgeting

| Sub-chunk | What |
|-----------|------|
| **9.2.1 Section system** | `_Section` class with priority (1=highest), max_chars budget, lazy fetcher function |
| **9.2.2 Budget management** | Sections built in priority order. If total exceeds `MAX_CONTEXT_CHARS` (12000), lower-priority sections truncated/dropped. |
| **9.2.3 Performance tracking** | `_snapshot_history` deque (last 50 builds). `get_snapshot_stats()` returns avg chars, latency, sections included. |
| **9.2.4 Memory pressure** | `get_memory_pressure()` — RSS MB, context budget, cache size |

**18 Context Sections (priority order):**

| Priority | Section | Max Chars |
|----------|---------|-----------|
| 1 | Governance Rules (MANDATORY) | 2000 |
| 2 | Model Trust Scores | 400 |
| 3 | Past Experience (episodic) | 1500 |
| 4 | System Activity (last 24h) | 1000 |
| 5 | Knowledge Gaps | 500 |
| 6 | AI Prediction (DL model) | 300 |
| 7 | Brain Synapse Strengths (Hebbian) | 400 |
| 8 | Self-Observation (Mirror) | 200 |
| 9 | Recent Genesis Keys | 800 |
| 10 | Grace Source Code Map | 600 |
| 11 | Database State | 500 |
| 12 | Recent Chat Context | 600 |
| 13 | Component Health | 500 |
| 14 | Brain Actions (what Grace can do) | 500 |
| 15 | Ouroboros Loop History | 400 |
| 16 | Coding Pipeline History | 400 |
| 17 | Provenance Ledger | 300 |
| 18 | Active Sessions | 200 |

### 9.3 Security Additions

**File:** `backend/core/security.py`
**Commit:** `75005885`

| Sub-chunk | What |
|-----------|------|
| **9.3.1 Per-User Rate Limiter** | `check_user_rate_limit(user_id, tier)` — tracks by user_id. Tiers: free=30rpm, pro=120rpm, admin=500rpm, default=60rpm. |
| **9.3.2 LLM Response Cache** | `LLMCache` class — in-memory LRU with TTL (1 hour default). SHA256-keyed by normalized prompt + model + temperature. Thread-safe. Hit/miss stats. |
| **9.3.3 API Cost Tracker** | `APICostTracker` class — tracks estimated API costs per model per user. Knows cost rates for Kimi, Claude, GPT-4o. Local models (Qwen, DeepSeek) are $0. Breakdowns: by_model, by_user, total_cost_usd. |
| **9.3.4 Backup upgrade** | `backup_database()` now supports PostgreSQL via `pg_dump`. Detects dialect automatically. |

### 9.4 Database Compatibility Layer (NEW)

**File:** `backend/core/db_compat.py`
**Commit:** `cba89fd2`

| Sub-chunk | What |
|-----------|------|
| **9.4.1 JSONColumn** | Dialect-agnostic JSON column: PostgreSQL uses native JSONB, SQLite stores as TEXT with auto JSON serialization |
| **9.4.2 ArrayColumn** | Dialect-agnostic ARRAY: PostgreSQL uses native ARRAY, SQLite stores as JSON TEXT |
| **9.4.3 get_table_stats()** | Row counts for all tables — works on both SQLite and PostgreSQL |
| **9.4.4 get_db_size_mb()** | Database size via `pg_database_size()` (PG) or `pragma_page_count()` (SQLite) |
| **9.4.5 is_postgres()** | Helper to check which dialect is active |

### 9.5 PostgreSQL Connection

**File:** `backend/database/connection.py`
**Commit:** `cba89fd2`

- Added dedicated PostgreSQL engine configuration with `QueuePool`, `pool_pre_ping`, `pool_recycle`, `statement_timeout=30s`, `READ COMMITTED` isolation
- Safe URL logging (strips credentials)

### 9.6 Session Retry Logic

**File:** `backend/database/session.py`
**Commit:** `cba89fd2`

- `_is_retryable_error()` now handles: SQLite locks, PostgreSQL deadlocks, serialization failures, connection resets, unexpected server disconnections

### 9.7 Inline Code Completion (EXPANSION)

**File:** `backend/api/completion_api.py`
**Commit:** `5188dc05`

**Before:** 2 languages (Python, JS), ~25 patterns
**After:** 8 languages, 80+ patterns, 4-level completion strategy

| Sub-chunk | What |
|-----------|------|
| **9.7.1 CompletionCache** | LRU cache (256 entries) keyed by `(language, last_5_lines_hash)`. Avoids re-calling LLM for same prefix. |
| **9.7.2 8 Language Patterns** | Python (40+), JavaScript (25+), TypeScript (extends JS with interfaces/generics), CSS (25+), HTML (12+), SQL (20+), Rust (18+), Go (20+) |
| **9.7.3 4-Level Strategy** | Level 0: bracket/quote auto-close (<1ms) → Level 1: pattern match (<5ms) → Level 1.5: block completion → Level 2: cache → Level 3: LLM call |
| **9.7.4 Context extraction** | `_extract_context()` — extracts variables, imports, functions, classes from surrounding code for better LLM completions |
| **9.7.5 Block completion** | `_block_completion()` — detects unfinished blocks and suggests closure |
| **9.7.6 Output cleaning** | `_clean_completion()` — strips markdown fences, explanatory text, limits to 5 lines |
| **9.7.7 Stats endpoint** | `GET /api/complete/stats` — cache hit/miss statistics |

### 9.8 Brain Action Wiring

**File:** `backend/api/brain_api_v2.py`
**Commit:** `edd4d308`

8 new system actions wired into the brain:

| Action | Handler | What |
|--------|---------|------|
| `worker_pool` | `_worker_pool_status()` | IO + CPU pool status, active tasks, latency |
| `llm_cache` | `_llm_cache_stats()` | Cache size, hit rate, TTL |
| `clear_llm_cache` | `_clear_llm_cache()` | Flush the LLM cache |
| `api_costs` | `_api_cost_summary()` | Cost breakdown by model and user |
| `memory_pressure` | `_memory_pressure()` | RSS MB, context budget |
| `snapshot_stats` | `_snapshot_stats()` | Memory injector performance |
| `db_info` | `_db_info()` | Dialect, size, table stats, health |
| `user_rate_limit` | `_user_rate_check(p)` | Check per-user rate limit |

### 9.9 App Wiring

**File:** `backend/app.py`
**Commits:** `cc2565d7`, `75005885`

- Worker pools initialized on startup (`get_io_pool()`, `get_cpu_pool()`)
- Worker pools shut down on exit (`shutdown_all()`)
- New endpoint: `GET /api/runtime/workers` — pool status
- Updated: `GET /api/runtime/security` — now includes LLM cache stats + API cost tracking

---

## Chunk 10: Frontend — React UI

**Location:** `frontend/`

### 10.1 Architecture

| Sub-chunk | File | Purpose |
|-----------|------|---------|
| **10.1.1 Entry Point** | `src/main.jsx` | `createRoot` → `<App />` |
| **10.1.2 Root Component** | `src/App.jsx` | View-based navigation (no React Router). 15+ views: home, chat, folders, docs, codebase, dev, governance, agents, memory, integrations, health, settings, projects, lab, apis |
| **10.1.3 API Config** | `src/config/api.js` | Base URL, V1 resource endpoints, upload endpoints |
| **10.1.4 Brain Client** | `src/api/brain-client.js` | `brainCall(domain, action, payload)` → `POST /brain/{domain}` |

### 10.2 State Management (Zustand)

5 stores in `src/store/index.js`:

| Store | What it tracks |
|-------|---------------|
| **usePreferencesStore** | Theme, sidebar, chat settings, notifications. Persisted to localStorage. |
| **useChatStore** | Active chat, chats list, messages, streaming state, drafts. Persisted. |
| **useUIStore** | Loading, modals, toasts, search, command palette, file browser state. |
| **useAuthStore** | User, tokens, Genesis keys, session. Persisted. |
| **useSystemStore** | Online/WS status, health, services, connections, available models. |

### 10.3 Key Components (52 JSX files)

| Sub-chunk | Components | Purpose |
|-----------|-----------|---------|
| **10.3.1 Chat** | `ChatTab.jsx`, `ChatWindow.jsx`, `ConsensusChat.jsx` | Main chat interface with multi-model consensus |
| **10.3.2 Files** | `FoldersTab.jsx`, `DocsTab.jsx` | File browser with tree view, drag-and-drop upload |
| **10.3.3 Dev** | `DevTab.jsx`, `CodebaseTab.jsx`, `LabTab.jsx` | Developer tools, codebase analysis, sandbox lab |
| **10.3.4 Governance** | `GovernanceTab.jsx`, `GovernanceDiscussion.jsx` | Rule management, compliance frameworks |
| **10.3.5 System** | `SystemHealthTab.jsx`, `BackendPanel.jsx` | Health monitoring, backend exploration |
| **10.3.6 Version Control** | `VersionControl.jsx` + 5 sub-components | CommitTimeline, GitTree, DiffViewer, ModuleHistory, RevertModal |
| **10.3.7 Shared** | `ErrorBoundary.jsx`, `Toast.jsx`, `Skeleton.jsx` | Error handling, notifications, loading states |
| **10.3.8 App Shell** | `HomePage` (inline), `InputBar` (inline), `CommandPalette` (inline), `Sidebar` (inline) | All defined inline in App.jsx |

### 10.4 Styling

- **Primary:** Inline styles (all components)
- **Secondary:** 47 co-located `.css` files
- **Components:** MUI 7 + Emotion for Toast, Skeleton, ErrorBoundary
- **Theme:** Dark mode, accent `#e94560`, backgrounds `#0a0a1a`/`#1a1a2e`
- **No CSS modules, no Tailwind**

### 10.5 Custom Hooks

| Hook | File | Purpose |
|------|------|---------|
| `useChunkedUpload` | `src/hooks/useChunkedUpload.js` | 5GB chunked file upload with progress tracking |
| `useConnectionStatus` | `src/hooks/useConnectionStatus.js` | Real-time connection monitoring for all external services |

---

## Chunk 11: VSCode Extension

**Location:** `grace-os-vscode/`

### 11.1 Architecture (7 layers)

| Layer | Directory | Key Files |
|-------|----------|-----------|
| **Entry** | `src/` | `extension.ts` — activation, command registration, panel creation |
| **Core** | `src/core/` | `GraceOSCore.ts` (main coordinator), `GhostLedger.ts` (provenance), `AutonomousScheduler.ts` |
| **Commands** | `src/commands/` | 15+ commands: chat, analyze, heal, learn, deploy, blueprint, genesis |
| **Panels** | `src/panels/` | Dashboard webview, Chat webview |
| **Providers** | `src/providers/` | TreeDataProviders: Memory, Genesis, Learning, Diagnostics |
| **Systems** | `src/systems/` | `NeuralSymbolicAI.ts`, `DeepMagmaMemory.ts`, `DiagnosticMachine.ts` |
| **Bridges** | `src/bridges/` | `IDEBridge.ts` (VSCode API wrapper), `WebSocketBridge.ts` (backend connection) |

### 11.2 Extension Commands

- `graceOS.chat` — Open chat panel
- `graceOS.analyzeFile` — Analyze current file
- `graceOS.heal` — Self-heal issues
- `graceOS.learn` — Trigger learning cycle
- `graceOS.blueprint` — Generate code blueprint
- `graceOS.genesisKey` — View Genesis key for file
- `graceOS.showDashboard` — Open dashboard webview

---

## Chunk 12: MCP Servers

**Location:** `backend/mcp_repos/`

### 12.1 MCP Orchestrator

**File:** `backend/grace_mcp/` — coordinates all MCP servers, routes tool calls.

### 12.2 Server Implementations

| Server | Location | Language | Purpose |
|--------|----------|----------|---------|
| **DesktopCommanderMCP** | `mcp_repos/DesktopCommanderMCP/` | TypeScript | File ops, terminal, search, PDF operations |
| **Git** | `mcp_repos/mcp-servers/src/git/` | Python | Git operations (status, diff, commit, log) |
| **Filesystem** | `mcp_repos/mcp-servers/src/filesystem/` | TypeScript | File read/write/search with root restrictions |
| **Memory** | `mcp_repos/mcp-servers/src/memory/` | TypeScript | Knowledge graph (entities, relations, observations) |
| **Sequential Thinking** | `mcp_repos/mcp-servers/src/sequentialthinking/` | TypeScript | Step-by-step reasoning tool |
| **Time** | `mcp_repos/mcp-servers/src/time/` | Python | Time utilities |
| **Fetch** | `mcp_repos/mcp-servers/src/fetch/` | Python | HTTP fetch with caching |

---

## Chunk 13: Infrastructure & DevOps

### 13.1 Docker

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Full-stack orchestration |
| `backend/Dockerfile` | Multi-stage: MCP builder → Python builder → runtime |
| `frontend/Dockerfile` | Node build → nginx runtime |
| `frontend/nginx.conf` | Production nginx: API proxy, WebSocket, SPA routing |

### 13.2 Docker Services

| Service | Port | Profile |
|---------|------|---------|
| `backend` | 8000 | default |
| `frontend` | 80 | default |
| `qdrant` | 6333, 6334 | default |
| `ollama` | 11434 | optional |
| `ollama-gpu` | 11434 | gpu |
| `postgres` | 5432 | postgres |
| `redis` | 6379 | cache |

### 13.3 Kubernetes

| File | Contents |
|------|----------|
| `k8s/deployment.yaml` | Namespace, ConfigMap, Secret, Deployments for backend/frontend/qdrant |
| `k8s/services.yaml` | Service definitions with ClusterIP/LoadBalancer |

### 13.4 CI/CD

| File | Purpose |
|------|---------|
| `pipelines/grace-ci.yaml` | CI pipeline: lint, test, build, security scan |
| `pipelines/grace-deploy.yaml` | Deployment pipeline: build images, push, deploy to k8s |

### 13.5 Monitoring

| File | Purpose |
|------|---------|
| `monitoring/grafana-dashboard.json` | Grafana dashboard with panels for: API latency, error rates, LLM costs, memory usage, trust scores |

---

## Chunk 14: Database Layer

**Location:** `backend/database/`, `backend/models/`

### 14.1 Connection & Session

| File | Purpose |
|------|---------|
| `database/config.py` | `DatabaseConfig`, `DatabaseType` enum (SQLITE, POSTGRESQL, MYSQL) |
| `database/connection.py` | `DatabaseConnection` singleton. SQLite: WAL mode, StaticPool. PostgreSQL: QueuePool, statement_timeout, READ COMMITTED. |
| `database/session.py` | `SessionLocal`, `get_session`, `session_scope` context manager. Retry with backoff for lock/deadlock errors. |
| `database/base.py` | `BaseModel` with `id`, `created_at`, `updated_at` |

### 14.2 ORM Models

| Model File | Tables |
|------------|--------|
| `models/database_models.py` | `User`, `Conversation`, `Message`, `Embedding`, `Chat`, `ChatHistory`, `Document`, `DocumentChunk`, `GovernanceRule`, `GovernanceDocument`, `GovernanceDecision`, `LearningExample`, `LearningPattern`, `Episode`, `Procedure`, `LLMUsageStats` |
| `models/genesis_key_models.py` | `GenesisKey`, `FixSuggestion`, `GenesisKeyArchive`, `UserProfile` |
| `models/telemetry_models.py` | `OperationLog`, `PerformanceBaseline`, `DriftAlert`, `OperationReplay`, `SystemState` |
| `models/notion_models.py` | `NotionProfile`, `NotionTask`, `TaskHistory`, `TaskTemplate` |
| `models/librarian_models.py` | `LibrarianTag`, `DocumentTag`, `LibrarianRule` |
| `models/query_intelligence_models.py` | `QueryHandlingLog`, `KnowledgeGap`, `ContextSubmission` |

### 14.3 Key Enums

| Enum | Values |
|------|--------|
| `GenesisKeyType` | USER_INPUT, AI_RESPONSE, CODE_CHANGE, FILE_OPERATION, API_REQUEST, ERROR, etc. |
| `GenesisKeyStatus` | ACTIVE, ARCHIVED, ROLLED_BACK, ERROR, FIXED |
| `ChatType` | GENERAL, FORENSIC |
| `TaskStatus` | TODO, IN_PROGRESS, IN_REVIEW, COMPLETED, ARCHIVED |
| `OperationType` | INGESTION, RETRIEVAL, CHAT_GENERATION, EMBEDDING |

---

## Chunk 15: Security

### 15.1 Authentication

| Component | How |
|-----------|-----|
| **Identity** | Genesis ID-based (e.g., `GU-...`). No traditional username/password. |
| **Login** | `POST /auth/login` → assigns Genesis ID, sets session cookies |
| **Session** | Cookie-based: `genesis_id`, `session_id` |
| **Middleware** | `GenesisKeyMiddleware` assigns IDs, tracks all requests |

### 15.2 Security Module (`backend/core/security.py`)

| Component | What |
|-----------|------|
| **Secrets Manager** | Encrypted vault (`Fernet` cipher), env var fallback |
| **Rate Limiter** | Sliding window per-brain, per-IP. Configurable RPM per domain. |
| **Per-User Rate Limiter** | (Aaron-new2) Tier-based: free=30, pro=120, admin=500 RPM |
| **Request Validation** | 16MB size cap, null byte removal, SQL injection detection |
| **Database Backup** | SQLite (file copy) + PostgreSQL (`pg_dump`) |
| **LLM Cache** | (Aaron-new2) SHA256-keyed LRU with 1hr TTL |
| **API Cost Tracker** | (Aaron-new2) Per-model per-user cost estimation |

### 15.3 Governance

Governance rules are uploaded documents that constrain AI behavior. Stored in `GovernanceDocument` and `GovernanceRule` tables. Injected into every LLM prompt via Memory Injector as the highest-priority context section.

---

## Data Flow Diagrams

### User Chat Flow

```
User types message
    │
    ▼
Frontend: brainCall("chat", "send", {message})
    │
    ▼
POST /brain/chat → brain_api_v2.py
    │
    ▼
ChatService.send()
    ├── Memory Injector builds context (18 sections)
    ├── Governance rules prepended
    ├── Episodic memory searched
    ├── LLM called with enriched prompt
    ├── Response through hallucination guard
    ├── Genesis Key created for interaction
    ├── Message saved to DB
    └── Response streamed to frontend
    │
    ▼
Frontend: useChatStore updates messages
```

### Document Ingestion Flow

```
User uploads file
    │
    ▼
Frontend: chunked upload → /api/upload/*
    │
    ▼
Backend: TextIngestionService
    ├── Content extraction (PDF, Word, ZIP, etc.)
    ├── Semantic chunking
    ├── Embedding generation (sentence-transformers)
    ├── Qdrant vector storage
    ├── Genesis Key created
    ├── Librarian categorization
    ├── Memory Mesh notification
    └── Autonomous learning triggered
```

### Autonomous Healing Flow

```
Diagnostic Engine (60s heartbeat)
    │
    ▼
SensorLayer.collect_all()
    │
    ▼
InterpreterLayer.interpret()
    │
    ▼
JudgementLayer.judge()
    │  (health < 70?)
    ▼
ActionRouter.route()
    ├── Heal → HealingExecutor (10 actions)
    ├── Alert → NotificationManager
    ├── Learn → CognitiveIntegration
    ├── Freeze → Pause component
    └── Escalate → ConsensusEngine
    │
    ▼
Genesis Key created for all actions
```

---

## File Index

### Backend: Core Files (READ THESE FIRST)

| Priority | File | What |
|----------|------|------|
| 1 | `backend/app.py` | FastAPI entry, all wiring |
| 2 | `backend/api/brain_api_v2.py` | Brain API, all 207+ actions |
| 3 | `backend/core/memory_injector.py` | What LLMs actually see |
| 4 | `backend/settings.py` | All configuration |
| 5 | `backend/core/services/chat_service.py` | Chat logic |
| 6 | `backend/core/worker_pool.py` | Concurrency management |
| 7 | `backend/core/security.py` | Security, rate limiting, caching |
| 8 | `backend/database/connection.py` | DB connection setup |

### Backend: Cognitive Files

| Priority | File | What |
|----------|------|------|
| 1 | `backend/cognitive/engine.py` | Central cortex |
| 2 | `backend/cognitive/pipeline.py` | 9-stage cognitive pipeline |
| 3 | `backend/cognitive/consensus_engine.py` | Multi-model deliberation |
| 4 | `backend/cognitive/magma/grace_magma_system.py` | MAGMA entry point |
| 5 | `backend/cognitive/central_orchestrator.py` | System coordinator |
| 6 | `backend/cognitive/circuit_breaker.py` | Loop protection |
| 7 | `backend/cognitive/immune_system.py` | Self-healing AVN |

### Backend: GraceOS Kernel

| Priority | File | What |
|----------|------|------|
| 1 | `backend/grace_os/kernel/session_manager.py` | Pipeline orchestrator |
| 2 | `backend/grace_os/kernel/message_bus.py` | Message routing |
| 3 | `backend/grace_os/kernel/trust_scorekeeper.py` | Trust aggregation |
| 4 | `backend/grace_os/layers/base_layer.py` | Layer base class |
| 5 | `backend/grace_os/layers/grace_layer.py` | LLM + MCP integration base |

### Frontend: Key Files

| Priority | File | What |
|----------|------|------|
| 1 | `frontend/src/App.jsx` | Root component, all views |
| 2 | `frontend/src/store/index.js` | All 5 Zustand stores |
| 3 | `frontend/src/api/brain-client.js` | API client |
| 4 | `frontend/src/config/api.js` | Endpoint config |
| 5 | `frontend/src/components/ChatTab.jsx` | Main chat UI |

### Documentation: Key Docs

| Priority | File | What |
|----------|------|------|
| 1 | `README.md` | Project overview |
| 2 | `docs/ARCHITECTURE.md` | System architecture with Mermaid diagrams |
| 3 | `backend/docs/ARCHITECTURE.md` | Backend Brain-Domain-Service pattern |
| 4 | `docs/COMPLETE_SYSTEM_SUMMARY.md` | System status (70% operational) |
| 5 | `docs/technical_spec_14_remaining.md` | 14 remaining integration items (~40-50 hours) |
| 6 | `knowledge_base/grace_system_overview.md` | Concise system overview |

---

## Quick Reference: Key Commands

```bash
# Start everything (Docker)
docker compose up --build

# Start backend only
cd backend && pip install -r requirements.txt && python app.py

# Start frontend only
cd frontend && npm install && npm run dev

# Run tests
cd backend && python -m pytest tests/

# Check system health
curl http://localhost:8000/health

# Brain API call
curl -X POST http://localhost:8000/brain/system \
  -H "Content-Type: application/json" \
  -d '{"action": "health", "payload": {}}'
```

---

*Document generated 2026-03-03 for developer handover from Aaron-new2 branch.*
