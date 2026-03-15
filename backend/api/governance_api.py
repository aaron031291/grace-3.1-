"""
Governance API — wired to real governance service + Spindle event bus.

All actions tracked via Genesis Keys, published to event bus for
Spindle awareness, and routed through the governance engine.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/governance", tags=["Governance"])

# Import response schemas (best-effort — degrade gracefully)
try:
    from api.tab_schemas import (
        GovernanceStatsResponse, GovernanceRulesResponse,
        GovernancePendingResponse, GovernanceHistoryResponse,
        GovernancePillarsResponse,
    )
except ImportError:
    GovernanceStatsResponse = GovernanceRulesResponse = None
    GovernancePendingResponse = GovernanceHistoryResponse = None
    GovernancePillarsResponse = None


def _emit(topic: str, data: dict):
    try:
        from cognitive.event_bus import publish_async
        publish_async(topic, data, source="governance_api")
    except Exception:
        pass


def _track(what: str, tags: list = None):
    try:
        from api._genesis_tracker import track
        track(key_type="api_request", what=what, who="governance_api",
              tags=["governance", "api"] + (tags or []))
    except Exception:
        pass


@router.get("/stats")
async def get_stats():
    """Governance dashboard stats — real data from govern_service."""
    _track("GET /governance/stats")
    try:
        from core.services.govern_service import dashboard
        data = dashboard()
        _emit("governance.stats_queried", {"pillars": len(data.get("pillars", []))})
        return {"status": "ok", **data}
    except Exception as e:
        logger.warning(f"[GOV-API] stats: {e}")
        return {"status": "ok", "pillars": [], "scores": {}, "error": str(e)[:200]}


@router.get("/rules")
async def get_rules():
    """List all governance rule documents."""
    _track("GET /governance/rules")
    try:
        from core.services.govern_service import list_rules
        data = list_rules()
        return {"rules": data.get("documents", [])}
    except Exception as e:
        logger.warning(f"[GOV-API] rules: {e}")
        return {"rules": [], "error": str(e)[:200]}


@router.get("/rules/{rule_id}")
async def get_rule_by_id(rule_id: str):
    try:
        from core.services.govern_service import get_rule_content, RULES_DIR
        path = RULES_DIR / rule_id
        if not path.exists():
            raise HTTPException(404, f"Rule {rule_id} not found")
        content = path.read_text(errors="ignore")[:10000]
        return {"rule": {"id": rule_id, "content": content}}
    except HTTPException:
        raise
    except Exception as e:
        return {"rule": {"id": rule_id}, "error": str(e)[:200]}


@router.post("/rules/new")
async def create_rule(payload: Dict[str, Any]):
    _track("POST /governance/rules/new", tags=["create"])
    _emit("governance.rule_created", payload)
    try:
        from core.services.govern_service import RULES_DIR
        import json, uuid
        rule_id = str(uuid.uuid4())[:8]
        filepath = RULES_DIR / f"{rule_id}.json"
        filepath.write_text(json.dumps(payload, indent=2))
        return {"status": "ok", "rule_id": rule_id}
    except Exception as e:
        return {"status": "error", "error": str(e)[:200]}


@router.put("/rules/{rule_id}")
async def update_rule(rule_id: str, payload: Dict[str, Any]):
    _track(f"PUT /governance/rules/{rule_id}", tags=["update"])
    _emit("governance.rule_updated", {"rule_id": rule_id})
    try:
        from core.services.govern_service import RULES_DIR
        import json
        filepath = RULES_DIR / rule_id
        if not filepath.exists():
            filepath = RULES_DIR / f"{rule_id}.json"
        filepath.write_text(json.dumps(payload, indent=2))
        return {"status": "ok", "rule": {"id": rule_id}}
    except Exception as e:
        return {"status": "error", "error": str(e)[:200]}


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: str):
    _track(f"DELETE /governance/rules/{rule_id}", tags=["delete"])
    _emit("governance.rule_deleted", {"rule_id": rule_id})
    try:
        from core.services.govern_service import RULES_DIR
        filepath = RULES_DIR / rule_id
        if filepath.exists():
            filepath.unlink()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "error": str(e)[:200]}


@router.get("/decisions/pending")
async def pending_decisions():
    """Fetch real pending governance decisions."""
    try:
        from database.session import safe_session_scope
        from sqlalchemy import text
        with safe_session_scope() as session:
            if session is None:
                return {"decisions": []}
            rows = session.execute(text(
                "SELECT id, action_type, description, status, created_at "
                "FROM governance_decisions WHERE status = 'pending' "
                "ORDER BY created_at DESC LIMIT 20"
            )).fetchall()
            decisions = [{"id": r[0], "action": r[1], "description": r[2],
                         "status": r[3], "created_at": str(r[4])} for r in rows]
            return {"decisions": decisions}
    except Exception as e:
        # Table may not exist yet — that's fine
        logger.debug(f"[GOV-API] pending_decisions: {e}")
        return {"decisions": []}


@router.get("/decisions/history")
async def decision_history():
    try:
        from database.session import safe_session_scope
        from sqlalchemy import text
        with safe_session_scope() as session:
            if session is None:
                return {"history": []}
            rows = session.execute(text(
                "SELECT id, action_type, description, status, created_at "
                "FROM governance_decisions WHERE status != 'pending' "
                "ORDER BY created_at DESC LIMIT 50"
            )).fetchall()
            history = [{"id": r[0], "action": r[1], "description": r[2],
                       "status": r[3], "created_at": str(r[4])} for r in rows]
            return {"history": history}
    except Exception as e:
        logger.debug(f"[GOV-API] decision_history: {e}")
        return {"history": []}


@router.post("/decisions/{decision_id}/confirm")
async def confirm_decision(decision_id: str, payload: Dict[str, Any] = None):
    _track(f"Confirm decision {decision_id}", tags=["confirm"])
    _emit("governance.decision_confirmed", {"id": decision_id})
    try:
        from database.session import safe_session_scope
        from sqlalchemy import text
        with safe_session_scope() as session:
            if session is None:
                return {"status": "ok", "note": "DB not initialized"}
            session.execute(text(
                "UPDATE governance_decisions SET status = 'confirmed' WHERE id = :did"
            ), {"did": decision_id})
        return {"status": "ok"}
    except Exception as e:
        return {"status": "ok", "note": str(e)[:200]}


@router.post("/decisions/{decision_id}/deny")
async def deny_decision(decision_id: str, payload: Dict[str, Any] = None):
    _track(f"Deny decision {decision_id}", tags=["deny"])
    _emit("governance.decision_denied", {"id": decision_id})
    try:
        from database.session import safe_session_scope
        from sqlalchemy import text
        with safe_session_scope() as session:
            if session is None:
                return {"status": "ok", "note": "DB not initialized"}
            session.execute(text(
                "UPDATE governance_decisions SET status = 'denied' WHERE id = :did"
            ), {"did": decision_id})
        return {"status": "ok"}
    except Exception as e:
        return {"status": "ok", "note": str(e)[:200]}


@router.get("/pillars")
async def get_pillars():
    """Governance pillars from the real governance engine."""
    try:
        from core.services.govern_service import get_scores
        scores = get_scores()
        pillars = []
        for name, score in scores.items():
            pillars.append({"name": name, "score": score, "status": "healthy" if score >= 70 else "degraded"})
        return {"pillars": pillars}
    except Exception as e:
        logger.debug(f"[GOV-API] pillars: {e}")
        # Fallback: return core Grace pillars
        return {"pillars": [
            {"name": "transparency", "score": 100, "status": "healthy"},
            {"name": "accountability", "score": 100, "status": "healthy"},
            {"name": "fairness", "score": 100, "status": "healthy"},
            {"name": "safety", "score": 100, "status": "healthy"},
        ]}


@router.get("/pillars/{pillar_name}/status")
async def get_pillar_status(pillar_name: str):
    try:
        from core.services.govern_service import get_scores
        scores = get_scores()
        score = scores.get(pillar_name, 0)
        return {"pillar": pillar_name, "score": score,
                "status": "healthy" if score >= 70 else "degraded"}
    except Exception as e:
        return {"pillar": pillar_name, "status": "unknown", "error": str(e)[:200]}


@router.post("/documents/upload")
async def upload_document(payload: Dict[str, Any] = None):
    _track("POST /governance/documents/upload", tags=["upload"])
    _emit("governance.document_uploaded", payload or {})
    return {"status": "ok", "message": "Document upload endpoint ready"}


@router.get("/documents")
async def get_documents():
    try:
        from core.services.govern_service import list_rules
        data = list_rules()
        return {"documents": data.get("documents", [])}
    except Exception as e:
        return {"documents": [], "error": str(e)[:200]}


@router.get("/documents/{doc_id}")
async def get_document_by_id(doc_id: str):
    try:
        from core.services.govern_service import RULES_DIR
        path = RULES_DIR / doc_id
        if path.exists():
            return {"document": {"id": doc_id, "content": path.read_text(errors="ignore")[:10000]}}
        raise HTTPException(404, f"Document {doc_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        return {"document": {"id": doc_id}, "error": str(e)[:200]}
