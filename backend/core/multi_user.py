"""
Multi-User System — lightweight IDs, activity tracking, team summaries.

Every user gets a lightweight ID on signup.
Activity tracked per-person, per-project.
Daily summaries: individual + team.
Hot-swap containers with auto-save.
"""

import json
import hashlib
import time
import threading
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
USERS_DIR = DATA_DIR / "users"

_activity_log: List[dict] = []
_activity_lock = threading.Lock()
_active_sessions: Dict[str, dict] = {}


# ═══════════════════════════════════════════════════════════════════
#  LIGHTWEIGHT USER IDS
# ═══════════════════════════════════════════════════════════════════

def create_user(email: str, name: str = "") -> dict:
    """Create a user with a lightweight ID."""
    USERS_DIR.mkdir(parents=True, exist_ok=True)
    user_id = f"U-{hashlib.sha256(email.encode()).hexdigest()[:8]}"

    user = {
        "id": user_id,
        "email": email,
        "name": name or email.split("@")[0],
        "created_at": datetime.utcnow().isoformat(),
        "active_project": None,
        "projects": [],
    }

    user_file = USERS_DIR / f"{user_id}.json"
    if not user_file.exists():
        user_file.write_text(json.dumps(user, indent=2))

    return user


def get_user(user_id: str) -> dict:
    user_file = USERS_DIR / f"{user_id}.json"
    if user_file.exists():
        return json.loads(user_file.read_text())
    return {"error": "User not found"}


def list_users() -> list:
    USERS_DIR.mkdir(parents=True, exist_ok=True)
    users = []
    for f in USERS_DIR.glob("U-*.json"):
        try:
            users.append(json.loads(f.read_text()))
        except Exception:
            pass
    return users


# ═══════════════════════════════════════════════════════════════════
#  ACTIVITY TRACKING
# ═══════════════════════════════════════════════════════════════════

def log_activity(user_id: str, action: str, project_id: str = "",
                 detail: str = "", data: dict = None):
    """Log user activity."""
    entry = {
        "user_id": user_id,
        "action": action,
        "project_id": project_id,
        "detail": detail[:200],
        "data": data or {},
        "ts": datetime.utcnow().isoformat(),
    }
    with _activity_lock:
        _activity_log.append(entry)
        if len(_activity_log) > 10000:
            _activity_log.pop(0)

    try:
        from core.tracing import light_track
        light_track("user_input", f"{user_id}: {action} in {project_id}",
                     "multi_user", ["activity", user_id, project_id])
    except Exception:
        pass


def get_user_activity(user_id: str, hours: int = 24) -> list:
    """Get activity for a specific user."""
    cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
    with _activity_lock:
        return [a for a in _activity_log
                if a["user_id"] == user_id and a["ts"] >= cutoff]


def get_project_activity(project_id: str, hours: int = 24) -> list:
    """Get activity for a specific project."""
    cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
    with _activity_lock:
        return [a for a in _activity_log
                if a["project_id"] == project_id and a["ts"] >= cutoff]


# ═══════════════════════════════════════════════════════════════════
#  DAILY SUMMARIES
# ═══════════════════════════════════════════════════════════════════

def generate_daily_summary(project_id: str = "", hours: int = 24) -> dict:
    """Generate daily summary: per-person + team."""
    cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()

    with _activity_lock:
        if project_id:
            activities = [a for a in _activity_log
                          if a["project_id"] == project_id and a["ts"] >= cutoff]
        else:
            activities = [a for a in _activity_log if a["ts"] >= cutoff]

    # Per-person breakdown
    by_user = defaultdict(list)
    for a in activities:
        by_user[a["user_id"]].append(a)

    individual = {}
    for uid, acts in by_user.items():
        individual[uid] = {
            "total_actions": len(acts),
            "actions": defaultdict(int),
            "projects": list(set(a["project_id"] for a in acts if a["project_id"])),
        }
        for a in acts:
            individual[uid]["actions"][a["action"]] += 1
        individual[uid]["actions"] = dict(individual[uid]["actions"])

    # Team summary
    team = {
        "total_actions": len(activities),
        "total_users": len(by_user),
        "projects_touched": list(set(a["project_id"] for a in activities if a["project_id"])),
        "action_distribution": dict(defaultdict(int, {a["action"]: 0 for a in activities})),
    }
    for a in activities:
        team["action_distribution"][a["action"]] = team["action_distribution"].get(a["action"], 0) + 1

    return {
        "period_hours": hours,
        "individual": individual,
        "team": team,
        "generated_at": datetime.utcnow().isoformat(),
    }


# ═══════════════════════════════════════════════════════════════════
#  HOT-SWAP SESSIONS
# ═══════════════════════════════════════════════════════════════════

def switch_project(user_id: str, new_project: str) -> dict:
    """Hot-swap to a different project. Auto-saves current state."""
    old_project = _active_sessions.get(user_id, {}).get("project")

    # Auto-save current context
    if old_project:
        _save_session(user_id, old_project)

    # Load new context
    _active_sessions[user_id] = {
        "project": new_project,
        "switched_at": datetime.utcnow().isoformat(),
        "previous": old_project,
    }

    # Set environment
    try:
        from core.environment import set_environment
        set_environment(new_project, user_id)
    except Exception:
        pass

    log_activity(user_id, "switch_project", new_project,
                 f"Switched from {old_project or 'none'} to {new_project}")

    return {
        "user_id": user_id,
        "project": new_project,
        "previous": old_project,
        "auto_saved": old_project is not None,
    }


def _save_session(user_id: str, project_id: str):
    """Auto-save session state."""
    session_dir = DATA_DIR / "sessions" / user_id
    session_dir.mkdir(parents=True, exist_ok=True)
    session_file = session_dir / f"{project_id}.json"
    session_file.write_text(json.dumps({
        "project_id": project_id,
        "saved_at": datetime.utcnow().isoformat(),
        "user_id": user_id,
    }, indent=2))


def get_active_session(user_id: str) -> dict:
    return _active_sessions.get(user_id, {"project": None})
