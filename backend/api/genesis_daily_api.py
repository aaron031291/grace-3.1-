"""
Genesis Daily API — serves Governance tab Genesis Keys panel.

Endpoints:
  GET /api/genesis-daily/folders?days=60  → { folders: [{ date, label, key_count, ... }] }
  GET /api/genesis-daily/stats            → { total_keys, today_keys }
  GET /api/genesis-daily/folder/{date}    → { demographics, by_type: [{ type, label, icon, keys }] }
  GET /api/genesis-daily/key/{key_id}     → single key detail for right panel
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone, timedelta
from sqlalchemy import func
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/genesis-daily", tags=["Genesis (Governance)"])


def _type_icon(key_type: str) -> str:
    icons = {
        "error": "❌", "api_request": "🌐", "system_event": "⚙️", "code_change": "📝",
        "file_operation": "📄", "ai_response": "🧠", "learning_complete": "📚",
        "user_upload": "👤", "file_ingestion": "📥", "librarian_action": "📚",
    }
    return icons.get(key_type.lower().replace(" ", "_"), "🔑")


@router.get("/folders")
async def get_folders(days: int = 60):
    """List daily folders (dates with genesis keys) for the Governance Genesis Keys panel."""
    try:
        from database.session import session_scope
        from models.genesis_key_models import GenesisKey

        since = datetime.now(timezone.utc) - timedelta(days=days)
        with session_scope() as s:
            try:
                q = s.query(
                    func.date(GenesisKey.when_timestamp).label("date"),
                    func.count(GenesisKey.id).label("key_count"),
                ).filter(GenesisKey.when_timestamp >= since).group_by(func.date(GenesisKey.when_timestamp)).order_by(func.date(GenesisKey.when_timestamp).desc())
                rows = q.all()
            except Exception:
                keys = s.query(GenesisKey.when_timestamp, GenesisKey.is_error).filter(GenesisKey.when_timestamp >= since).limit(15000).all()
                by_date = defaultdict(lambda: {"key_count": 0, "error_count": 0})
                for row in keys:
                    ts = row[0] if hasattr(row, "__getitem__") else row.when_timestamp
                    is_err = row[1] if hasattr(row, "__getitem__") and len(row) > 1 else getattr(row, "is_error", False)
                    if ts:
                        d = ts.date() if hasattr(ts, "date") else str(ts)[:10]
                        by_date[d]["key_count"] += 1
                        if is_err:
                            by_date[d]["error_count"] += 1
                return {"folders": [_folder_item({"date": d, "key_count": v["key_count"], "error_count": v["error_count"]}) for d, v in sorted(by_date.items(), key=lambda x: str(x[0]), reverse=True)]}

            error_counts = {}
            try:
                err_q = s.query(func.date(GenesisKey.when_timestamp).label("date"), func.count(GenesisKey.id).label("c")).filter(GenesisKey.when_timestamp >= since, GenesisKey.is_error == True).group_by(func.date(GenesisKey.when_timestamp))
                for row in err_q.all():
                    error_counts[str(row.date)] = row.c
            except Exception:
                pass

            folders = []
            for row in rows:
                d = str(row.date)
                kc = row.key_count
                folders.append(_folder_item({"date": d, "key_count": kc, "error_count": error_counts.get(d, 0)}))
            return {"folders": folders}
    except Exception as e:
        logger.exception("genesis-daily/folders: %s", e)
        return {"folders": []}


def _folder_item(r) -> dict:
    d = r.get("date") or getattr(r, "date", None)
    if hasattr(d, "isoformat"):
        d = d.isoformat()[:10]
    d = str(d)[:10]
    kc = r.get("key_count", getattr(r, "key_count", 0))
    ec = r.get("error_count", getattr(r, "error_count", 0))
    try:
        dt = datetime.strptime(d, "%Y-%m-%d")
        label = dt.strftime("%b %d, %Y")
    except Exception:
        label = d
    return {"date": d, "label": label, "key_count": kc, "error_count": ec}


@router.get("/stats")
async def get_stats():
    """Total and today key counts for Governance Genesis Keys panel."""
    try:
        from database.session import session_scope
        from models.genesis_key_models import GenesisKey
        from sqlalchemy import func

        with session_scope() as s:
            total = s.query(func.count(GenesisKey.id)).scalar() or 0
            today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            today = s.query(func.count(GenesisKey.id)).filter(GenesisKey.when_timestamp >= today_start).scalar() or 0
            return {"total_keys": total, "today_keys": today}
    except Exception as e:
        logger.exception("genesis-daily/stats: %s", e)
        return {"total_keys": 0, "today_keys": 0}


@router.get("/folder/{date}")
async def get_folder(date: str):
    """Keys for a single day, grouped by type, for Governance Genesis Keys panel."""
    try:
        from database.session import session_scope
        from models.genesis_key_models import GenesisKey
        from sqlalchemy import func

        try:
            day_start = datetime.strptime(date, "%Y-%m-%d")
            day_end = day_start + timedelta(days=1)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date, use YYYY-MM-DD")

        with session_scope() as s:
            keys = (
                s.query(GenesisKey)
                .filter(GenesisKey.when_timestamp >= day_start, GenesisKey.when_timestamp < day_end)
                .order_by(GenesisKey.when_timestamp.desc())
                .all()
            )
        if not keys:
            return {"demographics": {"total_keys": 0, "total_errors": 0, "total_fixes": 0, "unique_actors": 0, "unique_files": 0}, "by_type": []}

        by_type = defaultdict(list)
        actors = set()
        files = set()
        errors = 0
        fixes = 0
        for k in keys:
            t = str(k.key_type.value) if hasattr(k.key_type, "value") else str(k.key_type)
            by_type[t].append(_key_summary(k))
            if k.who_actor:
                actors.add(k.who_actor)
            if k.file_path:
                files.add(k.file_path)
            if k.is_error:
                errors += 1
            if k.fix_applied:
                fixes += 1

        type_list = []
        for t, key_list in sorted(by_type.items(), key=lambda x: -len(x[1])):
            type_errors = sum(1 for k in key_list if k.get("is_error"))
            type_list.append({
                "type": t,
                "label": t.replace("_", " ").title(),
                "icon": _type_icon(t),
                "count": len(key_list),
                "error_count": type_errors,
                "keys": key_list,
            })

        return {
            "demographics": {
                "total_keys": len(keys),
                "total_errors": errors,
                "total_fixes": fixes,
                "unique_actors": len(actors),
                "unique_files": len(files),
            },
            "by_type": type_list,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("genesis-daily/folder: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


def _key_summary(k) -> dict:
    return {
        "key_id": k.key_id,
        "what": (k.what_description or "")[:200],
        "timestamp": k.when_timestamp.isoformat() if k.when_timestamp else None,
        "file_path": k.file_path,
        "is_error": bool(k.is_error),
        "fix_applied": bool(k.fix_applied),
    }


@router.get("/key/{key_id}")
async def get_key(key_id: str):
    """Single Genesis key detail for Governance Genesis Keys right panel."""
    try:
        from database.session import session_scope
        from models.genesis_key_models import GenesisKey

        with session_scope() as s:
            k = s.query(GenesisKey).filter(GenesisKey.key_id == key_id).first()
        if not k:
            raise HTTPException(status_code=404, detail="Genesis key not found")

        return {
            "key_id": k.key_id,
            "key_type": str(k.key_type.value) if hasattr(k.key_type, "value") else str(k.key_type),
            "what": k.what_description,
            "who": k.who_actor,
            "when": k.when_timestamp.isoformat() if k.when_timestamp else None,
            "where": k.where_location,
            "why": k.why_reason,
            "how": k.how_method,
            "file_path": k.file_path,
            "line_number": k.line_number,
            "function_name": k.function_name,
            "is_error": k.is_error,
            "error_type": k.error_type,
            "error_message": (k.error_message or "")[:500],
            "fix_applied": k.fix_applied,
            "status": str(k.status.value) if hasattr(k.status, "value") else str(k.status),
            "tags": k.tags or [],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("genesis-daily/key: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
