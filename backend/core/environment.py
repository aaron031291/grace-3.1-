"""
Environment Manager — select which project/workspace all output goes to.

Every action in Grace (Dev tab, chat, code generation, file writes)
routes to the ACTIVE environment. Switch environment = switch where
data lands.

Environments map to project folders:
  "microsoft" → data/projects/microsoft/
  "apple" → data/projects/apple/
  "grace" → data/projects/grace-ai/ (locked from delete)

Models run independently — if Kimi is down, Opus/Qwen/DeepSeek still work.
"""

import threading
import logging
from typing import Dict, Optional
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

_active_env: Dict[str, str] = {"default": "grace-ai"}
_env_lock = threading.Lock()

PROJECTS_DIR = Path(__file__).parent.parent / "data" / "projects"


def set_environment(env_name: str, user_id: str = "default") -> dict:
    """Set the active environment/project for a user."""
    with _env_lock:
        _active_env[user_id] = env_name

    project_dir = PROJECTS_DIR / env_name
    if not project_dir.exists():
        project_dir.mkdir(parents=True)
        (project_dir / "frontend").mkdir(exist_ok=True)
        (project_dir / "backend").mkdir(exist_ok=True)
        (project_dir / "docs").mkdir(exist_ok=True)
        (project_dir / "tests").mkdir(exist_ok=True)

    try:
        from api._genesis_tracker import track
        track(key_type="system_event", what=f"Environment switched to: {env_name}",
              who="environment_manager", tags=["environment", env_name])
    except Exception:
        pass

    return {"environment": env_name, "path": str(project_dir), "created": True}


def get_environment(user_id: str = "default") -> str:
    """Get the active environment for a user."""
    with _env_lock:
        return _active_env.get(user_id, "grace-ai")


def get_environment_path(user_id: str = "default") -> Path:
    """Get the file system path for the active environment."""
    env = get_environment(user_id)
    return PROJECTS_DIR / env


def list_environments() -> list:
    """List all available environments."""
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    envs = []
    for d in sorted(PROJECTS_DIR.iterdir()):
        if d.is_dir() and not d.name.startswith("."):
            file_count = sum(1 for _ in d.rglob("*") if _.is_file())
            envs.append({
                "name": d.name,
                "path": str(d),
                "file_count": file_count,
                "locked": d.name == "grace-ai",
                "active": d.name == get_environment(),
            })
    return envs


def route_file_write(relative_path: str, content: str, source: str = "dev_tab",
                     user_id: str = "default") -> dict:
    """Write a file to the ACTIVE environment's project folder."""
    env_path = get_environment_path(user_id)
    target = env_path / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")

    try:
        from core.workspace_bridge import write_file
        write_file(str(target), content, source)
        # Log lineage to domain folder (codebase → governance layer)
        try:
            from core.domain_lineage_bridge import log_lineage
            domain = get_environment(user_id)
            log_lineage(
                domain=domain,
                file_path=relative_path,
                operation_type="modify",
                source=source,
                genesis_key_id=None,
                user_id=user_id,
            )
        except Exception:
            pass
    except Exception:
        pass

    return {
        "saved": True,
        "environment": get_environment(user_id),
        "path": str(target),
        "relative": relative_path,
    }
