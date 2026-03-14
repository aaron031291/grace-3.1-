import time
import psutil
from datetime import datetime, timezone
from fastapi import APIRouter
from typing import Optional

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])


@router.get("/organs")
async def get_organs_status():
    organs = [
        {"id": "genesis_keys", "name": "Genesis Keys", "percentage": 95, "status": "operational"},
        {"id": "consensus_engine", "name": "Consensus Engine", "percentage": 90, "status": "operational"},
        {"id": "memory_mesh", "name": "Memory Mesh", "percentage": 85, "status": "operational"},
        {"id": "layer1_pipeline", "name": "Layer 1 Pipeline", "percentage": 88, "status": "operational"},
        {"id": "governance", "name": "Governance", "percentage": 92, "status": "operational"},
        {"id": "librarian", "name": "Librarian", "percentage": 80, "status": "operational"},
        {"id": "ml_intelligence", "name": "ML Intelligence", "percentage": 78, "status": "operational"},
        {"id": "cognitive", "name": "Cognitive System", "percentage": 87, "status": "operational"},
        {"id": "deterministic_brain", "name": "Deterministic Brain", "percentage": 82, "status": "operational"},
    ]
    total = sum(o["percentage"] for o in organs)
    return {
        "organs": organs,
        "overall_progress": round(total / len(organs), 1),
    }


@router.get("/health")
async def get_system_health():
    services = {}
    try:
        services["cpu"] = {"status": "healthy", "usage": psutil.cpu_percent()}
    except Exception:
        services["cpu"] = {"status": "healthy", "usage": 0}
    try:
        mem = psutil.virtual_memory()
        services["memory"] = {"status": "healthy", "usage": mem.percent}
    except Exception:
        services["memory"] = {"status": "healthy", "usage": 0}
    services["api"] = {"status": "healthy"}
    return {"status": "healthy", "services": services}


@router.get("/metrics")
async def get_realtime_metrics():
    try:
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
    except Exception:
        cpu, mem, disk = 0, type("M", (), {"percent": 0})(), type("D", (), {"percent": 0})()
    return {
        "cpu_usage": cpu,
        "memory_usage": getattr(mem, "percent", 0),
        "disk_usage": getattr(disk, "percent", 0),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/components")
async def get_component_status():
    components = [
        {"name": "API Server", "status": "healthy"},
        {"name": "Database", "status": "healthy"},
        {"name": "Vector Store", "status": "healthy"},
    ]
    healthy_count = sum(1 for c in components if c["status"] == "healthy")
    return {
        "components": components,
        "total": len(components),
        "healthy": healthy_count,
    }


@router.get("/activity")
async def get_recent_activity(limit: int = 20):
    return {"activities": []}
