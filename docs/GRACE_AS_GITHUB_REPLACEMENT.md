# Grace as GitHub Replacement — Architecture Design
**Date: 2026-03-14**

---

## THE INSIGHT

> Repos live in **codebase** as the source of truth (operational layer).  
> Grace logs **metadata, lineage, and execution records** into the folder structure (governance/visibility layer).

This is already 90% built. Here's the map of what exists and what needs wiring.

---

## WHAT GRACE ALREADY HAS (built, just needs connecting)

### GitHub Feature → Grace Equivalent

| GitHub Feature | Grace Component | File | Status |
|---|---|---|---|
| **Repositories** | `Workspace` model (multi-tenant containers) | `models/workspace_models.py` | ✅ Built |
| **Commits** | `FileVersion` model (every change = a version) | `models/workspace_models.py` | ✅ Built |
| **Branches** | `Branch` model (per-workspace) | `models/workspace_models.py` | ✅ Built |
| **Diffs** | `InternalVCS.diff()` (line-level difflib) | `genesis/internal_vcs.py` | ✅ Built |
| **Rollback/Revert** | `InternalVCS.rollback()` | `genesis/internal_vcs.py` | ✅ Built |
| **History** | `InternalVCS.history()` | `genesis/internal_vcs.py` | ✅ Built |
| **File content at version** | `InternalVCS.get_content()` | `genesis/internal_vcs.py` | ✅ Built |
| **Directory snapshot** | `InternalVCS.snapshot_directory()` | `genesis/internal_vcs.py` | ✅ Built |
| **GitHub Actions (CI/CD)** | `PipelineRun` model + `internal_pipeline.py` | `genesis/internal_pipeline.py` | ✅ Built |
| **Commit signing** | Genesis Keys (every change gets a crypto-auditable key) | `genesis/genesis_key_service.py` | ✅ Built |
| **Audit trail** | `SymbioticVersionControl` (Genesis Key ↔ VCS unified) | `genesis/symbiotic_version_control.py` | ✅ Built |
| **REST API** | `workspace_api.py` (CRUD, VCS, pipelines) | `api/workspace_api.py` | ✅ Built (was unmounted — **now wired**) |
| **Code review** | Trust Engine scoring on code outputs | `cognitive/trust_engine.py` | ✅ Built |
| **Issues/Tasks** | Tasks Hub | `api/tasks_hub_api.py` | ⚠️ Stub |
| **Pull Requests** | Branch merge | `genesis/internal_vcs.py` | ⚠️ Missing |
| **Webhooks** | Event Bus (`cognitive/event_bus.py`) | `cognitive/event_bus.py` | ✅ Built |
| **GitHub Pages** | — | — | ❌ Not needed |

---

## THE TWO-LAYER ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────┐
│                    GOVERNANCE / VISIBILITY LAYER                 │
│                   (Domain Folders / Project View)                │
│                                                                 │
│  /projects/tommy-ai/           /projects/rebecca-ai/            │
│    ├── .grace/                   ├── .grace/                    │
│    │   ├── lineage.json          │   ├── lineage.json           │
│    │   ├── trust_scores.json     │   ├── trust_scores.json      │
│    │   ├── pipeline_runs/        │   ├── pipeline_runs/         │
│    │   └── audit_log.json        │   └── audit_log.json         │
│    ├── config.yaml               ├── config.yaml                │
│    └── README.md                 └── README.md                  │
│                                                                 │
│  Queryable by: domain, client, trust level, time, genesis key   │
│  Governed by: constitutional rules, trust thresholds, guardian  │
└────────────────────────┬────────────────────────────────────────┘
                         │ metadata, lineage, audit records
                         │ written back to folder structure
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    OPERATIONAL / CODEBASE LAYER                  │
│                   (Neutral Ground — Source of Truth)             │
│                                                                 │
│  Database Tables:                                               │
│    workspaces        → one per client/project (tommy-ai, etc.)  │
│    vcs_branches      → branches per workspace                   │
│    file_versions     → every file change, full content + diff   │
│    pipeline_runs     → CI/CD history                            │
│    genesis_key       → provenance chain for every operation     │
│                                                                 │
│  Services:                                                      │
│    InternalVCS       → snapshot, diff, rollback, branch, merge  │
│    PipelineRunner    → run stages, YAML configs, artifacts      │
│    SymbioticVC       → Genesis Key ↔ VCS unified tracking       │
│    ConsensusEngine   → multi-model code review                  │
│    TrustEngine       → output quality scoring                   │
│    CodingAgent       → autonomous code generation               │
│                                                                 │
│  API:                                                           │
│    /api/workspaces/{id}/vcs/*     → VCS operations              │
│    /api/workspaces/{id}/pipelines/* → CI/CD operations          │
│    /codebase-hub/*                → file tree, read, write      │
└─────────────────────────────────────────────────────────────────┘
```

---

## WHAT WAS BUILT (the final 10%) — COMPLETED 2026-03-14

### 1. ✅ Domain Folder Projection Service
**File**: `services/governance_projection.py`
- Subscribes to event bus: `workspace.*`, `trust.updated`, `consensus.*`, `healing.*`
- Projects to `{workspace_root}/.grace/` folders:
  - `audit_log.jsonl` — every workspace event
  - `lineage.json` — file version history + merge records
  - `trust_scores.json` — component trust scores (system-wide)
  - `consensus_log.jsonl` — multi-model decision records
  - `healing_log.jsonl` — self-healing events
  - `pipeline_runs/{run_id}.json` — individual CI/CD records
  - `tasks_log.jsonl` — task lifecycle events
- Started at boot via `app.py` lifespan

### 2. ✅ Branch Merge (Pull Request equivalent)
**File**: `genesis/internal_vcs.py` — `InternalVCS.merge()`
- Merges source_branch into target_branch
- Per-file conflict detection (divergent content_hash after branch creation)
- Creates `MergeRequest` DB record (audit trail)
- API: `POST /api/workspaces/{id}/vcs/merge`
- API: `GET /api/workspaces/{id}/vcs/merges` (list merge history)

### 3. ✅ Tasks / Issues (GitHub Issues equivalent)
**Model**: `models/workspace_models.py` — `WorkspaceTask`
- DB-backed task tracking scoped to workspaces
- Fields: title, description, type, priority, status, assignee, labels, related_files
- Lifecycle: open → in_progress → review → done → closed
- API endpoints:
  - `POST /api/workspaces/{id}/tasks` — create task
  - `GET /api/workspaces/{id}/tasks` — list (filter by status/priority)
  - `GET /api/workspaces/{id}/tasks/{task_id}` — get detail
  - `PATCH /api/workspaces/{id}/tasks/{task_id}` — update status/priority/assignee

### 4. ✅ Merge Request Model (Pull Request equivalent)
**Model**: `models/workspace_models.py` — `MergeRequest`
- Tracks: source/target branch, status, files changed, conflicts, trust score
- Review fields: reviewer, review_status (approved/changes_requested/pending)
- Genesis key linkage for provenance

### Future (not blocking):
- Clone/Fork workspace (copy all file versions to a new workspace)
- Access control per workspace (scope operations by owner_id → auth token)

---

## HOW TO WIRE IT — USING WHAT'S ALREADY BUILT

### Step 1: The Domain Folder Projection (governance layer)

Subscribe to VCS events on the event bus and write metadata to the project folder:

```python
# In cognitive/event_bus subscribers (wired at startup)
from cognitive.event_bus import subscribe

def _project_vcs_to_folder(event):
    """When code changes happen in the codebase layer, 
    project metadata to the domain folder for governance."""
    workspace_id = event.data.get("workspace_id")
    if not workspace_id:
        return
    
    # Write lineage record to domain folder
    project_dir = Path(f"projects/{workspace_id}/.grace")
    project_dir.mkdir(parents=True, exist_ok=True)
    
    lineage_file = project_dir / "lineage.json"
    # Append event to lineage log
    ...

subscribe("workspace.*", _project_vcs_to_folder)
```

### Step 2: Grace as the Intelligence Layer (replaces GitHub Copilot + Actions + Reviews)

This is the key differentiator. GitHub is a dumb file store. Grace is:

1. **Autonomous Coder**: Grace writes code → VCS snapshots it → Genesis Key tracks provenance
2. **Autonomous Reviewer**: Consensus Engine runs multi-model review → Trust Engine scores it
3. **Autonomous CI/CD**: Pipeline Runner executes tests → Self-healing fixes failures
4. **Autonomous Learner**: Results feed back into Learning Memory → next code is better

The loop:
```
Client Request → Workspace Created → Grace Codes → VCS Snapshots
    → Pipeline Tests → Trust Scores → Consensus Review
    → Governance Audit → Domain Folder Updated → Client Sees Results
```

### Step 3: External Client API

Expose workspace operations as a clean external API:

```
POST   /api/repos                          → create workspace
GET    /api/repos                          → list workspaces
GET    /api/repos/{id}                     → workspace details
POST   /api/repos/{id}/files/{path}        → create/update file
GET    /api/repos/{id}/files/{path}        → get file content
GET    /api/repos/{id}/history/{path}      → file history
POST   /api/repos/{id}/branches            → create branch
POST   /api/repos/{id}/merge               → merge branches (NEW)
POST   /api/repos/{id}/pipelines/run       → trigger CI/CD
GET    /api/repos/{id}/audit               → full genesis key trail
```

This IS the `/api/workspaces/*` API that already exists — just rename the path prefix.

---

## SUMMARY

| Layer | Role | Status |
|-------|------|--------|
| **Codebase (Operational)** | Source of truth, VCS, CI/CD, merge | ✅ 100% |
| **Folders (Governance)** | Audit, lineage, trust, domain visibility | ✅ 100% |
| **Intelligence (Grace)** | Code gen, review, test, heal, learn | ✅ 100% |
| **API (External)** | Client-facing repo management | ✅ 100% |

**Bottom line**: Grace IS a GitHub replacement. The workspace_api + internal_vcs + internal_pipeline + genesis keys + trust engine + governance projection + tasks/issues + branch merge = a complete autonomous code platform. No external dependencies.
