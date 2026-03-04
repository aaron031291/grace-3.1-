# GRACE 3.1.0 — Forensic System Analysis

**Date:** 2026-03-04  
**Branch:** `Cursor/aaron-new2system-forensic-analysis-89c3`  
**Commit:** `c31ced44` — "fix(backend): stabilize chat endpoints, session mgmt & modernize codebase"

---

## Executive Summary

GRACE (Genesis-driven RAG Autonomous Cognitive Engine) is a large full-stack monorepo consisting of a FastAPI backend, React 19 frontend, VSCode extension, and multiple MCP servers. The system is ambitious and feature-rich, but the forensic analysis reveals **5 critical**, **12 high**, and **15+ medium** issues across broken imports, failed migrations, security leaks, unreachable code, build misconfigurations, and structural debt.

---

## CRITICAL Issues (System-Breaking)

### C1. Migration `add_scraping_tables.py` — Wrong Import (Will Crash)

**File:** `backend/database/migrations/add_scraping_tables.py:5`

```python
from database.connection import DatabaseConnection, Base  # Base does NOT exist here
```

`Base` is defined in `database.base`, not `database.connection`. This migration will raise `ImportError` every time it runs.

**Fix:** Change to `from database.base import BaseModel as Base` or `from database.base import Base`.

---

### C2. Migration `add_query_intelligence_tables.py` — PostgreSQL-Only SQL on SQLite Default

**File:** `backend/database/migrations/add_query_intelligence_tables.py:22-101`

Uses `SERIAL PRIMARY KEY` and `ON DELETE CASCADE` in raw DDL — both PostgreSQL-specific. Since the default database is SQLite, this migration **will fail** on any default installation.

**Fix:** Use SQLAlchemy ORM `create_all()` instead of raw SQL, or provide SQLite-compatible DDL (`INTEGER PRIMARY KEY AUTOINCREMENT`).

---

### C3. Migration `migrate_add_telemetry.py` — Missing Required Argument

**File:** `backend/database/migrate_add_telemetry.py:35`

```python
DatabaseConnection.initialize()  # TypeError: missing required arg 'config'
```

`DatabaseConnection.initialize()` requires a `DatabaseConfig` argument. This script will crash with `TypeError` when run standalone.

**Fix:** Add `config = DatabaseConfig.from_env()` before the call.

---

### C4. `force_reingest.py` — Wrong Import Path

**File:** `backend/force_reingest.py:13`

```python
from database.connection import get_session  # get_session is in database.session, not database.connection
```

`get_session` is defined in `database.session`. This utility script is completely non-functional.

**Fix:** Change to `from database.session import get_session`.

---

### C5. 50MB Video File Committed to Git

**File:** `backend/mcp_repos/DesktopCommanderMCP/1080_60.mp4` — **50 MB**

A full-resolution video file is committed to the repository. This bloats clone times, wastes storage, and is already baked into git history. Not in `.gitignore`.

**Fix:** Remove from repo, add `*.mp4` to `.gitignore`, and consider `git filter-branch` or BFG Repo Cleaner to purge from history.

---

## HIGH Issues (Functionality Holes)

### H1. Broken Imports Behind Silent try/except

**File:** `backend/core/services/govern_service.py`

| Line | Import | Actual Location |
|------|--------|-----------------|
| 57 | `from governance.governance_engine import GovernanceEngine` | Module does not exist (only `security/governance.py`) |
| 87 | `from kpi.kpi_tracker import get_tracker` | Should be `ml_intelligence.kpi_tracker` |

Both wrapped in `try/except` — they silently return degraded fallback values. The governance dashboard and trust scores are **always returning defaults**, never real data.

---

### H2. `run_migrations.py` Missing Several Migration Modules

**File:** `backend/run_migrations.py`

The main migration script does **not** include:
- `add_scraping_tables` (web scraping tables)
- `add_query_intelligence_tables` (query tracking)
- `add_document_download_fields` (download tracking)
- `add_memory_mesh_tables` (memory mesh)

These features have database tables that will never be created via the standard migration path.

---

### H3. VSCode Extension Test Script Points to Wrong Directory

**File:** `grace-os-vscode/package.json:442`

```json
"test": "node ./out/test/runTest.js"
```

But `tsconfig.json` sets `outDir: "dist"`. Compiled output goes to `dist/`, not `out/`. Tests will **always fail** with `MODULE_NOT_FOUND`.

---

### H4. `requirements.txt` — Duplicate Dependency, No Pinning

**File:** `backend/requirements.txt`

- `filelock` appears **twice**: line 12 (unpinned) and line 78 (`==3.13.1`) — conflicting declarations.
- 77 out of 81 packages are **completely unpinned** — builds are non-reproducible.
- No `requirements.lock`, `Pipfile.lock`, or `pip-tools` managed file exists.

---

### H5. CI Pipeline Swallows All Test Failures

**File:** `.github/workflows/ci.yml:44,49,73`

```yaml
python -m pytest tests/ ... || true
mypy ... || true
npm run lint || true
```

Every test/lint/type-check step uses `|| true` — **failures never fail the CI build**. The entire CI pipeline is decorative; it will always pass regardless of actual results.

---

### H6. Hardcoded Google Analytics API Secrets

**Files:**
- `backend/mcp_repos/DesktopCommanderMCP/track-installation.js:77-78`
- `backend/mcp_repos/DesktopCommanderMCP/uninstall-claude-server.js:15-16`
- `backend/mcp_repos/DesktopCommanderMCP/setup-claude-server.js:15-16`
- `backend/mcp_repos/DesktopCommanderMCP/src/utils/capture.ts:257-275`

GA_API_SECRET `5M0mC--2S_6t94m8WrI60A` is hardcoded in multiple files. Should be in environment variables.

---

### H7. Filesystem MCP Server Dockerfile — Broken Build

**File:** `backend/mcp_repos/mcp-servers/src/filesystem/Dockerfile`

Uses `npm ci` but does not copy the root `package-lock.json` into the build context. The Docker build **will always fail**.

---

### H8. Hardcoded Absolute Path in Utility Script

**File:** `backend/delete_gdp_for_reingest.py:23`

```python
DB_PATH = "/home/umer/Public/projects/grace_3/backend/data/documents.db"
```

Hardcoded to a specific developer's machine. Will fail for anyone else.

---

### H9. Backend Dockerfile Only Builds One MCP Server

**File:** `backend/Dockerfile`

The MCP builder stage only copies and builds `DesktopCommanderMCP`. The other MCP servers (filesystem, memory, sequential-thinking, everything) are not built or included in the Docker image. Any feature depending on those servers will fail in containerized deployments.

---

### H10. CD Pipeline Has No Real Deployment

**File:** `.github/workflows/cd.yml`

Both `deploy-staging` and `deploy-production` jobs only `echo` messages — no actual deployment logic exists. The CD pipeline is a skeleton.

---

### H11. Unimplemented Features Left as Stubs

| File | Function | Status |
|------|----------|--------|
| `backend/grace_os/layers/l2_planning/planning_layer.py:77` | `_handle_replan()` | Returns "Re-plan not yet implemented." |
| `backend/retrieval/query_intelligence.py:218` | Context integration | Stub — just appends text to query |

---

### H12. `@modelcontextprotocol/sdk` Version Skew

| Package | Version |
|---------|---------|
| MCP Servers (memory, filesystem, etc.) | `^1.26.0` |
| DesktopCommanderMCP | `^1.9.0` |

Major version gap. The MCP orchestrator may send/receive incompatible messages between these components.

---

## MEDIUM Issues (Code Quality / Debt)

### M1. Silent Exception Swallowing Across Core Services

Multiple `except: pass` blocks in critical service code:

| File | Occurrences |
|------|-------------|
| `backend/core/services/files_service.py` | 2 |
| `backend/core/services/code_service.py` | 4 |
| `backend/core/services/data_service.py` | 1 |
| `backend/core/services/tasks_service.py` | 1 |
| `backend/core/services/govern_service.py` | 1 |
| `backend/core/services/system_service.py` | 2 |

Errors are silently swallowed, making debugging extremely difficult.

---

### M2. `app.py` is 1918 Lines — God File

**File:** `backend/app.py` — 1918 lines

Contains the entire FastAPI application, all route mounting, lifespan management, request models, and business logic. This is a maintenance and testing bottleneck.

---

### M3. Deprecated APIs Still in Use

| File | Deprecated Item |
|------|-----------------|
| `backend/mcp_repos/mcp-servers/src/filesystem/index.ts:190` | `read_file` → use `read_text_file` |
| `backend/mcp_repos/DesktopCommanderMCP/src/terminal-manager.ts:509` | `readOutput` → use `readOutputPaginated` |
| `backend/genesis/autonomous_triggers.py:762` | `session` parameter deprecated and ignored |

---

### M4. TypeScript Version Inconsistency

| Package | TypeScript Version |
|---------|--------------------|
| mcp-servers/sequentialthinking | `^5.3.3` |
| mcp-servers/memory | `^5.6.2` |
| mcp-servers/filesystem | `^5.8.2` |
| DesktopCommanderMCP | `^5.3.3` |
| grace-os-vscode | `^5.3.2` |

Five different TypeScript versions across the monorepo.

---

### M5. Frontend Uses Non-Standard Vite Fork

**File:** `frontend/package.json`

```json
"vite": "npm:rolldown-vite@7.2.5"
```

Using `rolldown-vite` aliased as `vite`. This is experimental and may diverge from upstream Vite, causing plugin incompatibility.

---

### M6. `react-trello` Likely Incompatible with React 19

**File:** `frontend/package.json`

`react-trello@^2.2.11` was last updated in 2021 and targets React 16/17. Running it under React 19 may cause runtime errors or warnings about legacy lifecycle methods.

---

### M7. Frontend Dockerfile Needs `--legacy-peer-deps`

**File:** `frontend/Dockerfile`

```dockerfile
RUN npm ci --legacy-peer-deps
```

This flag masks peer dependency conflicts rather than resolving them. Dependencies may have incompatible version requirements.

---

### M8. `.gitignore` Has Trailing Space

**File:** `.gitignore:83`

```
data/ 
```

Trailing space on the `data/` entry can cause unexpected gitignore behavior on some platforms.

---

### M9. Qdrant Storage Committed to Repository

**Directory:** `qdrant_storage/` — 2.4 MB

Local Qdrant vector database storage is committed. This is machine-specific runtime data and should be in `.gitignore`.

---

### M10. Audit/Patch Files in Repository Root

- `recent_13_commits.patch` (1.7 MB)
- `commits_audit.patch`
- `commits_audit_utf8.patch`
- `commits_audit_diffs/`
- `commits_audit_diffs.txt`

Development artifacts that should not be in the repository.

---

### M11. No CI Coverage for VSCode Extension or MCP Servers

**File:** `.github/workflows/ci.yml`

CI only tests backend (Python) and frontend (Node build). No jobs exist for:
- `grace-os-vscode` (compile, lint, test)
- MCP servers (build, test)

These components have zero automated quality gates.

---

### M12. SQL Injection Risk Pattern (Low Risk)

**File:** `backend/core/services/govern_service.py:141`

```python
f"SELECT * FROM governance_decisions ORDER BY id DESC LIMIT {int(limit)}"
```

Uses f-string in SQL. The `int()` cast prevents injection, but parameterized queries are the correct pattern.

---

### M13. Debug console.log Statements in Production MCP Code

**File:** `backend/mcp_repos/mcp-servers/src/everything/transports/streamableHttp.ts`

14 `console.log` statements in non-test production code.

---

### M14. No `.env.production` or `.env.staging` Templates

Only `.env.example` exists for both backend and frontend. No production/staging templates exist for deployment configuration.

---

### M15. `@types/node` Version Inconsistency

| Package | `@types/node` |
|---------|---------------|
| MCP Servers | `^22` |
| DesktopCommanderMCP | `^20.17.24` |
| grace-os-vscode | `^20.10.0` |

---

## Architecture Map — What's Healthy vs. Broken

```
GRACE 3.1.0 System Health Map
==============================

[HEALTHY]  FastAPI core app.py ............... Runs, serves endpoints
[HEALTHY]  Database connection/session ....... SQLite/PostgreSQL working
[HEALTHY]  Docker Compose stack .............. Backend + Frontend + Qdrant + Ollama
[HEALTHY]  React 19 Frontend ................ Builds with Vite
[HEALTHY]  Cognitive engine (OODA, memory) ... Functional
[HEALTHY]  RAG retrieval pipeline ........... Multi-tier working
[HEALTHY]  Genesis key tracking ............. Recording events
[HEALTHY]  Security middleware .............. Rate limiting, CORS, headers
[HEALTHY]  Brain API v2 .................... Direct function calls

[DEGRADED] Governance dashboard ............. Always returns defaults (broken import)
[DEGRADED] Trust/KPI scores ................ Always returns 0.5 (broken import)
[DEGRADED] Planning layer .................. Re-planning not implemented
[DEGRADED] Query intelligence .............. Context integration is a stub
[DEGRADED] CI pipeline ..................... All failures swallowed (|| true)
[DEGRADED] Core services ................... Silent exception swallowing

[BROKEN]   Scraping tables migration ........ ImportError (wrong Base import)
[BROKEN]   Query intelligence migration ..... PostgreSQL SQL on SQLite
[BROKEN]   Telemetry migration .............. TypeError (missing config arg)
[BROKEN]   force_reingest.py ................ ImportError (wrong import path)
[BROKEN]   delete_gdp_for_reingest.py ....... Hardcoded path to dev machine
[BROKEN]   VSCode extension tests ........... Wrong output directory (out/ vs dist/)
[BROKEN]   Filesystem MCP Dockerfile ........ Missing package-lock.json
[BROKEN]   CD pipeline ...................... No actual deployment logic
```

---

## Recommended Priority Actions

1. **Fix the 4 broken imports** (C1, C4, and H1) — 15 min fix, restores migrations + governance
2. **Fix telemetry migration** (C3) — add `DatabaseConfig.from_env()` call
3. **Make query intelligence migration DB-agnostic** (C2) — use ORM instead of raw SQL
4. **Remove 50MB video from repo** (C5) — add `*.mp4` to `.gitignore`
5. **Remove `|| true` from CI** (H5) — make CI actually catch regressions
6. **Pin `requirements.txt` versions** (H4) — run `pip freeze` for reproducibility
7. **Fix VSCode extension test path** (H3) — change `out/` to `dist/`
8. **Add missing migrations to `run_migrations.py`** (H2)
9. **Move hardcoded secrets to env vars** (H6)
10. **Break up `app.py`** (M2) — extract into focused modules

---

*Report generated by forensic analysis of commit `c31ced44` on the `Cursor/aaron-new2system-forensic-analysis-89c3` branch.*
