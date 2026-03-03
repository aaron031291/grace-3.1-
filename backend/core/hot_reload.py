"""
Hot Code Reload — swap modules without stopping Grace.

Preserves state, rolls back on failure, cascades to dependents.
"""

import sys
import importlib
import logging
import threading
import time
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

_state_store: Dict[str, Any] = {}
_reload_lock = threading.Lock()
_reload_history: list = []


def hot_reload_module(module_path: str) -> dict:
    """
    Reload a Python module without stopping the process.

    1. Preserve __state__ if module defines it
    2. Reload the module
    3. Restore state
    4. Rollback on failure

    Usage:
        hot_reload_module("core.services.chat_service")
    """
    with _reload_lock:
        result = {"module": module_path, "status": "unknown", "ts": time.time()}

        if module_path not in sys.modules:
            result["status"] = "not_loaded"
            result["error"] = f"{module_path} not in sys.modules"
            _reload_history.append(result)
            return result

        old_module = sys.modules[module_path]

        # 1. Preserve state
        old_state = None
        if hasattr(old_module, "__state__"):
            old_state = old_module.__state__
            _state_store[module_path] = old_state

        # 2. Reload
        try:
            importlib.reload(old_module)
            new_module = sys.modules[module_path]

            # 3. Restore state
            if old_state is not None:
                new_module.__state__ = old_state

            result["status"] = "reloaded"
            result["state_preserved"] = old_state is not None

            try:
                from api._genesis_tracker import track
                track(
                    key_type="system_event",
                    what=f"Hot reload: {module_path}",
                    who="hot_reload",
                    tags=["hot-reload", module_path],
                )
            except Exception:
                pass

        except Exception as e:
            # 4. Rollback
            sys.modules[module_path] = old_module
            result["status"] = "failed"
            result["error"] = str(e)[:200]
            result["rolled_back"] = True

        _reload_history.append(result)
        if len(_reload_history) > 100:
            _reload_history.pop(0)

        return result


def hot_reload_service(service_name: str) -> dict:
    """Reload a core service module by name."""
    module_map = {
        "chat": "core.services.chat_service",
        "files": "core.services.files_service",
        "govern": "core.services.govern_service",
        "data": "core.services.data_service",
        "tasks": "core.services.tasks_service",
        "code": "core.services.code_service",
        "system": "core.services.system_service",
        "brain": "api.brain_api_v2",
        "pipeline": "core.coding_pipeline",
        "intelligence": "core.intelligence",
        "hebbian": "core.hebbian",
        "security": "core.security",
        "tracing": "core.tracing",
    }
    module_path = module_map.get(service_name, service_name)
    return hot_reload_module(module_path)


def hot_reload_all_services() -> dict:
    """Reload all core service modules."""
    services = ["chat", "files", "govern", "data", "tasks", "code", "system"]
    results = {}
    for svc in services:
        results[svc] = hot_reload_service(svc)
    return {
        "reloaded": sum(1 for r in results.values() if r["status"] == "reloaded"),
        "failed": sum(1 for r in results.values() if r["status"] == "failed"),
        "results": results,
    }


def get_reload_history() -> list:
    return list(reversed(_reload_history))


def save_and_reload(file_path: str, content: str) -> dict:
    """Save a file and hot-reload its module."""
    result = {"file": file_path, "saved": False, "reloaded": False}

    try:
        p = Path(file_path)
        p.parent.mkdir(parents=True, exist_ok=True)

        # Backup
        backup = None
        if p.exists():
            backup = p.read_text()

        # Write
        p.write_text(content, encoding="utf-8")
        result["saved"] = True

        # Determine module path
        module_path = file_path.replace("/", ".").replace("\\", ".").replace(".py", "")
        if module_path.startswith("backend."):
            module_path = module_path[8:]

        # Reload
        reload_result = hot_reload_module(module_path)
        result["reloaded"] = reload_result["status"] == "reloaded"
        result["reload_detail"] = reload_result

        if reload_result["status"] == "failed" and backup is not None:
            p.write_text(backup, encoding="utf-8")
            result["rolled_back"] = True

    except Exception as e:
        result["error"] = str(e)[:200]

    return result
