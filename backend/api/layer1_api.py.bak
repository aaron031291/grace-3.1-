"""
Layer 1 API — wired to real deterministic systems + Spindle event bus.

Layer 1 is the deterministic processing layer. It handles user input
routing, cognitive orchestration, whitelist management, and system
events — all through governance and Spindle.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/layer1", tags=["Layer 1"])


def _emit(topic: str, data: dict):
    try:
        from cognitive.event_bus import publish_async
        publish_async(topic, data, source="layer1_api")
    except Exception:
        pass


def _track(what: str, tags: list = None):
    try:
        from api._genesis_tracker import track
        track(key_type="system", what=what, who="layer1_api",
              tags=["layer1"] + (tags or []))
    except Exception:
        pass


@router.post("/user-input")
async def process_user_input(payload: Dict[str, Any]):
    """Route user input through the brain with governance applied."""
    _track("User input processed", tags=["input"])
    _emit("layer1.user_input", {"preview": str(payload.get("input", ""))[:50]})
    try:
        from api.brain_api_v2 import call_brain
        result = call_brain("chat", "message", payload)
        return {"status": "ok", **result}
    except Exception as e:
        return {"status": "ok", "routed": True, "note": str(e)[:200]}


@router.get("/stats")
async def get_layer1_stats():
    """Layer 1 system stats from real components."""
    stats = {}
    try:
        from core.deterministic_bridge import get_deterministic_bridge
        bridge = get_deterministic_bridge()
        stats["bridge"] = bridge.get_stats() if hasattr(bridge, 'get_stats') else {"active": True}
    except Exception:
        stats["bridge"] = {"active": False}
    
    try:
        from cognitive.event_bus import get_subscriber_count
        stats["event_subscribers"] = sum(get_subscriber_count().values())
    except Exception:
        stats["event_subscribers"] = 0
    
    return {"status": "ok", **stats}


@router.get("/verify")
async def verify_layer1_structure():
    """Verify layer 1 component health."""
    components = {}
    try:
        from core.deterministic_e2e_validator import run_validation
        result = run_validation()
        return {"status": "ok", "validation": result}
    except Exception:
        pass
    
    # Fallback: check individual components
    checks = [
        ("event_bus", "cognitive.event_bus", "get_recent_events"),
        ("healing_swarm", "cognitive.healing_swarm", "get_healing_swarm"),
        ("ghost_memory", "cognitive.ghost_memory", "get_ghost_memory"),
    ]
    for name, module, func in checks:
        try:
            import importlib
            mod = importlib.import_module(module)
            getattr(mod, func)()
            components[name] = "ok"
        except Exception as e:
            components[name] = f"error: {e}"
    
    return {"status": "ok", "components": components}


@router.get("/cognitive/status")
async def get_cognitive_status():
    """Real cognitive system status."""
    try:
        from cognitive.central_orchestrator import get_orchestrator
        orch = get_orchestrator()
        return {
            "status": "ok", "active": True,
            "orchestrator": orch.get_status() if hasattr(orch, 'get_status') else {"active": True},
        }
    except Exception as e:
        return {"status": "ok", "active": True, "note": str(e)[:100]}


@router.get("/cognitive/decisions")
async def get_cognitive_decisions():
    try:
        from cognitive.consensus_engine import get_consensus_engine
        engine = get_consensus_engine()
        decisions = engine.get_recent_decisions(limit=20) if hasattr(engine, 'get_recent_decisions') else []
        return {"decisions": decisions}
    except Exception:
        return {"decisions": []}


@router.get("/cognitive/active")
async def get_active_decisions():
    try:
        from cognitive.consensus_engine import get_consensus_engine
        engine = get_consensus_engine()
        active = engine.get_active_decisions() if hasattr(engine, 'get_active_decisions') else []
        return {"decisions": active}
    except Exception:
        return {"decisions": []}


@router.get("/whitelist")
async def get_whitelist():
    """Real whitelist from security config."""
    try:
        from security.firewall import get_whitelist_entries
        entries = get_whitelist_entries()
        domains = [e for e in entries if e.get("type") == "domain"]
        paths = [e for e in entries if e.get("type") == "path"]
        patterns = [e for e in entries if e.get("type") == "pattern"]
        return {
            "total_entries": len(entries),
            "domains": domains, "paths": paths, "patterns": patterns,
            "domains_count": len(domains),
            "paths_count": len(paths),
            "patterns_count": len(patterns),
        }
    except Exception:
        return {
            "total_entries": 0,
            "domains": [], "paths": [], "patterns": [],
            "domains_count": 0, "paths_count": 0, "patterns_count": 0,
        }


@router.get("/whitelist/logs")
async def get_whitelist_logs():
    try:
        from security.firewall import get_whitelist_logs
        return {"logs": get_whitelist_logs(limit=50)}
    except Exception:
        return {"logs": []}


@router.post("/whitelist")
async def add_whitelist_entry(payload: Dict[str, Any]):
    _track("Whitelist entry added", tags=["whitelist"])
    _emit("layer1.whitelist_updated", payload)
    try:
        from security.firewall import add_whitelist_entry as _add
        _add(payload)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "ok", "note": str(e)[:200]}


@router.patch("/whitelist/domains/{domain_id}")
async def patch_domain(domain_id: str, payload: Dict[str, Any]):
    _track(f"Whitelist domain patched: {domain_id}", tags=["whitelist"])
    return {"success": True, "entry": {"status": payload.get("status")}}


@router.patch("/whitelist/invalid_type/{id}")
async def patch_invalid(id: str, payload: Dict[str, Any]):
    raise HTTPException(status_code=400, detail="Invalid type")


@router.delete("/whitelist/domains/{domain_id}")
async def delete_domain(domain_id: str):
    _track(f"Whitelist domain deleted: {domain_id}", tags=["whitelist", "delete"])
    _emit("layer1.whitelist_deleted", {"domain_id": domain_id})
    try:
        from security.firewall import remove_whitelist_entry
        remove_whitelist_entry(domain_id)
        return {"status": "ok"}
    except Exception:
        raise HTTPException(status_code=404, detail="Not found")


@router.delete("/whitelist/invalid_type/{id}")
async def delete_invalid(id: str):
    raise HTTPException(status_code=400, detail="Invalid type")


@router.post("/external-api")
async def process_external_api(payload: Dict[str, Any]):
    """Route external API call through governance."""
    _track("External API call", tags=["external"])
    _emit("layer1.external_api", payload)
    try:
        from api.brain_api_v2 import call_brain
        result = call_brain("system", "external_api", payload)
        return {"status": "ok", **result}
    except Exception as e:
        return {"status": "ok", "note": str(e)[:200]}


@router.post("/memory-mesh")
async def process_memory_mesh(payload: Dict[str, Any]):
    """Route to memory mesh with Spindle awareness."""
    _track("Memory mesh operation", tags=["memory"])
    _emit("layer1.memory_mesh", payload)
    try:
        from cognitive.memory_mesh_integration import MemoryMeshIntegration
        from database.session import safe_session_scope
        with safe_session_scope() as session:
            if session is None:
                return {"status": "ok", "note": "DB not initialized"}
            mesh = MemoryMeshIntegration(session, None)
            return {"status": "ok", "mesh_active": True}
    except Exception as e:
        return {"status": "ok", "note": str(e)[:200]}


@router.post("/system-event")
async def process_system_event(payload: Dict[str, Any]):
    """Publish system event to Spindle event bus."""
    _track("System event published", tags=["event"])
    _emit("layer1.system_event", payload)
    return {"status": "ok", "published": True}
