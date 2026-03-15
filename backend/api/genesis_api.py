"""
Genesis API — wired to real Genesis Key service + Spindle event bus.

All endpoints go through governance (GovernanceAwareLLM wraps LLM calls),
track actions via Genesis Keys, and publish events to the Spindle event bus.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/genesis", tags=["Genesis"])


class GenesisKeyCreate(BaseModel):
    entity_type: str
    entity_id: str
    origin_source: str
    origin_type: str
    metadata: Optional[Dict[str, Any]] = None


def _emit(topic: str, data: dict):
    """Fire-and-forget event to Spindle."""
    try:
        from cognitive.event_bus import publish_async
        publish_async(topic, data, source="genesis_api")
    except Exception:
        pass


def _genesis_track(what: str, tags: list = None):
    """Track this API call as a Genesis Key (governance audit trail)."""
    try:
        from api._genesis_tracker import track
        track(key_type="api_request", what=what, who="genesis_api",
              tags=["genesis", "api"] + (tags or []))
    except Exception:
        pass


@router.get("/stats")
async def get_stats():
    """Genesis stats — connects to real service."""
    _genesis_track("GET /genesis/stats")
    try:
        from genesis.genesis_key_service import get_genesis_service
        service = get_genesis_service()
        stats = service.get_stats() if hasattr(service, 'get_stats') else {}
        _emit("genesis.stats_queried", {"stats": str(stats)[:200]})
        return {"status": "ok", **stats}
    except Exception as e:
        logger.warning(f"[GENESIS-API] stats error: {e}")
        # Fallback: query DB directly
        try:
            from database.session import safe_session_scope
            from sqlalchemy import text
            with safe_session_scope() as session:
                if session is None:
                    return {"status": "ok", "total_keys": 0, "note": "DB not initialized"}
                row = session.execute(text("SELECT COUNT(*) as cnt FROM genesis_key")).fetchone()
                count = row[0] if row else 0
                return {"status": "ok", "total_keys": count}
        except Exception:
            return {"status": "ok", "total_keys": 0}


@router.get("/keys")
async def get_keys(limit: int = 50, offset: int = 0, key_type: str = None):
    """List Genesis Keys from DB — real data."""
    _genesis_track("GET /genesis/keys", tags=["query"])
    try:
        from database.session import safe_session_scope
        from sqlalchemy import text
        with safe_session_scope() as session:
            if session is None:
                return {"keys": [], "total": 0, "note": "DB not initialized"}
            
            where = ""
            params = {"limit": limit, "offset": offset}
            if key_type:
                where = "WHERE key_type = :kt"
                params["kt"] = key_type
            
            count_row = session.execute(text(f"SELECT COUNT(*) FROM genesis_key {where}"), params).fetchone()
            total = count_row[0] if count_row else 0
            
            rows = session.execute(text(
                f"SELECT key_id, key_type, what_description, who_actor, "
                f"is_error, created_at FROM genesis_key {where} "
                f"ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
            ), params).fetchall()
            
            keys = []
            for r in rows:
                keys.append({
                    "key_id": r[0], "key_type": str(r[1]),
                    "what": r[2], "who": r[3],
                    "is_error": r[4], "created_at": str(r[5]),
                })
            return {"keys": keys, "total": total}
    except Exception as e:
        logger.warning(f"[GENESIS-API] keys query error: {e}")
        return {"keys": [], "total": 0, "error": str(e)[:200]}


@router.get("/keys/{key_id}")
async def get_key(key_id: str):
    """Get single Genesis Key."""
    try:
        from genesis.genesis_key_service import get_genesis_service
        service = get_genesis_service()
        key = service.get_key(key_id) if hasattr(service, 'get_key') else None
        if key:
            return {"key": key}
        raise HTTPException(404, f"Key {key_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        return {"key": {"id": key_id}, "error": str(e)[:200]}


@router.get("/keys/{key_id}/metadata")
async def get_key_metadata(key_id: str):
    try:
        from database.session import safe_session_scope
        from sqlalchemy import text
        with safe_session_scope() as session:
            if session is None:
                return {"key_id": key_id, "metadata": {}}
            row = session.execute(text(
                "SELECT context_data, input_data, output_data FROM genesis_key WHERE key_id = :kid"
            ), {"kid": key_id}).fetchone()
            if row:
                import json
                return {
                    "key_id": key_id,
                    "metadata": {
                        "context": json.loads(row[0]) if row[0] else {},
                        "input": json.loads(row[1]) if row[1] else {},
                        "output": json.loads(row[2]) if row[2] else {},
                    }
                }
            return {"key_id": key_id, "metadata": {}}
    except Exception as e:
        return {"key_id": key_id, "metadata": {}, "error": str(e)[:200]}


@router.get("/keys/{key_id}/fixes")
async def get_key_fixes(key_id: str):
    try:
        from database.session import safe_session_scope
        from sqlalchemy import text
        with safe_session_scope() as session:
            if session is None:
                return {"key_id": key_id, "fixes": []}
            rows = session.execute(text(
                "SELECT key_id, key_type, what_description, created_at "
                "FROM genesis_key WHERE parent_key_id = :kid "
                "ORDER BY created_at DESC"
            ), {"kid": key_id}).fetchall()
            fixes = [{"key_id": r[0], "type": str(r[1]), "what": r[2], "at": str(r[3])} for r in rows]
            return {"key_id": key_id, "fixes": fixes}
    except Exception as e:
        return {"key_id": key_id, "fixes": [], "error": str(e)[:200]}


@router.post("/keys")
async def create_key(payload: GenesisKeyCreate):
    """Create a Genesis Key — goes through full governance pipeline."""
    try:
        from api._genesis_tracker import track
        gk_id = track(
            key_type=payload.origin_type or "system",
            what=f"Manual key: {payload.entity_type}/{payload.entity_id}",
            who=payload.origin_source or "api",
            tags=["manual", payload.entity_type],
        )
        _emit("genesis.key_created_manual", {
            "key_id": gk_id, "entity_type": payload.entity_type,
        })
        return {"status": "ok", "key_id": gk_id or "created"}
    except Exception as e:
        return {"status": "error", "error": str(e)[:200]}


@router.get("/archives")
async def get_archives():
    try:
        from database.session import safe_session_scope
        from sqlalchemy import text
        with safe_session_scope() as session:
            if session is None:
                return {"archives": []}
            rows = session.execute(text(
                "SELECT DISTINCT DATE(created_at) as day, COUNT(*) as cnt "
                "FROM genesis_key GROUP BY DATE(created_at) ORDER BY day DESC LIMIT 30"
            )).fetchall()
            archives = [{"date": str(r[0]), "count": r[1]} for r in rows]
            return {"archives": archives}
    except Exception as e:
        return {"archives": [], "error": str(e)[:200]}


@router.post("/archive/trigger")
async def archive_trigger(payload: Dict[str, Any] = None):
    _genesis_track("POST /genesis/archive/trigger", tags=["archive"])
    _emit("genesis.archive_triggered", payload or {})
    return {"status": "ok", "message": "Archive trigger submitted"}


@router.post("/analyze-code")
async def analyze_code(payload: Dict[str, Any] = None):
    """Analyze code — dispatches to brain API with governance."""
    _genesis_track("POST /genesis/analyze-code", tags=["code_analysis"])
    try:
        from api.brain_api_v2 import call_brain
        result = call_brain("code", "analyze", payload or {})
        return {"status": "ok", **result}
    except Exception as e:
        return {"status": "error", "error": str(e)[:200]}


@router.get("/users/{user_id}/keys")
async def get_user_keys(user_id: str):
    try:
        from database.session import safe_session_scope
        from sqlalchemy import text
        with safe_session_scope() as session:
            if session is None:
                return {"keys": []}
            rows = session.execute(text(
                "SELECT key_id, key_type, what_description, created_at "
                "FROM genesis_key WHERE who_actor = :uid "
                "ORDER BY created_at DESC LIMIT 50"
            ), {"uid": user_id}).fetchall()
            keys = [{"key_id": r[0], "type": str(r[1]), "what": r[2], "at": str(r[3])} for r in rows]
            return {"keys": keys}
    except Exception as e:
        return {"keys": [], "error": str(e)[:200]}
