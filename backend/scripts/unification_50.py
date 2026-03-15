"""
Grace Unification Run — 50 tasks for full system hardening + healing.
Covers: DB, imports, startup, APIs, healing, pipeline, Spindle, frontend, tests, governance.
All output logged to logs/unification_run.log + KPIs tracked.

Run:  python -m scripts.unification_50
"""
import sys, os, time, logging, json, threading
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Log to file AND console
log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs', 'unification_run.log')
os.makedirs(os.path.dirname(log_path), exist_ok=True)

file_handler = logging.FileHandler(log_path, encoding='utf-8', mode='w')
file_handler.setFormatter(logging.Formatter('[%(asctime)s][%(levelname)s] %(message)s', datefmt='%H:%M:%S'))
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter('[%(asctime)s][%(levelname)s] %(message)s', datefmt='%H:%M:%S'))

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

log = logging.getLogger('unification')

TASKS = [
    # === DATABASE & MIGRATIONS (1-8) ===
    {"id":"UNI-001","type":"fix","file":"database/migrations/add_scraping_tables.py","desc":"Fix import: change 'from database.connection import Base' to 'from database.base import BaseModel as Base'","error":"ImportError: cannot import name 'Base'"},
    {"id":"UNI-002","type":"fix","file":"database/migrate_add_telemetry.py","desc":"Fix DatabaseConnection.initialize() missing config arg. Use session_scope() instead","error":"TypeError: initialize() missing required argument"},
    {"id":"UNI-003","type":"fix","file":"force_reingest.py","desc":"Fix import: change 'from database.connection import get_session' to 'from database.session import session_scope'","error":"ImportError: cannot import name 'get_session'"},
    {"id":"UNI-004","type":"fix","file":"database/migrations/add_query_intelligence_tables.py","desc":"Replace PostgreSQL SERIAL PRIMARY KEY with SQLAlchemy Column(Integer, primary_key=True, autoincrement=True)","error":"sqlite3.OperationalError: near SERIAL"},
    {"id":"UNI-005","type":"fix","file":"models/database_models.py","desc":"Add __table_args__ = {'extend_existing': True} to all model classes to prevent Table already defined errors from circular imports","error":"InvalidRequestError: Table 'users' is already defined"},
    {"id":"UNI-006","type":"fix","file":"database/session.py","desc":"Add defensive check: if SessionLocal is None when session_scope is called, auto-initialize with default config","error":"Database not initialized errors on every API call"},
    {"id":"UNI-007","type":"fix","file":"database/connection.py","desc":"Ensure initialize() is idempotent - calling it twice should not raise. Add a _initialized flag check","error":"Double-init causes connection pool conflicts"},
    {"id":"UNI-008","type":"fix","file":"database/base.py","desc":"Verify BaseModel has __table_args__ with extend_existing=True to prevent metadata conflicts across imports","error":"Circular import table redefinition"},
    # === STARTUP & INIT (9-14) ===
    {"id":"UNI-009","type":"fix","file":"app.py","desc":"Move DatabaseConnection.initialize() to run BEFORE any router imports. Currently middleware tries Genesis keys before DB is ready","error":"Failed to create Genesis Key: Database not initialized"},
    {"id":"UNI-010","type":"fix","file":"app.py","desc":"Add WindowsSelectorEventLoopPolicy for Windows at the top of app.py, before any async code runs","error":"ConnectionResetError: [WinError 10054]"},
    {"id":"UNI-011","type":"fix","file":"setup/initializer.py","desc":"Add timeout and graceful skip for Ollama/Qdrant checks during boot. Don't block startup if Docker services are down","error":"Boot hangs waiting for Docker services"},
    {"id":"UNI-012","type":"fix","file":"genesis/middleware.py","desc":"Rate-limit Genesis key creation errors to 1 warning per 60s instead of logging on every request","error":"Genesis middleware ERROR spam fills logs"},
    {"id":"UNI-013","type":"fix","file":"api/genesis_daily_api.py","desc":"Check if session_scope is a Mock before calling it. Add isinstance check to prevent test mock leaking to prod","error":"Exception: no db - session_scope is Mock"},
    {"id":"UNI-014","type":"fix","file":"startup_preflight.py","desc":"Add pre-flight checks for DB connectivity, required env vars, and Python version before starting the main app","error":"Startup fails silently without clear error message"},
    # === IMPORT & MODULE FIXES (15-20) ===
    {"id":"UNI-015","type":"fix","file":"core/services/govern_service.py","desc":"Fix broken GovernanceEngine import path. The import fails silently - fix the path so governance actually loads","error":"Silent ImportError for GovernanceEngine"},
    {"id":"UNI-016","type":"fix","file":"scraping/service.py","desc":"Add try/except for trafilatura import with BeautifulSoup fallback since trafilatura is not installed","error":"ImportError: No module named 'trafilatura'"},
    {"id":"UNI-017","type":"fix","file":"vector_db/client.py","desc":"Add max retry count (3) for Qdrant connection. After 3 fails, disable vector search gracefully","error":"Infinite Qdrant retry loop blocks operations"},
    {"id":"UNI-018","type":"fix","file":"cognitive/coding_agents.py","desc":"Validate API keys in _init_agents. Skip agents without valid keys instead of creating broken agent objects","error":"401 Unauthorized on agents without keys"},
    {"id":"UNI-019","type":"fix","file":"llm_orchestrator/factory.py","desc":"Add fallback chain: if primary LLM unavailable, try secondary, then local Ollama, then return error gracefully","error":"Single LLM failure crashes the whole request"},
    {"id":"UNI-020","type":"fix","file":"cognitive/event_bus.py","desc":"Add max subscriber limit and auto-cleanup of dead subscribers to prevent memory leaks in long-running processes","error":"Event bus accumulates stale subscribers"},
    # === SPINDLE & OODA (21-26) ===
    {"id":"UNI-021","type":"fix","file":"cognitive/spindle_event_store.py","desc":"Increase write queue from 50k to 100k and reduce flush sleep from 0.5s to 0.1s for faster drain","error":"Write queue full spam under load"},
    {"id":"UNI-022","type":"fix","file":"diagnostic_machine/action_router.py","desc":"Verify OODA phase reset works correctly between diagnostic cycles. Ensure OODAPhase import exists","error":"Cannot decide in phase OODAPhase.COMPLETED"},
    {"id":"UNI-023","type":"fix","file":"cognitive/ooda.py","desc":"Add a safe_reset method that catches all exceptions during reset and logs them instead of crashing","error":"OODA reset failures cascade to diagnostic engine"},
    {"id":"UNI-024","type":"fix","file":"spindle_daemon.py","desc":"Add heartbeat check - if no events processed in 60s, log a warning and attempt reconnection","error":"Spindle daemon silently stops processing"},
    {"id":"UNI-025","type":"fix","file":"cognitive/deterministic_validator.py","desc":"Add timeout to Z3 solver calls (5s max). Long-running Z3 checks block the Spindle daemon","error":"Z3 sat check hangs on complex constraints"},
    {"id":"UNI-026","type":"fix","file":"cognitive/spindle_event_store.py","desc":"In _sync_sequence_from_db, handle the case where the DB returns None (empty table) gracefully","error":"Sequence sync fails on fresh database"},
    # === SELF-HEALING (27-32) ===
    {"id":"UNI-027","type":"fix","file":"cognitive/healing_coordinator.py","desc":"Add post-repair verification: after network_repair, check connectivity before marking resolved","error":"Healing reports success but errors continue"},
    {"id":"UNI-028","type":"fix","file":"cognitive/healing_coordinator.py","desc":"Add circuit breaker: if same component fails healing 3 times in 5 minutes, stop retrying and alert","error":"Healing loop retries forever on unfixable issues"},
    {"id":"UNI-029","type":"fix","file":"cognitive/sandbox_repair_engine.py","desc":"Add retry with 1s delay for _cleanup_sandbox on Windows when temp files are locked","error":"PermissionError: [WinError 32] file in use"},
    {"id":"UNI-030","type":"fix","file":"self_healing/playbooks/tcp_connection_reset.yaml","desc":"Add max_retries: 3 and backoff_seconds: 5 to the tcp_connection_reset playbook","error":"TCP healing retries infinitely"},
    {"id":"UNI-031","type":"fix","file":"cognitive/healing_coordinator.py","desc":"Log healing outcomes to KPI tracker: record_kpi('self_healing', action_type, passed=resolved)","error":"Healing results not tracked in KPIs"},
    {"id":"UNI-032","type":"fix","file":"diagnostic_machine/diagnostic_engine.py","desc":"Add rate limiting to diagnostic cycles: max 1 cycle per 10 seconds to prevent CPU thrashing","error":"Diagnostic engine runs cycles too frequently"},
    # === CODING PIPELINE (33-38) ===
    {"id":"UNI-033","type":"fix","file":"core/coding_pipeline.py","desc":"Add try/except around Path.home() in deploy gate with os.path.expanduser fallback","error":"OSError on Path.home() in restricted environments"},
    {"id":"UNI-034","type":"fix","file":"core/coding_pipeline.py","desc":"Add timeout to _consensus calls (30s max). Slow LLM responses block the whole pipeline","error":"Pipeline hangs waiting for consensus"},
    {"id":"UNI-035","type":"fix","file":"core/coding_pipeline.py","desc":"Log pipeline progress events to Spindle event store, not just in-memory event bus","error":"Pipeline progress lost on process restart"},
    {"id":"UNI-036","type":"fix","file":"core/deterministic_first_loop.py","desc":"Handle ImportError for missing modules gracefully - return partial results instead of crashing","error":"Phase 0 fails if any dependency missing"},
    {"id":"UNI-037","type":"fix","file":"core/deterministic_bridge.py","desc":"Add AST parse error recovery: if file has syntax error, skip it and continue scanning","error":"One bad file crashes entire deterministic scan"},
    {"id":"UNI-038","type":"fix","file":"core/workspace_bridge.py","desc":"Add file size limit check (10MB max) before writing to prevent memory issues with large generated files","error":"Large generated files consume all memory"},
    # === APIS & FRONTEND (39-44) ===
    {"id":"UNI-039","type":"fix","file":"api/brain_api_v2.py","desc":"Add request timeout of 30s to all external LLM API calls. Currently no timeout causes hanging requests","error":"External API calls hang indefinitely"},
    {"id":"UNI-040","type":"fix","file":"api/health.py","desc":"Add coding_agent pool status to the health endpoint: active_jobs, max_jobs, recent success rate","error":"Health endpoint missing coding agent status"},
    {"id":"UNI-041","type":"fix","file":"api/kpi_api.py","desc":"Include coding_agent KPIs in the dashboard response alongside self_healing and diagnostic KPIs","error":"KPI dashboard missing coding agent metrics"},
    {"id":"UNI-042","type":"fix","file":"api/coding_agent_gov_api.py","desc":"Add rate limiting: max 10 hardening runs per hour to prevent accidental spam","error":"No rate limit on hardening task dispatch"},
    {"id":"UNI-043","type":"fix","file":"frontend/src/components/CodingAgentTab.jsx","desc":"Add loading spinner during initial fetch, error banner when backend offline, null-safe item rendering","error":"Component shows blank state without feedback"},
    {"id":"UNI-044","type":"fix","file":"api/autonomous_log_api.py","desc":"Add coding_agent.hardening.task to topic formatters so hardening events show properly in live feed","error":"Hardening events show as generic in live feed"},
    # === GOVERNANCE & TRUST (45-48) ===
    {"id":"UNI-045","type":"fix","file":"core/governance_engine.py","desc":"Add auto-decay for KPI scores: scores older than 24h get weighted 50% less for freshness","error":"Stale KPIs give misleading trust picture"},
    {"id":"UNI-046","type":"fix","file":"core/safety.py","desc":"Add code signing: hash every generated file with SHA-256 and store in Genesis key for tamper detection","error":"Generated code has no integrity verification"},
    {"id":"UNI-047","type":"fix","file":"genesis/genesis_key_service.py","desc":"Add batch key creation method for pipeline runs - creating keys one at a time is too slow","error":"Genesis key creation bottleneck in pipeline"},
    {"id":"UNI-048","type":"fix","file":"core/trust_score.py","desc":"Include coding agent success rate in the global trust score calculation","error":"Trust score ignores coding agent performance"},
    # === ANALYSIS & INTEGRATION (49-50) ===
    {"id":"UNI-049","type":"analyze","file":"core/coding_pipeline.py","desc":"Analyze the full 9-phase pipeline for race conditions, missing error handling, and verify Layer 6-7-8 integration is complete","error":"End-to-end pipeline integrity audit"},
    {"id":"UNI-050","type":"analyze","file":"app.py","desc":"Analyze the full startup sequence: DB init, router registration, middleware, Spindle, healing. Identify any ordering issues","error":"Startup sequence audit for correct initialization order"},
]

def dispatch_all():
    from cognitive.coding_agents import get_coding_agent_pool, CodingTask
    from cognitive.event_bus import publish_async

    pool = get_coding_agent_pool()

    # Start Spindle event store flush
    try:
        from cognitive.spindle_event_store import get_event_store
        store = get_event_store()
        store.start_background_flush()
    except Exception:
        pass

    log.info("=" * 65)
    log.info("  GRACE UNIFICATION RUN - 50 Tasks")
    log.info(f"  Agents: {list(pool.agents.keys())}")
    log.info(f"  Max concurrent: {pool.MAX_CONCURRENT_JOBS}")
    log.info(f"  Log file: {log_path}")
    log.info("=" * 65)

    publish_async("coding_agent.hardening.task", {
        "phase": "start", "total_tasks": len(TASKS), "run": "unification_50",
    }, source="unification")

    results_log = []  # Persistent log of all results
    completed_count = {"n": 0}
    lock = threading.Lock()

    def run_task(task_def):
        task = CodingTask(
            id=task_def["id"], task_type=task_def["type"],
            file_path=task_def["file"], description=task_def["desc"],
            error=task_def["error"], context={"source": "unification"},
        )
        log.info(f'[{task_def["id"]}] START | {task_def["file"]:50s} | {task_def["desc"][:60]}')

        publish_async("coding_agent.hardening.task", {
            "phase": "dispatching", "task_id": task_def["id"],
            "file": task_def["file"], "type": task_def["type"],
        }, source="unification")

        task_results = pool.dispatch_parallel(task, agents=["kimi", "opus"])

        with lock:
            completed_count["n"] += 1
            n = completed_count["n"]

        best = max(task_results, key=lambda r: r.confidence) if task_results else None
        status = best.status if best else "failed"
        conf = best.confidence if best else 0
        has_patch = bool(best and best.patch)

        entry = {
            "task_id": task_def["id"],
            "file": task_def["file"],
            "status": status,
            "confidence": conf,
            "has_patch": has_patch,
            "patch_len": len(best.patch) if best and best.patch else 0,
            "agents": [{"agent": r.agent, "status": r.status, "confidence": r.confidence} for r in task_results],
        }
        results_log.append(entry)

        icon = "PASS" if status == "completed" and conf >= 0.6 else "WARN" if status == "completed" else "FAIL"
        log.info(
            f'[{task_def["id"]}] {icon} | conf={conf:.0%} | patch={entry["patch_len"]:5d}ch | '
            f'agents=[{", ".join(r.agent + ":" + r.status for r in task_results)}] | [{n}/{len(TASKS)}]'
        )

        publish_async("coding_agent.hardening.task", {
            "phase": "completed", "task_id": task_def["id"],
            "status": status, "confidence": conf, "completed": n, "total": len(TASKS),
        }, source="unification")

    # Dispatch in batches of 5
    BATCH = 5
    for i in range(0, len(TASKS), BATCH):
        batch = TASKS[i:i + BATCH]
        log.info(f'\n--- Batch {i // BATCH + 1}/{(len(TASKS) + BATCH - 1) // BATCH} (tasks {i+1}-{i+len(batch)}) ---')

        threads = []
        for td in batch:
            t = threading.Thread(target=run_task, args=(td,), daemon=True, name=f'uni-{td["id"]}')
            threads.append(t)
            t.start()
        for t in threads:
            t.join(timeout=180)

    # Summary
    passed = [r for r in results_log if r["status"] == "completed" and r["confidence"] >= 0.6]
    warned = [r for r in results_log if r["status"] == "completed" and r["confidence"] < 0.6]
    failed = [r for r in results_log if r["status"] != "completed"]
    avg_conf = sum(r["confidence"] for r in results_log) / len(results_log) if results_log else 0
    total_patches = sum(r["patch_len"] for r in results_log)

    log.info("\n" + "=" * 65)
    log.info("  UNIFICATION COMPLETE")
    log.info(f"  Tasks:      {len(TASKS)}")
    log.info(f"  Passed:     {len(passed)} (confidence >= 60%)")
    log.info(f"  Warned:     {len(warned)} (completed but low confidence)")
    log.info(f"  Failed:     {len(failed)}")
    log.info(f"  Avg conf:   {avg_conf:.0%}")
    log.info(f"  Total code: {total_patches:,} chars of patches generated")
    log.info("=" * 65)

    # Save results JSON
    results_path = os.path.join(os.path.dirname(log_path), 'unification_results.json')
    with open(results_path, 'w', encoding='utf-8') as f:
        json.dump({
            "run": "unification_50",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "summary": {
                "total": len(TASKS), "passed": len(passed),
                "warned": len(warned), "failed": len(failed),
                "avg_confidence": round(avg_conf, 3),
                "total_patch_chars": total_patches,
            },
            "results": results_log,
        }, f, indent=2)
    log.info(f"Results saved: {results_path}")

    publish_async("coding_agent.hardening.task", {
        "phase": "summary", "run": "unification_50",
        "total": len(TASKS), "passed": len(passed),
        "failed": len(failed), "avg_confidence": round(avg_conf, 3),
    }, source="unification")

    # Print KPI summary
    try:
        from core.governance_engine import get_kpi_scores
        kpis = get_kpi_scores("coding_agent")
        log.info("\n=== CODING AGENT KPIs ===")
        for key, data in kpis.items():
            log.info(f"  {key}: score={data['score']}% ({data['passed']}/{data['total_checks']})")
    except Exception as e:
        log.info(f"KPI fetch: {e}")

    # Stop flush
    try:
        store.stop_background_flush()
    except Exception:
        pass

    return results_log


if __name__ == "__main__":
    dispatch_all()
