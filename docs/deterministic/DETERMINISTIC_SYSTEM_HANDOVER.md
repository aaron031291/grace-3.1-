# GRACE Deterministic System — Developer Handover

## What This Document Is

This is the complete technical handover for the Deterministic System in GRACE. It covers what was built, why it exists, how it works, and how every piece connects. Read this before touching any deterministic code.

---

## Core Purpose

The deterministic system exists to solve one problem: **you cannot trust LLM output blindly**.

Every piece of data in GRACE flows through Genesis Keys (what, when, where, why, who, how). That data gets stored like a library and categorized by the Librarian. RAG retrieves it and sends it where information needs to go. The deterministic system finds broken data, fixes what it can through structural analysis, and only hands off to LLMs when deterministic methods are exhausted — and even then, the LLM is constrained by verified facts on both sides.

The design principle: **deterministic verification wraps every LLM interaction**. The LLM never operates in open space. It receives exact facts as input and its output is verified by exact checks before acceptance.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    DATA FLOW (Genesis Keys)                         │
│                                                                     │
│  Every action creates a Genesis Key:                                │
│    WHAT happened, WHEN it happened, WHERE in the system,            │
│    WHY it was done, WHO did it, HOW it was performed                │
│                                                                     │
│  User input ──→ Genesis Key ──→ Knowledge Base (stored like library)│
│  AI response ──→ Genesis Key ──→ Librarian (categorized)            │
│  Code change ──→ Genesis Key ──→ RAG (retrievable)                  │
│  Error ──→ Genesis Key ──→ Deterministic Bus (triggers scan)        │
│  Fix ──→ Genesis Key ──→ Memory Mesh (learning)                     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                DETERMINISTIC BRAIN (9th brain)                      │
│                                                                     │
│  The deterministic layer is a first-class brain in the brain API.   │
│  It sits alongside chat, files, govern, ai, system, data, tasks,   │
│  code. It has 21 actions and its own REST endpoint.                 │
│                                                                     │
│  call_brain("deterministic", "scan", {})                            │
│  call_brain("deterministic", "probe_heal", {"component": "rag"})    │
│  call_brain("deterministic", "validate_code", {"code": "..."})      │
│  POST /api/v2/deterministic { action: "scan", payload: {} }         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## The Nine Modules

### 1. `core/deterministic_bridge.py` — The Original Bridge

The foundational module. Finds problems WITHOUT LLM reasoning.

**DeterministicDetector** runs 9 checks:
- Syntax (AST parse every Python file)
- Imports (critical packages + Grace modules)
- Files (critical files exist)
- Database (SQLite health, required tables)
- Tests (pytest pass/fail)
- Services (Ollama, Qdrant reachable)
- Circular imports (module graph)
- Unused variables (AST-based)
- Config (.env validation)

**DeterministicAutoFixer** fixes without LLM:
- Missing colon → adds colon
- Missing package → pip install
- Missing `__init__.py` → creates file

**`deterministic_fix_cycle()`** — the hallucination-proof chain:
```
DETECT (deterministic) → AUTO-FIX (deterministic) → remaining → LLM (constrained) → VERIFY (deterministic)
```

### 2. `deterministic_validator.py` — The Orchestrator

Runs the full validation pipeline. Calls every checker in sequence:

1. Silent failure detection (except:pass patterns)
2. Router wiring (routers not registered in app.py)
3. Broken import detection (imports to non-existent modules)
4. Layer 1 initialization check
5. Configuration validation (LLM provider, API keys)
6. Kimi/Opus connectivity
7. **Genesis Key validation** (calls `run_genesis_validation()`)
8. **RAG pipeline validation** (calls `run_rag_validation()`)

Produces a unified `ValidationReport` with severity counts and per-issue details.

### 3. `genesis/deterministic_genesis_validator.py` — Genesis Key Validation

9 checks on the Genesis Key system:

| Check | What it verifies |
|-------|-----------------|
| Schema integrity | Required columns exist in model, enum classes defined, service imports match |
| Chain integrity | `parent_key_id` references resolve, no duplicate `key_id` values |
| Fix linkage | `fix_key_id` references valid keys, fix_suggestions link to real keys |
| KB sync | `knowledge_base/layer_1/genesis_key/` files match DB key count |
| User profiles | `user_id` in genesis keys has matching `user_profile` record |
| Connector wiring | `GenesisKeysConnector` field names match `GenesisKey` model |
| Route wiring | Frontend `/genesis/*` routes registered in app.py |
| Timestamp ordering | Child keys have timestamps after parent keys |
| Import chain | Critical Genesis files exist and parse without syntax errors |

All checks use direct SQLite queries and AST parsing. No LLM.

### 4. `retrieval/deterministic_rag_validator.py` — RAG Pipeline Validation

10 checks on the RAG pipeline:

| Check | What it verifies |
|-------|-----------------|
| Embedding model | `EmbeddingModel` class exists, `embed_text()` method present, singleton factory exists |
| Qdrant connectivity | HTTP probe to Qdrant, `documents` collection exists and has vectors |
| Document-chunk consistency | Completed docs have chunks, no orphan chunks, confidence in [0,1], chunks have vector IDs |
| Ingestion pipeline | `ingestion/service.py` → `embedding/embedder.py` → `vector_db/client.py` chain intact |
| Retriever wiring | `DocumentRetriever` has required refs and methods, `retrieve_and_rank` bug detected |
| RAG prompt integrity | `utils/rag_prompt.py` exists, references context injection |
| KB file tracking | Files on disk vs. ingested documents in DB |
| Connector registration | RAG + Ingestion connectors exist in Layer 1 with correct classes |
| Import chain | All 7 RAG pipeline files parse without syntax errors |
| API wiring | Retrieve and ingest routers registered in app.py |

### 5. `core/deterministic_lifecycle.py` — The Recursive Lifecycle

The full agentic lifecycle for any component. Recursive until healthy or escalated.

**Steps:**

```
REGISTER → LOG → PROBE → TEST → SCAN → FIX → REASON → HEAL → VERIFY → LOOP
```

| Step | What happens | Deterministic? |
|------|-------------|----------------|
| REGISTER | Component discovered, Genesis Key created | Yes |
| LOG | Event logged with AST verification | Yes |
| PROBE | HTTP probe, import check, or file+AST parse | Yes |
| TEST | Component validator I/O tests | Yes |
| SCAN | File scan + deterministic bridge full scan | Yes |
| FIX | `DeterministicAutoFixer` — no LLM | Yes |
| REASON | LLM gets ONLY verified facts, generates fix | **No** (LLM, but constrained) |
| HEAL | HealingCoordinator, SelfHealer, or coding agent | **No** (may use LLM) |
| VERIFY | Re-probe + re-test | Yes |
| LOOP | If still broken and iterations remain, go to PROBE | Yes |

Max 5 iterations. If still broken after 5, escalated to human review.

**Key functions:**
- `register_component()` — register with Genesis tracking
- `auto_discover_components()` — pull from component_health registry and semantic_search
- `probe_component()` — 3 methods: HTTP, import, file+AST
- `scan_component()` — targeted file scan + full deterministic bridge
- `fix_deterministic()` — DeterministicAutoFixer
- `reason_with_llm()` — feeds ONLY deterministic facts to LLM
- `heal_component()` — tries HealingCoordinator → SelfHealer → coding agent
- `run_lifecycle()` — the recursive loop
- `lifecycle_scan()` — read-only diagnostic (no healing)

### 6. `core/deterministic_event_bus.py` — Multi-Entry-Point Architecture

The linear pipeline problem: if a service goes down, you don't want to start at REGISTER. You want to enter at HEAL directly. If an import breaks, you want to enter at SCAN, not PROBE.

The event bus solves this. Problems enter at ANY stage via topics:

| Topic | Entry Point | What triggers it |
|-------|-------------|-----------------|
| `deterministic.component_registered` | REGISTER | New component discovered |
| `deterministic.probe_failed` | PROBE → SCAN → FIX | Probe found component dead |
| `deterministic.problem_detected` | SCAN → FIX | Any scanner found issues |
| `deterministic.fix_needed` | FIX → REASON → HEAL | Deterministic fix failed |
| `deterministic.heal_needed` | HEAL | LLM reasoning done, execute healing |
| `deterministic.verify_needed` | VERIFY → LOOP | Healing done, check if it worked |
| `deterministic.code_change` | SCAN (targeted) | File changed, re-scan it |
| `deterministic.service_down` | HEAL (immediate) | Service unreachable |
| `deterministic.genesis_error` | SCAN | Genesis Key with is_error=True |

**Priority queue** — critical problems processed before normal ones.

**Bridges** — automatic routing from existing systems:
- Cognitive event bus: `genesis.error` → deterministic scan, `system.health_changed` → service_down, `file.changed` → code_change, `healing.failed` → fix_needed
- Genesis realtime: error keys → deterministic scan

**How to publish:**
```python
from core.deterministic_event_bus import publish, Priority

# Service went down — enter at HEAL stage immediately
publish("deterministic.service_down", "qdrant",
        {"error": "Connection refused"}, Priority.CRITICAL)

# Code changed — enter at SCAN stage
publish("deterministic.code_change", "retrieval",
        {"file": "retrieval/retriever.py"}, Priority.NORMAL)
```

### 7. `core/deterministic_coding_contracts.py` — Hard Governance

Governance contracts that tell LLMs "follow these rules" are soft enforcement — the LLM can ignore them. Deterministic coding contracts are HARD enforcement. Each step is verified by code. If any step fails, the generated code is REJECTED.

**4 contracts:**

| Contract | When | Pre-checks | Verify | Approve |
|----------|------|-----------|--------|---------|
| `code_generation` | Any LLM-generated code | — | Syntax, imports, security, docstring | Trust ≥ 0.5 |
| `code_fix` | Deterministic fix failed, LLM generates fix | File exists, problems documented | Syntax, imports, security | Trust ≥ 0.5 |
| `component_creation` | New component file | File doesn't exist yet | Syntax, imports, security, docstring REQUIRED | Trust ≥ 0.6 |
| `healing` | Self-healing code changes | Healing method documented | Syntax, imports, security STRICT | Trust ≥ 0.5 |

**Security checks (deterministic, AST-based):**
- `eval()` / `exec()` → REJECTED
- `os.system()` / `os.popen()` → REJECTED
- `subprocess.call(shell=True)` → REJECTED

**How to use:**
```python
from core.deterministic_coding_contracts import execute_code_generation_contract

result = execute_code_generation_contract(
    component="my_service",
    generated_code=llm_output,
    min_trust=0.5,
)

if result.code_accepted:
    # Safe to apply
    apply_code(llm_output)
else:
    # REJECTED — result.violations explains why
    print(result.violations)
```

### 8. `core/deterministic_logger.py` — Structured Event Logging

Every lifecycle event is logged with:
- Unique event ID
- Event type (COMPONENT_REGISTERED, PROBE_ALIVE, PROBE_DEAD, etc.)
- Component name
- Severity (critical, warning, info, debug)
- Timestamp
- Optional AST verification (if file_path provided)
- Optional Genesis Key tracking

**Event types:**
`COMPONENT_REGISTERED`, `PROBE_ALIVE`, `PROBE_DEAD`, `SCAN_STARTED`, `SCAN_RESULT`, `FIX_ATTEMPTED`, `FIX_RESULT`, `HEAL_ESCALATED`, `VERIFY_RESULT`, `LIFECYCLE_STARTED`, `LIFECYCLE_COMPLETE`

### 9. `core/component_validator.py` — Deterministic I/O Testing

Runs known-input/expected-output tests on components. Each component gets a report card with pass rate, errors, and status (healthy/degraded/failing). Tests 8 core components: brain_api, files_service, govern_service, time_sense, resilience, security, librarian, hebbian.

---

## The Deterministic Brain — All 21 Actions

The `deterministic` brain is registered in `brain_api_v2.py` alongside the other 8 brains. Access it via:

```python
call_brain("deterministic", "<action>", {<payload>})
```

Or via REST:
```
POST /api/v2/deterministic
{ "action": "<action>", "payload": {<payload>} }
```

| Action | What it does |
|--------|-------------|
| `scan` | Full deterministic scan (syntax, imports, services, files, DB) |
| `fix` | Deterministic fix cycle (detect → auto-fix → LLM if needed) |
| `genesis_scan` | Genesis Key validation (schema, chains, linkage, KB sync) |
| `rag_scan` | RAG pipeline validation (embedding, Qdrant, chunks, wiring) |
| `lifecycle_scan` | Probe all components, scan dead ones (read-only) |
| `probe_heal` | Full recursive lifecycle (probe→test→scan→fix→reason→heal→verify→loop) |
| `probe_all` | Probe every registered component for liveness |
| `lifecycle_events` | Get deterministic lifecycle event log |
| `registry` | Show all registered lifecycle components |
| `publish` | Publish a problem to any event bus entry point |
| `bus_stats` | Event bus statistics (queue, topics, handlers) |
| `bus_log` | Recent event bus task log |
| `init_bridges` | Initialize bridges to cognitive bus and Genesis realtime |
| `validate_code` | Run code generation contract on LLM output |
| `validate_fix` | Run code fix contract |
| `validate_component` | Run component creation contract |
| `validate_healing` | Run healing contract |
| `contracts` | List all available coding contracts |
| `log` | Event log (same as lifecycle_events) |
| `log_summary` | Event summary by component, type, severity |

---

## REST Endpoints

### Brain API
```
POST /api/v2/deterministic   { action, payload }
```

### Introspection API
```
GET  /api/system/validate              Full validation (includes genesis + rag)
GET  /api/system/validate/genesis      Genesis Key validation only
GET  /api/system/validate/rag          RAG pipeline validation only
GET  /api/system/validate/lifecycle    Lifecycle scan (probe + scan dead)
POST /api/system/validate/lifecycle/heal   Full recursive lifecycle with healing
GET  /api/system/validate/lifecycle/events   Event log
GET  /api/system/validate/lifecycle/registry   Component registry
```

### Autonomous Loop API
```
POST /api/autonomous/lifecycle/scan           Quick lifecycle scan
POST /api/autonomous/lifecycle/probe-and-heal Full recursive lifecycle
GET  /api/autonomous/lifecycle/registry       Component registry
GET  /api/autonomous/lifecycle/events         Event log
```

---

## Brain Orchestrator Routing

The deterministic brain is the PRIMARY brain for these task types:

| Task Type | Brain Order |
|-----------|-------------|
| fix | **deterministic**, ai, code, system |
| test | **deterministic**, ai, system, code |
| analyze | **deterministic**, ai, system, files |
| heal | **deterministic**, system, ai, govern |
| review | **deterministic**, ai, code, govern |
| scan | **deterministic**, system, ai |
| validate | **deterministic**, system |
| probe | **deterministic**, system |

---

## Frontend (DevTab)

8 buttons in the Dev Tab, all under `brain: "deterministic"`:

| Button | Action | Description |
|--------|--------|-------------|
| Deterministic Scan | `scan` | Full system scan — AST, imports, services |
| Deterministic Fix | `fix` | Detect → auto-fix → LLM if needed |
| Genesis Det. Scan | `genesis_scan` | Genesis Key system validation |
| RAG Det. Scan | `rag_scan` | RAG pipeline validation |
| Lifecycle Scan | `lifecycle_scan` | Probe all → scan dead |
| Probe & Heal | `probe_heal` | Full recursive lifecycle with healing |
| Event Bus | `bus_stats` | Event bus statistics and status |
| Coding Contracts | `contracts` | List all deterministic coding contracts |

---

## How Data Flows Through the System

### 1. Data Enters via Genesis Keys

Every action in GRACE creates a Genesis Key with full metadata:
- **WHAT**: Description of what happened
- **WHEN**: Timestamp
- **WHERE**: File path, function, line number
- **WHY**: Purpose/reason
- **WHO**: User, system, or process
- **HOW**: Method used

### 2. Data is Stored and Categorized

- **Database**: `genesis_key` table in SQLite
- **Knowledge Base**: `knowledge_base/layer_1/genesis_key/{user_id}/` (JSON files)
- **Memory Mesh**: Learnable events fed to `MemoryMeshIntegration.ingest_learning_experience()`
- **Hot Tier**: In-memory cache via `GenesisStorage.store_hot()`
- **Qdrant**: Background batch upsert to `genesis_keys` vector collection

The Librarian auto-categorizes ingested data. Documents get chunked, embedded, and stored in Qdrant for retrieval.

### 3. RAG Retrieves and Routes Data

When information is needed:
1. Query → `EmbeddingModel.embed_text()` → query embedding
2. Embedding → `QdrantVectorDB.search_vectors()` → matching chunks
3. Chunks → `DocumentRetriever.build_context()` → formatted context
4. Context → `build_rag_prompt()` → LLM prompt with retrieved context

### 4. Deterministic System Finds Broken Data

The deterministic system runs validation across all layers:
- **Genesis validator**: checks key chains, fix linkage, KB sync, user profiles
- **RAG validator**: checks document-chunk consistency, embedding model, Qdrant, wiring
- **Bridge scanner**: checks syntax, imports, services, database, tests
- **Lifecycle**: probes components for liveness, tests for correctness

### 5. Fix Chain

When a problem is found:
1. **Deterministic fix first** — DeterministicAutoFixer handles known patterns (missing colon, missing package, missing `__init__.py`)
2. **If deterministic fix fails** — LLM receives ONLY verified facts (not guesses) and generates a fix
3. **Coding contract enforced** — LLM output is AST-parsed, import-checked, security-scanned, and trust-gated BEFORE acceptance
4. **If accepted** — fix is applied via coding agent or healing coordinator
5. **Verify** — re-probe and re-test to confirm fix worked
6. **If still broken** — recursive loop (max 5 iterations) or escalate to human

---

## File Map

```
backend/
├── deterministic_validator.py              # Orchestrator — runs all validators
├── core/
│   ├── deterministic_bridge.py             # Original: detect → fix → verify
│   ├── deterministic_lifecycle.py          # Recursive: probe → scan → fix → heal → loop
│   ├── deterministic_event_bus.py          # Multi-entry-point event-driven lifecycle
│   ├── deterministic_coding_contracts.py   # Hard-enforced governance for code
│   ├── deterministic_logger.py             # Structured lifecycle event logging
│   ├── component_validator.py              # Deterministic I/O testing
│   ├── brain_orchestrator.py               # Routes tasks to deterministic brain
│   └── semantic_search.py                  # Component map (discoverability)
├── genesis/
│   └── deterministic_genesis_validator.py  # Genesis Key system validation
├── retrieval/
│   └── deterministic_rag_validator.py      # RAG pipeline validation
├── api/
│   ├── brain_api_v2.py                     # Deterministic brain (9th domain)
│   ├── introspection_api.py                # /validate/genesis, /validate/rag, /validate/lifecycle
│   └── autonomous_loop_api.py              # /lifecycle/scan, /lifecycle/probe-and-heal
└── system_introspector.py                  # Deterministic system cataloging

frontend/
└── src/components/DevTab.jsx               # 8 deterministic buttons
```

---

## Design Decisions

### Why a separate brain and not just actions under "ai" or "system"?

The deterministic system cross-cuts everything. It validates genesis keys (govern), RAG pipelines (ai), services (system), code (code), and data integrity (data). Putting it under one existing brain would be arbitrary. As its own brain, it can be the PRIMARY brain for fix/test/heal/validate tasks.

### Why multi-entry-point event bus instead of linear pipeline?

A linear pipeline (probe → scan → fix → heal) misses problems that don't start at the beginning. If a service goes down, you need to enter at HEAL, not PROBE. If an import breaks during deployment, you need to enter at SCAN. The event bus lets any component publish to any entry point, and the default routing takes it from there.

### Why hard-enforced coding contracts instead of prompt-based governance?

Prompt governance says "don't use eval()". The LLM can still output eval(). A coding contract runs `ast.walk()` on the output and REJECTS it if eval() is present. The difference is between asking and enforcing.

### Why does the LLM only see deterministic facts?

If you ask an LLM "what's wrong with this codebase?", it will hallucinate problems. If you give it exact facts — "line 42 of retriever.py has a syntax error: expected ':'", "module cognitive.memory_mesh cannot be imported: ModuleNotFoundError" — the LLM can only reason about real problems. The deterministic layer produces the facts. The LLM consumes them.

---

## For Developers: How to Add a New Component

1. **Register it in the lifecycle:**
```python
from core.deterministic_lifecycle import register_component

register_component(
    component_id="my_service",
    label="My Service",
    file_path="core/my_service.py",
    health_url="http://localhost:8000/api/my-service/health",
    dependencies=["database", "qdrant"],
)
```

2. **It gets a Genesis Key** for the registration event.
3. **The lifecycle probes it** on the next scan.
4. **If it breaks**, the event bus picks it up and routes to the appropriate fix chain.
5. **Any code it generates** goes through a coding contract before acceptance.

---

## For Developers: How to Publish a Problem

```python
from core.deterministic_event_bus import publish, Priority

# Something broke in RAG — enter at SCAN
publish("deterministic.problem_detected", "rag",
        {"error": "Qdrant collection missing", "file": "retrieval/retriever.py"},
        priority=Priority.HIGH, source="my_monitor")

# Service went down — enter at HEAL immediately
publish("deterministic.service_down", "ollama",
        {"error": "Connection refused on port 11434"},
        priority=Priority.CRITICAL, source="health_check")
```

---

## For Developers: How to Enforce a Coding Contract

```python
from core.deterministic_coding_contracts import execute_code_generation_contract

result = execute_code_generation_contract(
    component="my_service",
    generated_code=llm_output,
    min_trust=0.5,
)

if not result.code_accepted:
    # result.violations tells you exactly what failed
    # e.g. ["Syntax error: expected ':' (line 12)", "Dangerous call: eval() at line 5"]
    raise ValueError(f"Code rejected: {result.violations}")
```
