# GRACE AI Copilot Instructions

## System Overview

GRACE is a **neuro-symbolic AI system** combining neural pattern learning (LLM/embeddings) with symbolic reasoning (trust-scored knowledge graphs). It is NOT just "RAG + LLM" - it's an autonomous learning platform with self-reflection, memory persistence, and cognitive decision-making.

### Core Architecture

```
Genesis Keys (Universal Tracking)
    ↓
Layer 1 (Trust-Scored Learning Memory) ← Foundation of all knowledge
    ↓
Memory Mesh (Episodic + Procedural + Patterns)
    ↓
OODA Loop (Observe → Orient → Decide → Act) ← All decisions flow here
    ↓
Autonomous Systems (Self-healing, Mirror observation, Learning triggers)
```

**Key Principle**: Every input/change is tracked via Genesis Keys with what/where/when/who/why/how metadata. This enables complete provenance, version control, and autonomous learning triggers.

## Critical Development Patterns

### 1. Genesis Key Tracking (Universal)

**Every significant operation MUST create a Genesis Key**. This is the backbone of GRACE's memory and autonomous systems.

```python
from genesis.genesis_key_service import get_genesis_service
from models.genesis_key_models import GenesisKeyType

# When processing ANY input/change
genesis_service = get_genesis_service(session)
genesis_key = genesis_service.create_key(
    key_type=GenesisKeyType.FILE_INGESTION,  # Choose appropriate type
    what_description="Clear description of what happened",
    who_actor="system|user_id|agent_name",
    where_location="file_path or component_name",
    why_reason="Why this action was taken",
    how_method="function_name or process",
    context_data={"relevant": "metadata"},
    session=session
)
```

**Genesis Keys trigger autonomous actions** - file ingestion triggers learning, errors trigger self-healing, practice failures trigger retry loops. Never bypass this system.

### 2. Trust-Scored Learning (Layer 1)

GRACE's knowledge is deterministic, not probabilistic guessing. Every concept has measurable trust.

```python
from cognitive.memory_mesh_integration import MemoryMeshIntegration

memory_mesh = MemoryMeshIntegration(session)
learning_id = memory_mesh.ingest_learning_experience(
    experience_type="knowledge_extraction",
    context={"topic": "API design", "source": "technical_doc.pdf"},
    action_taken="Learned REST best practices",
    outcome="Successfully extracted 5 concepts",
    expected_outcome="Extract API patterns",
    source="technical_documentation",  # Affects trust score
    genesis_key_id=genesis_key.key_id  # ALWAYS link
)
```

**Trust scores are calculated from**: source reliability (0.9 for technical docs), data confidence (extraction quality), operational confidence (practice success), consistency (alignment with existing knowledge).

### 3. OODA Loop for Decisions

**All significant decisions MUST flow through OODA** (Observe → Orient → Decide → Act). Never skip phases.

```python
from cognitive.engine import CognitiveEngine

engine = CognitiveEngine()
context = engine.begin_decision(
    problem_statement="User uploaded malformed PDF",
    goal="Extract text successfully or provide clear error",
    success_criteria=["Text extracted OR user informed of specific issue"]
)

# OBSERVE: Gather facts
engine.observe(context, {"file_size": 1024, "mime_type": "application/pdf"})

# ORIENT: Consider constraints
engine.orient(context, {"max_retries": 3}, {"user_waiting": True})

# DECIDE: Generate and select from alternatives
selected = engine.decide(context, lambda: [
    {"action": "retry_with_ocr", "confidence": 0.8},
    {"action": "inform_user_corrupted", "confidence": 0.6}
])

# ACT: Execute with result tracking
result = engine.act(context, lambda: process_pdf_with_ocr(file))
```

This enforces the 12 cognitive invariants including ambiguity tracking, blast radius analysis, and reversibility checks.

### 4. Autonomous Triggers (Self-Learning)

Genesis Keys automatically trigger learning/healing - understand the recursive loops:

- **File ingested** → Genesis Key created → Study task spawned → Learning stored → Practice triggered → Results observed → Mirror analyzes patterns → Improvements generated → New learning tasks
- **Error detected** → Genesis Key created → Self-healing triggered → Fix applied → Trust score updated → Memory Mesh stores outcome

**Don't fight this system** - route operations through `Layer1Integration` to trigger autonomous actions:

```python
from genesis.layer1_integration import get_layer1_integration

layer1 = get_layer1_integration(session)
result = layer1.process_file_operation(
    operation_type="create",
    file_path="knowledge_base/new_doc.pdf",
    metadata={"source": "user_upload"}
)
# Automatically triggers: Genesis Key → Learning → Practice → Memory storage
```

## Essential Project Knowledge

### Directory Structure Logic

- **`backend/`** - FastAPI Python backend
  - `api/` - REST endpoints (40+ routers, all use FastAPI `APIRouter`)
  - `cognitive/` - OODA loop, invariants, learning memory, self-healing
  - `genesis/` - Genesis Key system, Layer 1 integration, autonomous triggers
  - `database/` - SQLAlchemy models, migrations, session management
  - `ingestion/` - Document processing (PDF/DOCX/TXT/Markdown/Code)
  - `retrieval/` - Hybrid search (vector + semantic + keyword)
  - `llm_orchestrator/` - Multi-LLM coordination with cognitive enforcement
  - `layer_1/` - Immutable memory folder (JSON files, never database-only)
- **`frontend/`** - React + Vite SPA
  - `src/components/` - UI tabs (Chatbot, Documents, Version Control, Cognitive, etc.)
- **`knowledge_base/`** - Ingested documents (Git-tracked for version control)
- **`layer_1/`** - File-based memory persistence (Genesis Keys, learning memory, decisions)

### Database Schema Essentials

Core tables you'll frequently interact with:

- `genesis_key` - Universal tracking (key_id, key_type, what/where/when/who/why/how)
- `learning_examples` - Layer 1 knowledge with trust scores
- `episodes` - Episodic memory (high-trust experiences)
- `procedures` - Procedural memory (learned skills, auto-created at trust ≥ 0.85)
- `documents` / `document_chunks` - Ingested files + vector embeddings
- `decision_logs` - OODA decision audit trail

**Migration pattern**: Always create migration scripts in `backend/database/migrate_*.py` and update `run_migrations.py`.

### Development Workflow

**Start system**:
```bash
./start.sh        # Starts both backend + frontend
# OR
docker-compose up -d  # Full stack with Qdrant, Ollama, Postgres
```

**Backend development**:
```bash
cd backend
source venv/bin/activate  # Create with: python -m venv venv
uvicorn app:app --reload --port 8000
```

**Frontend development**:
```bash
cd frontend
npm run dev  # Vite dev server on port 5173
```

**Run tests**: Use test files named `test_*.py` in `backend/` (NOT using pytest framework, just direct execution):
```bash
python backend/test_memory_mesh.py
python backend/test_genesis_pipeline.py
```

### Environment Configuration

Key settings in `backend/.env`:

```bash
# Toggle major features
LIGHTWEIGHT_MODE=false          # Skip heavy ML models
DISABLE_GENESIS_TRACKING=false  # NEVER set true in prod
SKIP_AUTO_INGESTION=false       # Auto-study knowledge_base/
SUPPRESS_INGESTION_ERRORS=false # Show all errors

# LLM backend
OLLAMA_URL=http://localhost:11434
OLLAMA_LLM_DEFAULT=mistral:7b

# Vector DB
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Database
DATABASE_TYPE=sqlite  # or postgresql for production
```

## Code Conventions

### API Endpoints

All routers follow this pattern:

```python
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from database.session import get_session

router = APIRouter(prefix="/my-feature", tags=["My Feature"])

@router.post("/action")
async def perform_action(
    request: RequestModel,
    session: Session = Depends(get_session)
):
    """
    Clear docstring explaining what this does.
    
    Args:
        request: Input model
        session: Database session (auto-injected)
    
    Returns:
        Response model or dict
    """
    try:
        # Implementation
        return {"success": True}
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

**Always** register routers in `backend/app.py` with descriptive prefixes.

### Logging

Use structured logging with context:

```python
import logging
logger = logging.getLogger(__name__)

logger.info(f"[COMPONENT-NAME] Action completed: {details}")
logger.warning(f"[COMPONENT-NAME] ⚠️ Degraded state: {reason}")
logger.error(f"[COMPONENT-NAME] ❌ Failed: {error}", exc_info=True)
```

Prefix conventions: `[GENESIS]`, `[MEMORY-MESH]`, `[OODA]`, `[COGNITIVE]`, `[INGESTION]`

### Error Handling

GRACE has self-healing - errors should create Genesis Keys for learning:

```python
try:
    result = risky_operation()
except Exception as e:
    # Create error Genesis Key (triggers autonomous healing)
    genesis_service.create_key(
        key_type=GenesisKeyType.ERROR,
        what_description=f"Operation failed: {str(e)}",
        who_actor="system",
        where_location=f"{__name__}.risky_operation",
        why_reason="Exception during normal flow",
        how_method="try/except handler",
        context_data={"error_type": type(e).__name__, "traceback": ...}
    )
    # Then handle gracefully
    raise HTTPException(status_code=500, detail="Operation failed") from e
```

## Common Pitfalls

1. **Don't bypass Genesis Keys** - They're not optional logging, they trigger autonomous learning/healing
2. **Never modify `layer_1/` manually** - Use Layer1Integration API
3. **Don't skip OODA phases** - The engine validates phase ordering
4. **Trust scores aren't arbitrary** - They're calculated from source reliability + operational confidence + consistency
5. **Genesis Keys are immutable** - Create new keys for corrections, don't edit existing
6. **Memory Mesh auto-creates episodes/procedures** - Don't manually create them at trust thresholds
7. **Layer 1 is file-backed** - Database is cache; `layer_1/` folder is source of truth

## Key Files to Reference

- `COGNITIVE_BLUEPRINT.md` - 12 invariants governing all decisions
- `COMPLETE_SYSTEM_SUMMARY.md` - Autonomous learning architecture
- `QUICKSTART.md` - Telemetry & self-modeling usage
- `DEPLOYMENT_GUIDE.md` - Production setup
- `backend/app.py` - Central FastAPI app (lines 1-100 show all router imports)
- `backend/settings.py` - Configuration system

## Testing Philosophy

Tests validate **autonomous behavior and trust scoring**, not just units:

```python
# Test autonomous triggers
def test_file_ingestion_triggers_learning():
    result = layer1.process_file_operation(...)
    assert result['learning_triggered'] == True
    assert result['genesis_key_id'] is not None

# Test trust calculation
def test_trust_score_calculation():
    learning = memory_mesh.ingest_learning_experience(...)
    assert 0.0 <= learning.trust_score <= 1.0
    assert learning.source_reliability > 0
```

Focus on **integration** (does Genesis Key trigger learning?) not isolated units.

---

**When in doubt**: Trace data flow through Genesis Keys → Layer 1 → Memory Mesh → Autonomous Triggers. This is GRACE's nervous system.
