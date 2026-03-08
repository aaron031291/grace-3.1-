"""
Runtime Triggers API — watches for system anomalies and pipes them
into the self-healing loop automatically.

Trigger categories:
  RESOURCE   — CPU > 90%, RAM > 85%, disk > 95%
  SERVICE    — Ollama/Qdrant/Kimi/Opus unreachable
  CODE       — import errors, dependency mismatches, missing modules
  NETWORK    — port conflicts, connection refused, timeout
  LOGICAL    — test failures, invariant violations, consensus disagreement
  BUILD      — deterministic verify_built failed (required checks)
  DEGRADATION— latency spikes, error-rate increase, throughput drop

Each trigger can:
  1. Be detected by the scan endpoint
  2. Auto-fire the self-healing pipeline
  3. Be logged with full context for the Dev tab to display
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
import os
import sys
import threading
import time
import importlib
import socket

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/triggers", tags=["Runtime Triggers"])

_trigger_log: list = []
_trigger_lock = threading.Lock()
_MAX_LOG = 200


class TriggerEntry:
    def __init__(self, category: str, name: str, severity: str,
                 detail: str, value: Any = None, healed: bool = False):
        self.category = category
        self.name = name
        self.severity = severity
        self.detail = detail
        self.value = value
        self.healed = healed
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self):
        return {
            "category": self.category,
            "name": self.name,
            "severity": self.severity,
            "detail": self.detail,
            "value": self.value,
            "healed": self.healed,
            "timestamp": self.timestamp,
        }


def _log_trigger(t: TriggerEntry):
    with _trigger_lock:
        _trigger_log.append(t.to_dict())
        if len(_trigger_log) > _MAX_LOG:
            _trigger_log.pop(0)


# ── Scanners ─────────────────────────────────────────────────────────

def _scan_resources() -> List[dict]:
    """CPU, RAM, disk."""
    triggers = []
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        if cpu > 90:
            triggers.append(TriggerEntry("RESOURCE", "high_cpu", "critical",
                                         f"CPU at {cpu}%", cpu))
        elif cpu > 75:
            triggers.append(TriggerEntry("RESOURCE", "elevated_cpu", "warning",
                                         f"CPU at {cpu}%", cpu))
        if mem.percent > 85:
            triggers.append(TriggerEntry("RESOURCE", "high_ram", "critical",
                                         f"RAM at {mem.percent}%", mem.percent))
        elif mem.percent > 70:
            triggers.append(TriggerEntry("RESOURCE", "elevated_ram", "warning",
                                         f"RAM at {mem.percent}%", mem.percent))
        if disk.percent > 95:
            triggers.append(TriggerEntry("RESOURCE", "disk_full", "critical",
                                         f"Disk at {disk.percent}%", disk.percent))
    except ImportError:
        triggers.append(TriggerEntry("RESOURCE", "psutil_missing", "info",
                                     "psutil not installed — resource monitoring limited"))
    return triggers


def _scan_services() -> List[dict]:
    """Ollama, Qdrant, Kimi, Opus, Database."""
    triggers = []
    try:
        from settings import settings
    except Exception:
        return triggers

    # Ollama
    try:
        import urllib.request
        url = (settings.OLLAMA_URL or "http://localhost:11434").rstrip("/") + "/api/tags"
        req = urllib.request.Request(url, method="GET")
        urllib.request.urlopen(req, timeout=3)
    except Exception as e:
        triggers.append(TriggerEntry("SERVICE", "ollama_down", "critical",
                                     f"Ollama unreachable: {e}"))

    # Qdrant (cloud or local)
    try:
        cloud_url = getattr(settings, "QDRANT_URL", "")
        api_key = getattr(settings, "QDRANT_API_KEY", "")
        if cloud_url:
            from qdrant_client import QdrantClient as _QC
            _qc = _QC(url=cloud_url, api_key=api_key, timeout=5)
            _qc.get_collections()
        else:
            import urllib.request as ur
            ur.urlopen(f"http://{settings.QDRANT_HOST}:{settings.QDRANT_PORT}/collections", timeout=3)
    except Exception as e:
        triggers.append(TriggerEntry("SERVICE", "qdrant_down", "critical",
                                     f"Qdrant unreachable: {e}"))

    # Database
    try:
        from database.connection import DatabaseConnection
        if not DatabaseConnection.health_check():
            triggers.append(TriggerEntry("SERVICE", "db_unhealthy", "critical",
                                         "Database health check failed"))
    except Exception as e:
        triggers.append(TriggerEntry("SERVICE", "db_error", "critical", str(e)))

    # Kimi
    if settings.KIMI_API_KEY:
        try:
            import urllib.request as ur2
            req = ur2.Request(settings.KIMI_BASE_URL.rstrip("/") + "/models",
                              headers={"Authorization": f"Bearer {settings.KIMI_API_KEY}"})
            ur2.urlopen(req, timeout=5)
        except Exception:
            triggers.append(TriggerEntry("SERVICE", "kimi_unreachable", "warning",
                                         "Kimi API unreachable"))

    # Opus
    if settings.OPUS_API_KEY:
        try:
            import urllib.request as ur3
            req = ur3.Request("https://api.anthropic.com/v1/messages",
                              headers={"x-api-key": settings.OPUS_API_KEY,
                                       "anthropic-version": "2023-06-01"})
            ur3.urlopen(req, timeout=5)
        except Exception:
            triggers.append(TriggerEntry("SERVICE", "opus_unreachable", "warning",
                                         "Opus/Anthropic API unreachable"))

    return triggers


def _scan_code() -> List[dict]:
    """Import errors, missing dependencies."""
    triggers = []
    critical_modules = [
        "sqlalchemy", "fastapi", "pydantic", "uvicorn",
    ]
    for mod in critical_modules:
        try:
            importlib.import_module(mod)
        except ImportError as e:
            triggers.append(TriggerEntry("CODE", "missing_dependency", "critical",
                                         f"Cannot import {mod}: {e}", mod))

    backend_modules = [
        "database.connection", "database.session",
        "cognitive.consensus_engine",
        "llm_orchestrator.factory",
    ]
    for mod in backend_modules:
        try:
            importlib.import_module(mod)
        except Exception as e:
            triggers.append(TriggerEntry("CODE", "import_error", "warning",
                                         f"Backend module {mod}: {e}", mod))
    return triggers


def _scan_build() -> List[dict]:
    """Deterministic build verification — failed required checks become triggers."""
    triggers = []
    try:
        from core.build_verification import run_verify_built_checks
        manifest = run_verify_built_checks(skip_verify_script=True)
        for c in manifest.get("checks", []):
            if c.get("required") and c.get("passed") is False:
                triggers.append(TriggerEntry(
                    "BUILD",
                    f"build_{c.get('id', 'unknown')}",
                    "critical",
                    c.get("detail", "required check failed"),
                    value=c.get("id"),
                ))
        if manifest.get("summary", {}).get("required_failed", 0) > 0:
            triggers.append(TriggerEntry(
                "BUILD",
                "verify_built_required_failed",
                "critical",
                f"{manifest['summary']['required_failed']} required build check(s) failed",
                value=manifest["summary"]["required_failed"],
            ))
    except Exception as e:
        triggers.append(TriggerEntry("BUILD", "verify_built_error", "warning", str(e)[:200]))
    return triggers


def _scan_network() -> List[dict]:
    """Port conflicts."""
    triggers = []
    ports_to_check = [
        (8000, "Grace API"),
        (11434, "Ollama"),
        (6333, "Qdrant"),
    ]
    for port, name in ports_to_check:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(("127.0.0.1", port))
                if result != 0 and name != "Grace API":
                    triggers.append(TriggerEntry("NETWORK", "port_unreachable", "warning",
                                                 f"{name} port {port} not listening", port))
        except Exception:
            pass
    return triggers


def _scan_logical() -> List[dict]:
    """Test failures, integration gaps."""
    triggers = []
    try:
        from cognitive.test_framework import smoke_test
        result = smoke_test()
        if result.get("status") != "pass":
            failed = result.get("failed", 0)
            triggers.append(TriggerEntry("LOGICAL", "test_failures", "warning",
                                         f"Smoke test: {failed} failures",
                                         result.get("summary")))
    except Exception:
        pass

    try:
        from api.api_registry_api import _build_registry
        reg = _build_registry()
        broken = [r for r in reg.get("routes", []) if not r.get("healthy", True)]
        if broken:
            triggers.append(TriggerEntry("LOGICAL", "broken_apis", "warning",
                                         f"{len(broken)} broken API routes",
                                         [r.get("path") for r in broken[:10]]))
    except Exception:
        pass

    return triggers


# ── Healing bridge ───────────────────────────────────────────────────

def _auto_heal(triggers: List[dict]) -> dict:
    """Pipe critical triggers into self-healing."""
    healed = []
    critical = [t for t in triggers if t.get("severity") == "critical"]
    if not critical:
        return {"healed": 0, "actions": []}

    # Try diagnostic machine first
    try:
        from diagnostic_machine.diagnostic_engine import get_diagnostic_engine
        engine = get_diagnostic_engine()
        from diagnostic_machine.diagnostic_engine import TriggerSource
        cycle = engine.run_cycle(TriggerSource.SENSOR_FLAG)
        healed.append({
            "action": "diagnostic_cycle",
            "result": cycle.get("health_status", "unknown") if isinstance(cycle, dict) else "ran",
        })
    except Exception as e:
        logger.warning("Diagnostic healing failed: %s", e)

    # Service-specific healing — all paths through brain
    for t in critical:
        name = (t.get("name") or "").lower()
        try:
            from api.brain_api_v2 import call_brain
            if "db" in name:
                r = call_brain("system", "reset_db", {})
                healed.append({"action": "db_reconnect", "trigger": name, "ok": r.get("ok")})
            elif "ollama" in name:
                r = call_brain("system", "scan_heal", {})
                healed.append({"action": "ollama_scan_heal", "trigger": name, "ok": r.get("ok"),
                               "note": "Ollama may require manual restart"})
            elif "ram" in name or "cpu" in name:
                r = call_brain("system", "gc", {})
                healed.append({"action": "gc_collect", "trigger": name, "ok": r.get("ok")})
            else:
                r = call_brain("govern", "heal", {})
                healed.append({"action": "heal", "trigger": name, "ok": r.get("ok")})
        except Exception as e:
            healed.append({"action": "heal_error", "trigger": name, "error": str(e)})

    return {"healed": len(healed), "actions": healed}


# ── Endpoints ────────────────────────────────────────────────────────

@router.get("/scan")
async def scan_triggers():
    """Run a full trigger scan across all categories."""
    all_triggers = []
    categories = {
        "RESOURCE": _scan_resources,
        "SERVICE": _scan_services,
        "CODE": _scan_code,
        "NETWORK": _scan_network,
        "LOGICAL": _scan_logical,
        "BUILD": _scan_build,
    }
    for cat, scanner in categories.items():
        try:
            found = scanner()
            for t in found:
                entry = t if isinstance(t, dict) else t.to_dict()
                _log_trigger(t if isinstance(t, TriggerEntry) else
                             TriggerEntry(cat, entry.get("name", ""), entry.get("severity", "info"),
                                          entry.get("detail", "")))
                all_triggers.append(entry if isinstance(entry, dict) else entry)
        except Exception as e:
            logger.error("Trigger scan error in %s: %s", cat, e)

    return {
        "total": len(all_triggers),
        "critical": sum(1 for t in all_triggers if t.get("severity") == "critical"),
        "warning": sum(1 for t in all_triggers if t.get("severity") == "warning"),
        "triggers": all_triggers,
        "scanned_at": datetime.utcnow().isoformat(),
    }


@router.post("/scan-and-heal")
async def scan_and_heal():
    """Scan for triggers and auto-heal critical issues."""
    scan = await scan_triggers()
    heal_result = _auto_heal(scan["triggers"])
    return {
        "scan": scan,
        "healing": heal_result,
    }


@router.get("/log")
async def get_trigger_log(limit: int = 50):
    """Get recent trigger history."""
    with _trigger_lock:
        return {"log": list(reversed(_trigger_log[-limit:])), "total": len(_trigger_log)}


@router.post("/stress-heal")
async def stress_then_heal():
    """
    Run stress test, collect results, then auto-heal any issues found.
    This is the full pipeline: stress → diagnose → heal.
    """
    results = {"stress": None, "diagnostic": None, "triggers": None, "healing": None}

    # 1. Run logic tests as a stress indicator
    try:
        from cognitive.deep_test_engine import get_deep_test_engine
        engine = get_deep_test_engine()
        test_result = engine.run_logic_tests()
        results["stress"] = {
            "passed": test_result.get("passed", 0),
            "failed": test_result.get("failed", 0),
            "total": test_result.get("total", 0),
            "pass_rate": test_result.get("pass_rate", 0),
            "status": test_result.get("status", "unknown"),
        }
    except Exception as e:
        results["stress"] = {"error": str(e)}

    # 2. Run diagnostic
    try:
        from cognitive.autonomous_diagnostics import get_diagnostics
        diag = get_diagnostics()
        diag_result = diag.on_startup()
        results["diagnostic"] = diag_result
    except Exception as e:
        results["diagnostic"] = {"error": str(e)}

    # 3. Scan triggers
    scan = await scan_triggers()
    results["triggers"] = scan

    # 4. Auto-heal
    heal = _auto_heal(scan["triggers"])
    results["healing"] = heal

    return results
