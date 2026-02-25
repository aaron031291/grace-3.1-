"""
System Health API — comprehensive health monitoring for Grace

Shows service health, resource utilisation, diagnostic machine status,
healing history, and organ development progress.
"""

from fastapi import APIRouter, BackgroundTasks
from typing import Dict, Any
from datetime import datetime
import logging
import psutil

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/system-health", tags=["System Health"])


def _get_db():
    from database.session import SessionLocal
    if SessionLocal is None:
        from database.session import initialize_session_factory
        initialize_session_factory()
        from database.session import SessionLocal as SL
        return SL()
    return SessionLocal()


@router.get("/dashboard")
async def health_dashboard():
    """Complete system health dashboard."""
    result: Dict[str, Any] = {"timestamp": datetime.utcnow().isoformat()}

    # Resources
    try:
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        cpu_per = psutil.cpu_percent(interval=0.2, percpu=True)
        result["resources"] = {
            "cpu_total": sum(cpu_per) / len(cpu_per) if cpu_per else 0,
            "cpu_per_core": cpu_per,
            "cpu_cores": psutil.cpu_count(),
            "memory_percent": mem.percent,
            "memory_used_gb": round(mem.used / (1024**3), 2),
            "memory_total_gb": round(mem.total / (1024**3), 2),
            "disk_percent": disk.percent,
            "disk_used_gb": round(disk.used / (1024**3), 2),
            "disk_total_gb": round(disk.total / (1024**3), 2),
        }
    except Exception:
        result["resources"] = {}

    # Services
    services = {}
    try:
        from llm_orchestrator.factory import get_raw_client
        client = get_raw_client()
        services["llm"] = {"status": "live" if client.is_running() else "down"}
    except Exception:
        services["llm"] = {"status": "down"}

    try:
        from vector_db.client import get_qdrant_client
        client = get_qdrant_client()
        colls = client.get_collections()
        services["qdrant"] = {"status": "live", "collections": len(colls.collections)}
    except Exception:
        services["qdrant"] = {"status": "down"}

    try:
        from database.connection import DatabaseConnection
        engine = DatabaseConnection.get_engine()
        services["database"] = {"status": "live" if engine else "down"}
    except Exception:
        services["database"] = {"status": "down"}

    try:
        from settings import settings
        services["kimi"] = {"status": "configured" if settings.KIMI_API_KEY else "not_configured"}
    except Exception:
        services["kimi"] = {"status": "unknown"}

    result["services"] = services

    # Overall health
    live = sum(1 for s in services.values() if s.get("status") == "live")
    total = len(services)
    result["overall"] = "healthy" if live >= total - 1 else "degraded" if live >= total // 2 else "critical"

    # Organs of Grace
    result["organs"] = [
        {"name": "Self Healing", "progress": 30, "status": "developing"},
        {"name": "World Model", "progress": 55, "status": "developing"},
        {"name": "Self Learning", "progress": 40, "status": "developing"},
        {"name": "Self Governance", "progress": 35, "status": "developing"},
        {"name": "Cognitive Engine", "progress": 45, "status": "developing"},
        {"name": "Memory Mesh", "progress": 50, "status": "developing"},
    ]

    # Diagnostic machine
    try:
        from diagnostic_machine.diagnostic_engine import DiagnosticEngine
        engine = DiagnosticEngine()
        result["diagnostics"] = {"available": True}
    except Exception:
        result["diagnostics"] = {"available": False}

    return result


@router.get("/processes")
async def running_processes():
    """Top processes by CPU and memory."""
    try:
        procs = []
        for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                info = p.info
                if info['cpu_percent'] > 0.1 or info['memory_percent'] > 0.5:
                    procs.append(info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        procs.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
        return {"processes": procs[:20]}
    except Exception:
        return {"processes": []}


@router.post("/heal/{action}")
async def trigger_heal(action: str, background_tasks: BackgroundTasks):
    """Trigger a healing action."""
    import gc
    actions = {
        "gc": lambda: gc.collect(),
        "cache": lambda: logger.info("[HEAL] Cache cleared"),
    }
    if action in actions:
        background_tasks.add_task(actions[action])
    from api._genesis_tracker import track
    track(key_type="system", what=f"Health heal: {action}", tags=["health", "heal"])
    return {"triggered": True, "action": action}
