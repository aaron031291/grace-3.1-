"""Tasks domain service — scheduling, time sense."""
from pathlib import Path
import json, uuid, logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
SCHED_PATH = Path(__file__).parent.parent.parent / "data" / "scheduled_tasks.json"

def _load_scheduled():
    SCHED_PATH.parent.mkdir(parents=True, exist_ok=True)
    if SCHED_PATH.exists():
        try: return json.loads(SCHED_PATH.read_text())
        except Exception: pass
    return []

def _save_scheduled(data):
    SCHED_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCHED_PATH.write_text(json.dumps(data, indent=2, default=str))

def live_activity():
    try:
        from database.session import session_scope
        from sqlalchemy import text
        with session_scope() as db:
            cutoff = (datetime.utcnow() - timedelta(minutes=5)).isoformat()
            rows = db.execute(text(
                "SELECT key_type, what_description, who_actor, when_timestamp "
                "FROM genesis_key WHERE when_timestamp >= :c ORDER BY when_timestamp DESC LIMIT 20"
            ), {"c": cutoff}).fetchall()
            return {"activities": [dict(r._mapping) for r in rows],
                    "timestamp": datetime.utcnow().isoformat()}
    except Exception:
        return {"activities": [], "timestamp": datetime.utcnow().isoformat()}

def task_history(limit=40):
    try:
        from database.session import session_scope
        from sqlalchemy import text
        with session_scope() as db:
            cutoff = (datetime.utcnow() - timedelta(hours=24)).isoformat()
            rows = db.execute(text(
                "SELECT key_type, what_description, who_actor, when_timestamp "
                "FROM genesis_key WHERE when_timestamp >= :c ORDER BY when_timestamp DESC LIMIT :l"
            ), {"c": cutoff, "l": int(limit)}).fetchall()
            return {"history": [dict(r._mapping) for r in rows]}
    except Exception:
        return {"history": []}

def submit_task(payload):
    try:
        from api._genesis_tracker import track
        gk = track(key_type="system_event",
                    what=f"Task: {payload.get('title', '')}",
                    who="tasks_service", tags=["task", "submitted"])
        return {"submitted": True, "genesis_key_id": gk}
    except Exception:
        return {"submitted": True}

def get_scheduled():
    tasks = _load_scheduled()
    now = datetime.utcnow().isoformat()
    for t in tasks:
        if t.get("status") == "scheduled" and t.get("scheduled_for", "") <= now:
            t["status"] = "overdue"
    return {"tasks": tasks}

def schedule_task(payload):
    tasks = _load_scheduled()
    task = {"id": f"sched-{uuid.uuid4().hex[:8]}",
            "title": payload.get("title", ""),
            "scheduled_for": payload.get("scheduled_for", ""),
            "priority": payload.get("priority", "medium"),
            "status": "scheduled",
            "created_at": datetime.utcnow().isoformat()}
    tasks.append(task)
    _save_scheduled(tasks)
    return task

def delete_scheduled(task_id):
    tasks = _load_scheduled()
    filtered = [t for t in tasks if t.get("id") != task_id]
    _save_scheduled(filtered)
    return {"deleted": True}

def time_sense():
    from cognitive.time_sense import TimeSense
    return TimeSense.get_context()

def planner_sessions():
    try:
        from database.session import session_scope
        return {"sessions": []}
    except Exception:
        return {"sessions": []}
