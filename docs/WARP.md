# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

GRACE (Generative Recursive Autonomous Cognitive Engine) is an autonomous AI system with self-healing, self-modeling, and adaptive learning capabilities. The system combines FastAPI backend, React frontend, vector database (Qdrant), and LLM orchestration (Ollama) to provide intelligent document management, knowledge base operations, and autonomous learning workflows.

## Development Commands

### Backend

```bash
# Start backend server (development)
cd backend
uvicorn app:app --reload --port 8000

# Run all tests
cd backend
pytest tests/ -v

# Run specific test file
pytest tests/test_api_monitoring.py -v

# Run tests with coverage
pytest tests/ -v --cov=.

# Start with Gunicorn (production)
cd backend
gunicorn app:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Frontend

```bash
# Development server
cd frontend
npm run dev

# Build for production
npm run build

# Lint code
npm run lint

# Preview production build
npm run preview
```

### Docker

```bash
# Start full stack with SQLite (development)
docker-compose up -d

# Start with PostgreSQL (production)
docker-compose --profile postgres up -d

# Start with Ollama (local LLM)
docker-compose --profile with-ollama up -d

# Start with GPU support
docker-compose --profile gpu up -d

# View logs
docker-compose logs -f backend

# Restart service
docker-compose restart backend

# Stop all services
docker-compose down
```

### Database

```bash
# Run migrations
cd backend
python -c "from database.migration import create_tables; create_tables()"

# Initialize with seed data
python database/init_example.py

# Verify database status
python check_db.py
```

### Verification

```bash
# Run system verification
./verify_system.sh

# Verify documents chat feature
./verify_documents_chat.sh

# Check vector database health
curl http://localhost:6333/health
```

## Architecture

### High-Level System Architecture

GRACE consists of several interconnected layers:

**Layer 1 - Master Integration**: Central orchestration hub that connects all subsystems through the Genesis Key system. Handles input processing, event routing, and system-wide coordination.

**Genesis Keys**: Immutable audit trail tracking system that records all operations with what/where/when/who/how/why metadata. Every significant event creates a Genesis Key that enables autonomous triggers, debugging, and forensic analysis.

**Cognitive Layer**: Implements autonomous learning, self-healing, and mirror self-modeling:
- `autonomous_healing_system.py`: 5 health levels, 7 anomaly types, 8 healing actions with trust-based execution
- `mirror_self_modeling.py`: Self-awareness through operation observation, pattern detection, and recursive improvement
- `ingestion_self_healing_integration.py`: Complete autonomous cycle for file ingestion with learning triggers

**Learning Orchestrator**: 8-process learning system (3 study agents, 2 practice agents, 1 mirror, 2 collectors) with Memory Mesh for knowledge gap tracking and prioritization.

**Diagnostic Machine**: 4-layer diagnostic system with sensors, interpreters, judgment engine, and action router for system health monitoring and anomaly response.

**Agent Framework**: Software engineering agent capabilities with code generation, testing, deployment, and autonomous task execution via the Governed Bridge.

### Backend Structure

```
backend/
├── api/                    # FastAPI routers (50+ endpoints)
│   ├── ingestion_integration.py  # Complete autonomous ingestion cycle
│   ├── master_integration.py     # Layer 1 master orchestrator
│   ├── agent_api.py             # Software agent endpoints
│   ├── governance_api.py        # Three-pillar governance
│   └── ...                      # 40+ other API modules
├── cognitive/              # Autonomous learning & self-healing
│   ├── autonomous_healing_system.py
│   ├── mirror_self_modeling.py
│   └── proactive_learner.py
├── genesis/                # Genesis Key system & triggers
│   ├── autonomous_triggers.py
│   ├── comprehensive_tracker.py
│   └── cicd.py            # Genesis-based CI/CD
├── layer1/                 # Master integration layer
│   ├── master_integration_layer.py
│   └── message_bus.py
├── agent/                  # Software agent framework
│   └── grace_agent.py
├── diagnostic_machine/     # 4-layer diagnostics
│   ├── sensors.py
│   ├── interpreters.py
│   ├── judgement.py
│   └── action_router.py
├── llm_orchestrator/       # Multi-LLM coordination
│   └── orchestrator.py
├── embedding/              # Vector embeddings (2560-dim)
│   └── embedder.py
├── ingestion/              # Document processing pipeline
│   └── service.py
├── vector_db/              # Qdrant client
│   └── client.py
├── database/               # SQLAlchemy models & migrations
│   ├── models.py
│   └── migration.py
└── app.py                  # Main FastAPI application
```

### Frontend Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── ChatInterface.jsx       # Main chat interface
│   │   ├── FileBrowser.jsx         # File management UI
│   │   ├── GenesisKeyTab.jsx       # Genesis Key viewer
│   │   ├── LibrarianTab.jsx        # Librarian interface
│   │   ├── CodeBaseTab.jsx         # Codebase browser
│   │   ├── APITab.jsx              # API testing interface
│   │   └── version_control/        # Git version control
│   │       ├── CommitTimeline.jsx
│   │       └── GitTree.jsx
│   └── App.jsx                     # Main app with tab routing
└── package.json
```

### Key Data Flow: File Ingestion → Learning → Self-Healing

```
1. File Upload
   ↓
2. Genesis Key Created (FILE_INGESTION)
   ↓
3. Text Extraction (PDF/TXT/MD) → Chunking (512 chars, 50 overlap)
   ↓
4. Embedding Generation (Qwen-4B, 2560-dim) → Qdrant Storage
   ↓
5. Autonomous Learning Triggered (study task created)
   ↓
6. Health Check → Self-Healing (if anomalies detected)
   ↓
7. Mirror Observation (every 10th operation) → Pattern Detection
   ↓
8. Improvement Suggestions → Learning Tasks Triggered
   ↓
9. Continuous Iteration & Self-Improvement
```

### Critical Systems Integration

**Genesis Keys track everything**: Every file ingestion, API call, learning event, healing action, and system state change creates a Genesis Key with complete metadata (what/where/when/who/how/why).

**Autonomous Triggers**: Genesis Keys automatically trigger downstream actions:
- ERROR keys → Self-healing system activated
- FILE_INGESTION keys → Learning orchestrator triggered
- Every 50 operations → Mirror self-modeling analysis

**Trust-Based Execution**: Healing actions have trust levels (0-9). System only executes actions if trust score allows, with multi-LLM consensus for complex decisions.

**Memory Mesh**: Tracks knowledge gaps, learning priorities, and confidence scores. Immutable ledger of all learning activities with genesis key correlation.

## Important Implementation Details

### Vector Database Configuration

**Critical**: Qdrant collection MUST use 2560-dimensional vectors (not 384). The embedding model is Qwen2.5-Coder-1.5B-Instruct which produces 2560-dim vectors. Dimension mismatch causes silent ingestion failures.

```python
# Correct Qdrant collection config
qdrant_client.create_collection(
    collection_name="documents",
    vectors_config=VectorParams(size=2560, distance=Distance.COSINE)
)
```

### Database Tables

Core tables:
- `documents`: File metadata with confidence scores
- `chunks`: Text chunks with embeddings
- `genesis_keys`: Complete audit trail (what/where/when/who/how/why)
- `learning_tasks`: Autonomous learning task queue
- `memory_mesh_entries`: Knowledge gap tracking
- `chats` / `chat_history`: Conversation management
- `librarian_rules`: Rule-based categorization

### Environment Configuration

Required environment variables:
- `DATABASE_TYPE`: sqlite (dev) or postgresql (prod)
- `QDRANT_HOST`: Vector database host (default: localhost)
- `OLLAMA_URL`: LLM service URL (default: http://localhost:11434)
- `EMBEDDING_DEVICE`: cpu or cuda
- `LOG_LEVEL`: INFO (dev) or WARNING (prod)

### API Endpoint Structure

Major API groups:
- `/files/*`: File management (upload, browse, delete)
- `/retrieve/*`: Semantic search and retrieval
- `/genesis-keys/*`: Genesis Key querying and filtering
- `/grace/*`: Master integration status and control
- `/ingestion-integration/*`: Complete autonomous ingestion cycle
- `/agent/*`: Software agent task execution
- `/cognitive/*`: Self-healing and mirror endpoints
- `/health`: Comprehensive system health check

### Version Control Integration

GRACE includes built-in Git version control via Dulwich (pure Python):
- `backend/version_control/git_service.py`: Git operations
- `backend/api/version_control.py`: Version control API
- Frontend components for commit history, tree view, diff viewing

### Testing Strategy

Tests are organized by component:
- `backend/tests/test_api_*.py`: API endpoint tests
- `backend/tests/test_diagnostic_machine.py`: Diagnostic system tests
- `backend/tests/test_contradiction_detection.py`: Semantic contradiction tests
- `backend/test_*.py`: Integration tests at root level
- `tests/`: System-level integration tests

Run tests from `backend/` directory. Some tests require Qdrant running.

### Common Pitfalls

**Qdrant must be running**: System fails silently if vector database is unavailable. Always verify: `curl http://localhost:6333/health`

**First embedding model load is slow**: Initial model download/load takes 2-3 seconds. Subsequent operations are fast.

**Genesis Keys are immutable**: Never modify existing keys. Create new keys for state changes.

**Trust scores affect healing**: Low trust scores prevent autonomous healing actions. Check trust levels before debugging healing failures.

**Memory Mesh requires learning tasks**: Knowledge gaps only resolve when learning tasks complete. Check `learning_tasks` table for pending work.

## Code Patterns

### Creating Genesis Keys

```python
from genesis.comprehensive_tracker import ComprehensiveTracker

tracker = ComprehensiveTracker()
key = tracker.create_genesis_key(
    event_type="FILE_INGESTION",
    what="Ingested document.pdf",
    where="knowledge_base/documents/",
    when=datetime.utcnow(),
    who="system",
    why="User upload request",
    how="Multi-modal ingestion pipeline",
    details={"filename": "document.pdf", "size": 1024}
)
```

### Triggering Autonomous Learning

```python
from api.ingestion_integration import router

# POST /ingestion-integration/ingest-file
# This automatically:
# 1. Creates Genesis Key
# 2. Ingests file
# 3. Triggers learning task
# 4. Monitors health
# 5. Runs mirror observation (periodic)
```

### Multi-LLM Orchestration

```python
from llm_orchestrator.orchestrator import LLMOrchestrator

orchestrator = LLMOrchestrator()
result = await orchestrator.generate_with_consensus(
    prompt="Analyze this system anomaly",
    num_models=3,
    consensus_threshold=0.7
)
```

## Architecture Diagrams

See detailed architecture documentation in:
- `COMPLETE_SYSTEM_SUMMARY.md`: Complete autonomous system overview
- `ARCHITECTURE_VERSION_CONTROL.md`: Version control architecture
- `DEPLOYMENT_GUIDE.md`: Production deployment architecture
- `COGNITIVE_BLUEPRINT.md`: Cognitive layer architecture
- `LAYER1_COMPLETE_INPUT_SYSTEM.md`: Master integration architecture

## Deployment

Production deployment uses:
- **PostgreSQL**: Production database (replace SQLite)
- **Nginx**: Reverse proxy with rate limiting
- **Docker**: Multi-container orchestration
- **Gunicorn**: Production WSGI server
- **TLS/SSL**: Certbot for Let's Encrypt certificates

See `DEPLOYMENT_GUIDE.md` for complete production setup.

## Monitoring & Health

System health endpoint: `GET /health`

Returns status of:
- Ollama LLM service
- Qdrant vector database
- Database connection
- Available models
- System components (Layer 1, Learning Orchestrator, Memory Mesh)

Genesis Keys provide complete audit trail for forensic analysis.
