"""
Workspace domain service Ã¢â‚¬â€ bridges dev tab, codebase, docs, and projects
through Grace's internal VCS + CI/CD platform.

Sync interface for the Brain API (matching all other brain services).
Connects to:
  - genesis.internal_vcs (version control)
  - genesis.internal_pipeline (CI/CD)
  - core.services.code_service (codebase/projects bridge)
  - api.docs_library_api (docs bridge)
  - genesis tracker (event tracking)
  - layer1 message bus (cross-system events)
"""

import asyncio
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run async coroutine from sync context (Brain API is sync dispatch)."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result(timeout=30)
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


def _track(key_type: str, what: str, workspace_id: str, **kw):
    try:
        from api._genesis_tracker import track
        track(key_type=key_type, what=what,
              who=f"workspace.{workspace_id}",
              tags=["workspace", workspace_id], **kw)
    except Exception as e:
        logger.warning("[WORKSPACE] non-critical: %s", e)


# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Workspace CRUD Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

def ws_list() -> dict:
    from genesis.internal_vcs import _list_workspaces_sync
    return {"workspaces": _list_workspaces_sync()}


def ws_create(p: dict) -> dict:
    from genesis.internal_vcs import _create_workspace_sync
    result = _create_workspace_sync(
        p["workspace_id"], p["name"], p["root_path"],
        p.get("owner_id"), p.get("description", ""), p.get("config"),
    )
    if result.get("status") == "created":
        _track("system_event", f"Workspace created: {p['workspace_id']}", p["workspace_id"])
    return result


# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ VCS operations Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

def ws_snapshot(p: dict) -> dict:
    from genesis.internal_vcs import get_vcs
    vcs = get_vcs(p["workspace_id"])
    result = vcs._snapshot_sync(
        p["file_path"], p["content"],
        p.get("message", ""), p.get("author", "grace"),
        p.get("branch_name"), p.get("genesis_key_id"),
    )
    if result.get("status") == "created":
        _track("code_change",
               f"VCS snapshot: {p['file_path']} v{result.get('version')}",
               p["workspace_id"], file_path=p["file_path"])
    return result


def ws_snapshot_dir(p: dict) -> dict:
    from genesis.internal_vcs import get_vcs
    vcs = get_vcs(p["workspace_id"])
    return vcs._snapshot_directory_sync(
        p.get("directory_path", ""), p.get("message", ""),
        p.get("author", "grace"), p.get("extensions"),
    )


def ws_history(p: dict) -> dict:
    from genesis.internal_vcs import get_vcs
    vcs = get_vcs(p["workspace_id"])
    return {"history": vcs._history_sync(
        p["file_path"], p.get("branch_name"), p.get("limit", 50),
    )}


def ws_diff(p: dict) -> dict:
    from genesis.internal_vcs import get_vcs
    vcs = get_vcs(p["workspace_id"])
    return vcs._diff_sync(p["file_path"], p["version_a"], p["version_b"])


def ws_rollback(p: dict) -> dict:
    from genesis.internal_vcs import get_vcs
    vcs = get_vcs(p["workspace_id"])
    result = vcs._rollback_sync(
        p["file_path"], p["target_version"], p.get("author", "grace"),
    )
    _track("code_change",
           f"VCS rollback: {p['file_path']} Ã¢â€ â€™ v{p['target_version']}",
           p["workspace_id"], file_path=p["file_path"])
    return result


def ws_content(p: dict) -> dict:
    from genesis.internal_vcs import get_vcs
    vcs = get_vcs(p["workspace_id"])
    return vcs._get_content_sync(p["file_path"], p.get("version"))


def ws_files(p: dict) -> dict:
    from genesis.internal_vcs import get_vcs
    vcs = get_vcs(p["workspace_id"])
    return {"files": vcs._list_tracked_files_sync(p.get("branch_name"))}


def ws_branches(p: dict) -> dict:
    from genesis.internal_vcs import get_vcs
    vcs = get_vcs(p["workspace_id"])
    return {"branches": vcs._list_branches_sync()}


def ws_create_branch(p: dict) -> dict:
    from genesis.internal_vcs import get_vcs
    vcs = get_vcs(p["workspace_id"])
    result = vcs._create_branch_sync(p["name"], p.get("from_branch", "main"))
    if result.get("status") == "created":
        _track("system_event", f"Branch created: {p['name']}", p["workspace_id"])
    return result


# Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ Pipeline operations Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

def ws_pipeline_run(p: dict) -> dict:
    from genesis.internal_pipeline import get_pipeline_runner, PipelineConfig
    runner = get_pipeline_runner(p["workspace_id"])

    if p.get("yaml_path"):
        config = runner.load_pipeline_yaml(p["yaml_path"])
    elif p.get("stages"):
        config = PipelineConfig(
            name=p.get("pipeline_name", "unnamed"),
            stages=p["stages"],
            working_dir=p.get("working_dir"),
            environment=p.get("environment", {}),
        )
    else:
        return {"error": "Provide yaml_path or stages"}

    result = _run_async(runner.run_pipeline(
        config=config,
        trigger=p.get("trigger", "manual"),
        triggered_by=p.get("triggered_by", "grace"),
    ))
    _track("system_event",
           f"Pipeline {config.name}: {result.get('status')}",
           p["workspace_id"])
    return result


def ws_pipeline_history(p: dict) -> dict:
    from genesis.internal_pipeline import get_pipeline_runner
    runner = get_pipeline_runner(p["workspace_id"])
    return {"runs": runner.get_run_history(p.get("limit", 20))}
