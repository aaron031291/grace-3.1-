# Genesis Key System — Complete Technical Summary

## What Genesis Keys Are

A Genesis Key is a provenance record. Every action in GRACE — user input, AI response, code change, file upload, error, fix, learning event — creates a Genesis Key that captures:

- **WHAT** happened (`what_description`)
- **WHEN** it happened (`when_timestamp`)
- **WHERE** in the system (`where_location`, `file_path`, `line_number`, `function_name`)
- **WHY** it was done (`why_reason`)
- **WHO** did it (`who_actor`, `user_id`)
- **HOW** it was performed (`how_method`)

Every key gets an ID like `GK-a1b2c3d4...`. Every user gets an ID like `GU-f5e6d7c8...`. Keys chain together via `parent_key_id` to form full provenance trails.

---

## Data Model

### Tables

| Table | Purpose | Key Fields |
|-------|---------|-----------|
| `genesis_key` | Main provenance records | `key_id`, `parent_key_id`, `key_type`, `status`, `what_description`, `who_actor`, `when_timestamp`, `where_location`, `why_reason`, `how_method`, `file_path`, `is_error`, `error_type`, `error_message`, `has_fix_suggestion`, `fix_applied`, `fix_key_id`, `commit_sha`, `metadata_human`, `metadata_ai`, `input_data`, `output_data`, `context_data`, `tags` |
| `fix_suggestion` | Fix proposals for errors | `suggestion_id`, `genesis_key_id` (FK), `suggestion_type`, `title`, `description`, `severity`, `fix_code`, `fix_diff`, `status`, `confidence`, `applied_at`, `applied_by`, `result_key_id` |
| `genesis_key_archive` | Daily archives | `archive_id`, `archive_date`, `key_count`, `error_count`, `fix_count`, `user_count`, `most_active_user`, `most_changed_file`, `report_summary`, `report_data` |
| `user_profile` | User tracking | `user_id`, `username`, `email`, `first_seen`, `last_seen`, `total_actions`, `total_changes`, `total_errors`, `total_fixes` |

### Key Types (21 total)

| Category | Types |
|----------|-------|
| User interactions | `USER_INPUT`, `USER_UPLOAD` |
| AI/Agent | `AI_RESPONSE`, `AI_CODE_GENERATION`, `CODING_AGENT_ACTION` |
| Code/Files | `CODE_CHANGE`, `FILE_OPERATION`, `FILE_INGESTION` |
| API/External | `API_REQUEST`, `EXTERNAL_API_CALL`, `WEB_FETCH` |
| Data | `DATABASE_CHANGE`, `LIBRARIAN_ACTION` |
| Learning | `LEARNING_COMPLETE`, `GAP_IDENTIFIED`, `PRACTICE_OUTCOME` |
| System | `CONFIGURATION`, `SYSTEM_EVENT`, `ERROR`, `FIX`, `ROLLBACK` |

### Key Statuses

`ACTIVE`, `ARCHIVED`, `ROLLED_BACK`, `ERROR`, `FIXED`

### Fix Suggestion Statuses

`PENDING`, `APPLIED`, `REJECTED`, `EXPIRED`

---

## How Keys Are Created

There are two creation paths:

### Path 1: `_genesis_tracker.track()` — Fire-and-Forget

The primary creation path used by 40+ modules across the codebase. Any module can call:

```python
from api._genesis_tracker import track

track(
    key_type="ai_response",
    what="RAG retrieval: 5 chunks for 'how does consensus work'",
    who="retriever.retrieve",
    how="qdrant_vector_search",
    input_data={"query": "how does consensus work", "limit": 5},
    output_data={"chunks_found": 5, "top_score": 0.87},
    tags=["rag", "retrieval", "search"],
)
```

This function never crashes the caller. If tracking fails, the error is swallowed. Under the hood it:

1. Checks sampling gate (`GenesisStorage.should_store`) — first 10 always stored, then 1% sampling
2. Stores in hot tier (`GenesisStorage.store_hot`) — in-memory ring buffer
3. Fires realtime engine (`GenesisRealtimeEngine.on_key_created`) — triggers watchers and alert rules
4. Publishes to cognitive event bus (`genesis.{key_type}`, `genesis.key_created`)
5. Creates DB record via `GenesisKeyService.create_key()`
6. Queues for Qdrant batch upsert (background thread, embeddings for vector search)

### Path 2: `GenesisKeyService.create_key()` — Full Service

Used when you need the created key object back:

```python
from genesis.genesis_key_service import get_genesis_service

service = get_genesis_service(session=db_session)
key = service.create_key(
    key_type=GenesisKeyType.CODE_CHANGE,
    what_description="Refactored retriever.py",
    who_actor="developer",
    file_path="retrieval/retriever.py",
    code_before="old code...",
    code_after="new code...",
)
```

After creation, the service runs three post-creation hooks:

1. **KB Integration**: Writes JSON to `knowledge_base/layer_1/genesis_key/{user_id}/`
2. **Memory Mesh**: For learnable types (AI_RESPONSE, ERROR, FIX, CODE_CHANGE, etc.), feeds to `MemoryMeshIntegration.ingest_learning_experience()` in a background thread
3. **Autonomous Triggers**: Calls `GenesisTriggerPipeline.on_genesis_key_created()` which routes by key type to trigger actions

---

## Where Keys Are Stored (5 Storage Tiers)

| Tier | Location | Purpose | Retention |
|------|----------|---------|-----------|
| **Hot** | In-memory (`GenesisStorage._hot`) | Fast access, ring buffer | Session lifetime |
| **Database** | SQLite `genesis_key` table | Persistent, queryable | Until archived |
| **Knowledge Base** | `knowledge_base/layer_1/genesis_key/{user_id}/` | JSON files for RAG ingestion | Permanent |
| **Qdrant** | `genesis_keys` collection | Vector embeddings for semantic search | Permanent |
| **Archive** | `genesis_archives/{date}/` | Daily JSON + reports | Permanent |

### Storage Flow

```
track() called
    │
    ├─→ Hot Tier (in-memory, immediate)
    ├─→ Realtime Engine (watchers, alerts)
    ├─→ Cognitive Event Bus (genesis.key_created)
    ├─→ Database (genesis_key table)
    ├─→ Knowledge Base (JSON files by user)
    ├─→ Memory Mesh (learnable types only, background thread)
    ├─→ Qdrant (background batch, every 30s)
    └─→ Autonomous Triggers (type-based routing)
```

---

## How Keys Are Consumed

### Component Health (Real-time Monitoring)

`api/component_health_api.py` queries Genesis Keys by time window to determine component status:

- `_get_genesis_keys(minutes=60, limit=2000)` — fetches recent keys from DB
- Classifies 16 components as green/yellow/orange/red based on key patterns
- Error keys raise severity, silence on always-on components triggers warnings
- Feeds into the health map, timeline, problems, and remediation

### Pattern Mining (Intelligence)

`core/intelligence.py` → `GenesisKeyMiner` mines keys for:

- Type distribution (which key types dominate)
- Actor frequency (who is most active)
- Error clusters (same error repeating)
- Temporal patterns (time-based activity)
- Hot files (most-changed files)
- Tag co-occurrence (which tags appear together)
- Repeated failures (same failure pattern recurring)

Accessed via `call_brain("system", "mine_keys", {"hours": 24})`.

### Diagnostic Sensors

`diagnostic_machine/sensors.py` has a `GENESIS_KEYS` sensor type that collects:

- Total keys, active, error, fix suggestion counts
- Type distribution
- Recent error keys

The diagnostic engine uses this data in its 4-layer pipeline (Sensors → Interpreters → Judgement → Action Router).

### Daily Curation (Librarian)

`librarian/genesis_key_curator.py` → `GenesisKeyCurator`:

- Runs daily (scheduled at midnight)
- Exports keys organized by type and date
- Generates daily metadata summaries
- Uses `GenesisKeyDailyOrganizer` for the actual export

### Archival

`genesis/archival_service.py` → `ArchivalService`:

- Archives keys older than target date
- Generates statistics (error counts, top actors, most changed files)
- Produces human-readable reports and JSON data files
- Marks keys as `ARCHIVED` in DB
- Scheduled daily at 02:00

### Reports

Keys feed into multiple report types:

- **Health dashboard**: `call_brain("system", "health")` — uses key counts for service status
- **BI dashboard**: `call_brain("system", "bi")` — business intelligence from key patterns
- **Intelligence report**: `call_brain("system", "intelligence")` — pattern mining results
- **Daily summary**: `call_brain("system", "daily_summary")` — daily archive reports
- **Diagnostics report**: `GET /diagnostic/health` — health score from key-based sensors

---

## Self-Healing Integration

Genesis Keys are central to the self-healing pipeline:

### Error Detection

When `track()` is called with `is_error=True`:

1. **Realtime alerts**: `GenesisRealtimeEngine` checks for error spikes (3+ in 60s), bursts (10+ in 300s), high error rates (20%+ in 120s)
2. **Cognitive event bus**: publishes `genesis.error` and `genesis.ERROR`
3. **Deterministic event bus**: bridges pick up `genesis.error` → publishes `deterministic.genesis_error` → enters scan chain
4. **Component health**: error keys change component status from green to orange/red

### Autonomous Triggers on Key Creation

`genesis/autonomous_triggers.py` → `GenesisTriggerPipeline` fires when specific key types are created:

| Key Type | Trigger | Action |
|----------|---------|--------|
| `FILE_OPERATION` | File create/modify | Auto-study if learning-worthy file |
| `USER_INPUT` | User message | Predictive context prefetch (top 3 topics) |
| `LEARNING_COMPLETE` | Study session done | Auto-practice if skill is practice-worthy |
| `PRACTICE_OUTCOME` (failed) | Practice failed | Create GAP_IDENTIFIED key → targeted study → retry practice (RECURSIVE LOOP) |
| `GAP_IDENTIFIED` | Knowledge gap found | Submit study task + practice retry |
| `ERROR` | Error occurred | Health check trigger → autonomous healing |
| (any, conditional) | Low confidence/contradiction | Multi-LLM verification (Kimi + Opus + Qwen agree) |
| (periodic) | Every 50 triggers | Mirror self-modeling analysis |

### Fix Suggestions

When an error key is created, the system can generate fix suggestions:

```python
service.create_fix_suggestion(
    genesis_key_id="GK-abc123",
    suggestion_type="syntax",
    title="Missing colon on line 42",
    description="Add ':' after def statement",
    severity="high",
    fix_code="def my_func():",
    confidence=0.95,
)
```

Fix suggestions can be applied via `service.apply_fix(suggestion_id, applied_by)`, which:
1. Creates a new `FIX` key linked to the original error key
2. Updates the original key's `fix_applied` and `fix_key_id`
3. Sets original key status to `FIXED`

### Rollback

Any key can be rolled back via `service.rollback_to_key(key_id, rolled_back_by)`:
1. Creates a `ROLLBACK` key with `parent_key_id` pointing to the target
2. Restores `code_before` as the new state
3. If git service available, reverts to the key's `commit_sha`

### Diagnostic Action Router

`diagnostic_machine/action_router.py` creates Genesis Keys for every diagnostic action:
- `_create_action_genesis_key()` — creates key before action execution
- `_update_genesis_key_status()` — updates key with result (COMPLETED/FAILED/SKIPPED)
- Links healing actions to Genesis Keys for full provenance

---

## Deterministic Validation

`genesis/deterministic_genesis_validator.py` runs 9 deterministic checks on the Genesis Key system itself:

| Check | What breaks if it fails |
|-------|------------------------|
| Schema integrity | Model missing columns → keys can't be created |
| Chain integrity | Orphaned parent_key_id → broken provenance chains |
| Fix linkage | fix_key_id pointing nowhere → fix tracking broken |
| KB sync | DB has keys but KB has no files → RAG can't retrieve genesis data |
| User profiles | user_ids with no profile → stats tracking broken |
| Connector wiring | Connector uses wrong field names → Layer 1 integration broken |
| Route wiring | Frontend expects routes that don't exist → UI broken |
| Timestamp ordering | Child before parent → provenance timeline invalid |
| Import chain | Syntax errors in genesis files → whole system breaks |

---

## Integration Points — Complete Map

### Producers (Create Genesis Keys)

**Core Services:**
- `api/_genesis_tracker.py` — `track()` (primary, 40+ callers)
- `genesis/genesis_key_service.py` — `GenesisKeyService.create_key()` (full service)
- `genesis/tracking_middleware.py` — HTTP middleware, creates key per request
- `genesis/middleware.py` — `GenesisKeyMiddleware`, alternative middleware
- `genesis/file_watcher.py` — creates `FILE_OPERATION` keys on file changes

**Layer 1 Connectors:**
- `layer1/components/genesis_keys_connector.py` — creates keys on ingestion, learning, contributions
- `layer1/components/ingestion_connector.py` — generates fallback `GK-ingestion-{id}`
- `layer1/components/version_control_connector.py` — passes genesis_key_id through commits

**Cognitive/AI:**
- `cognitive/self_healing.py` — tracks healing actions
- `cognitive/healing_coordinator.py` — tracks resolution chain
- `cognitive/qwen_coding_net.py` — tracks code generation
- `cognitive/grace_compiler.py` — tracks `coding_agent_action`
- All modules importing `track` from `_genesis_tracker`

**Diagnostic Machine:**
- `diagnostic_machine/action_router.py` — creates keys for diagnostic actions and healing

**File Manager:**
- `file_manager/genesis_file_tracker.py` — `GenesisFileTracker` tracks uploads, processing, intelligence extraction, health checks

**Genesis Module:**
- `genesis/healing_system.py` — creates `FIX` keys for scaffolded healing
- `genesis/autonomous_triggers.py` — creates `GAP_IDENTIFIED`, `PRACTICE_OUTCOME` keys
- `genesis/autonomous_engine.py` — maps action types to key types
- `genesis/intelligent_cicd_orchestrator.py` — `GK-webhook-*`, `GK-icicd-*`
- `genesis/autonomous_cicd_engine.py` — `GK-acicd-*`

**Deterministic System:**
- `core/deterministic_lifecycle.py` — tracks component registration, lifecycle completion
- `core/deterministic_event_bus.py` — tracks event bus tasks
- `core/deterministic_coding_contracts.py` — tracks contract verdicts
- `core/deterministic_logger.py` — tracks lifecycle events

### Consumers (Read/Use Genesis Keys)

**Health & Monitoring:**
- `api/component_health_api.py` — `_get_genesis_keys()` for component status
- `api/autonomous_loop_api.py` — uses keys for trigger classification
- `api/consensus_fixer_api.py` — uses keys for consensus classification
- `diagnostic_machine/sensors.py` — `_collect_genesis_keys()` sensor data
- `diagnostic_machine/interpreters.py` — `GENESIS_KEY_ANOMALY` detection
- `diagnostic_machine/action_router.py` — reads keys for mirror analysis

**Intelligence & Mining:**
- `core/intelligence.py` — `GenesisKeyMiner` mines patterns from keys
- `genesis/realtime.py` — `GenesisRealtimeEngine` monitors error rates and triggers alerts

**Organization & Archival:**
- `librarian/genesis_key_curator.py` — daily curation and export
- `genesis/archival_service.py` — daily archival with reports
- `genesis/daily_organizer.py` — organizes by type and date

**Retrieval:**
- `retrieval/cognitive_retriever.py` — passes `genesis_key_id` in query/feedback
- `retrieval/multi_tier_integration.py` — passes `genesis_key_id` in queries

**Validation:**
- `genesis/deterministic_genesis_validator.py` — validates the system itself

**Frontend:**
- `frontend/src/components/GenesisKeyPanel.jsx` — displays keys, stats, archives
- `frontend/src/components/DevTab.jsx` — genesis stats, deterministic validation

### Schema Consumers (Tables Referencing genesis_key_id)

- `learning_examples.genesis_key_id` — Memory Mesh learning records
- `episodic_memory.genesis_key_id` — Episodic memory episodes
- `query_intelligence.genesis_key_id` — Query intelligence records
- `file_intelligence.genesis_key_id` — File intelligence records
- `notion_profile.genesis_key_id` — Notion integration
- `notion_task.genesis_key_id` — Notion tasks

---

## Known Issues

These are real problems found by the deterministic validators and code review:

### 1. `on_genesis_key_created_data` vs `on_genesis_key_created`

**Location**: `genesis/genesis_key_service.py` line 403, `genesis/autonomous_triggers.py`

The service calls `trigger_pipeline.on_genesis_key_created_data(extracted_key_data)` but the trigger pipeline only defines `on_genesis_key_created(genesis_key)` (expects a GenesisKey object, not a dict). The call raises `AttributeError` and is silently caught, so **autonomous triggers never fire from key creation**.

**Fix**: Add `on_genesis_key_created_data(data: dict)` to `GenesisTriggerPipeline`, or change the service to pass the key object.

### 2. `save_genesis_key_data` Missing in KB Integration

**Location**: `genesis/genesis_key_service.py` line 333, `genesis/kb_integration.py`

The service calls `kb_integration.save_genesis_key_data(extracted_key_data)` but `GenesisKBIntegration` only defines `save_genesis_key(key: GenesisKey)`. Falls back to passing the key object via `AttributeError` catch.

**Fix**: Add `save_genesis_key_data(data: dict)` to `GenesisKBIntegration`.

### 3. GenesisKeysConnector Model Mismatch

**Location**: `layer1/components/genesis_keys_connector.py`

The connector creates `GenesisKey` instances with fields `genesis_key_id`, `created_at`, `immutable`, `metadata`. The actual model uses `key_id`, `when_timestamp`, and has no `immutable` field. The `metadata` field doesn't exist — the model uses `metadata_human` and `metadata_ai`.

**Fix**: Update connector to use correct model field names.

### 4. `_handle_practice_outcome` Invalid Fields

**Location**: `genesis/autonomous_triggers.py`

Creates a `GenesisKey` with `description` and `metadata` — neither exists on the model. Should use `what_description` and `context_data`.

### 5. Frontend Routes Not Registered

**Location**: `frontend/src/components/GenesisKeyPanel.jsx`, `backend/app.py`

The panel fetches `/genesis/keys`, `/genesis/stats`, `/genesis/archives`, but no genesis router is registered in `app.py`. Genesis data is only accessible via the brain API (`call_brain("govern", "genesis_keys", {...})`).

---

## Evolution Timeline

### Phase 1: Core Tracking

- `GenesisKey` model with 5W1H fields
- `GenesisKeyService` with create, fix, rollback
- `_genesis_tracker.track()` fire-and-forget wrapper
- Database storage in SQLite

### Phase 2: Storage & Organization

- KB integration (JSON files in knowledge_base/)
- Qdrant vector storage (background batch upsert)
- Hot tier in-memory storage with sampling
- Daily organizer and archival service
- Librarian curator for daily curation

### Phase 3: Reactive System

- Realtime engine with watchers and alert rules (spike, burst, error rate)
- Cognitive event bus integration (`genesis.key_created`, `genesis.error`)
- Autonomous triggers on key creation (study, practice, health check, mirror)
- Recursive self-improvement loop (practice fail → gap → study → retry)

### Phase 4: Health & Diagnostics

- Component health API uses Genesis Keys for component status classification
- Diagnostic machine sensors collect Genesis Key metrics
- Action router creates keys for diagnostic and healing actions
- Pattern mining via `GenesisKeyMiner`

### Phase 5: Deterministic Integration (Current)

- `deterministic_genesis_validator.py` — 9 deterministic checks on Genesis Key system
- Deterministic event bus bridges Genesis errors to scan chain
- Deterministic lifecycle tracks component registration via Genesis Keys
- Deterministic coding contracts track verdict results via Genesis Keys
- Deterministic logger tracks every lifecycle event via Genesis Keys
- Genesis Key system is now self-validating — the deterministic system checks the integrity of the very tracking system everything depends on

---

## Summary: The Full Data Flow

```
1. ACTION OCCURS
   (user input, AI response, code change, error, file upload, etc.)
        │
2. GENESIS KEY CREATED
   track() captures: WHAT, WHEN, WHERE, WHY, WHO, HOW
        │
3. STORED IN 5 TIERS
   Hot (memory) → DB (SQLite) → KB (JSON files) → Qdrant (vectors) → Archive (daily)
        │
4. CATEGORIZED BY LIBRARIAN
   Daily curation → organized by type and date → summaries generated
        │
5. RAG RETRIEVES WHEN NEEDED
   Query → embed → Qdrant search → chunks → context → LLM prompt
        │
6. DETERMINISTIC SYSTEM VALIDATES
   Schema, chains, fix linkage, KB sync, user profiles, wiring
        │
7. IF BROKEN → FIX CHAIN
   Deterministic fix first → LLM reasoning (constrained by facts) → coding agent → verify
        │
8. IF ERROR → SELF-HEALING
   Error key → realtime alerts → autonomous triggers → healing coordinator → fix suggestion
        │
9. FULL PROVENANCE MAINTAINED
   Every fix creates a new key linked to the original → complete chain → rollback possible
```
