"""
Hot Code Reload — swap modules without stopping Grace.

Preserves state, rolls back on failure. Full hot-reload (config + code) via
POST /api/runtime/hot-reload or brain system/hot_reload_all.
Optional: set HOT_RELOAD_WATCH=1 to auto-reload when .py files are saved.
"""

import os
import sys
import importlib
import logging
import threading
import time
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Set HOT_RELOAD_WATCH=1 to start background watcher that reloads on .py save
WATCH_ENABLED = os.getenv("HOT_RELOAD_WATCH", "").strip().lower() in ("1", "true", "yes")

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
        "cognitive_pipeline": "cognitive.pipeline",
        "unified_memory": "cognitive.unified_memory",
        "intelligence": "core.intelligence",
        "hebbian": "core.hebbian",
        "security": "core.security",
        "tracing": "core.tracing",
        "model_updater": "cognitive.model_updater",
        "commit_batch": "core.commit_batch_trigger",
        "runtime_triggers": "api.runtime_triggers_api",
        "genesis_tracker": "api._genesis_tracker",
        "autonomous_loop": "api.autonomous_loop_api",
        "hot_reload": "core.hot_reload",
    }
    module_path = module_map.get(service_name, service_name)
    return hot_reload_module(module_path)


def hot_reload_all_services() -> dict:
    """Reload all core service modules so runtime updates apply without restart."""
    services = [
        "chat", "files", "govern", "data", "tasks", "code", "system",
        "brain", "cognitive_pipeline", "unified_memory",
        "model_updater", "commit_batch", "runtime_triggers", "genesis_tracker",
        "autonomous_loop",
    ]
    results = {}
    for svc in services:
        results[svc] = hot_reload_service(svc)
    return {
        "reloaded": sum(1 for r in results.values() if r["status"] == "reloaded"),
        "failed": sum(1 for r in results.values() if r["status"] == "failed"),
        "not_loaded": sum(1 for r in results.values() if r["status"] == "not_loaded"),
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


def _file_path_to_module(backend_root: Path, file_path: Path) -> Optional[str]:
    """Convert backend-relative .py path to importable module name."""
    try:
        rel = file_path.resolve().relative_to(backend_root)
        if rel.suffix != ".py" or rel.name == "__init__.py":
            return None
        parts = list(rel.parts[:-1]) + [rel.stem]
        return ".".join(parts)
    except (ValueError, IndexError):
        return None


_watch_stop = threading.Event()
_watch_started = False


def _reload_watcher_loop(backend_root: Path, interval: float = 2.0):
    """Background loop: when a .py file mtime changes, hot-reload that module."""
    last_mtimes: Dict[Path, float] = {}
    while not _watch_stop.is_set():
        try:
            for py in backend_root.rglob("*.py"):
                if "__pycache__" in str(py) or "venv" in str(py):
                    continue
                try:
                    mtime = py.stat().st_mtime
                except OSError:
                    continue
                prev = last_mtimes.get(py)
                last_mtimes[py] = mtime
                if prev is not None and mtime > prev:
                    mod = _file_path_to_module(backend_root, py)
                    if mod and mod in sys.modules and mod != "core.hot_reload":
                        hot_reload_module(mod)
                        logger.info("Hot-reload (watch): %s", mod)
        except Exception as e:
            logger.debug("Reload watcher: %s", e)
        _watch_stop.wait(timeout=interval)


def start_reload_watcher():
    """Start background file watcher for auto hot-reload on save (if HOT_RELOAD_WATCH=1)."""
    global _watch_started
    if not WATCH_ENABLED or _watch_started:
        return
    _watch_started = True
    backend_root = Path(__file__).resolve().parent.parent
    t = threading.Thread(
        target=_reload_watcher_loop,
        args=(backend_root,),
        daemon=True,
        name="hot_reload_watch",
    )
    t.start()
    logger.info("Hot-reload watcher started (backend=%s)", backend_root)


def stop_reload_watcher():
    """Signal hot-reload watcher to stop (for graceful shutdown)."""
    _watch_stop.set()
