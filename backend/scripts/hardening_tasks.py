"""
Grace Hardening Tasks — 20 real fix/heal tasks dispatched to Kimi & Opus.

Each task targets an actual problem in the codebase. Agents work in parallel
(max 5 concurrent), results flow through:
  - Live Feed (autonomous_log_api WebSocket)
  - Coding Agent Governance tab (HITL review)
  - Genesis Key tracking
  - Spindle event bus

Run:  python -m scripts.hardening_tasks
"""

import sys
import os
import time
import logging
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s][%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("hardening")

# ── 20 Hardening Tasks ──────────────────────────────────────────────────

HARDENING_TASKS = [
    # --- Database & Connection Fixes ---
    {
        "id": "HARDEN-001",
        "type": "fix",
        "desc": "Fix database/migrations/add_scraping_tables.py — imports Base from database.connection but it's in database.base. Change 'from database.connection import Base' to 'from database.base import BaseModel as Base'.",
        "file": "database/migrations/add_scraping_tables.py",
        "error": "ImportError: cannot import name 'Base' from 'database.connection'",
    },
    {
        "id": "HARDEN-002",
        "type": "fix",
        "desc": "Fix database/migrate_add_telemetry.py — DatabaseConnection.initialize() called without required config argument. Add config parameter or use session_scope() pattern instead.",
        "file": "database/migrate_add_telemetry.py",
        "error": "TypeError: initialize() missing required argument: 'config'",
    },
    {
        "id": "HARDEN-003",
        "type": "fix",
        "desc": "Fix force_reingest.py — imports get_session from database.connection but it's in database.session. Change to 'from database.session import session_scope'.",
        "file": "force_reingest.py",
        "error": "ImportError: cannot import name 'get_session' from 'database.connection'",
    },
    {
        "id": "HARDEN-004",
        "type": "fix",
        "desc": "Fix database/migrations/add_query_intelligence_tables.py — uses PostgreSQL SERIAL PRIMARY KEY syntax which fails on SQLite. Use platform-agnostic Column(Integer, primary_key=True, autoincrement=True) instead.",
        "file": "database/migrations/add_query_intelligence_tables.py",
        "error": "sqlite3.OperationalError: near 'SERIAL': syntax error",
    },
    # --- Silent Import Failures ---
    {
        "id": "HARDEN-005",
        "type": "fix",
        "desc": "Fix core/services/govern_service.py — GovernanceEngine and KPI tracker imports are broken but silently caught. Fix the import paths so governance actually loads.",
        "file": "core/services/govern_service.py",
        "error": "Silent ImportError for GovernanceEngine — governance rules not enforced",
    },
    {
        "id": "HARDEN-006",
        "type": "fix",
        "desc": "Fix genesis middleware spam — genesis/middleware.py logs 'Database not initialized' on every request. Add a check: if DB not ready, skip Genesis key creation silently with a single startup warning instead of per-request errors.",
        "file": "genesis/middleware.py",
        "error": "ERROR: Failed to create request Genesis Key: Database not initialized",
    },
    # --- Event Bus & Spindle ---
    {
        "id": "HARDEN-007",
        "type": "fix",
        "desc": "Fix SpindleEventStore write queue overflow — the queue fills to 50k and spams warnings. Increase queue size to 100k and ensure the flush thread drains faster by reducing sleep from 0.5s to 0.1s.",
        "file": "cognitive/spindle_event_store.py",
        "error": "WARNING: Write queue full, falling back to sync append (repeated 1000s of times)",
    },
    {
        "id": "HARDEN-008",
        "type": "fix",
        "desc": "Fix OODA loop phase errors in diagnostic_machine/action_router.py — ensure the OODA loop is properly reset between diagnostic cycles. The OODAPhase import and phase recovery logic needs verification.",
        "file": "diagnostic_machine/action_router.py",
        "error": "OODA Decide failed: Cannot decide in phase OODAPhase.COMPLETED",
    },
    # --- Connection & Network ---
    {
        "id": "HARDEN-009",
        "type": "fix",
        "desc": "Fix ProactorEventLoop ConnectionResetError on Windows — the main Grace process should set WindowsSelectorEventLoopPolicy like spindle_daemon.py does. Add the policy check to app.py or grace_start.py.",
        "file": "app.py",
        "error": "ConnectionResetError: [WinError 10054] connection forcibly closed",
    },
    {
        "id": "HARDEN-010",
        "type": "fix",
        "desc": "Fix vector_db/client.py — Qdrant connection fails silently and retries forever. Add a max retry count (3 attempts), then disable vector search gracefully instead of blocking startup.",
        "file": "vector_db/client.py",
        "error": "ConnectionError: repeated Qdrant connection failures blocking boot",
    },
    # --- Model & API Robustness ---
    {
        "id": "HARDEN-011",
        "type": "fix",
        "desc": "Fix SQLAlchemy 'Table already defined' error — models/database_models.py has duplicate table definitions from circular imports. Add __table_args__ = {'extend_existing': True} to affected models.",
        "file": "models/database_models.py",
        "error": "InvalidRequestError: Table 'users' is already defined for this MetaData instance",
    },
    {
        "id": "HARDEN-012",
        "type": "fix",
        "desc": "Fix scraping/service.py — trafilatura import fails. Add a try/except around the import with a clear warning, and provide a fallback using BeautifulSoup which is already installed.",
        "file": "scraping/service.py",
        "error": "ImportError: No module named 'trafilatura'",
    },
    # --- Startup & Initialization ---
    {
        "id": "HARDEN-013",
        "type": "fix",
        "desc": "Fix genesis_daily_api.py — session_scope is mocked during tests causing 'no db' exceptions. The mock detection is wrong. Check if session_scope is actually callable before use.",
        "file": "api/genesis_daily_api.py",
        "error": "Exception: no db — session_scope is a Mock object",
    },
    {
        "id": "HARDEN-014",
        "type": "fix",
        "desc": "Fix startup sequence — ensure DatabaseConnection.initialize() is called BEFORE any Genesis middleware or API routes try to use it. Move DB init to the top of the startup chain in app.py.",
        "file": "app.py",
        "error": "Database not initialized. Call DatabaseConnection.initialize() first",
    },
    # --- Coding Pipeline Hardening ---
    {
        "id": "HARDEN-015",
        "type": "fix",
        "desc": "Fix coding_pipeline.py Layer 8 deploy gate — Path.home() may fail on some Windows setups. Add a try/except fallback to use os.path.expanduser('~') instead.",
        "file": "core/coding_pipeline.py",
        "error": "Potential OSError on Path.home() in restricted environments",
    },
    {
        "id": "HARDEN-016",
        "type": "fix",
        "desc": "Harden coding_agents.py — when Kimi or Opus API keys are missing, the agent pool still creates agent objects that will fail on every call. Add API key validation in _init_agents and skip agents without keys.",
        "file": "cognitive/coding_agents.py",
        "error": "API call fails with 401 Unauthorized for agents without configured keys",
    },
    # --- Self-Healing ---
    {
        "id": "HARDEN-017",
        "type": "fix",
        "desc": "Fix healing_coordinator.py — the network_repair healing step succeeds but doesn't verify the fix actually worked. Add a post-repair connectivity check before marking as resolved.",
        "file": "cognitive/healing_coordinator.py",
        "error": "Healing reports success but connection errors continue immediately after",
    },
    {
        "id": "HARDEN-018",
        "type": "fix",
        "desc": "Fix sandbox_repair_engine.py — _cleanup_sandbox can fail silently if the temp directory is locked by another process on Windows. Add retry with delay for cleanup.",
        "file": "cognitive/sandbox_repair_engine.py",
        "error": "PermissionError: [WinError 32] file in use during sandbox cleanup",
    },
    # --- Frontend Integration ---
    {
        "id": "HARDEN-019",
        "type": "analyze",
        "desc": "Analyze the CodingAgentTab.jsx component for missing error boundaries, loading states, and edge cases. Suggest improvements for when the backend is offline or returns unexpected data.",
        "file": "frontend/src/components/CodingAgentTab.jsx",
        "error": "Frontend may crash if API returns unexpected shapes",
    },
    {
        "id": "HARDEN-020",
        "type": "analyze",
        "desc": "Analyze the full coding pipeline flow end-to-end: Layer 6 code generation → Layer 7 cross-verification → Layer 8 deploy gate → desktop backup. Identify any remaining gaps or race conditions.",
        "file": "core/coding_pipeline.py",
        "error": "End-to-end pipeline integrity check needed",
    },
]


def dispatch_all():
    """Dispatch all 20 hardening tasks through the CodingAgentPool."""
    from cognitive.coding_agents import get_coding_agent_pool, CodingTask
    from cognitive.event_bus import publish_async

    pool = get_coding_agent_pool()
    logger.info("=" * 60)
    logger.info("  GRACE HARDENING — 20 Tasks for Kimi & Opus")
    logger.info(f"  Max concurrent: {pool.MAX_CONCURRENT_JOBS}")
    logger.info(f"  Agents: {list(pool.agents.keys())}")
    logger.info("=" * 60)

    # Emit start event for live feed
    publish_async("coding_agent.hardening.task", {
        "phase": "start",
        "total_tasks": len(HARDENING_TASKS),
        "max_concurrent": pool.MAX_CONCURRENT_JOBS,
    }, source="hardening")

    results = []
    threads = []
    completed = {"count": 0}
    lock = threading.Lock()

    def run_task(task_def):
        task = CodingTask(
            id=task_def["id"],
            task_type=task_def["type"],
            file_path=task_def["file"],
            description=task_def["desc"],
            error=task_def["error"],
            context={"source": "hardening", "priority": "high"},
        )

        logger.info(f"[{task_def['id']}] Dispatching: {task_def['desc'][:80]}...")

        # Emit per-task event
        publish_async("coding_agent.hardening.task", {
            "phase": "dispatching",
            "task_id": task_def["id"],
            "file": task_def["file"],
            "type": task_def["type"],
        }, source="hardening")

        # Dispatch to both agents for consensus
        task_results = pool.dispatch_parallel(task, agents=["kimi", "opus"])

        with lock:
            completed["count"] += 1
            for r in task_results:
                results.append(r)

        best = max(task_results, key=lambda r: r.confidence) if task_results else None
        status = best.status if best else "failed"
        confidence = best.confidence if best else 0

        logger.info(
            f"[{task_def['id']}] Done — {status} "
            f"(confidence={confidence:.0%}, "
            f"agents={[r.agent for r in task_results]}) "
            f"[{completed['count']}/{len(HARDENING_TASKS)}]"
        )

        # Emit completion event
        publish_async("coding_agent.hardening.task", {
            "phase": "completed",
            "task_id": task_def["id"],
            "status": status,
            "confidence": confidence,
            "agents": [r.agent for r in task_results],
            "completed": completed["count"],
            "total": len(HARDENING_TASKS),
        }, source="hardening")

    # Dispatch in batches respecting the 5-job limit
    # The semaphore in CodingAgentPool handles the actual limiting,
    # but we batch threads to avoid creating 20 threads at once
    BATCH_SIZE = 5
    for batch_start in range(0, len(HARDENING_TASKS), BATCH_SIZE):
        batch = HARDENING_TASKS[batch_start:batch_start + BATCH_SIZE]
        batch_threads = []

        logger.info(f"\n--- Batch {batch_start // BATCH_SIZE + 1} "
                     f"(tasks {batch_start + 1}-{batch_start + len(batch)}) ---")

        for task_def in batch:
            t = threading.Thread(
                target=run_task,
                args=(task_def,),
                name=f"harden-{task_def['id']}",
                daemon=True,
            )
            batch_threads.append(t)
            threads.append(t)
            t.start()

        # Wait for this batch to complete before starting next
        for t in batch_threads:
            t.join(timeout=180)

    # Summary
    completed_results = [r for r in results if r.status == "completed"]
    failed_results = [r for r in results if r.status == "failed"]
    total_confidence = sum(r.confidence for r in results) / len(results) if results else 0

    logger.info("\n" + "=" * 60)
    logger.info("  HARDENING COMPLETE")
    logger.info(f"  Total results:  {len(results)} (from {len(HARDENING_TASKS)} tasks × 2 agents)")
    logger.info(f"  Completed:      {len(completed_results)}")
    logger.info(f"  Failed:         {len(failed_results)}")
    logger.info(f"  Avg confidence: {total_confidence:.0%}")
    logger.info("=" * 60)

    # Emit final summary
    publish_async("coding_agent.hardening.task", {
        "phase": "summary",
        "total_tasks": len(HARDENING_TASKS),
        "total_results": len(results),
        "completed": len(completed_results),
        "failed": len(failed_results),
        "avg_confidence": round(total_confidence, 3),
    }, source="hardening")

    return results


if __name__ == "__main__":
    dispatch_all()
