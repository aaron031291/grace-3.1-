<p align="center">
  <h1 align="center">🧠 GRACE — Genesis-driven RAG Autonomous Cognitive Engine</h1>
  <p align="center">
    A self-evolving AI platform with multi-tier RAG, autonomous learning, cognitive reasoning, and full-stack tooling.
  </p>
</p>

<p align="center">
  <img alt="Version" src="https://img.shields.io/badge/version-3.1.0-blue.svg" />
  <img alt="Python" src="https://img.shields.io/badge/python-3.11+-green.svg" />
  <img alt="React" src="https://img.shields.io/badge/react-19-61DAFB.svg" />
  <img alt="FastAPI" src="https://img.shields.io/badge/fastapi-latest-009688.svg" />
  <img alt="License" src="https://img.shields.io/badge/license-MIT-yellow.svg" />
</p>

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Run Grace natively](#run-grace-natively)
  - [Local Development Setup](#local-development-setup)
  - [Docker Deployment](#docker-deployment)
  - [Kubernetes Deployment](#kubernetes-deployment)
- [Environment Configuration](#environment-configuration)
- [Core Systems](#core-systems)
  - [Multi-Tier RAG Pipeline](#1-multi-tier-rag-pipeline)
  - [Cognitive System](#2-cognitive-system)
  - [Genesis Tracking System](#3-genesis-tracking-system)
  - [ML Intelligence Module](#4-ml-intelligence-module)
  - [Librarian System](#5-librarian-system)
  - [Diagnostic Machine](#6-diagnostic-machine-4-layer)
  - [LLM Orchestrator](#7-llm-orchestrator)
  - [Agent Framework](#8-agent-framework)
  - [MAGMA Subsystem](#9-magma-subsystem)
- [API Reference](#api-reference)
- [Frontend](#frontend)
- [Database](#database)
- [Security](#security)
- [CI/CD](#cicd)
- [Monitoring & Telemetry](#monitoring--telemetry)
- [Grace OS VSCode Extension](#grace-os-vscode-extension)
- [Testing](#testing)
- [Contributing](#contributing)
- [Changelog](#changelog)

---

## Overview

**GRACE** is a self-evolving, production-ready AI platform built around Retrieval-Augmented Generation (RAG) with autonomous cognitive capabilities. Unlike standard RAG systems, GRACE features:

- **Multi-tier query handling** — VectorDB → Model Knowledge → User Context fallback
- **Autonomous learning** — continuous self-improvement with sandbox experimentation
- **Cognitive reasoning** — contradiction detection, OODA loops, episodic memory
- **Self-healing ingestion** — auto-recovery from pipeline failures
- **Genesis key tracking** — immutable provenance chain for all data mutations
- **Three-pillar governance** — human-in-the-loop approval workflows
- **4-layer diagnostic machine** — sensors → interpreters → judgement → action
- **Full-stack UI** — React 19 frontend with 40+ interactive tabs/panels

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          GRACE Architecture                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────┐   │
│  │  React 19 UI │◄──►│  FastAPI API  │◄──►│  Ollama (Mistral:7b)    │   │
│  │  (Vite/MUI)  │    │  50+ Routers │    │  Local LLM Inference    │   │
│  └──────────────┘    └──────┬───────┘    └──────────────────────────┘   │
│                             │                                           │
│         ┌───────────────────┼────────────────────┐                      │
│         ▼                   ▼                    ▼                      │
│  ┌─────────────┐   ┌──────────────┐    ┌─────────────────┐             │
│  │  Cognitive   │   │  Retrieval   │    │   Ingestion     │             │
│  │  Layer       │   │  (Multi-Tier)│    │   Pipeline      │             │
│  │  - OODA      │   │  - Qdrant    │    │   - Auto-ingest │             │
│  │  - Memory    │   │  - Reranker  │    │   - Self-heal   │             │
│  │  - Contradict│   │  - Trust     │    │   - Librarian   │             │
│  └─────────────┘   └──────────────┘    └─────────────────┘             │
│         │                   │                    │                      │
│         ▼                   ▼                    ▼                      │
│  ┌─────────────┐   ┌──────────────┐    ┌─────────────────┐             │
│  │  Genesis     │   │  SQLite/     │    │   Qdrant        │             │
│  │  Tracking    │   │  PostgreSQL  │    │   Vector DB     │             │
│  └─────────────┘   └──────────────┘    └─────────────────┘             │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ Support Systems: ML Intelligence │ Diagnostic Machine │ Telemetry│   │
│  │ LLM Orchestrator │ Agent │ Scraping │ SerpAPI │ Voice │ Grace OS │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

### Backend
| Component | Technology |
|-----------|-----------|
| **Framework** | FastAPI (Python 3.11+), mcp, fastmcp |
| **LLM** | Provider-agnostic: Ollama (Mistral:7b default) or OpenAI (GPT-4o) |
| **Embeddings** | Sentence Transformers (Qwen 4B default, CUDA/CPU) |
| **Vector DB** | Qdrant |
| **SQL DB** | SQLite (default) / PostgreSQL / MySQL / MariaDB |
| **ORM** | SQLAlchemy |
| **ML/DL** | PyTorch, scikit-learn, Transformers |
| **Web Scraping** | Trafilatura, Requests |
| **Search** | SerpAPI integration |
| **File Parsing** | pdfplumber, PyPDF2, python-docx, python-pptx, openpyxl |
| **Voice** | SpeechRecognition, pydub, moviepy |
| **Task Scheduling** | schedule, asyncio |
| **Process Monitoring** | psutil, watchdog, watchfiles |
| **Real-time** | WebSockets, Server-Sent Events (SSE) |

### Frontend
| Component | Technology |
|-----------|-----------|
| **Framework** | React 19 |
| **Build Tool** | Vite (rolldown-vite) |
| **UI Library** | Material UI 7 (MUI) |
| **HTTP Client** | Axios |
| **Drag & Drop** | @dnd-kit, @hello-pangea/dnd |
| **State** | React hooks + Zustand |

### Infrastructure
| Component | Technology |
|-----------|-----------|
| **Containerization** | Docker (multi-stage builds) |
| **Orchestration** | Docker Compose, Kubernetes |
| **CI/CD** | Genesis CI (native) |
| **Monitoring** | Prometheus metrics, Grafana dashboards |
| **Caching** | Redis (optional) |
| **IDE Extension** | Grace OS VSCode Extension (TypeScript) |

---

## Project Structure

```
grace-3.1-/
├── backend/                    # FastAPI backend (Python)
│   ├── app.py                  # Main application (1700+ lines, 50+ routers)
│   ├── settings.py             # Centralized configuration
│   ├── logging_config.py       # Structured logging setup
│   ├── Dockerfile              # Multi-stage production build
│   ├── requirements.txt        # Python dependencies (81 packages)
│   ├── .env                    # Environment configuration
│   │
│   ├── mcp_repos/              # MCP Server Implementations
│   │   ├── DesktopCommanderMCP/ # Node.js MCP server for File/Terminal/Search
│   │   └── mcp-servers/        # Community MCP servers
│   │
│   ├── tests/                  # Backend test suites (100+ files)
│   │   ├── data/               # Test data and fixtures
│   │   ├── embedding/          # Embedding model tests
│   │   └── ollama/             # Ollama integration tests
│   │
│   ├── api/                    # API Router Layer (52 files)
│   │   ├── layer1.py           # Layer 1 cognitive processing
│   │   ├── retrieve.py         # RAG retrieval endpoints
│   │   ├── ingest.py           # Document ingestion
│   │   ├── librarian_api.py    # AI-powered librarian
│   │   ├── cognitive.py        # Cognitive system endpoints
│   │   ├── governance_api.py   # Three-pillar governance
│   │   ├── testing_api.py      # Autonomous testing
│   │   ├── streaming.py        # SSE streaming
│   │   ├── websocket.py        # WebSocket real-time
│   │   ├── voice_api.py        # Speech-to-text / text-to-speech
│   │   ├── agent_api.py        # Software engineering agent
│   │   ├── autonomous_api.py   # Autonomous action engine
│   │   ├── cicd_api.py         # Genesis CI/CD pipelines
│   │   ├── scraping.py         # Web scraping
│   │   ├── notion.py           # Notion task management
│   │   ├── grace_planning_api.py    # Concept-to-execution workflow
│   │   ├── grace_todos_api.py       # Autonomous task management
│   │   ├── ide_bridge_api.py        # VSCode extension bridge
│   │   └── ...                 # (38 more API modules)
│   │
│   ├── cognitive/              # Cognitive Processing (31 files)
│   │   ├── engine.py           # Core cognitive engine
│   │   ├── ooda.py             # OODA decision loop
│   │   ├── contradiction_detector.py
│   │   ├── ambiguity.py        # Ambiguity resolution
│   │   ├── episodic_memory.py  # Episode-based memory
│   │   ├── procedural_memory.py
│   │   ├── learning_memory.py  # Pattern extraction & learning
│   │   ├── mirror_self_modeling.py  # Self-reflection modeling
│   │   ├── active_learning_system.py
│   │   ├── continuous_learning_orchestrator.py
│   │   ├── autonomous_healing_system.py  # Self-healing
│   │   ├── autonomous_sandbox_lab.py     # Experimentation
│   │   ├── memory_mesh_*.py    # Memory mesh (cache, learner, metrics, snapshot)
│   │   ├── predictive_context_loader.py
│   │   ├── magma/              # MAGMA Sub-engine (10 files)
│   │   │   ├── grace_magma_system.py
│   │   │   ├── intent_router.py
│   │   │   ├── rrf_fusion.py   # Reciprocal Rank Fusion
│   │   │   ├── causal_inference.py
│   │   │   ├── topological_retrieval.py
│   │   │   ├── relation_graphs.py
│   │   │   ├── synaptic_ingestion.py
│   │   │   └── ...
│   │   └── ...
│   │
│   ├── genesis/                # Genesis Tracking System (29 files)
│   │   ├── symbiotic_version_control.py # Hybrid Git + Genesis versioning
│   │   ├── autonomous_engine.py    # Autonomous action engine
│   │   ├── autonomous_cicd_engine.py
│   │   ├── adaptive_cicd.py    # Trust/KPI-driven CI/CD
│   │   ├── cicd.py             # Core CI/CD pipeline
│   │   ├── file_watcher.py     # Filesystem monitoring
│   │   ├── file_version_tracker.py
│   │   ├── genesis_key_service.py  # Immutable provenance keys
│   │   ├── git_genesis_bridge.py   # Git integration
│   │   ├── healing_system.py   # Self-healing
│   │   ├── middleware.py       # Genesis key middleware
│   │   ├── repo_scanner.py     # Repository analysis
│   │   ├── whitelist_learning_pipeline.py  # Human → AI learning
│   │   ├── intelligent_cicd_orchestrator.py
│   │   └── ...
│   │
│   ├── ml_intelligence/        # ML Intelligence (20 files)
│   │   ├── neural_trust_scorer.py    # Neural trust scoring
│   │   ├── multi_armed_bandit.py     # MAB optimization
│   │   ├── meta_learning.py          # Meta-learning
│   │   ├── neuro_symbolic_reasoner.py
│   │   ├── contrastive_learning.py
│   │   ├── uncertainty_quantification.py
│   │   ├── active_learning_sampler.py
│   │   ├── trust_aware_embedding.py
│   │   ├── online_learning_pipeline.py
│   │   ├── kpi_tracker.py
│   │   ├── integration_orchestrator.py
│   │   └── ...
│   │
│   ├── librarian/              # AI Librarian System (10 files)
│   │   ├── engine.py           # Core librarian engine
│   │   ├── ai_analyzer.py      # AI-powered analysis
│   │   ├── relationship_manager.py
│   │   ├── rule_categorizer.py # Auto-categorization rules
│   │   ├── tag_manager.py      # Intelligent tagging
│   │   ├── approval_workflow.py
│   │   ├── genesis_key_curator.py
│   │   └── ...
│   │
│   ├── retrieval/              # RAG Retrieval (7 files)
│   │   ├── retriever.py        # Core vector retrieval
│   │   ├── cognitive_retriever.py   # Cognitive-enhanced retrieval
│   │   ├── trust_aware_retriever.py # Trust-scored retrieval
│   │   ├── query_intelligence.py    # Query classification
│   │   ├── reranker.py         # Result re-ranking
│   │   ├── multi_tier_integration.py
│   │   └── ...
│   │
│   ├── ingestion/              # Document Ingestion (7 files)
│   │   ├── service.py          # Core ingestion service
│   │   ├── file_manager.py     # File lifecycle management
│   │   ├── cli.py              # CLI ingestion tool
│   │   └── ...
│   │
│   ├── diagnostic_machine/     # 4-Layer Diagnostic (12 files)
│   │   ├── sensors.py          # System sensors
│   │   ├── interpreters.py     # Data interpretation
│   │   ├── judgement.py        # Decision making
│   │   ├── action_router.py    # Action execution
│   │   ├── healing.py          # Auto-healing
│   │   ├── cognitive_integration.py
│   │   ├── realtime.py         # Real-time monitoring
│   │   ├── trend_analysis.py
│   │   └── ...
│   │
│   ├── llm_orchestrator/       # LLM Management (9 files)
│   │   ├── llm_orchestrator.py # Core orchestration
│   │   ├── multi_llm_client.py # Multi-model client
│   │   ├── hallucination_guard.py  # Hallucination detection
│   │   ├── cognitive_enforcer.py
│   │   ├── fine_tuning.py      # Model fine-tuning
│   │   ├── llm_collaboration.py
│   │   └── ...
│   │
│   ├── security/               # Security (8 files)
│   │   ├── config.py           # Security configuration
│   │   ├── middleware.py       # Headers, rate limiting, validation
│   │   ├── auth.py             # Authentication
│   │   ├── governance.py       # Governance enforcement
│   │   ├── validators.py       # Input validation
│   │   └── ...
│   │
│   ├── database/               # Database Layer (19 files)
│   │   ├── session.py          # SQLAlchemy session management
│   │   ├── connection.py       # Multi-DB connection handling
│   │   ├── config.py           # Database configuration
│   │   ├── base.py             # Declarative base
│   │   ├── migration.py        # Table creation
│   │   ├── migrate_add_*.py    # Migration scripts
│   │   └── migrations/
│   │
│   ├── models/                 # Data Models (8 files)
│   │   ├── database_models.py  # SQLAlchemy models
│   │   ├── genesis_key_models.py
│   │   ├── librarian_models.py
│   │   ├── notion_models.py
│   │   ├── telemetry_models.py
│   │   └── repositories.py    # Repository pattern
│   │
│   ├── embedding/              # Embedding Engine
│   │   ├── embedder.py         # Sync embedding model
│   │   └── async_embedder.py   # Async embedding model
│   │
│   ├── ollama_client/          # Ollama LLM Client
│   │   └── client.py           # HTTP client for Ollama API
│   │
│   ├── vector_db/              # Qdrant Vector DB Client
│   │   └── client.py           # Qdrant connection management
│   │
│   ├── file_manager/            # File Intelligence (8 files)
│   │   ├── file_handler.py     # Core file operations
│   │   ├── adaptive_file_processor.py  # Smart file processing
│   │   ├── file_health_monitor.py      # File system health monitoring
│   │   ├── file_intelligence_agent.py  # AI-powered file analysis
│   │   ├── genesis_file_tracker.py     # Genesis-tracked files
│   │   ├── grace_file_integration.py   # System integration
│   │   └── knowledge_base_manager.py   # KB lifecycle management
│   │
│   ├── agent/                  # GRACE Agent Framework
│   │   └── grace_agent.py      # Core agent logic
│   │
│   ├── grace_mcp/              # Unified Agentic Orchestrator
│   │   ├── orchestrator.py     # Multi-turn tool-calling loop
│   │   ├── client.py           # MCP stdio client
│   │   ├── builtin_tools.py    # Local RAG & Web tools
│   │   └── audit_logger.py     # Tool execution auditing
│   │
│   ├── layer1/                 # Layer 1 Architecture
│   │   ├── message_bus.py      # Event-driven message bus
│   │   ├── initialize.py       # Component initialization
│   │   └── components/         # 11 pluggable connectors
│   │       ├── data_integrity_connector.py
│   │       ├── genesis_keys_connector.py
│   │       ├── ingestion_connector.py
│   │       ├── knowledge_base_connector.py
│   │       ├── kpi_connector.py
│   │       ├── llm_orchestration_connector.py
│   │       ├── memory_mesh_connector.py
│   │       ├── neuro_symbolic_connector.py
│   │       ├── rag_connector.py
│   │       └── version_control_connector.py
│   │
│   ├── execution/              # Code Execution Engine
│   │   ├── bridge.py           # Execution bridge
│   │   ├── governed_bridge.py  # Governance-controlled execution
│   │   ├── actions.py          # Action definitions
│   │   └── feedback.py         # Execution feedback
│   │
│   ├── search/                 # Web Search Integration
│   │   └── serpapi_service.py  # SerpAPI web search
│   │
│   ├── scraping/               # Web Scraping Engine
│   │   ├── service.py          # URL scraping service
│   │   ├── document_downloader.py
│   │   └── url_validator.py
│   │
│   ├── telemetry/              # System Telemetry
│   │   ├── telemetry_service.py
│   │   ├── replay_service.py   # Action replay
│   │   └── decorators.py       # Telemetry decorators
│   │
│   ├── confidence_scorer/      # Confidence Scoring
│   │   ├── confidence_scorer.py
│   │   └── contradiction_detector.py
│   │
│   ├── core/                   # Core Framework
│   │   ├── base_component.py   # Component base class
│   │   ├── registry.py         # Component registry
│   │   └── loop_output.py      # Processing loop output
│   │
│   ├── version_control/        # Git Integration
│   │   └── git_service.py      # Git operations service
│   │
│   ├── services/               # High-Level Services
│   │   ├── grace_autonomous_engine.py
│   │   ├── grace_systems_integration.py
│   │   └── grace_team_management.py
│   │
│   ├── cache/                  # Caching Layer
│   │   └── redis_cache.py      # Redis-based caching service
│   ├── utils/                  # Shared Utilities
│   │   ├── error_suppression.py  # Graceful error handling
│   │   ├── rag_prompt.py       # RAG prompt templates
│   │   └── structured_logging.py # JSON structured logs
│   ├── scripts/                # Utility scripts (7 files)
│   ├── setup/                  # Setup & initialization
│   │   └── initializer.py      # Full system initializer
│   └── tests/                  # Backend test suites (57 files)
│
├── frontend/                   # React 19 Frontend
│   ├── src/
│   │   ├── App.jsx             # Main app with routing
│   │   ├── main.jsx            # Entry point
│   │   ├── components/         # UI Components (90 files)
│   │   │   ├── ChatWindow.jsx  # Chat interface
│   │   │   ├── FileBrowser.jsx # File management
│   │   │   ├── CodeBaseTab.jsx # Code browser
│   │   │   ├── CognitiveTab.jsx
│   │   │   ├── LearningTab.jsx
│   │   │   ├── LibrarianTab.jsx
│   │   │   ├── GovernanceTab.jsx
│   │   │   ├── GracePlanningTab.jsx
│   │   │   ├── GraceTodosTab.jsx
│   │   │   ├── MLIntelligenceTab.jsx
│   │   │   ├── NotionTab.jsx
│   │   │   ├── CICDDashboard.jsx
│   │   │   ├── IngestionDashboard.jsx
│   │   │   ├── WebScraper.jsx
│   │   │   ├── VoiceButton.jsx
│   │   │   └── ...
│   │   ├── config/             # API configuration
│   │   └── store/              # State management
│   ├── package.json
│   ├── Dockerfile              # Nginx production build
│   │
│   │   ├── version_control/    # Version control sub-components (11 files)
│   │   │   ├── CommitTimeline.jsx
│   │   │   ├── DiffViewer.jsx
│   │   │   ├── GitTree.jsx
│   │   │   ├── ModuleHistory.jsx
│   │   │   └── RevertModal.jsx
│   └── vite.config.js
│
├── grace-os-vscode/            # VSCode Extension (TypeScript)
│   ├── src/                    # Extension source (39 files)
│   ├── package.json            # Extension manifest
│   └── tsconfig.json
│
├── docker-compose.yml          # Full-stack Docker deployment
├── k8s/                        # Kubernetes manifests
│   ├── deployment.yaml
│   └── services.yaml
├── pipelines/                  # CI/CD pipeline definitions
│   ├── grace-ci.yaml
│   └── grace-deploy.yaml
├── monitoring/                 # Monitoring configs
│   └── grafana-dashboard.json
├── .github/                    # GitHub integration
│   ├── workflows/
│   │   ├── ci.yml              # CI: lint, test, build
│   │   └── cd.yml              # CD: deploy
│   ├── ISSUE_TEMPLATE/
│   └── pull_request_template.md
├── tools/                      # Maintenance scripts
├── tests/                      # Integration tests (11 files)
├── benchmarks/                 # Embedding benchmarks
├── knowledge_base/             # User knowledge base directory
├── docs/                       # Documentation (229 files)
├── start.bat / start.sh        # Unified start scripts
├── CHANGELOG.md
├── CONTRIBUTING.md
└── .gitignore
```

---

## Getting Started

### Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| **Python** | 3.11+ | Backend runtime |
| **Node.js** | 20+ | Frontend build |
| **Ollama** | Latest | Local LLM server |
| **Qdrant** | Latest | Vector database |
| **CUDA** (optional) | 11.8+ | GPU-accelerated embeddings |
| **Docker** (optional) | Latest | Containerized deployment |
| **Git** | Latest | Version control |

### Run Grace natively

Grace runs natively via local scripts and Genesis CI/CD. No GitHub or external CI required.

- **Run the app:** One command runs everything: **`start.bat`** (no args) or **`start_grace.bat`** — starts Qdrant (if Docker), then backend (GPU venv) + frontend. See [Start scripts](docs/START_SCRIPTS.md).
- **Pull latest:** If you have an upstream remote, `git pull upstream main` (or `origin main`). See [Pull the latest GRACE](docs/START_SCRIPTS.md#pull-the-latest-grace).
- **CI/CD:** Use Genesis CI/CD only: pipelines `grace-ci`, `grace-quick`, and `grace-deploy` via `/api/cicd/trigger`. See [Genesis CI/CD docs](knowledge_base/cicd_pipelines/README.md).

### Local Development Setup

#### 1. Clone the Repository
```bash
git clone https://github.com/aaron031291/grace-3.1-.git
cd grace-3.1-
```

#### 2. Start External Services

**Ollama** (LLM inference):
```bash
# Install: https://ollama.ai
ollama serve
ollama pull mistral:7b
```

**Qdrant** (vector database):
```bash
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant:latest
```

#### 3. Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate
# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment config
copy .env.example .env   # Windows
cp .env.example .env     # Linux/Mac

# Start backend
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

#### 4. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

#### 5. Access the Application
| Service | URL |
|---------|-----|
| **Frontend UI** | http://localhost:5173 |
| **Backend API** | http://localhost:8000 |
| **API Docs (Swagger)** | http://localhost:8000/docs |
| **API Docs (ReDoc)** | http://localhost:8000/redoc |
| **Qdrant Dashboard** | http://localhost:6333/dashboard |

#### Quick Start (Windows)
```powershell
# PowerShell: use .\ (required for scripts in current folder)
.\start.bat           # One command: Qdrant + backend + frontend
.\start.bat backend   # Backend only
.\start.bat frontend # Frontend only
```
```cmd
REM CMD: from project folder (no args = everything)
start.bat
start.bat backend
```

#### Quick Start (Linux/Mac)
```bash
./start.sh           # Starts both backend + frontend
./start.sh backend   # Backend only
./start.sh frontend  # Frontend only
```

#### Check logs (last 200 lines) and GPU
- **Logs:** From project root, `backend\logs\grace.log` (or `backend/logs/grace.log` on Mac/Linux). In PowerShell: `Get-Content backend\logs\grace.log -Tail 200`
- **GPU / embedding:** With backend running, open **http://localhost:8000/api/runtime/connectivity** and check `services.embedding.using_gpu` and `cuda_available`. If `false`, use Python 3.12 and run `.\setup_gpu.bat` then restart the backend.

### Docker Deployment

```bash
# Full stack (backend + frontend + Qdrant)
docker-compose up -d

# With local Ollama
docker-compose --profile with-ollama up -d

# With GPU-accelerated Ollama
docker-compose --profile gpu up -d

# With PostgreSQL instead of SQLite
docker-compose --profile postgres up -d

# With Redis caching
docker-compose --profile cache up -d
```

**Docker services:**

| Service | Container | Port |
|---------|-----------|------|
| Backend API | `grace-backend` | 8000 |
| Frontend | `grace-frontend` | 80 |
| Qdrant | `grace-qdrant` | 6333, 6334 |
| Ollama | `grace-ollama` | 11434 |
| Ollama (GPU) | `grace-ollama-gpu` | 11434 |
| PostgreSQL | `grace-postgres` | 5432 |
| Redis | `grace-redis` | 6379 |

### Kubernetes Deployment

```bash
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/services.yaml
```

---

## Environment Configuration

All configuration is managed via `.env` in the `backend/` directory. Copy `.env.example` to `.env` and adjust:

### Security Settings
| Variable | Default | Description |
|----------|---------|-------------|
| `PRODUCTION_MODE` | `false` | Enable strict security (HTTPS cookies, HSTS) |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:3000,...` | Comma-separated allowed origins |
| `RATE_LIMIT_ENABLED` | `true` | Enable API rate limiting |
| `RATE_LIMIT_DEFAULT` | `100/minute` | Default rate limit |
| `RATE_LIMIT_AUTH` | `10/minute` | Auth endpoint rate limit |
| `RATE_LIMIT_UPLOAD` | `20/minute` | Upload endpoint rate limit |
| `RATE_LIMIT_AI` | `30/minute` | AI endpoint rate limit |
| `SESSION_COOKIE_SECURE` | `false` | HTTPS-only cookies (set `true` in prod) |
| `LOG_SECURITY_EVENTS` | `true` | Log security events |

### Database
| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_TYPE` | `sqlite` | `sqlite`, `postgresql`, `mysql`, `mariadb` |
| `DATABASE_PATH` | `./data/grace.db` | SQLite file path |
| `DATABASE_HOST` | `localhost` | Remote DB host |
| `DATABASE_PORT` | `0` | Remote DB port |
| `DATABASE_USER` | _(empty)_ | Remote DB username |
| `DATABASE_PASSWORD` | _(empty)_ | Remote DB password |
| `DATABASE_NAME` | `grace` | Database name |
| `DATABASE_ECHO` | `false` | SQL query logging |

### Ollama & LLM
| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_URL` | `http://localhost:11434` | Ollama server URL |
| `LLM_PROVIDER` | `ollama` | LLM provider: `ollama` or `openai` |
| `LLM_API_KEY` | _(empty)_ | OpenAI API Key (required for `openai`) |
| `LLM_MODEL` | `mistral:7b` | LLM model name (default: mistral:7b or gpt-4o) |
| `MAX_NUM_PREDICT` | `512` | Max tokens per response |

### Embeddings
| Variable | Default | Description |
|----------|---------|-------------|
| `EMBEDDING_DEFAULT` | `qwen_4b` | Embedding model name |
| `EMBEDDING_DEVICE` | `cuda` | `cuda` or `cpu` |
| `EMBEDDING_NORMALIZE` | `true` | Normalize embeddings |

### Qdrant Vector Database
| Variable | Default | Description |
|----------|---------|-------------|
| `QDRANT_HOST` | `localhost` | Qdrant host |
| `QDRANT_PORT` | `6333` | Qdrant port |
| `QDRANT_API_KEY` | _(empty)_ | API key (Qdrant Cloud) |
| `QDRANT_COLLECTION_NAME` | `documents` | Collection name |
| `QDRANT_TIMEOUT` | `30` | Request timeout (seconds) |

### Ingestion
| Variable | Default | Description |
|----------|---------|-------------|
| `INGESTION_CHUNK_SIZE` | `512` | Document chunk size |
| `INGESTION_CHUNK_OVERLAP` | `50` | Chunk overlap |
| `EXCLUDE_GENESIS_FROM_INGESTION` | `true` | Skip Genesis files during ingestion |

### Librarian
| Variable | Default | Description |
|----------|---------|-------------|
| `LIBRARIAN_AUTO_PROCESS` | `true` | Auto-process new documents |
| `LIBRARIAN_USE_AI` | `true` | AI-powered categorization |
| `LIBRARIAN_DETECT_RELATIONSHIPS` | `true` | Detect document relationships |
| `LIBRARIAN_AI_CONFIDENCE_THRESHOLD` | `0.6` | Min AI confidence for auto-apply |
| `LIBRARIAN_SIMILARITY_THRESHOLD` | `0.7` | Min similarity for relationships |
| `LIBRARIAN_MAX_RELATIONSHIP_CANDIDATES` | `20` | Max candidates per document |
| `LIBRARIAN_AI_MODEL` | `mistral:7b` | Model for librarian AI |

### SerpAPI (Web Search)
| Variable | Default | Description |
|----------|---------|-------------|
| `SERPAPI_KEY` | _(empty)_ | SerpAPI key |
| `SERPAPI_ENABLED` | `true` | Enable web search |
| `SERPAPI_MAX_RESULTS` | `5` | Max search results |
| `SERPAPI_AUTO_SCRAPE` | `true` | Auto-scrape search result pages |

### Component Control Flags
| Variable | Default | Description |
|----------|---------|-------------|
| `SKIP_QDRANT_CHECK` | `false` | Skip Qdrant connectivity check |
| `SKIP_OLLAMA_CHECK` | `false` | Skip Ollama connectivity check |
| `SKIP_AUTO_INGESTION` | `false` | Disable background ingestion |
| `SKIP_EMBEDDING_LOAD` | `false` | Skip embedding model loading |
| `LIGHTWEIGHT_MODE` | `false` | Disable all heavy components |
| `DISABLE_GENESIS_TRACKING` | `false` | Disable provenance tracking |
| `DISABLE_CONTINUOUS_LEARNING` | `false` | Disable autonomous learning |
| `HEALING_SIMULATION_MODE` | `false` | Simulated self-healing |

### Error Suppression
| Variable | Default | Description |
|----------|---------|-------------|
| `SUPPRESS_INGESTION_ERRORS` | `false` | Continue on ingestion errors |
| `SUPPRESS_GENESIS_ERRORS` | `false` | Continue on Genesis errors |
| `SUPPRESS_QDRANT_ERRORS` | `false` | Continue on Qdrant errors |
| `SUPPRESS_EMBEDDING_ERRORS` | `false` | Continue on embedding errors |

### Application
| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `false` | Enable debug mode |
| `LOG_LEVEL` | `INFO` | Logging level |

---

## Core Systems

### 1. Multi-Tier RAG Pipeline

GRACE enforces a RAG-first approach with three-tier query fallback:

```
User Query
    │
    ▼
┌─────────────────────┐
│  Tier 1: VectorDB   │ ← Qdrant semantic search (highest confidence)
│  (Qdrant)            │
└────────┬────────────┘
         │ no results above threshold
         ▼
┌─────────────────────┐
│  Tier 2: Model      │ ← LLM's parametric knowledge (medium confidence)
│  Knowledge           │
└────────┬────────────┘
         │ low confidence
         ▼
┌─────────────────────┐
│  Tier 3: User       │ ← Request user context / web search (lowest)
│  Context + SerpAPI   │
└─────────────────────┘
```

**Key modules:**
- `retrieval/retriever.py` — Core vector retrieval against Qdrant
- `retrieval/cognitive_retriever.py` — Enhanced retrieval with cognitive layer
- `retrieval/trust_aware_retriever.py` — Trust-scored retrieval
- `retrieval/query_intelligence.py` — Query classification and routing
- `retrieval/reranker.py` — Result re-ranking with confidence scoring
- `retrieval/multi_tier_integration.py` — Tier fallback orchestration

**Supported document formats:** PDF, DOCX, PPTX, XLSX, TXT, Markdown, Python, JSON, YAML, CSV

---

### 2. Cognitive System

The cognitive layer provides GRACE with reasoning, memory, and self-improvement capabilities.

| Module | Purpose |
|--------|---------|
| `engine.py` | Core cognitive processing engine |
| `ooda.py` | OODA (Observe-Orient-Decide-Act) decision loop |
| `contradiction_detector.py` | Detect conflicting information across documents |
| `ambiguity.py` | Resolve ambiguous queries |
| `episodic_memory.py` | Store and retrieve experience episodes |
| `procedural_memory.py` | Remember how to perform tasks |
| `learning_memory.py` | Extract and store learned patterns |
| `mirror_self_modeling.py` | Self-reflection and self-awareness |
| `active_learning_system.py` | Identify knowledge gaps, request learning |
| `continuous_learning_orchestrator.py` | Background autonomous learning loop |
| `autonomous_healing_system.py` | Self-diagnose and self-repair |
| `autonomous_sandbox_lab.py` | Run experiments in isolated sandbox |
| `memory_mesh_*.py` | Distributed memory mesh (cache, learning, metrics, snapshots) |
| `predictive_context_loader.py` | Pre-load relevant context |
| `thread_learning_orchestrator.py` | Multi-threaded learning |
| `learning_subagent_system.py` | Spawn sub-agents for specific learning tasks |

---

### 3. Genesis Tracking System

Genesis provides **immutable provenance tracking** — every data mutation in the system is tracked with a Genesis Key, creating a complete audit trail.

**Key capabilities:**
- **Genesis Keys** — Unique identifiers for every creation, modification, or deletion
- **File Version Tracking** — Full version history of all files
- **File Watcher** — Real-time filesystem monitoring with automatic tracking
- **Git Bridge** — Sync Genesis tracking with Git commits
- **CI/CD Integration** — Self-hosted CI/CD pipelines with trust-based gating
- **Adaptive CI/CD** — KPI-driven pipeline adjustments
- **Whitelist Learning** — Human-curated input feeding back into system learning
- **Repository Scanning** — Analyze codebases for patterns and structure

---

### 4. ML Intelligence Module

Production ML capabilities for trust scoring, exploration vs. exploitation, and meta-learning.

| Module | Algorithm |
|--------|-----------|
| `neural_trust_scorer.py` | Neural network trust scoring |
| `multi_armed_bandit.py` | Thompson Sampling / UCB for exploration |
| `meta_learning.py` | Few-shot meta-learning (MAML-inspired) |
| `neuro_symbolic_reasoner.py` | Hybrid neural + symbolic reasoning |
| `contrastive_learning.py` | Contrastive representation learning |
| `uncertainty_quantification.py` | Bayesian uncertainty estimation |
| `active_learning_sampler.py` | Pool-based active learning |
| `trust_aware_embedding.py` | Trust-weighted embeddings |
| `online_learning_pipeline.py` | Streaming online learning |
| `kpi_tracker.py` | KPI monitoring and alerts |

---

### 5. Librarian System

AI-powered document management with intelligent categorization and relationship detection.

- **AI Analyzer** — Automatically categorize and tag documents using LLM
- **Rule Categorizer** — Rule-based categorization with customizable rules
- **Relationship Manager** — Detect semantic relationships between documents
- **Tag Manager** — Intelligent tagging with tag suggestions
- **Approval Workflow** — Human-in-the-loop approval for AI suggestions
- **Genesis Key Curator** — Track librarian changes via Genesis

---

### 6. Diagnostic Machine (4-Layer)

A bio-inspired diagnostic system modeled after biological health monitoring:

```
┌──────────┐    ┌──────────────┐    ┌───────────┐    ┌──────────────┐
│  Sensors │ ──►│ Interpreters │ ──►│ Judgement  │ ──►│ Action Router│
│          │    │              │    │            │    │              │
│ - CPU    │    │ - Anomaly    │    │ - Risk     │    │ - Auto-heal  │
│ - Memory │    │   detection  │    │   scoring  │    │ - Alert      │
│ - Disk   │    │ - Threshold  │    │ - Priority │    │ - Escalate   │
│ - Network│    │   analysis   │    │   matrix   │    │ - Rollback   │
│ - Qdrant │    │ - Trend      │    │            │    │              │
│ - Ollama │    │   analysis   │    │            │    │              │
└──────────┘    └──────────────┘    └───────────┘    └──────────────┘
```

---

### 7. LLM Orchestrator

Multi-model LLM management with safety guardrails:

- **Multi-LLM Client** — Connect to multiple Ollama instances or models
- **Hallucination Guard** — Detect and prevent hallucinated responses
- **Cognitive Enforcer** — Enforce response quality standards
- **Fine-Tuning** — Model fine-tuning pipeline
- **LLM Collaboration** — Multi-model consensus responses
- **Repository Access** — Give LLMs access to code context

---

### 8. Unified Agentic Orchestrator

The central nervous system for Grace OS agentic capabilities. It manages multi-turn tool-calling loops across both local (Built-in) and remote (MCP) tools.

- **Orchestration Loop** — Stateful management of conversation turns and tool execution
- **Provider Agnostic** — Works seamlessly with Ollama, OpenAI, and other Tool-Calling LLMs
- **Audit Logging** — Full transparency into every tool call made by the agent

#### Available Tools

| Category | Tools | Description |
|----------|-------|-------------|
| **Local (Built-in)** | `rag_search`, `web_search`, `web_fetch` | Knowledge base search & internet access |
| **Filesystem (MCP)** | `read_file`, `write_file`, `list_directory`, `move_file`, `get_file_info`, `write_pdf` | Full disk I/O with safety boundaries |
| **Terminal (MCP)** | `start_process`, `read_process_output`, `interact_with_process`, `force_terminate` | OS-level command execution |
| **Search (MCP)** | `start_search`, `get_more_search_results` | Advanced local filesystem indexing & search |
| **Code (MCP)** | `edit_block` | Surgical search-and-replace for file modifications |

---

### 9. Agent Framework

A software engineering agent capable of autonomous code execution:

- **Grace Agent** (`agent/grace_agent.py`) — Task decomposition, planning, and execution
- **Execution Bridge** (`execution/bridge.py`) — Safe code execution sandbox
- **Governed Bridge** (`execution/governed_bridge.py`) — Governance-controlled execution
- **Feedback Loop** (`execution/feedback.py`) — Results feedback for learning

---

### 10. MAGMA Subsystem

**M**ulti-**A**gent **G**raph-based **M**emory **A**rchitecture — an advanced cognitive processing engine:

| Module | Purpose |
|--------|---------|
| `grace_magma_system.py` | Core MAGMA coordinator |
| `intent_router.py` | Query intent classification and routing |
| `rrf_fusion.py` | Reciprocal Rank Fusion for multi-source results |
| `causal_inference.py` | Causal relationship discovery |
| `topological_retrieval.py` | Graph-based topological retrieval |
| `relation_graphs.py` | Knowledge relation graphs |
| `synaptic_ingestion.py` | Neural-inspired ingestion pipeline |
| `async_consolidation.py` | Async memory consolidation |
| `layer_integrations.py` | Cross-layer integration |

---

## API Reference

GRACE exposes **50+ API router modules** via FastAPI. Interactive documentation is available at `/docs` (Swagger) and `/redoc` (ReDoc) when the server is running.

### Core Endpoints

| Category | Prefix | Key Endpoints |
|----------|--------|---------------|
| **Chat** | `/chat` | `POST /chat`, `POST /chats`, `GET /chats/{id}/history` |
| **Health** | `/health` | `GET /health`, `GET /api/health/comprehensive` |
| **Metrics** | `/metrics` | `GET /metrics` (Prometheus format) |
| **Streaming** | `/api/stream` | SSE streaming chat |
| **WebSocket** | `/ws` | Real-time bidirectional updates |
| **Master Integration** | `/api/master` | Cross-system integration |

### Knowledge & Retrieval

| Category | Prefix | Description |
|----------|--------|-------------|
| **Ingest** | `/api/ingest` | Document upload & ingestion |
| **Retrieve** | `/api/retrieve` | RAG retrieval queries |
| **Librarian** | `/api/librarian` | AI document management |
| **Knowledge Base** | `/api/knowledge-base` | External KB connectors |
| **File Management** | `/api/files` | File CRUD operations |
| **Directory Hierarchy** | `/api/directory-hierarchy` | Directory tree navigation |
| **File Ingestion** | `/api/file-ingestion` | File auto-ingestion |
| **Web Scraping** | `/api/scraping` | URL scraping & crawling |

### Cognitive & Learning

| Category | Prefix | Description |
|----------|--------|-------------|
| **Cognitive** | `/api/cognitive` | Cognitive system endpoints |
| **Layer 1** | `/api/layer1` | Layer 1 cognitive processing |
| **Learning Memory** | `/api/learning-memory` | Learning pattern storage |
| **ML Intelligence** | `/api/ml-intelligence` | Neural trust, bandits, meta-learning |
| **Autonomous Learning** | `/api/autonomous-learning` | Self-directed learning |
| **Proactive Learning** | `/api/proactive-learning` | Knowledge gap detection |
| **Training** | `/api/training` | Model training endpoints |
| **Learning Efficiency** | `/api/learning-efficiency` | Data-to-insight metrics |

### Genesis & Governance

| Category | Prefix | Description |
|----------|--------|-------------|
| **Genesis Keys** | `/api/genesis-keys` | Provenance key management |
| **Version Control** | `/api/version-control` | File versioning |
| **Governance** | `/api/governance` | Three-pillar governance |
| **Repositories** | `/api/repositories` | Multi-repo management |
| **Repo Genesis** | `/api/repo-genesis` | Repository analysis |

### CI/CD & Automation

| Category | Prefix | Description |
|----------|--------|-------------|
| **CI/CD** | `/api/cicd` | Genesis CI/CD pipelines |
| **CI/CD Versioning** | `/api/cicd-versioning` | Pipeline version control |
| **Adaptive CI/CD** | `/api/adaptive-cicd` | Trust/KPI-driven CI/CD |
| **Knowledge Base CI/CD** | `/api/kb-cicd` | KB pipeline integration |
| **Autonomous** | `/api/autonomous` | Autonomous action engine |
| **Autonomous CI/CD** | `/api/autonomous-cicd` | AI-driven CI/CD automation |
| **Testing** | `/api/testing` | Autonomous self-testing |
| **Whitelist** | `/api/whitelist` | Human-to-AI learning pipeline |

### Tools & Utilities

| Category | Prefix | Description |
|----------|--------|-------------|
| **Auth** | `/api/auth` | Authentication |
| **Voice** | `/api/voice` | STT/TTS voice interaction |
| **Agent** | `/api/agent` | Software engineering agent |
| **Notion** | `/api/notion` | Kanban task management |
| **Context** | `/api/context` | User context submission |
| **Telemetry** | `/api/telemetry` | System telemetry |
| **Monitoring** | `/api/monitoring` | Health monitoring |
| **KPI** | `/api/kpi` | KPI dashboard |
| **Sandbox Lab** | `/api/sandbox` | Experimentation sandbox |
| **Diagnostic** | `/api/diagnostic` | 4-layer diagnostic |
| **Codebase** | `/api/codebase` | Code browsing & analysis |
| **IDE Bridge** | `/api/ide-bridge` | VSCode extension bridge |
| **Grace Todos** | `/api/grace-todos` | Autonomous task management |
| **Grace Planning** | `/api/grace-planning` | Concept → execution workflow |
| **Ingestion Pipeline** | `/api/ingestion` | Librarian ingestion |
| **Ingestion Integration** | `/api/ingestion-integration` | Complete autonomous ingestion cycle |
| **LLM Orchestration** | `/api/llm-orchestration` | Multi-LLM management |
| **Unified Agentic** | `/api/mcp` | Multi-turn tool-calling & MCP API |

---

## Frontend

The React 19 frontend provides a rich, interactive UI with **90 component files** across **40+ specialized tabs and panels**:

| Component | Description |
|-----------|-------------|
| `ChatWindow` | Main chat interface with markdown rendering |
| `ChatList` | Conversation sidebar with search |
| `FileBrowser` | File upload, download, and browsing |
| `CodeBaseTab` | Source code browsing and analysis |
| `LibrarianTab` | AI document management dashboard |
| `CognitiveTab` | Cognitive system visualization |
| `LearningTab` | Learning progress and patterns |
| `MLIntelligenceTab` | ML metrics and trust scores |
| `GovernanceTab` | Governance workflow management |
| `GracePlanningTab` | Concept-to-execution workflow |
| `GraceTodosTab` | Drag-and-drop task management |
| `NotionTab` | Kanban-style task board |
| `CICDDashboard` | CI/CD pipeline monitoring |
| `IngestionDashboard` | Document ingestion status |
| `KPIDashboard` | System KPI metrics |
| `SandboxTab` | Experimentation sandbox |
| `ExperimentTab` | Experiment results |
| `OrchestrationTab` | LLM orchestration controls |
| `ResearchTab` | Research and analysis |
| `RAGTab` | RAG pipeline visualization |
| `InsightsTab` | System insights |
| `TelemetryTab` | Telemetry data viewer |
| `MonitoringTab` | System health monitoring |
| `WebScraper` | URL scraping interface |
| `VersionControl` | Genesis version control viewer |
| `GenesisKeyPanel/Tab` | Genesis key explorer |
| `WhitelistTab` | Human-in-the-loop learning |
| `VoiceButton` | Voice interaction controls |
| `PersistentVoicePanel` | Always-on voice panel |
| `SearchInternetButton` | SerpAPI web search |
| `ConnectorsTab` | External connectors |
| `RepositoryManager` | Multi-repo management |
| `KnowledgeBaseManager` | Knowledge base management |
| `APITab` | API testing interface |
| `DirectoryChat` | Folder-scoped chat |
| `GenesisLogin` | Authentication UI |
| `ErrorBoundary` | Error handling |
| `Skeleton` | Loading state |
| `Toast` | Notifications |
| `LazyComponents` | Code-split lazy loading |

---

## Database

GRACE supports multiple database backends via SQLAlchemy:

| Backend | Config Value | Status |
|---------|-------------|--------|
| **SQLite** | `sqlite` | Default, zero-config |
| **PostgreSQL** | `postgresql` | Production recommended |
| **MySQL** | `mysql` | Supported |
| **MariaDB** | `mariadb` | Supported |

### Database Models

| Model | Description |
|-------|-------------|
| `Chat` | Chat sessions |
| `ChatHistory` | Messages in chats |
| `Document` | Ingested documents |
| `GenesisKey` | Immutable provenance keys |
| `LibrarianDocument` | Librarian metadata |
| `NotionTask` | Task management |
| `TelemetryEvent` | Telemetry data points |
| `QueryIntelligence` | Query classification results |

### Migrations

Run migrations with:
```bash
cd backend
python run_all_migrations.py
```

Individual migration scripts are in `database/migrate_add_*.py`.

---

## Security

GRACE includes a comprehensive security framework:

### Middleware Stack (applied in order)
1. **SecurityHeadersMiddleware** — HSTS, CSP, X-Frame-Options, etc.
2. **RateLimitMiddleware** — Configurable per-endpoint rate limiting
3. **RequestValidationMiddleware** — Input validation and sanitization
4. **CORSMiddleware** — Cross-origin resource sharing

### Features
- Input validation and sanitization (`security/validators.py`)
- SQL injection protection
- XSS protection headers
- Rate limiting per endpoint type (auth, upload, AI, default)
- Security event logging
- Production mode with stricter policies
- Three-pillar governance (`security/governance.py`) for critical actions

---

## CI/CD

### GitHub Actions

**CI Pipeline** (`.github/workflows/ci.yml`):
- Matrix testing across Python 3.10 and 3.11
- Flake8 linting (critical errors block, others warn)
- Pytest test execution
- Mypy type checking
- Frontend npm lint and build
- Docker image build verification

**CD Pipeline** (`.github/workflows/cd.yml`):
- Automated deployment on main branch pushes

### Self-Hosted Genesis CI/CD
GRACE also includes its own CI/CD system:
- `genesis/cicd.py` — Core CI/CD pipeline
- `genesis/adaptive_cicd.py` — Trust and KPI-driven pipeline adjustments
- `genesis/intelligent_cicd_orchestrator.py` — AI-powered CI/CD orchestration

---

## Startup & Self-Healing

GRACE is designed for high availability and autonomous recovery:

- **JSON Self-Healing** — Automatic detection and repair of truncated or corrupted `.json` configuration files.
- **Model Fallback** — Intelligent fallback to alternative LLM providers (e.g., switching to Ollama if OpenAI is unavailable).
- **Schema Migrations** — Automatic database schema synchronization on startup via `run_all_migrations.py`.
- **Environment Validation** — Strict verification of required API keys and connection strings before system boot.

---

## Monitoring & Telemetry

| Component | Description |
|-----------|-------------|
| `/metrics` | Prometheus-format metrics endpoint |
| `monitoring/grafana-dashboard.json` | Pre-built Grafana dashboard |
| `telemetry/telemetry_service.py` | System telemetry (drift detection, baselines, alerts) |
| `telemetry/replay_service.py` | Action replay for debugging |
| `diagnostic_machine/` | 4-layer diagnostic system |
| `api/monitoring_api.py` | System health monitoring API |
| `api/kpi_api.py` | KPI dashboard API |

---

## Grace OS VSCode Extension

A dedicated VSCode extension (`grace-os-vscode/`) that connects the IDE to GRACE:

- **IDE Bridge API** — Bidirectional communication between VSCode and GRACE
- **Cognitive IDE** — AI-powered code analysis and suggestions
- **Genesis Integration** — Track code changes in real-time via Genesis Keys
- Located at `grace-os-vscode/` with its own `package.json` and TypeScript source

---

## Testing

### Backend Tests
```bash
cd backend

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=.

# Run specific test
pytest tests/test_mcp_chat.py -v

# Lint check (critical errors only)
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
```

### Frontend Tests
```bash
cd frontend
npm run lint
npm run build   # Validates the build
```

### Integration Tests
```bash
# From root directory
cd tests/
pytest -v
```

### Benchmark Tests
```bash
cd benchmarks/
python benchmark_embedding_optimized.py
python benchmark_embedding_parallel.py
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines. Key points:

- **Branch naming**: `feature/`, `fix/`, `docs/`, `refactor/`, `test/`
- **Commit style**: Conventional Commits (`feat(scope): description`)
- **Python style**: PEP 8, type hints, 120 char max line length
- **Frontend style**: ESLint, functional components with hooks
- **Testing**: All PRs should include tests
- **CI**: All checks must pass before merge

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for full version history.

| Version | Date | Highlights |
|---------|------|------------|
| **3.1.0** | 2026-01-14 | Production readiness — Docker, CI/CD, Security |
| **3.0.0** | 2026-01-01 | Cognitive system, Agent framework, ML Intelligence |
| **2.0.0** | 2025-06-01 | RAG pipeline, Document ingestion |
| **1.0.0** | 2025-01-01 | Initial release |

---

<p align="center">
  Built with ❤️ by the GRACE team
</p>
