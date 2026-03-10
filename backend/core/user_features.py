"""
User-level features — undo/redo, profiles, notifications, permissions.
"""

import json
import threading
import time
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"


# ═══════════════════════════════════════════════════════════════════
#  UNDO/REDO STACK — per file, stores last 50 versions
# ═══════════════════════════════════════════════════════════════════

_undo_stacks: Dict[str, list] = defaultdict(list)
_redo_stacks: Dict[str, list] = defaultdict(list)
MAX_UNDO = 50


def push_undo(file_path: str, content: str):
    """Save current content before a change."""
    stack = _undo_stacks[file_path]
    stack.append({"content": content, "ts": time.time()})
    if len(stack) > MAX_UNDO:
        stack.pop(0)
    _redo_stacks[file_path].clear()


def undo(file_path: str) -> Optional[dict]:
    """Undo last change. Returns previous content."""
    stack = _undo_stacks[file_path]
    if not stack:
        return None
    entry = stack.pop()
    # Push current to redo
    try:
        current = Path(file_path).read_text(errors="ignore")
        _redo_stacks[file_path].append({"content": current, "ts": time.time()})
    except Exception:
        pass
    # Restore
    try:
        Path(file_path).write_text(entry["content"], encoding="utf-8")
    except Exception:
        pass
    return entry


def redo(file_path: str) -> Optional[dict]:
    """Redo last undone change."""
    stack = _redo_stacks[file_path]
    if not stack:
        return None
    entry = stack.pop()
    try:
        current = Path(file_path).read_text(errors="ignore")
        _undo_stacks[file_path].append({"content": current, "ts": time.time()})
    except Exception:
        pass
    try:
        Path(file_path).write_text(entry["content"], encoding="utf-8")
    except Exception:
        pass
    return entry


# ═══════════════════════════════════════════════════════════════════
#  USER PROFILES — preferences per user
# ═══════════════════════════════════════════════════════════════════

PROFILES_PATH = DATA_DIR / "user_profiles.json"


def _load_profiles() -> dict:
    PROFILES_PATH.parent.mkdir(parents=True, exist_ok=True)
    if PROFILES_PATH.exists():
        try:
            return json.loads(PROFILES_PATH.read_text())
        except Exception:
            pass
    return {}


def _save_profiles(data: dict):
    PROFILES_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROFILES_PATH.write_text(json.dumps(data, indent=2, default=str))


def get_profile(user_id: str = "default") -> dict:
    profiles = _load_profiles()
    return profiles.get(user_id, {
        "user_id": user_id,
        "theme": "dark",
        "default_model": "consensus",
        "sidebar_width": 200,
        "detail_width": 320,
        "keyboard_shortcuts": True,
        "notifications": True,
        "auto_save": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })


def update_profile(user_id: str, updates: dict) -> dict:
    profiles = _load_profiles()
    profile = profiles.get(user_id, get_profile(user_id))
    profile.update(updates)
    profile["updated_at"] = datetime.now(timezone.utc).isoformat()
    profiles[user_id] = profile
    _save_profiles(profiles)
    return profile


# ═══════════════════════════════════════════════════════════════════
#  NOTIFICATIONS — in-app notification system
# ═══════════════════════════════════════════════════════════════════

_notifications: List[dict] = []
_notif_lock = threading.Lock()


def notify(title: str, message: str, type: str = "info", source: str = "system"):
    """Create an in-app notification."""
    notif = {
        "id": int(time.time() * 1000),
        "title": title,
        "message": message,
        "type": type,  # info, success, warning, error
        "source": source,
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    with _notif_lock:
        _notifications.append(notif)
        if len(_notifications) > 200:
            _notifications.pop(0)
    return notif


def get_notifications(unread_only: bool = False) -> list:
    with _notif_lock:
        if unread_only:
            return [n for n in _notifications if not n["read"]]
        return list(reversed(_notifications[-50:]))


def mark_read(notif_id: int):
    with _notif_lock:
        for n in _notifications:
            if n["id"] == notif_id:
                n["read"] = True
                return True
    return False


def clear_notifications():
    with _notif_lock:
        _notifications.clear()


# ═══════════════════════════════════════════════════════════════════
#  WORKSPACE PERMISSIONS — per-folder access control
# ═══════════════════════════════════════════════════════════════════

PERMISSIONS_PATH = DATA_DIR / "workspace_permissions.json"


def _load_permissions() -> dict:
    PERMISSIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if PERMISSIONS_PATH.exists():
        try:
            return json.loads(PERMISSIONS_PATH.read_text())
        except Exception:
            pass
    return {}


def _save_permissions(data: dict):
    PERMISSIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    PERMISSIONS_PATH.write_text(json.dumps(data, indent=2, default=str))


def set_permission(workspace: str, user_id: str, level: str = "read"):
    """Set permission: read, write, admin."""
    perms = _load_permissions()
    if workspace not in perms:
        perms[workspace] = {}
    perms[workspace][user_id] = {"level": level, "granted_at": datetime.now(timezone.utc).isoformat()}
    _save_permissions(perms)
    return {"workspace": workspace, "user": user_id, "level": level}


def check_permission(workspace: str, user_id: str, required: str = "read") -> bool:
    perms = _load_permissions()
    user_perms = perms.get(workspace, {}).get(user_id, {})
    level = user_perms.get("level", "none")
    levels = {"none": 0, "read": 1, "write": 2, "admin": 3}
    return levels.get(level, 0) >= levels.get(required, 0)


def get_workspace_permissions(workspace: str) -> dict:
    perms = _load_permissions()
    return perms.get(workspace, {})


# ═══════════════════════════════════════════════════════════════════
#  KEYBOARD SHORTCUTS
# ═══════════════════════════════════════════════════════════════════

SHORTCUTS = {
    "Ctrl+S / Cmd+S": "Save current file + hot reload",
    "Ctrl+K / Cmd+K": "Open refactor prompt (Cmd+K style)",
    "Ctrl+P / Cmd+P": "Open fuzzy search across all workspaces",
    "Ctrl+Z / Cmd+Z": "Undo last change",
    "Ctrl+Shift+Z": "Redo",
    "Tab": "Accept ghost-text completion",
    "Escape": "Dismiss ghost-text / close panels",
    "Ctrl+/": "Toggle comment (in code editor)",
    "Ctrl+F": "Find in current file",
    "Ctrl+Shift+F": "Search across all files",
    "Ctrl+`": "Toggle terminal view",
    "Double-click": "Open action in full window",
    "Right-click": "Context menu with power actions",
}


def get_shortcuts() -> dict:
    return {"shortcuts": SHORTCUTS, "total": len(SHORTCUTS)}


# ═══════════════════════════════════════════════════════════════════
#  FUZZY SEARCH — across all workspaces
# ═══════════════════════════════════════════════════════════════════

def fuzzy_search(query: str, max_results: int = 20) -> list:
    """Search file names and content across all workspaces."""
    results = []
    query_lower = query.lower()

    search_dirs = [
        DATA_DIR / "projects",
        DATA_DIR / "governance_rules",
        Path(__file__).parent.parent / "core",
        Path(__file__).parent.parent / "api",
    ]

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        for f in search_dir.rglob("*"):
            if not f.is_file():
                continue
            if f.suffix in (".pyc", ".pyo"):
                continue

            # Name match
            if query_lower in f.name.lower():
                results.append({
                    "type": "file",
                    "name": f.name,
                    "path": str(f.relative_to(Path(__file__).parent.parent)),
                    "match": "filename",
                })

            # Content match (only text files, first 5000 chars)
            if len(results) < max_results and f.suffix in (".py", ".js", ".ts", ".jsx", ".tsx", ".json", ".md", ".txt", ".yaml", ".yml"):
                try:
                    content = f.read_text(errors="ignore")[:5000]
                    if query_lower in content.lower():
                        line_num = next((i+1 for i, line in enumerate(content.split("\n")) if query_lower in line.lower()), 0)
                        results.append({
                            "type": "content",
                            "name": f.name,
                            "path": str(f.relative_to(Path(__file__).parent.parent)),
                            "match": "content",
                            "line": line_num,
                        })
                except Exception:
                    pass

            if len(results) >= max_results:
                break

    return results[:max_results]
