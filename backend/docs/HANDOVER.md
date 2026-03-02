# Grace AI — Developer Handover Document

## What Is Grace?

Grace is a self-evolving AI platform. It has 8 "brain" domains that handle everything from chat to code generation, with autonomous self-healing, self-learning, and multi-model consensus (Kimi, Opus, Qwen, DeepSeek).

---

## Before vs After

| Metric | Old System | New System |
|--------|-----------|------------|
| API files | 94 | 18 |
| Routes | 678 | 57 |
| HTTP self-calls | 78 | 0 |
| Router imports in app.py | 56 | 5 |
| Brain actions | — | 103 |
| Test coverage | 0 tests | 35 tests + 26 verification checks |
| Genesis keys | Write-only audit log | Full intelligence pipeline |
| Self-healing | Manual | Autonomous (30s Ouroboros loop) |
| Model consensus | Not connected | 4 models, real-time trust feedback |

### Why It Changed

The old system was 94 separate API files calling each other over HTTP (`requests.get("http://localhost:8000/...")`). Every internal call had network overhead, auth checks, serialization. The new system uses **direct Python function calls** — zero HTTP, zero overhead. All logic lives in `core/services/` and is accessed through 8 brain domains.

---

## How It's Wired

```
User/Frontend
     │
     ▼
  app.py (5 routers)
     │
     ├── /brain/{domain}     ← brain_api_v2.py (103 actions)
     ├── /api/v2/{d}/{a}     ← brain_controller.py (clean REST)
     ├── /health             ← health.py (k8s probes)
     ├── /auth               ← auth.py (sessions)
     └── /voice              ← voice_api.py (WebSocket)
     
brain_api_v2.py calls:
     │
     ├── core/services/chat_service.py      → DB (chats, messages)
     ├── core/services/files_service.py     → File system (knowledge base)
     ├── core/services/govern_service.py    → DB + files (rules, persona)
     ├── core/services/data_service.py      → JSON files (whitelist sources)
     ├── core/services/tasks_service.py     → DB + files (scheduling)
     ├── core/services/code_service.py      → File system + LLM
     └── core/services/system_service.py    → Runtime state
     
Every call also goes through:
     │
     ├── core/tracing.py         → trace ID propagation
     ├── core/security.py        → rate limiting + SQL injection check
     ├── core/hebbian.py         → synaptic weight update
     └── api/_genesis_tracker.py → Genesis key creation
```

### The 8 Brain Domains

| Domain | Actions | What It Does | Service File |
|--------|---------|-------------|-------------|
| **chat** | 8 | Conversations, prompts, consensus chat | `chat_service.py` |
| **files** | 9 | File tree, browse, read/write, search | `files_service.py` |
| **govern** | 12 | Governance, approvals, rules, persona, genesis keys | `govern_service.py` |
| **ai** | 20 | Consensus, DL model, OODA, ambiguity, invariants, testing | Cognitive modules |
| **system** | 31 | Health, runtime, monitoring, autonomous loop, probe, tracing | `system_service.py` |
| **data** | 7 | Whitelist sources, flash cache | `data_service.py` |
| **tasks** | 8 | Scheduling, time sense, planner | `tasks_service.py` |
| **code** | 8 | Codebase, projects, code generation | `code_service.py` |

### How to Call It

```python
# From Python (internal)
from api.brain_api_v2 import call_brain
result = call_brain("system", "runtime", {})

# From frontend (JavaScript)
import { brainCall } from './api/brain-client'
const result = await brainCall('system', 'runtime', {})

# From REST (external)
POST /brain/system { "action": "runtime", "payload": {} }
POST /api/v2/system/runtime {}

# Natural language (auto-routed)
POST /brain/ask { "query": "what is the system health?" }
```

---

## Intelligence Stack

### Layer 1: Hebbian Learning
Every `call_brain()` updates a synaptic weight between the caller and callee. Successful calls strengthen the connection (+0.05). Failures weaken it (-0.03). Over time, the system learns which brains work well together.

### Layer 2: Adaptive Trust
Real-time trust scores per model (Kimi=0.7, Opus=0.8, etc.). Updated on every consensus result. All models agree → trust goes up. Disagreement → outlier trust goes down.

### Layer 3: DL Model
3-head PyTorch MLP trained on 58K+ Genesis keys:
- Head 1: Will the next action succeed? (binary)
- Head 2: Which component is at risk? (10-class)
- Head 3: What trust score should this get? (regression)

### Layer 4: Cognitive Mesh
All cognitive modules wired through `core/cognitive_mesh.py`:
- OODA loop (observe-orient-decide-act)
- Ambiguity resolution
- Procedural memory (find proven procedures)
- Invariant checking
- Multi-armed bandits (explore/exploit)
- Meta-learning (adaptive learning rate)

### Layer 5: Auto-Router
Natural language → optimal brain + action. Uses keyword matching + Hebbian weights + trust scores.

### Layer 6: Ouroboros Loop (30s)
```
TIME_FILTER → MIRROR → TRIGGER → DECIDE → TRUST_GATE →
EPISODIC_RECALL → ACT → LEARN → KPI_UPDATE → LOOP
```

### Layer 7: Lightweight Tracking
`light_track()` — 1.6µs per key (300x faster than full Genesis keys). In-memory ring buffer, batch-flushes to DB every 10s.

---

## How to Test

```bash
# Full verification (26 checks)
python scripts/verify_system.py

# Full test suite (35 tests: smoke + component + integration + e2e)
python -m pytest tests/test_grace_system.py -v

# Deep probe (tests every brain action + service + cognitive module)
python scripts/deep_probe.py

# Start server and test live
python -m uvicorn app:app --host 0.0.0.0 --port 8000
curl http://localhost:8000/brain/directory
```

### What Each Test Level Covers

| Level | Tests | What |
|-------|-------|------|
| L1: Smoke | 11 | Every module imports correctly |
| L2: Component | 13 | Each component produces correct output |
| L3: Integration | 7 | Components work together (brain→service→data, consensus→trust) |
| L4: End-to-End | 4 | Full system flow validated |

---

## Key Files

| File | Purpose |
|------|---------|
| `app.py` | FastAPI entry point (5 routers) |
| `api/brain_api_v2.py` | THE brain — 103 actions, 8 domains |
| `core/services/*.py` | Business logic (7 service modules) |
| `core/intelligence.py` | Genesis key mining, adaptive trust, episodic mining |
| `core/deep_learning.py` | PyTorch DL model |
| `core/cognitive_mesh.py` | All cognitive modules unified |
| `core/cognitive_pipeline.py` | Pre/post processing on every brain action |
| `core/auto_router.py` | Natural language → brain routing |
| `core/hebbian.py` | Synaptic weights between brains |
| `core/resilience.py` | Circuit breakers, error boundaries, degradation |
| `core/security.py` | Rate limiting, SQL injection, secrets vault, backup |
| `core/tracing.py` | Trace IDs, lightweight Genesis keys, auto-probe |
| `api/_genesis_tracker.py` | Fire-and-forget Genesis key creation |
| `api/autonomous_loop_api.py` | Ouroboros 30s loop |

---

## Configuration (.env)

```env
# Required
KIMI_API_KEY=your-key
OPUS_API_KEY=your-key
QDRANT_URL=https://your-cluster.cloud.qdrant.io:6333
QDRANT_API_KEY=your-key
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL_CODE=qwen2.5-coder:7b
OLLAMA_MODEL_REASON=deepseek-r1:14b

# Optional
DATABASE_PATH=./data/grace.db
SKIP_EMBEDDING_LOAD=false
```

---

## Top 10 Next Steps (Priority Order)

### 1. Load Testing
Run k6 or locust at 500 RPS for 60s. Measure p99 latency. Target: <200ms. This is the single biggest gap — no performance numbers exist.

### 2. RBAC (Role-Based Access Control)
Currently any caller can invoke any brain action. Add per-brain permissions: `admin` can call system/heal, `user` can only call chat/send.

### 3. Frontend Migration
The React frontend still imports from `config/api.js` with old endpoints. Migrate all components to use `brainCall()` from `api/brain-client.js`.

### 4. API Versioning
Add `/api/v3/` support alongside `/api/v2/`. Brain actions should have backward-compatible schemas.

### 5. Database Migration to PostgreSQL
SQLite works for single-node but can't scale horizontally. For production: migrate to PostgreSQL with connection pooling (pgbouncer).

### 6. CI/CD Pipeline
Set up GitHub Actions: `pytest` on every PR, block merge if tests fail, auto-deploy to staging on merge to main.

### 7. Code Coverage
Current: 35 tests for 103 actions (~34%). Target: 80%. Add tests for every brain action that takes parameters.

### 8. OpenTelemetry Export
The built-in tracing works but doesn't export to Jaeger/Zipkin. Add an exporter for production observability.

### 9. Caching Layer
Hot brain actions (system/runtime, system/health_map) should cache responses for 5-10s. Reduces DB load.

### 10. Secrets Rotation
The encrypted vault exists but has no rotation mechanism. Add `POST /api/runtime/rotate-secrets` that re-encrypts with a new master key.

---

## Quick Reference

```bash
# Start Grace
cd backend && python -m uvicorn app:app --host 0.0.0.0 --port 8000

# Verify everything works
python scripts/verify_system.py

# Run tests
python -m pytest tests/test_grace_system.py -v

# Check brain directory
curl http://localhost:8000/brain/directory

# Ask Grace anything (auto-routed)
curl -X POST http://localhost:8000/brain/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "what is the system health?"}'

# Run consensus
curl -X POST http://localhost:8000/brain/ai \
  -H "Content-Type: application/json" \
  -d '{"action": "fast", "payload": {"prompt": "analyze this", "models": ["kimi", "opus"]}}'
```
