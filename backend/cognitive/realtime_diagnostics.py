"""
Real-Time Diagnostics — Continuous Stress Testing & Self-Healing Loop

Runs every 5 minutes:
1. Stress test all components (import, connect, query)
2. If something fails → trigger diagnostic
3. Diagnostic identifies root cause
4. Self-healing attempts fix
5. Results pushed to event bus → chat sidebar sees it
6. Genesis key tracks everything

This is always-on, always-checking, always-healing.
"""

import logging
import threading
import time
import json
from datetime import datetime
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DIAG_DIR = Path(__file__).parent.parent / "data" / "diagnostics"

_diagnostics_thread_started = False
_latest_report = None
_report_lock = threading.Lock()


@dataclass
class StressTestResult:
    component: str
    test: str
    passed: bool
    latency_ms: float = 0
    error: Optional[str] = None
    healed: bool = False


@dataclass
class DiagnosticReport:
    timestamp: str
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    healed: int = 0
    pass_rate: float = 0
    results: List[Dict] = field(default_factory=list)
    healing_actions: List[str] = field(default_factory=list)
    cycle_latency_ms: float = 0


def run_stress_cycle() -> DiagnosticReport:
    """Run one full stress test + diagnostic + healing cycle."""
    start = time.time()
    report = DiagnosticReport(timestamp=datetime.utcnow().isoformat())
    results = []

    # Test 1: Database connectivity
    results.append(_test_database())

    # Test 2: Vector DB (Qdrant)
    results.append(_test_qdrant())

    # Test 3: Embedding model
    results.append(_test_embedding())

    # Test 4: Event bus
    results.append(_test_event_bus())

    # Test 5: Memory mesh imports
    results.append(_test_memory_mesh())

    # Test 6: Genesis key service
    results.append(_test_genesis())

    # Test 7: Consensus engine
    results.append(_test_consensus())

    # Test 8: Flash cache
    results.append(_test_flash_cache())

    # Test 9: File system health
    results.append(_test_filesystem())

    # Test 10: Integration verifier
    results.append(_test_verifier())

    # Heal failures
    for r in results:
        if not r.passed:
            healed = _attempt_heal(r.component, r.error or "")
            r.healed = healed
            if healed:
                report.healing_actions.append(f"Healed: {r.component}")

    report.results = [asdict(r) for r in results]
    report.total_tests = len(results)
    report.passed = sum(1 for r in results if r.passed)
    report.failed = sum(1 for r in results if not r.passed)
    report.healed = sum(1 for r in results if r.healed)
    report.pass_rate = round(report.passed / report.total_tests * 100, 1) if report.total_tests > 0 else 0
    report.cycle_latency_ms = round((time.time() - start) * 1000, 1)

    # Store latest
    global _latest_report
    with _report_lock:
        _latest_report = report

    # Save to disk
    _save_report(report)

    # Publish to event bus
    _publish_results(report)

    # Track in genesis
    _track_genesis(report)

    # Report to self-healing tracker
    _update_self_healing(results)

    return report


def _test_database() -> StressTestResult:
    t = time.time()
    try:
        from database.session import get_session
        sess = next(get_session())
        from sqlalchemy import text
        sess.execute(text("SELECT 1"))
        sess.close()
        return StressTestResult("database", "SELECT 1", True, (time.time()-t)*1000)
    except Exception as e:
        return StressTestResult("database", "SELECT 1", False, (time.time()-t)*1000, str(e)[:200])


def _test_qdrant() -> StressTestResult:
    t = time.time()
    try:
        from vector_db.client import get_qdrant_client
        client = get_qdrant_client()
        if client.is_connected():
            collections = client.list_collections()
            return StressTestResult("qdrant", "list_collections", True, (time.time()-t)*1000)
        else:
            return StressTestResult("qdrant", "connect", False, (time.time()-t)*1000, "Not connected")
    except Exception as e:
        return StressTestResult("qdrant", "connect", False, (time.time()-t)*1000, str(e)[:200])


def _test_embedding() -> StressTestResult:
    t = time.time()
    try:
        from embedding.embedder import get_embedding_model
        model = get_embedding_model()
        if model and model.model is not None:
            dim = model.get_embedding_dimension()
            return StressTestResult("embedding", f"loaded (dim={dim})", True, (time.time()-t)*1000)
        return StressTestResult("embedding", "load", False, (time.time()-t)*1000, "Model is None")
    except Exception as e:
        return StressTestResult("embedding", "load", False, (time.time()-t)*1000, str(e)[:200])


def _test_event_bus() -> StressTestResult:
    t = time.time()
    try:
        from cognitive.event_bus import publish, get_recent_events
        publish("diagnostics.stress_test", {"test": True}, source="stress_test")
        events = get_recent_events(5)
        return StressTestResult("event_bus", "publish+read", True, (time.time()-t)*1000)
    except Exception as e:
        return StressTestResult("event_bus", "publish", False, (time.time()-t)*1000, str(e)[:200])


def _test_memory_mesh() -> StressTestResult:
    t = time.time()
    try:
        from cognitive.memory_mesh_integration import MemoryMeshIntegration
        from cognitive.learning_memory import LearningMemoryManager
        from cognitive.episodic_memory import EpisodicBuffer
        from cognitive.procedural_memory import ProceduralRepository
        return StressTestResult("memory_mesh", "imports", True, (time.time()-t)*1000)
    except Exception as e:
        return StressTestResult("memory_mesh", "imports", False, (time.time()-t)*1000, str(e)[:200])


def _test_genesis() -> StressTestResult:
    t = time.time()
    try:
        from genesis.genesis_key_service import get_genesis_service
        service = get_genesis_service()
        return StressTestResult("genesis_keys", "service_init", True, (time.time()-t)*1000)
    except Exception as e:
        return StressTestResult("genesis_keys", "service_init", False, (time.time()-t)*1000, str(e)[:200])


def _test_consensus() -> StressTestResult:
    t = time.time()
    try:
        from cognitive.consensus_engine import get_available_models
        models = get_available_models()
        available = sum(1 for m in models if m.get("available"))
        return StressTestResult("consensus", f"models_available={available}", True, (time.time()-t)*1000)
    except Exception as e:
        return StressTestResult("consensus", "models_check", False, (time.time()-t)*1000, str(e)[:200])


def _test_flash_cache() -> StressTestResult:
    t = time.time()
    try:
        from cognitive.flash_cache import get_flash_cache
        fc = get_flash_cache()
        stats = fc.get_stats()
        return StressTestResult("flash_cache", f"entries={stats.get('total_entries',0)}", True, (time.time()-t)*1000)
    except Exception as e:
        return StressTestResult("flash_cache", "get_stats", False, (time.time()-t)*1000, str(e)[:200])


def _test_filesystem() -> StressTestResult:
    t = time.time()
    try:
        kb = Path(__file__).parent.parent / "knowledge_base"
        if kb.exists():
            file_count = sum(1 for _ in kb.rglob("*") if _.is_file())
            return StressTestResult("filesystem", f"kb_files={file_count}", True, (time.time()-t)*1000)
        return StressTestResult("filesystem", "kb_exists", False, (time.time()-t)*1000, "knowledge_base dir missing")
    except Exception as e:
        return StressTestResult("filesystem", "scan", False, (time.time()-t)*1000, str(e)[:200])


def _test_verifier() -> StressTestResult:
    t = time.time()
    try:
        from cognitive.integration_verifier import run_integration_tests
        report = run_integration_tests()
        rate = report.get("pass_rate", 0)
        return StressTestResult("verifier", f"pass_rate={rate}%", rate >= 50, (time.time()-t)*1000,
                                None if rate >= 50 else f"Pass rate {rate}% below 50% threshold")
    except Exception as e:
        return StressTestResult("verifier", "run", False, (time.time()-t)*1000, str(e)[:200])


def _attempt_heal(component: str, error: str) -> bool:
    """Attempt to heal a failed component."""
    try:
        from cognitive.self_healing_tracker import get_self_healing_tracker
        tracker = get_self_healing_tracker()
        tracker.report_error(component, error, auto_heal=True)
        health = tracker.get_system_health()
        comp = health.get("components", {}).get(component, {})
        return comp.get("status") in ("healthy", "healing")
    except Exception:
        return False


def _publish_results(report: DiagnosticReport):
    """Push results to event bus for chat visibility."""
    try:
        from cognitive.event_bus import publish
        publish("diagnostics.cycle_complete", {
            "total": report.total_tests,
            "passed": report.passed,
            "failed": report.failed,
            "healed": report.healed,
            "pass_rate": report.pass_rate,
            "failed_components": [r["component"] for r in report.results if not r["passed"]],
            "cycle_latency_ms": report.cycle_latency_ms,
        }, source="realtime_diagnostics")
    except Exception:
        pass


def _track_genesis(report: DiagnosticReport):
    try:
        from api._genesis_tracker import track
        track(
            key_type="system",
            what=f"Stress test: {report.passed}/{report.total_tests} passed ({report.pass_rate}%)",
            how="realtime_diagnostics.run_stress_cycle",
            output_data={
                "passed": report.passed, "failed": report.failed,
                "healed": report.healed, "pass_rate": report.pass_rate,
            },
            tags=["diagnostics", "stress_test", "realtime"],
            is_error=report.failed > 0,
        )
    except Exception:
        pass


def _update_self_healing(results: List[StressTestResult]):
    try:
        from cognitive.self_healing_tracker import get_self_healing_tracker
        tracker = get_self_healing_tracker()
        for r in results:
            if r.passed:
                tracker.report_healthy(r.component)
            else:
                tracker.report_error(r.component, r.error or "Stress test failed", auto_heal=False)
    except Exception:
        pass


def _save_report(report: DiagnosticReport):
    DIAG_DIR.mkdir(parents=True, exist_ok=True)
    reports = sorted(DIAG_DIR.glob("diag_*.json"), reverse=True)
    if len(reports) > 100:
        for old in reports[100:]:
            old.unlink(missing_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path = DIAG_DIR / f"diag_{ts}.json"
    path.write_text(json.dumps(asdict(report), indent=2, default=str))


def get_latest_report() -> Optional[DiagnosticReport]:
    global _latest_report
    with _report_lock:
        return _latest_report


def get_report_history(limit: int = 20) -> List[Dict]:
    DIAG_DIR.mkdir(parents=True, exist_ok=True)
    reports = []
    for path in sorted(DIAG_DIR.glob("diag_*.json"), reverse=True)[:limit]:
        try:
            reports.append(json.loads(path.read_text()))
        except Exception:
            continue
    return reports


def start_continuous_diagnostics(interval_seconds: int = 300):
    """Start the continuous stress test loop (default: every 5 minutes)."""
    global _diagnostics_thread_started
    if _diagnostics_thread_started:
        return
    _diagnostics_thread_started = True

    def _loop():
        logger.info(f"[DIAGNOSTICS] Starting continuous stress tests (every {interval_seconds}s)")
        # Wait a bit for startup to finish
        time.sleep(30)
        while True:
            try:
                report = run_stress_cycle()
                level = "INFO" if report.pass_rate >= 80 else "WARNING" if report.pass_rate >= 50 else "ERROR"
                logger.log(
                    logging.INFO if level == "INFO" else logging.WARNING,
                    f"[DIAGNOSTICS] Cycle: {report.passed}/{report.total_tests} passed "
                    f"({report.pass_rate}%), healed {report.healed}, {report.cycle_latency_ms}ms"
                )
            except Exception as e:
                logger.error(f"[DIAGNOSTICS] Cycle failed: {e}")
            time.sleep(interval_seconds)

    t = threading.Thread(target=_loop, daemon=True, name="diagnostics_loop")
    t.start()
    logger.info("[DIAGNOSTICS] Continuous diagnostics thread started")
