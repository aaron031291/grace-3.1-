"""
Unified System Health API - Reports status of ALL Grace subsystems.

Provides a single endpoint that shows the entire organism's health:
- Core services (DB, Qdrant, Ollama)
- Message Bus (subscribers, messages, autonomous actions)
- Component Registry (registered components, health scores)
- Cognitive Engine, Magma Memory, Diagnostic Engine
- Systems Integration, Autonomous Engine
- Background workers (file watcher, auto-ingestion, continuous learning)
"""

from fastapi import APIRouter
from typing import Dict, Any

router = APIRouter(prefix="/api/system", tags=["System Health"])


@router.get("/health")
async def system_health() -> Dict[str, Any]:
    """
    Comprehensive health check for ALL Grace subsystems.
    Returns status of every component in one response.
    """
    health = {
        "status": "operational",
        "subsystems": {},
        "services": {},
        "message_bus": {},
        "summary": {},
    }

    # Core services
    health["services"]["database"] = _check_database()
    health["services"]["qdrant"] = _check_qdrant()
    health["services"]["ollama"] = _check_ollama()

    # Subsystems
    try:
        from startup import get_subsystems

        subs = get_subsystems()
        sub_status = subs.get_status()
        health["subsystems"] = sub_status

        # Message bus stats
        if subs.message_bus:
            try:
                bus_stats = subs.message_bus.get_stats()
                health["message_bus"] = {
                    "registered_components": bus_stats.get("registered_components", 0),
                    "total_messages": bus_stats.get("total_messages", 0),
                    "autonomous_actions": bus_stats.get("autonomous_actions", 0),
                    "subscribers": sum(bus_stats.get("subscribers", {}).values()),
                    "pending_requests": bus_stats.get("pending_requests", 0),
                }
            except Exception as e:
                health["message_bus"] = {"error": str(e)}

        # Component registry stats
        if subs.registry:
            try:
                reg_health = subs.registry.get_system_health()
                health["subsystems"]["registry_health"] = reg_health
            except Exception as e:
                health["subsystems"]["registry_health"] = {"error": str(e)}

        # Magma stats
        if subs.magma:
            try:
                magma_stats = subs.magma.get_stats()
                health["subsystems"]["magma_stats"] = magma_stats
            except Exception as e:
                health["subsystems"]["magma_stats"] = {"error": str(e)}

    except ImportError:
        health["subsystems"] = {"error": "startup module not available"}

    # Calculate overall health
    active = health["subsystems"].get("active_count", 0)
    services_up = sum(1 for v in health["services"].values() if v.get("status") == "connected")
    total_services = len(health["services"])

    health["summary"] = {
        "active_subsystems": active,
        "services_connected": f"{services_up}/{total_services}",
        "message_bus_alive": health["message_bus"].get("registered_components", 0) > 0,
        "health_score": round((active / 8 + services_up / total_services) / 2, 2) if total_services > 0 else 0,
    }

    if health["summary"]["health_score"] >= 0.7:
        health["status"] = "healthy"
    elif health["summary"]["health_score"] >= 0.4:
        health["status"] = "degraded"
    else:
        health["status"] = "critical"

    return health


@router.get("/subsystems")
async def list_subsystems() -> Dict[str, Any]:
    """List all subsystems and their status."""
    try:
        from startup import get_subsystems

        subs = get_subsystems()
        return subs.get_status()
    except ImportError:
        return {"error": "startup module not available"}


@router.get("/message-bus")
async def message_bus_status() -> Dict[str, Any]:
    """Get detailed message bus status."""
    try:
        from startup import get_subsystems

        subs = get_subsystems()
        if subs.message_bus:
            stats = subs.message_bus.get_stats()
            actions = subs.message_bus.get_autonomous_actions()
            return {
                "stats": stats,
                "autonomous_actions": actions,
            }
        return {"status": "not initialized"}
    except ImportError:
        return {"error": "startup module not available"}


def _check_database() -> Dict[str, Any]:
    """Check database health."""
    try:
        from database.connection import DatabaseConnection

        engine = DatabaseConnection.get_engine()
        if engine:
            return {"status": "connected", "type": engine.url.drivername}
    except Exception as e:
        return {"status": "disconnected", "error": str(e)}
    return {"status": "not initialized"}


def _check_qdrant() -> Dict[str, Any]:
    """Check Qdrant health."""
    try:
        from vector_db.client import get_qdrant_client

        client = get_qdrant_client()
        if client.is_connected():
            collections = client.list_collections()
            return {"status": "connected", "collections": len(collections)}
        return {"status": "disconnected"}
    except Exception as e:
        return {"status": "disconnected", "error": str(e)}


def _check_ollama() -> Dict[str, Any]:
    """Check Ollama health."""
    try:
        from ollama_client.client import get_ollama_client

        client = get_ollama_client()
        if client.is_running():
            models = client.get_all_models()
            return {"status": "connected", "models": len(models)}
        return {"status": "disconnected"}
    except Exception as e:
        return {"status": "disconnected", "error": str(e)}
