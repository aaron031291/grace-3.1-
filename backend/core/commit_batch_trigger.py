"""
Commit batch trigger: when N new commits (default 5) accumulate, run the upload action
(model version check + persist). State stored in data/commit_batch_state.json.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

STATE_FILE = Path(__file__).resolve().parent.parent / "data" / "commit_batch_state.json"
BATCH_SIZE = int(os.getenv("COMMIT_BATCH_SIZE", "5"))


def _load_state() -> Dict[str, Any]:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception as e:
            logger.warning("Commit batch state load failed: %s", e)
    return {"last_commit_sha": None, "last_upload_at": None}


def _save_state(last_commit_sha: str):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    import datetime
    STATE_FILE.write_text(json.dumps({
        "last_commit_sha": last_commit_sha,
        "last_upload_at": datetime.datetime.utcnow().isoformat(),
    }, indent=2))


def check_and_upload_if_batch() -> Dict[str, Any]:
    """
    Count new commits since last upload. If >= BATCH_SIZE (default 5), run model
    version check (upload) and persist new HEAD. Returns result dict with
    triggered, new_commits, last_sha.
    """
    out = {"triggered": False, "new_commits": 0, "last_sha": None, "error": None}
    try:
        from version_control.git_service import GitService
        backend = Path(__file__).resolve().parent.parent
        # Repo is usually workspace root (parent of backend)
        workspace = backend.parent
        repo_path = workspace if (workspace / ".git").exists() else backend
        git = GitService(str(repo_path))
        commits = git.get_commits(limit=50)
        if not commits:
            return out

        head_sha = commits[0].get("sha") if commits else None
        if not head_sha:
            return out

        state = _load_state()
        last_sha = state.get("last_commit_sha")

        if last_sha is None:
            _save_state(head_sha)
            out["last_sha"] = head_sha
            return out

        # Count commits from HEAD until we hit last_sha
        new_count = 0
        for c in commits:
            if c.get("sha") == last_sha:
                break
            new_count += 1
        # If last_sha not in first 50, treat as 50 new
        if new_count == len(commits) and last_sha not in [c.get("sha") for c in commits]:
            new_count = len(commits)

        out["new_commits"] = new_count

        if new_count >= BATCH_SIZE:
            from cognitive.model_updater import check_all_models
            check_all_models()
            # Hot reload so code/config changes are applied without restart
            try:
                from core.hot_reload import hot_reload_all_services
                hr = hot_reload_all_services()
                out["hot_reload"] = {"reloaded": hr.get("reloaded", 0), "failed": hr.get("failed", 0)}
            except Exception as e:
                out["hot_reload"] = {"error": str(e)[:100]}
            _save_state(head_sha)
            out["triggered"] = True
            out["last_sha"] = head_sha
            logger.info("Commit batch trigger: %s new commits, model check + hot reload", new_count)
    except Exception as e:
        out["error"] = str(e)
        logger.warning("Commit batch trigger failed: %s", e)
    return out
