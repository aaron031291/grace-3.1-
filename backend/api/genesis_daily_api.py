"""
Genesis Keys Daily Log API

Organises Genesis Keys into 24-hour folders:
- Each day gets a dated folder showing all keys created
- Keys are grouped by type with demographic breakdown
- Each key is clickable to see the code/context it connects to
- Librarian organises the daily log by key type and purpose
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import Counter
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/genesis-daily", tags=["Genesis Daily Log"])


def _get_db():
    from database.session import SessionLocal
    if SessionLocal is None:
        from database.session import initialize_session_factory
        initialize_session_factory()
        from database.session import SessionLocal as SL
        return SL()
    return SessionLocal()


def _key_to_dict(key) -> Dict[str, Any]:
    """Convert a GenesisKey ORM object to a serialisable dict."""
    return {
        "id": key.id,
        "key_id": key.key_id,
        "key_type": key.key_type.value if hasattr(key.key_type, 'value') else str(key.key_type),
        "status": key.status.value if hasattr(key.status, 'value') else str(key.status),
        "what": key.what_description,
        "where": key.where_location,
        "who": key.who_actor,
        "why": key.why_reason,
        "how": key.how_method,
        "timestamp": key.when_timestamp.isoformat() if key.when_timestamp else None,
        "file_path": key.file_path,
        "line_number": key.line_number,
        "function_name": key.function_name,
        "code_before": key.code_before[:500] if key.code_before else None,
        "code_after": key.code_after[:500] if key.code_after else None,
        "is_error": key.is_error,
        "error_type": key.error_type,
        "error_message": key.error_message,
        "tags": key.tags or [],
        "input_data": key.input_data,
        "output_data": key.output_data,
        "context_data": key.context_data,
        "parent_key_id": key.parent_key_id,
        "commit_sha": key.commit_sha,
        "branch_name": key.branch_name,
        "has_fix": key.has_fix_suggestion,
        "fix_applied": key.fix_applied,
    }


# ---------------------------------------------------------------------------
# 1. Daily folders — list all available date folders
# ---------------------------------------------------------------------------

@router.get("/folders")
async def list_daily_folders(days: int = 30):
    """
    List all daily folders with key counts.
    Each folder represents a 24-hour window of Genesis Key activity.
    """
    from models.genesis_key_models import GenesisKey
    from sqlalchemy import func, cast, Date
    db = _get_db()
    try:
        cutoff = datetime.utcnow() - timedelta(days=days)
        rows = (
            db.query(
                cast(GenesisKey.when_timestamp, Date).label("day"),
                func.count(GenesisKey.id).label("count"),
                func.sum(func.cast(GenesisKey.is_error, db.bind.dialect.name != 'sqlite' and 'INTEGER' or 'INTEGER')).label("errors"),
            )
            .filter(GenesisKey.when_timestamp >= cutoff)
            .group_by(cast(GenesisKey.when_timestamp, Date))
            .order_by(cast(GenesisKey.when_timestamp, Date).desc())
            .all()
        )

        folders = []
        for row in rows:
            day = row[0]
            day_str = day.isoformat() if hasattr(day, 'isoformat') else str(day)
            folders.append({
                "date": day_str,
                "label": _format_folder_name(day),
                "key_count": row[1],
                "error_count": row[2] or 0,
            })

        return {"total_folders": len(folders), "folders": folders}
    except Exception as e:
        logger.error(f"Failed to list daily folders: {e}")
        return {"total_folders": 0, "folders": [], "note": str(e)}
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 2. Single day — all keys for a 24-hour window, organised by type
# ---------------------------------------------------------------------------

@router.get("/folder/{date}")
async def get_daily_folder(date: str):
    """
    Get all Genesis Keys for a specific date, organised by type.
    The librarian groups them by key type with a demographic breakdown.
    """
    from models.genesis_key_models import GenesisKey
    db = _get_db()
    try:
        try:
            day = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

        day_start = datetime.combine(day, datetime.min.time())
        day_end = day_start + timedelta(days=1)

        keys = (
            db.query(GenesisKey)
            .filter(GenesisKey.when_timestamp >= day_start, GenesisKey.when_timestamp < day_end)
            .order_by(GenesisKey.when_timestamp.desc())
            .all()
        )

        all_keys = [_key_to_dict(k) for k in keys]

        by_type: Dict[str, list] = {}
        for kd in all_keys:
            kt = kd["key_type"]
            if kt not in by_type:
                by_type[kt] = []
            by_type[kt].append(kd)

        type_breakdown = []
        for kt, items in sorted(by_type.items(), key=lambda x: len(x[1]), reverse=True):
            type_breakdown.append({
                "type": kt,
                "label": _type_label(kt),
                "icon": _type_icon(kt),
                "count": len(items),
                "error_count": sum(1 for i in items if i["is_error"]),
                "keys": items,
            })

        actors = Counter(k["who"] for k in all_keys)
        files = Counter(k["file_path"] for k in all_keys if k["file_path"])
        error_types = Counter(k["error_type"] for k in all_keys if k["error_type"])

        demographics = {
            "total_keys": len(all_keys),
            "total_errors": sum(1 for k in all_keys if k["is_error"]),
            "total_fixes": sum(1 for k in all_keys if k["fix_applied"]),
            "unique_actors": len(actors),
            "top_actors": dict(actors.most_common(5)),
            "unique_files": len(files),
            "top_files": dict(files.most_common(5)),
            "top_error_types": dict(error_types.most_common(5)),
            "type_distribution": {kt: len(items) for kt, items in by_type.items()},
        }

        return {
            "date": date,
            "label": _format_folder_name(day),
            "demographics": demographics,
            "by_type": type_breakdown,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get daily folder: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 3. Single key detail — full context and connected code
# ---------------------------------------------------------------------------

@router.get("/key/{key_id}")
async def get_key_detail(key_id: str):
    """
    Get full detail for a single Genesis Key.
    Shows the code it connects to, input/output data, and full context.
    """
    from models.genesis_key_models import GenesisKey
    db = _get_db()
    try:
        key = db.query(GenesisKey).filter(
            (GenesisKey.key_id == key_id) | (GenesisKey.id == _try_int(key_id))
        ).first()
        if not key:
            raise HTTPException(status_code=404, detail="Genesis Key not found")

        result = _key_to_dict(key)

        if key.code_before:
            result["code_before"] = key.code_before
        if key.code_after:
            result["code_after"] = key.code_after

        if key.file_path:
            try:
                from api.world_model_api import _read_source_file
                source = _read_source_file(key.file_path)
                if not source.startswith("[Error"):
                    lines = source.split('\n')
                    if key.line_number and key.line_number > 0:
                        start = max(0, key.line_number - 10)
                        end = min(len(lines), key.line_number + 10)
                        result["source_context"] = {
                            "file_path": key.file_path,
                            "start_line": start + 1,
                            "end_line": end,
                            "lines": lines[start:end],
                            "highlight_line": key.line_number,
                        }
                    else:
                        result["source_context"] = {
                            "file_path": key.file_path,
                            "preview": source[:3000],
                            "total_lines": len(lines),
                        }
            except Exception:
                pass

        children = (
            db.query(GenesisKey)
            .filter(GenesisKey.parent_key_id == key.key_id)
            .order_by(GenesisKey.when_timestamp.asc())
            .limit(20)
            .all()
        )
        if children:
            result["child_keys"] = [
                {"key_id": c.key_id, "type": c.key_type.value if hasattr(c.key_type, 'value') else str(c.key_type),
                 "what": c.what_description, "timestamp": c.when_timestamp.isoformat() if c.when_timestamp else None}
                for c in children
            ]

        if key.parent_key_id:
            parent = db.query(GenesisKey).filter(GenesisKey.key_id == key.parent_key_id).first()
            if parent:
                result["parent_key"] = {
                    "key_id": parent.key_id,
                    "type": parent.key_type.value if hasattr(parent.key_type, 'value') else str(parent.key_type),
                    "what": parent.what_description,
                }

        if key.fix_suggestions:
            result["fix_suggestions"] = [
                {"id": fs.suggestion_id, "title": fs.title, "type": fs.suggestion_type,
                 "severity": fs.severity, "status": fs.status.value if hasattr(fs.status, 'value') else str(fs.status),
                 "confidence": fs.confidence, "fix_code": fs.fix_code[:500] if fs.fix_code else None}
                for fs in key.fix_suggestions
            ]

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 4. Overview stats
# ---------------------------------------------------------------------------

@router.get("/stats")
async def genesis_key_stats():
    """Overall Genesis Key statistics."""
    from models.genesis_key_models import GenesisKey
    from sqlalchemy import func
    db = _get_db()
    try:
        total = db.query(func.count(GenesisKey.id)).scalar() or 0
        errors = db.query(func.count(GenesisKey.id)).filter(GenesisKey.is_error == True).scalar() or 0
        today_start = datetime.combine(datetime.utcnow().date(), datetime.min.time())
        today_count = db.query(func.count(GenesisKey.id)).filter(GenesisKey.when_timestamp >= today_start).scalar() or 0

        by_type = dict(
            db.query(GenesisKey.key_type, func.count(GenesisKey.id))
            .group_by(GenesisKey.key_type).all()
        )
        type_dist = {}
        for kt, cnt in by_type.items():
            label = kt.value if hasattr(kt, 'value') else str(kt)
            type_dist[label] = cnt

        return {
            "total_keys": total,
            "total_errors": errors,
            "today_keys": today_count,
            "type_distribution": type_dist,
        }
    except Exception as e:
        return {"total_keys": 0, "today_keys": 0, "note": str(e)}
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _try_int(s):
    try:
        return int(s)
    except (ValueError, TypeError):
        return -1


def _format_folder_name(day) -> str:
    if hasattr(day, 'strftime'):
        return day.strftime("%A, %B %d, %Y")
    return str(day)


def _type_label(kt: str) -> str:
    labels = {
        "user_input": "User Inputs",
        "user_upload": "Uploads",
        "ai_response": "AI Responses",
        "ai_code_generation": "Code Generation",
        "coding_agent_action": "Coding Agent",
        "code_change": "Code Changes",
        "file_operation": "File Operations",
        "file_ingestion": "Ingestion",
        "api_request": "API Requests",
        "external_api_call": "External APIs",
        "web_fetch": "Web Fetches",
        "database_change": "Database Changes",
        "librarian_action": "Librarian Actions",
        "learning_complete": "Learning",
        "gap_identified": "Knowledge Gaps",
        "practice_outcome": "Practice Outcomes",
        "configuration": "Configuration",
        "system_event": "System Events",
        "error": "Errors",
        "fix": "Fixes",
        "rollback": "Rollbacks",
    }
    return labels.get(kt, kt.replace("_", " ").title())


def _type_icon(kt: str) -> str:
    icons = {
        "user_input": "💬", "user_upload": "📤", "ai_response": "🤖",
        "ai_code_generation": "⚡", "coding_agent_action": "🛠️",
        "code_change": "📝", "file_operation": "📁", "file_ingestion": "📥",
        "api_request": "🔗", "external_api_call": "🌐", "web_fetch": "🕸️",
        "database_change": "🗄️", "librarian_action": "📚",
        "learning_complete": "🎓", "gap_identified": "🔍", "practice_outcome": "🏋️",
        "configuration": "⚙️", "system_event": "🖥️",
        "error": "❌", "fix": "✅", "rollback": "↩️",
    }
    return icons.get(kt, "🔑")
