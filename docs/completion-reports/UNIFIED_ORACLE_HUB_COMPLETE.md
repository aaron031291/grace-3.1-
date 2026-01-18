# Unified Oracle Hub - Central Intelligence Ingestion System

## ✅ IMPLEMENTATION COMPLETE

The Oracle is now the **single source of truth** for ALL inbound intelligence.

## Architecture

```
📥 ALL INTELLIGENCE SOURCES
         ↓
┌─────────────────────────────────────┐
│     UNIFIED ORACLE HUB              │
│  ─────────────────────────────────  │
│  • AI Research (arXiv, HuggingFace) │
│  • GitHub (PRs, Issues, Code)       │
│  • Stack Overflow                   │
│  • Sandbox Insights                 │
│  • Coding Templates                 │
│  • Learning Memory                  │
│  • Whitelist Sources                │
│  • Self-Healing Fixes               │
│  • Librarian Ingestion              │
│  • Pattern Discoveries              │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│     ORACLE CORE                     │
│  ─────────────────────────────────  │
│  • store_research() for all items   │
│  • Genesis Key tracking             │
│  • Pattern recognition              │
│  • Semantic search                  │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│     KNOWLEDGE BASE                  │
│  ─────────────────────────────────  │
│  • knowledge_base/oracle/           │
│  • Organized by source type         │
│  • JSON exports for retrieval       │
└─────────────────────────────────────┘
```

## Files Created

| File | Purpose |
|------|---------|
| `backend/oracle_intelligence/unified_oracle_hub.py` | Central hub class with all ingestion methods |
| `backend/api/oracle_hub_api.py` | REST API endpoints for ingestion |
| `backend/oracle_intelligence/startup_hooks.py` | App startup initialization |
| `knowledge_base/oracle/` | Export directory for Oracle knowledge |

## API Endpoints

### Ingestion Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /oracle-hub/ingest` | Generic intelligence ingestion |
| `POST /oracle-hub/ingest/github` | GitHub PRs, issues, code |
| `POST /oracle-hub/ingest/sandbox` | Sandbox experiment results |
| `POST /oracle-hub/ingest/template` | Coding templates/patterns |
| `POST /oracle-hub/ingest/learning` | Learning memory data |
| `POST /oracle-hub/ingest/self-healing` | Self-healing fix results |
| `POST /oracle-hub/ingest/whitelist` | Approved external sources |
| `POST /oracle-hub/ingest/pattern` | Discovered patterns |
| `POST /oracle-hub/ingest/research` | AI research papers |

### Management Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /oracle-hub/export` | Export to knowledge_base/oracle/ |
| `POST /oracle-hub/sync/start` | Start background sync |
| `POST /oracle-hub/sync/stop` | Stop background sync |
| `GET /oracle-hub/stats` | Ingestion statistics |
| `GET /oracle-hub/status` | Hub connection status |
| `GET /oracle-hub/research` | Search Oracle research |
| `GET /oracle-hub/sources` | List all source types |

## Usage Examples

### 1. Ingest Sandbox Insight
```bash
curl -X POST http://localhost:8000/oracle-hub/ingest/sandbox \
  -H "Content-Type: application/json" \
  -d '{
    "experiment_id": "EXP-001",
    "experiment_name": "Cache optimization test",
    "results": {"latency_improvement": "40%"},
    "lessons_learned": ["Use LRU cache", "Set dynamic TTL"],
    "success": true
  }'
```

### 2. Ingest Coding Template
```bash
curl -X POST http://localhost:8000/oracle-hub/ingest/template \
  -H "Content-Type: application/json" \
  -d '{
    "template_name": "FastAPI CRUD Handler",
    "pattern_type": "api_handler",
    "code_example": "@router.post(\"/items\")\nasync def create(item: Item): ...",
    "description": "Standard CRUD pattern",
    "category": "backend"
  }'
```

### 3. Ingest Self-Healing Fix
```bash
curl -X POST http://localhost:8000/oracle-hub/ingest/self-healing \
  -H "Content-Type: application/json" \
  -d '{
    "error_type": "ImportError",
    "error_message": "No module named xyz",
    "fix_applied": "Added to requirements.txt",
    "success": true,
    "affected_files": ["requirements.txt"]
  }'
```

### 4. Start Background Sync
```bash
curl -X POST "http://localhost:8000/oracle-hub/sync/start?interval_seconds=300"
```

### 5. Export to Knowledge Base
```bash
curl -X POST http://localhost:8000/oracle-hub/export
```

### 6. Check Status
```bash
curl http://localhost:8000/oracle-hub/status
```

## Intelligence Sources (13 Types)

| Source | Description |
|--------|-------------|
| `ai_research` | arXiv, HuggingFace papers |
| `github_pulls` | GitHub PRs, issues, code |
| `stackoverflow` | Stack Overflow Q&A |
| `sandbox_insights` | Sandbox experiment results |
| `templates` | Coding patterns/templates |
| `learning_memory` | Training data, trust scores |
| `whitelist` | Approved external sources |
| `internal_updates` | Self-healing fixes |
| `librarian` | Files via Librarian pipeline |
| `pattern` | Discovered code patterns |
| `web_knowledge` | General web research |
| `documentation` | Official docs |
| `user_feedback` | User corrections |

## Automatic Hooks

The hub automatically connects to these systems at startup:
- **Librarian Pipeline** → All ingested files go to Oracle
- **Sandbox Lab** → All experiment results go to Oracle
- **Learning Memory** → All training data syncs to Oracle
- **Self-Healer** → All fixes are recorded in Oracle

## Background Sync

Every 5 minutes (configurable), the hub:
1. Pulls recent learnings from Learning Memory
2. Pulls recent experiments from Sandbox
3. Exports all research to `knowledge_base/oracle/`

## Folder Structure

```
knowledge_base/oracle/
├── index.json              # Master index
├── ai_research/           # arXiv, HuggingFace
├── github_pulls/          # GitHub data
├── sandbox_insights/      # Experiment results
├── templates/             # Coding patterns
├── learning_memory/       # Training data
├── internal_updates/      # Self-healing fixes
├── pattern/               # Discovered patterns
└── research/              # Oracle research entries
```

## Startup Integration

Add to `app.py` startup event:

```python
@app.on_event("startup")
async def startup():
    from oracle_intelligence.startup_hooks import initialize_oracle_hub_on_startup
    initialize_oracle_hub_on_startup()
```

## Summary

✅ **All 13 intelligence sources now feed the Oracle**
✅ **Automatic hooks connect Librarian, Sandbox, Learning Memory, Self-Healer**
✅ **Background sync runs every 5 minutes**
✅ **All knowledge exports to knowledge_base/oracle/**
✅ **REST API for manual ingestion**
✅ **Genesis Key tracking for every item**
✅ **Semantic search through Oracle research**
