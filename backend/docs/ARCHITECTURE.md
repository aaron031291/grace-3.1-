# Grace AI — Architecture Guide

## Overview

Grace is a self-evolving AI platform with autonomous self-healing, self-learning, and multi-model consensus. The architecture follows a **Brain-Domain-Service** pattern where 8 domain brains expose 87+ actions through direct Python function calls.

## Directory Structure

```
backend/
├── app.py                          FastAPI entry point (21 router imports)
├── api/
│   ├── brain_api_v2.py             8 domain brains, 87+ actions, zero HTTP self-calls
│   ├── core/
│   │   ├── brain_controller.py     POST /api/v2/{domain}/{action}
│   │   └── autonomous_controller.py Ouroboros loop + consensus fixer
│   ├── monitoring/
│   │   └── health_controller.py    Unified health/probe/triggers
│   ├── component_health_api.py     16-component behavioral profiling
│   ├── probe_agent_api.py          Automated endpoint crawler
│   ├── runtime_triggers_api.py     CPU/RAM/service/code/network triggers
│   ├── autonomous_loop_api.py      30s Ouroboros cycle
│   ├── consensus_fixer_api.py      All-model consensus auto-fix
│   ├── consensus_api.py            Multi-model deliberation
│   ├── health.py                   /health endpoint
│   ├── auth.py                     Authentication
│   ├── genesis_keys.py             Genesis key CRUD
│   ├── _genesis_tracker.py         Fire-and-forget Genesis tracking
│   ├── retrieve.py                 RAG retrieval
│   └── [6 more core service APIs]
├── core/
│   ├── services/                   ALL business logic (7 modules)
│   │   ├── chat_service.py         Conversations, prompts, LLM calls
│   │   ├── files_service.py        File tree, browse, read/write
│   │   ├── govern_service.py       Governance, rules, persona, genesis
│   │   ├── data_service.py         Whitelist sources, flash cache
│   │   ├── tasks_service.py        Scheduling, time sense
│   │   ├── code_service.py         Codebase, projects, code gen
│   │   └── system_service.py       Runtime, health, hot-reload
│   ├── engines/
│   │   ├── consensus_engine.py     Multi-model consensus (canonical)
│   │   └── diagnostic_engine.py    4-layer diagnostics + trust
│   ├── memory/
│   │   └── unified_memory.py       Learning + episodic + mesh facade
│   ├── awareness/
│   │   └── self_model.py           TimeSense + Mirror unified
│   └── resilience.py               Circuit breakers, error boundaries
├── cognitive/                      Core intelligence modules
├── database/                       SQLite with WAL, retry, session isolation
├── genesis/                        Genesis key provenance system
├── llm_orchestrator/               Multi-LLM client (Ollama, Kimi, Opus)
├── diagnostic_machine/             4-layer diagnostic pipeline
└── tests/                          Enterprise test suite
```

## Brain Domains

| Domain | Actions | Description |
|--------|---------|-------------|
| `chat` | 8 | Conversations, prompts, consensus chat, world model |
| `files` | 9 | File tree, browse, read/write, search, docs |
| `govern` | 12 | Governance, approvals, rules, persona, genesis keys |
| `ai` | 12 | Consensus, models, testing, knowledge gaps, oracle |
| `system` | 23 | Health, runtime, monitoring, autonomous loop, probe |
| `data` | 7 | Whitelist sources, flash cache |
| `tasks` | 8 | Scheduling, time sense, planner |
| `code` | 8 | Codebase, projects, code generation |

## API Usage

```bash
# Brain v1 (POST with action in body)
POST /brain/chat { "action": "send", "payload": { "chat_id": 1, "message": "hello" } }

# Brain v2 (clean REST)
POST /api/v2/chat/send { "chat_id": 1, "message": "hello" }

# Orchestration (multi-brain)
POST /brain/orchestrate { "steps": [
    {"brain": "system", "action": "runtime"},
    {"brain": "ai", "action": "models"}
]}
```

## Autonomous Loop (Ouroboros)

Runs every 30 seconds:

```
TIME_FILTER → MIRROR → TRIGGER → DECIDE → TRUST_GATE →
EPISODIC_RECALL → ACT → LEARN → KPI_UPDATE → LOOP
```

- **Trust gates**: Block actions below threshold (heal=0.5, code=0.8)
- **TimeSense**: Defer non-critical to quiet hours
- **Mirror**: Observe system patterns, detect anomalies
- **Episodic memory**: Recall similar past problems
- **KPIs**: Updated every cycle

## Genesis Keys

Every operation creates a Genesis key tracking:
- **What** happened
- **Who** did it
- **When** it occurred
- **Where** in the system
- **Why** it was done
- **How** it was executed

Keys flow through: Event Bus → Component Health → Mirror → Diagnostics → Self-Healing → back to Genesis Keys (closed loop).

## Resilience Patterns

- **Circuit Breakers**: Per-service (3 failures → 120s open → half-open test)
- **Error Boundaries**: Contain failures, log via Genesis key
- **Graceful Degradation**: FULL / REDUCED / EMERGENCY / READ_ONLY

## Configuration

Required `.env` settings:
```
KIMI_API_KEY=your-key           # Moonshot AI
OPUS_API_KEY=your-key           # Anthropic Claude
QDRANT_URL=your-cloud-url       # Qdrant Cloud
QDRANT_API_KEY=your-key         # Qdrant auth
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL_CODE=qwen2.5-coder:7b
OLLAMA_MODEL_REASON=deepseek-r1:14b
```

## Verification

```bash
python scripts/verify_system.py   # 26 checks, all should pass
python -m pytest tests/ -v        # 47+ tests
```
