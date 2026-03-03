"""
World Model API — unified system state for the frontend WorldModelPanel.

Aggregates data from ALL Grace subsystems into a single coherent view:
  - System health, connectivity, runtime status
  - Knowledge base stats (collections, documents, embeddings)
  - Source code map (components, files, functions)
  - Database state (tables, row counts, size)
  - Brain capabilities (all actions across all domains)
  - Cognitive state (trust, synapses, learning)
  - Genesis key activity
  - Active sessions and projects

The /chat endpoint enables natural language queries about the world model
using semantic search + memory injector context.
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import time
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/world-model", tags=["World Model"])


@router.get("/state")
async def world_model_state():
    """Full system state snapshot for the WorldModelPanel."""
    state = {
        "status": "operational",
        "timestamp": time.time(),
    }

    # Health
    try:
        from database.connection import DatabaseConnection
        state["health"] = "healthy" if DatabaseConnection.health_check() else "degraded"
    except Exception:
        state["health"] = "unknown"

    # Runtime
    try:
        from core.services.system_service import get_runtime_status
        state["runtime"] = get_runtime_status()
    except Exception:
        state["runtime"] = {"status": "unknown"}

    # Connectivity
    try:
        from settings import settings
        state["connectivity"] = {
            "ollama": {"configured": bool(settings.OLLAMA_URL)},
            "kimi": {"configured": bool(settings.KIMI_API_KEY)},
            "opus": {"configured": bool(settings.OPUS_API_KEY)},
            "qdrant": {"configured": bool(settings.QDRANT_API_KEY or settings.QDRANT_HOST)},
            "database": {"type": settings.DATABASE_TYPE, "connected": state.get("health") == "healthy"},
        }
    except Exception:
        state["connectivity"] = {}

    # Knowledge base
    try:
        from core.db_compat import get_table_stats, get_db_size_mb
        from database.connection import DatabaseConnection
        engine = DatabaseConnection.get_engine()
        tables = get_table_stats(engine)
        state["knowledge_base"] = {
            "total_tables": len(tables),
            "total_rows": sum(v for v in tables.values() if v > 0),
            "db_size_mb": get_db_size_mb(engine),
            "tables": {k: v for k, v in tables.items() if v > 0},
        }
    except Exception:
        state["knowledge_base"] = {"total_tables": 0}

    # Source code map
    try:
        from core.semantic_search import COMPONENTS
        state["source_code"] = {
            "total_components": len(COMPONENTS),
            "components": [
                {"id": cid, "file": info["file"], "purpose": info["purpose"][:80]}
                for cid, info in list(COMPONENTS.items())[:30]
            ],
        }
    except Exception:
        state["source_code"] = {"total_components": 0}

    # Brain capabilities
    try:
        from api.brain_api_v2 import _build_directory
        directory = _build_directory()
        total_actions = sum(len(d["actions"]) for d in directory.values())
        state["capabilities"] = {
            "total_actions": total_actions,
            "domains": {k: {"count": len(v["actions"]), "description": v["description"]}
                        for k, v in directory.items()},
        }
    except Exception:
        state["capabilities"] = {"total_actions": 0}

    # Trust scores
    try:
        from core.intelligence import AdaptiveTrust
        state["trust"] = AdaptiveTrust.get_all_trust()
    except Exception:
        state["trust"] = {}

    # Genesis key summary
    try:
        from core.genesis_storage import GenesisStorageManager
        mgr = GenesisStorageManager()
        state["genesis"] = mgr.stats()
    except Exception:
        state["genesis"] = {}

    # Worker pool
    try:
        from core.worker_pool import pool_status
        state["workers"] = pool_status()
    except Exception:
        state["workers"] = {}

    # LLM cache + costs
    try:
        from core.security import get_llm_cache, get_cost_tracker
        state["cache"] = get_llm_cache().stats()
        state["api_costs"] = get_cost_tracker().get_summary()
    except Exception:
        pass

    # Memory injector stats
    try:
        from core.memory_injector import get_snapshot_stats
        state["memory_injector"] = get_snapshot_stats()
    except Exception:
        pass

    return state


@router.get("/subsystems")
async def world_model_subsystems():
    """List all subsystems with their health status."""
    subsystems = []

    checks = [
        ("Database", _check_database),
        ("LLM Provider", _check_llm),
        ("Qdrant Vector DB", _check_qdrant),
        ("Genesis Tracking", _check_genesis),
        ("Diagnostic Engine", _check_diagnostics),
        ("Autonomous Loop", _check_autonomous),
        ("Worker Pool (IO)", _check_worker_io),
        ("Worker Pool (CPU)", _check_worker_cpu),
        ("Semantic Search", _check_semantic),
        ("Memory Injector", _check_memory_injector),
        ("File Watcher", _check_file_watcher),
        ("Governance", _check_governance),
        ("Trust Engine", _check_trust),
        ("Coding Pipeline", _check_pipeline),
        ("LLM Cache", _check_cache),
    ]

    for name, checker in checks:
        try:
            result = checker()
            subsystems.append({"name": name, **result})
        except Exception as e:
            subsystems.append({"name": name, "status": "error", "detail": str(e)})

    return {"subsystems": subsystems, "total": len(subsystems),
            "healthy": sum(1 for s in subsystems if s.get("status") == "healthy")}


@router.post("/chat")
async def world_model_chat(request: Request):
    """Chat with the world model — answers questions about Grace's internal state."""
    body = await request.json()
    query = body.get("query", "")
    include_state = body.get("include_system_state", True)

    if not query:
        return {"response": "Please ask a question about the system."}

    # Try semantic search first
    semantic_results = []
    try:
        from core.semantic_search import semantic_search
        results = semantic_search(query)
        semantic_results = results.get("results", [])
    except Exception:
        pass

    # Build context from world model
    context_parts = []

    if semantic_results:
        context_parts.append("SEMANTIC SEARCH RESULTS:")
        for r in semantic_results[:5]:
            context_parts.append(f"  - {r.get('id', '?')}: {r.get('purpose', '?')} (file: {r.get('file', '?')})")

    if include_state:
        try:
            from core.memory_injector import build_llm_context
            llm_context = build_llm_context(task=query)
            if llm_context:
                context_parts.append(f"\nSYSTEM STATE:\n{llm_context[:4000]}")
        except Exception:
            pass

    # Send to LLM with full context
    try:
        from core.independent_models import run_with_failover
        full_prompt = (
            f"You are Grace's World Model — you know everything about the system's internal state.\n"
            f"Answer this question using the system data provided below.\n\n"
            f"{''.join(context_parts)}\n\n"
            f"Question: {query}"
        )
        result = run_with_failover(
            full_prompt,
            preferred_order=["kimi", "opus", "qwen"],
            system_prompt=(
                "You are Grace AI's World Model. You have complete visibility into the system's "
                "health, components, trust scores, brain actions, database state, and cognitive systems. "
                "Answer questions about the system accurately and concisely using the provided data."
            ),
        )
        response = result.get("response", "Unable to generate response.")
    except Exception as e:
        if semantic_results:
            response = "Here's what I found:\n\n" + "\n".join(
                f"- **{r.get('id')}**: {r.get('purpose')} (at `{r.get('file')}`)"
                for r in semantic_results[:5]
            )
        else:
            response = f"World model query failed: {e}"

    return {
        "response": response,
        "query": query,
        "semantic_results": semantic_results[:5],
    }


# ── Subsystem health checks ────────────────────────────────────

def _check_database():
    from database.connection import DatabaseConnection
    healthy = DatabaseConnection.health_check()
    try:
        from settings import settings
        db_type = settings.DATABASE_TYPE
    except Exception:
        db_type = "sqlite"
    return {"status": "healthy" if healthy else "unhealthy", "type": db_type}


def _check_llm():
    try:
        from llm_orchestrator.factory import get_llm_client
        client = get_llm_client()
        running = client.is_running()
        return {"status": "healthy" if running else "degraded", "detail": "LLM reachable" if running else "LLM not responding"}
    except Exception as e:
        return {"status": "degraded", "detail": str(e)}


def _check_qdrant():
    try:
        from vector_db.client import get_qdrant_client
        client = get_qdrant_client()
        connected = client.is_connected()
        return {"status": "healthy" if connected else "degraded", "detail": "Connected" if connected else "Not connected"}
    except Exception:
        return {"status": "degraded", "detail": "Qdrant not configured"}


def _check_genesis():
    try:
        from core.genesis_storage import GenesisStorageManager
        stats = GenesisStorageManager().stats()
        return {"status": "healthy", "hot_count": stats.get("hot_tier_count", 0)}
    except Exception:
        return {"status": "degraded", "detail": "Genesis storage unavailable"}


def _check_diagnostics():
    try:
        from core.services.system_service import get_diagnostics_status
        result = get_diagnostics_status()
        return {"status": "healthy" if result else "degraded"}
    except Exception:
        return {"status": "unknown"}


def _check_autonomous():
    try:
        from api.autonomous_loop_api import _loop_state
        running = _loop_state.get("running", False)
        return {"status": "healthy" if running else "stopped", "cycles": _loop_state.get("cycle_count", 0)}
    except Exception:
        return {"status": "unknown"}


def _check_worker_io():
    try:
        from core.worker_pool import get_io_pool
        pool = get_io_pool()
        status = pool.get_status()
        return {"status": "healthy", "active": status["active"], "completed": status["completed"]}
    except Exception:
        return {"status": "unknown"}


def _check_worker_cpu():
    try:
        from core.worker_pool import get_cpu_pool
        pool = get_cpu_pool()
        status = pool.get_status()
        return {"status": "healthy", "active": status["active"], "completed": status["completed"]}
    except Exception:
        return {"status": "unknown"}


def _check_semantic():
    try:
        from core.semantic_search import COMPONENTS
        return {"status": "healthy", "components": len(COMPONENTS)}
    except Exception:
        return {"status": "degraded"}


def _check_memory_injector():
    try:
        from core.memory_injector import get_snapshot_stats
        stats = get_snapshot_stats()
        return {"status": "healthy", "snapshots": stats.get("snapshots", 0)}
    except Exception:
        return {"status": "unknown"}


def _check_file_watcher():
    try:
        from settings import settings
        if settings.DISABLE_GENESIS_TRACKING:
            return {"status": "disabled"}
        return {"status": "healthy", "detail": "Watching workspace"}
    except Exception:
        return {"status": "unknown"}


def _check_governance():
    try:
        from core.services.govern_service import list_rules
        rules = list_rules()
        doc_count = len(rules.get("documents", []))
        return {"status": "healthy", "documents": doc_count}
    except Exception:
        return {"status": "degraded"}


def _check_trust():
    try:
        from core.intelligence import AdaptiveTrust
        trust = AdaptiveTrust.get_all_trust()
        models = trust.get("models", {})
        return {"status": "healthy", "models_tracked": len(models)}
    except Exception:
        return {"status": "unknown"}


def _check_pipeline():
    try:
        from core.coding_pipeline import get_pipeline_progress
        progress = get_pipeline_progress()
        return {"status": "healthy"}
    except Exception:
        return {"status": "unknown"}


def _check_cache():
    try:
        from core.security import get_llm_cache
        stats = get_llm_cache().stats()
        return {"status": "healthy", "hit_rate": stats.get("hit_rate", 0)}
    except Exception:
        return {"status": "unknown"}
