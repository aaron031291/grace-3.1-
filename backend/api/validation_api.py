"""
api/validation_api.py
─────────────────────────────────────────────────────────────────────────────
Validation & Trust Score API

Exposes Grace's internal validation metrics to the frontend:
  - Code verification trust scores (per task and running average)
  - KPI health per component (coding_agent, self_healing, learning)
  - Input/output alignment checks (expected vs actual outputs)
  - Behavioral KPIs aligned with Grace's constitutional pillars
  - External user-facing success metrics

Frontend can poll GET /api/validation/status for a live dashboard.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/validation", tags=["Validation & Trust"])


# ── Core trust + KPI aggregator ───────────────────────────────────────────

def _get_kpi_snapshot() -> Dict[str, Any]:
    """Collect KPI data from ml_intelligence KPI tracker."""
    try:
        from ml_intelligence.kpi_tracker import get_kpi_tracker
        tracker = get_kpi_tracker()
        if not tracker:
            return {"available": False}
        components = [
            "coding_agent.verification",
            "verification_pass",
            "brain_code",
            "brain_ai",
            "brain_system",
            "brain_learn",
            "brain_memory",
            "error_pipeline",
        ]
        data = {}
        for comp in components:
            try:
                trust = tracker.get_component_trust_score(comp)
                comp_kpis = tracker.get_component_kpis(comp)
                if comp_kpis:
                    data[comp] = {
                        "trust_score": round(trust, 3) if trust else None,
                        "requests": comp_kpis.get_kpi("requests").count,
                        "successes": comp_kpis.get_kpi("successes").count,
                        "failures": comp_kpis.get_kpi("failures").count,
                        "rejections": comp_kpis.get_kpi("rejected").count,
                    }
                else:
                    data[comp] = {
                        "trust_score": None,
                        "requests": 0, "successes": 0, "failures": 0, "rejections": 0,
                    }
            except Exception:
                data[comp] = {"trust_score": None, "requests": 0, "successes": 0, "failures": 0, "rejections": 0}
        return {"available": True, "components": data}
    except Exception as e:
        return {"available": False, "error": str(e)[:80]}


def _get_recent_verification_results(limit: int = 20) -> List[Dict]:
    """Pull recent verification outcomes from Genesis KB."""
    try:
        from database.session import session_scope
        from models.genesis_key_models import GenesisKey
        from sqlalchemy import desc
        with session_scope() as session:
            rows = (
                session.query(GenesisKey)
                .filter(GenesisKey.key_type == "system_event")
                .filter(GenesisKey.what_description.like("%verification%"))
                .order_by(desc(GenesisKey.created_at))
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": str(r.id),
                    "description": r.what_description[:100],
                    "is_error": r.is_error,
                    "created_at": r.created_at.isoformat() if r.created_at else "",
                    "context": r.context_data if isinstance(r.context_data, dict) else {},
                }
                for r in rows
            ]
    except Exception:
        return []


def _get_healing_stats() -> Dict[str, Any]:
    """Get self-healing MTTR and success rate from error_pipeline."""
    try:
        from self_healing.error_pipeline import get_error_pipeline
        ep = get_error_pipeline()
        stats = ep.get_stats() if hasattr(ep, "get_stats") else {}
        return stats
    except Exception:
        return {}


def _get_memory_alignment() -> Dict[str, Any]:
    """Check if all 3 memory layers have data — input/output alignment signal."""
    out = {}
    try:
        from cognitive.unified_memory import get_unified_memory
        stats = get_unified_memory().get_stats()
        out["unified_memory"] = stats
    except Exception:
        out["unified_memory"] = {"error": "unavailable"}
    try:
        from cognitive import magma_bridge as magma
        out["magma"] = magma.get_stats()
    except Exception:
        out["magma"] = {"error": "unavailable"}
    try:
        from cognitive.ghost_memory import get_ghost_memory
        out["ghost"] = get_ghost_memory().get_stats()
    except Exception:
        out["ghost"] = {"error": "unavailable"}
    return out


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.get("/status")
async def get_validation_status():
    """
    Full validation dashboard — trust scores, KPIs, memory alignment.
    Suitable for frontend polling (30s interval recommended).
    """
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "kpis": _get_kpi_snapshot(),
        "recent_verifications": _get_recent_verification_results(limit=10),
        "healing_stats": _get_healing_stats(),
        "memory_alignment": _get_memory_alignment(),
    }


@router.get("/trust")
async def get_trust_scores():
    """
    Component-level trust scores aligned with Grace's pillars.
    Simple endpoint for the frontend trust gauge widget.
    """
    kpis = _get_kpi_snapshot()
    components = kpis.get("components", {})

    def _t(comp: str) -> Optional[float]:
        return (components.get(comp) or {}).get("trust_score")

    # Map to pillar-aligned user-facing names
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scores": {
            "coding_agent":     _t("coding_agent.verification"),
            "verification":     _t("verification_pass"),
            "self_healing":     _t("error_pipeline"),
            "intelligence":     _t("brain_ai"),
            "code_brain":       _t("brain_code"),
            "learning_brain":   _t("brain_learn"),
            "memory_brain":     _t("brain_memory"),
            "system_brain":     _t("brain_system"),
        },
        "overall": _compute_overall_trust(components),
    }


def _compute_overall_trust(components: dict) -> Optional[float]:
    """Simple weighted average of available trust scores."""
    scores = [
        v.get("trust_score") for v in components.values()
        if isinstance(v, dict) and v.get("trust_score") is not None
    ]
    if not scores:
        return None
    return round(sum(scores) / len(scores), 3)


@router.get("/kpis")
async def get_kpis():
    """Raw KPI metrics per component — requests, successes, failures, rejections."""
    return _get_kpi_snapshot()


@router.get("/verifications/recent")
async def get_recent_verifications(limit: int = 50):
    """
    Recent code verification decisions — accepted/rejected, trust score, flags.
    Use to display verification history in the frontend.
    """
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "results": _get_recent_verification_results(limit=limit),
    }


@router.post("/trigger-deep-probe")
async def trigger_deep_probe():
    """
    Trigger a full deep probe scan on demand.
    Returns a probe report ID — results show up in /api/validation/status.
    """
    try:
        import threading
        from cognitive.autonomous_diagnostics import AutonomousDiagnostics
        diag = AutonomousDiagnostics.get_instance()
        threading.Thread(target=diag.hourly_check, daemon=True, name="grace-demand-probe").start()
        return {"triggered": True, "message": "Deep probe started in background"}
    except Exception as e:
        return {"triggered": False, "error": str(e)[:100]}


# ── Launcher v4 Diagnostic Endpoints ──────────────────────────────────────────

@router.get("/playbooks/active")
async def get_active_playbooks():
    """Returns currently running self-healing playbooks + recent history."""
    try:
        from self_healing.error_pipeline import get_error_pipeline
        ep = get_error_pipeline()
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "active": getattr(ep, "active_playbooks", {}),
            "recent_history": getattr(ep, "playbook_history", [])[-20:]
        }
    except Exception as e:
        return {"error": str(e)}

@router.get("/memory/stream")
async def get_memory_stream(limit: int = 50):
    """Returns a combined recent activity stream from Episodic, Learning, and Procedural memory."""
    try:
        from cognitive.unified_memory import get_unified_memory
        um = get_unified_memory()
        stats = um.get_stats()
        cap = max(1, min(limit, 100))
        episodes = um.recall_episodes(limit=cap)
        learnings = um.recall_learnings(limit=cap)
        procedures = um.recall_procedures(limit=cap)
        recent_ingestion = []
        for e in episodes:
            recent_ingestion.append({"source": "episode", "created_at": e.get("created_at"), "summary": (e.get("problem") or "")[:120]})
        for L in learnings:
            recent_ingestion.append({"source": "learning", "summary": (L.get("input") or "")[:120], "trust": L.get("trust")})
        for p in procedures:
            recent_ingestion.append({"source": "procedure", "summary": (p.get("goal") or p.get("name") or "")[:120], "trust": p.get("trust")})
        recent_ingestion = recent_ingestion[:cap]
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stats": stats,
            "recent_ingestion": recent_ingestion,
        }
    except Exception as e:
        return {"error": str(e)}

@router.get("/patches/recent")
async def get_recent_patches(limit: int = 20):
    """Returns recently applied code patches from the coding agent task queue."""
    try:
        from coding_agent.task_queue import get_task_queue
        tq = get_task_queue()
        patches = getattr(tq, "recent_patches", [])[-limit:]
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "patches": patches
        }
    except Exception as e:
        return {"error": str(e)}

@router.get("/swarm/active")
async def get_active_swarm():
    """Returns the list of active background tasks for the Swarm Swimlane."""
    try:
        from coding_agent.task_queue import get_swarm_status
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tasks": get_swarm_status()
        }
    except Exception as e:
        return {"error": str(e)}

@router.post("/revert-patch")
async def revert_code_patch(patch_id: str):
    """Trigger an instant code revert for a specific patch ID."""
    try:
        from coding_agent.task_queue import get_task_queue
        tq = get_task_queue()
        # Find path
        target_patch = next((p for p in getattr(tq, "recent_patches", []) if p["id"] == patch_id), None)
        if not target_patch:
            return {"ok": False, "error": f"Patch {patch_id} not found in recent memory"}
        
        file_path = target_patch.get("file")
        if not file_path or not os.path.exists(file_path):
            return {"ok": False, "error": "Target file missing"}
            
        # For safety/simplicity in MVP: use git checkout to restore the file to HEAD
        # Assuming the file was modified but not committed. (Grace usually modifies files direct).
        import subprocess
        proc = subprocess.run(["git", "checkout", "--", file_path], capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__)))
        
        if proc.returncode == 0:
            target_patch["reverted"] = True
            return {"ok": True, "msg": f"Reverted {file_path} via git checkout"}
        else:
            return {"ok": False, "error": "Git revert failed: " + proc.stderr}
            
    except Exception as e:
        return {"ok": False, "error": str(e)}

@router.get("/llm/monitor")
async def get_llm_monitor(limit: int = 20):
    """Returns recent Qwen/DeepSeek prompts, outputs, and their Trust Scores."""
    try:
        from database.session import session_scope
        from models.genesis_key_models import GenesisKey
        from sqlalchemy import desc
        with session_scope() as session:
            rows = (
                session.query(GenesisKey)
                .filter(GenesisKey.key_type == "coding_task")
                .order_by(desc(GenesisKey.created_at))
                .limit(limit)
                .all()
            )
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "calls": [
                    {
                        "id": str(r.id),
                        "description": r.what_description,
                        "trust_score": (r.context_data or {}).get("trust_score"),
                        "created_at": r.created_at.isoformat() if r.created_at else "",
                    }
                    for r in rows
                ]
            }
    except Exception as e:
        return {"error": str(e)}
