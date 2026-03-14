# Grace 3.1 — Orphan & Disconnection Audit Report
**Generated: 2026-03-14**

---

## EXECUTIVE SUMMARY

**143 orphaned files** detected across the backend. **5 API routers** are completely unwired (have routes but are never mounted). **3 critical feedback loops** are broken — Consensus→Executive, Ghost→Prompt, and Memory Mesh reconciliation. Two major service classes (`GraceSystemsIntegration`, `GraceAutonomousEngine`) exist but are never started or called.

---

## 1. UNWIRED API ROUTERS (5)
These define `APIRouter()` with endpoints but are **never mounted** in `app.py`:

| File | What It Does | Action |
|------|-------------|--------|
| `api/ask_grace_api.py` | Natural language query endpoint | Wire into app.py or merge into brain_api_v2 |
| `api/connection_api.py` | System connection status | Wire into app.py |
| `api/workspace_api.py` | Workspace/project management | Wire into app.py |
| `api/world_model_api.py` | World model queries | Wire into app.py |
| `api/test_verify_api.py` | Test verification endpoints | Wire or delete if dev-only |

---

## 2. CRITICAL BROKEN FEEDBACK LOOPS

### 2a. Consensus Engine → Executive (BROKEN)
**All 12 consensus-related files** have ZERO references to any executive/actuator.
- `cognitive/consensus_engine.py` — votes are computed but never sent anywhere
- `cognitive/consensus_actuation.py` — exists but doesn't connect to execution
- `cognitive/consensus_pipeline.py` — pipeline ends in void
- `core/engines/consensus_engine.py` — duplicate engine, also disconnected
- **Impact**: Self-trust metric never updates, drift goes undetected

### 2b. Ghost Memory → Prompt Builder (BROKEN)
- `cognitive/ghost_memory.py` — captures events to `.gaf` files but has NO reference to `rag_prompt`, `prompt_builder`, or `build_rag`
- **Impact**: Continuity of self across reboots is lost; night-window replay never fires

### 2c. Trust Engine → Consensus (BROKEN)
- `cognitive/trust_engine.py` — computes trust scores but never feeds them to consensus
- **Impact**: Trust-weighted voting is non-functional

### 2d. Memory Mesh → Reconciliation (BROKEN)
All **15 memory_mesh files** have ZERO reconciliation/sync/repair references:
- `cognitive/memory_mesh_cache.py`
- `cognitive/memory_mesh_integration.py`
- `cognitive/memory_mesh_learner.py`
- `cognitive/memory_mesh_metrics.py`
- `cognitive/memory_mesh_snapshot.py`
- `layer1/components/memory_mesh_connector.py`
- **Impact**: Partition-tolerant merge never runs; divergence triggers endless conflict flags

### 2e. Healing Systems → Live Integration (BROKEN)
All **23 healing-related files** have NO reference to `live_integration`:
- `cognitive/autonomous_healing_loop.py`
- `cognitive/autonomous_healing_system.py`
- `cognitive/governance_healing_bridge.py`
- `cognitive/healing_coordinator.py`
- `cognitive/proactive_healing_engine.py`
- `cognitive/self_healing.py`
- `diagnostic_machine/healing.py`
- `genesis/healing_system.py`
- **Impact**: Self-healing detects issues but can't actuate repairs in the live system

---

## 3. DEAD SERVICES (Never Started)

| Service | File | What It Does | Problem |
|---------|------|-------------|---------|
| `GraceSystemsIntegration` | `services/grace_systems_integration.py` | Central hub connecting all subsystems (memory, diagnostics, oracle, security, healing, ingestion, learning) | **Never imported or instantiated** anywhere in app.py or startup |
| `GraceAutonomousEngine` | `services/grace_autonomous_engine.py` | Sub-agent management, multi-threading, task scheduling, distributed execution | **Never imported or instantiated** anywhere |
| `GraceTeamManagement` | `services/grace_team_management.py` | Team/agent coordination | **Never imported or instantiated** anywhere |

---

## 4. LEGACY / DEAD CODE

| File | Status |
|------|--------|
| `legacy_components/legacy_brain.py` | Old brain logic, superseded by `brain_api_v2` |
| `legacy_components/data_warehouse.py` | Old data warehouse, unclear if still needed |
| `cognitive_framework/FeedbackIntegrator.py` | Never imported |
| `cognitive_framework/GovernancePrimeDirective.py` | Never imported |
| `cognitive_framework/GraceCognitionLinter.py` | Never imported |
| `cognitive_framework/GraceLoopOutput.py` | Never imported |
| `core/cognitive_pipeline.py` | Never imported |
| `core/deterministic_e2e_validator.py` | Never imported |
| `core/error_watcher.py` | Never imported |
| `core/file_artifact_tracker.py` | Never imported |
| `core/services/workspace_service.py` | Never imported |

---

## 5. ORPHANED INFRASTRUCTURE

| File | Category |
|------|----------|
| `infrastructure/resource_arbitrator.py` | Never imported — resource management logic exists but isn't used |
| `coding_agent/validation_pipeline.py` | Never imported |
| `llm_orchestrator/cognitive_router.py` | Never imported — cognitive routing logic dead |
| `llm_orchestrator/fine_tuning.py` | Never imported |
| `memory/ingest_validation.py` | Never imported |
| `models/healing_models.py` | Never imported — DB models for healing exist but unused |
| `librarian/seed_default_rules.py` | Never imported |
| `verification/context_shadower.py` | Never imported |
| `setup/initializer.py` | Never imported |

---

## 6. ORPHANED DATABASE MIGRATIONS (never run automatically)

| File | What It Creates |
|------|----------------|
| `database/drop_librarian_tables.py` | Drops librarian tables |
| `database/migrate_add_file_intelligence.py` | File intelligence columns |
| `database/migrate_add_genesis_keys.py` | Genesis key columns |
| `database/migrate_add_librarian.py` | Librarian tables |
| `database/migrate_add_memory_mesh.py` | Memory mesh tables |
| `database/migration_memory_mesh_indexes.py` | Memory mesh indexes |
| `database/migrations/add_document_download_fields.py` | Document download fields |
| `database/migrations/add_memory_mesh_tables.py` | Memory mesh tables (duplicate?) |
| `database/migrations/add_query_intelligence_tables.py` | Query intelligence |
| `database/migrations/add_scraping_tables.py` | Scraping tables |
| `database/postgres_adapter.py` | Postgres-specific adapter |
| `database/init_example.py` | Example init script |

---

## 7. DUPLICATE/REDUNDANT SYSTEMS

| System | Files | Issue |
|--------|-------|-------|
| Consensus Engine | `cognitive/consensus_engine.py` AND `core/engines/consensus_engine.py` | Two implementations, neither wired |
| Autonomous Learning Starter | `start_autonomous_learning.py` AND `start_autonomous_learning_simple.py` AND `scripts/start_autonomous_learning.py` AND `scripts/start_autonomous_learning_simple.py` | 4 copies |
| Orphan Finder | `find_orphans.py` AND `find_cognitive_orphans.py` AND `scripts/cleanup_orphaned_files.py` AND `cleanup_orphaned_files.py` | 4 copies |
| Migration Runner | `run_migrations.py` AND `run_all_migrations.py` AND `scripts/run_migrations.py` AND `scripts/run_all_migrations.py` | 4 copies |
| Reset & Reingest | `reset_and_reingest.py` AND `scripts/reset_and_reingest.py` AND `RESET_AND_REINGEST_GUIDE.py` AND `scripts/RESET_AND_REINGEST_GUIDE.py` | 4 copies |

---

## 8. PRIORITY WIRING TASKS (in order)

### P0 — Critical (system can't self-improve without these)
1. **Wire Consensus → Executive**: Make `consensus_engine.py` output signed quorum packets to the execution layer
2. **Wire Ghost Memory → Prompt Builder**: Plumb `ghost_memory.py` retrieval into `build_rag_prompt()` so continuity works
3. **Wire Trust Engine → Consensus**: Feed trust scores into consensus voting weights
4. **Start `GraceSystemsIntegration`** in `app.py` lifespan — this is the missing central nervous system

### P1 — High (functional subsystems sitting idle)
5. **Wire Memory Mesh reconciliation** — add a background cron/task that calls mesh-sync
6. **Wire Healing → Live Integration** — connect healing detection to actual repair actuators
7. **Mount the 5 unwired API routers** in `app.py`
8. **Start `GraceAutonomousEngine`** in `app.py` lifespan for sub-agent management

### P2 — Cleanup
9. Consolidate duplicate scripts (4 orphan finders → 1, 4 migration runners → 1)
10. Delete or archive `legacy_components/` if confirmed superseded
11. Delete the 4 `cognitive_framework/` orphans or wire them in
12. Run all orphaned database migrations or delete them

---

## TOTAL COUNTS

| Category | Count |
|----------|-------|
| Orphaned files (never imported) | **143** |
| Unwired API routers | **5** |
| Broken critical feedback loops | **5** |
| Dead services (never started) | **3** |
| Legacy/dead modules | **11** |
| Orphaned DB migrations | **12** |
| Duplicate script clusters | **5** |
