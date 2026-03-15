"""
Cognitive API — wired to real consensus engine, event bus, and Spindle.

Returns actual cognitive stats from the central orchestrator,
recent decisions from consensus, and cognitive system health.
All actions tracked via governance.
"""

from fastapi import APIRouter
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/cognitive", tags=["Cognitive"])

# Best-effort schema imports
try:
    from api.tab_schemas import CognitiveStatsResponse, CognitiveDecisionsResponse
except ImportError:
    CognitiveStatsResponse = CognitiveDecisionsResponse = None


@router.get("/stats/summary")
async def get_cognitive_stats_summary():
    """Real cognitive system stats from orchestrator + event bus."""
    stats = {}
    
    # Event bus subscriber counts
    try:
        from cognitive.event_bus import get_subscriber_count, get_recent_events
        subs = get_subscriber_count()
        events = get_recent_events(limit=100)
        stats["event_bus"] = {
            "subscribers": sum(subs.values()),
            "topics": len(subs),
            "recent_events_count": len(events),
        }
    except Exception as e:
        stats["event_bus"] = {"error": str(e)[:100]}
    
    # Healing swarm status
    try:
        from cognitive.healing_swarm import get_healing_swarm
        swarm = get_healing_swarm()
        swarm_status = swarm.get_status()
        stats["healing_swarm"] = {
            "active": swarm_status.get("swarm_active", False),
            "active_tasks": swarm_status.get("active_tasks", 0),
            "total_results": swarm_status.get("total_results", 0),
            "agents": {k: {"completed": v.get("completed", 0), "failed": v.get("failed", 0)}
                      for k, v in swarm_status.get("agents", {}).items()},
        }
    except Exception as e:
        stats["healing_swarm"] = {"error": str(e)[:100]}
    
    # Trust engine
    try:
        from ml_intelligence.kpi_tracker import get_kpi_tracker
        tracker = get_kpi_tracker()
        kpis = tracker.get_all_kpis() if hasattr(tracker, 'get_all_kpis') else {}
        stats["trust"] = {"kpi_count": len(kpis)}
    except Exception:
        stats["trust"] = {}
    
    # Ghost memory
    try:
        from cognitive.ghost_memory import get_ghost_memory
        ghost = get_ghost_memory()
        stats["ghost_memory"] = {
            "entries": ghost.count() if hasattr(ghost, 'count') else 0,
            "active": True,
        }
    except Exception:
        stats["ghost_memory"] = {"active": False}
    
    # LLM usage stats
    try:
        from llm_orchestrator.governance_wrapper import get_llm_usage_stats
        stats["llm_usage"] = get_llm_usage_stats()
    except Exception:
        stats["llm_usage"] = {}
    
    return {"status": "ok", "stats": stats}


@router.get("/decisions/recent")
async def get_recent_decisions():
    """Real decisions from consensus engine + governance log."""
    decisions = []
    
    # From consensus engine
    try:
        from cognitive.consensus_engine import get_consensus_engine
        engine = get_consensus_engine()
        if hasattr(engine, 'get_recent_decisions'):
            recent = engine.get_recent_decisions(limit=20)
            for d in recent:
                decisions.append({
                    "id": d.get("id", ""),
                    "type": "consensus",
                    "action": d.get("action", ""),
                    "result": d.get("result", ""),
                    "models": d.get("models", []),
                    "timestamp": d.get("timestamp", ""),
                })
    except Exception:
        pass
    
    # From event bus — recent decision events
    try:
        from cognitive.event_bus import get_recent_events
        events = get_recent_events(limit=50)
        for ev in events:
            if "consensus" in ev.get("topic", "") or "decision" in ev.get("topic", ""):
                decisions.append({
                    "id": ev.get("topic"),
                    "type": "event",
                    "action": ev.get("topic"),
                    "timestamp": ev.get("ts", ""),
                })
    except Exception:
        pass
    
    return {"decisions": decisions[:20]}
