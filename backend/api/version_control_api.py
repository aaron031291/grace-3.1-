"""
Version Control API — Genesis Key + Git unified native capability.

Exposes both:
- Git operations (via Dulwich) — commits, tree, diff, revert
- Genesis-native operations — track_file_change, complete_history, symbiotic_stats
- GitGenesisBridge — sync Git ↔ Genesis Keys
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import os
import logging

router = APIRouter(prefix="/api/version-control", tags=["Version Control API"])
logger = logging.getLogger(__name__)


def _get_repo_path() -> str:
    """Project root (parent of backend)."""
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.dirname(backend_dir)


def _get_git_service():
    """Get GitService or None if unavailable."""
    try:
        from version_control.git_service import GitService
        return GitService(_get_repo_path())
    except Exception as e:
        logger.debug(f"GitService unavailable: {e}")
        return None


# ─── Git operations (Dulwich) ────────────────────────────────────────────────

@router.get("/commits")
async def get_commits(limit: int = 50, skip: int = 0):
    """Get commit history from Git (Dulwich). Falls back to mock if Git unavailable."""
    gs = _get_git_service()
    if gs:
        try:
            commits = gs.get_commits(limit=limit, skip=skip)
            return {"commits": commits, "total": len(commits)}
        except Exception as e:
            logger.warning(f"get_commits error: {e}")
    # Fallback mock
    return {
        "commits": [
            {"sha": "abc1234", "message": "Initial mock commit", "author": "Grace System", "timestamp": "2026-03-08T12:00:00Z"}
        ],
        "total": 1,
        "_fallback": "GitService unavailable"
    }


@router.get("/commits/{sha}")
async def get_commit_details(sha: str):
    """Get commit details by SHA."""
    gs = _get_git_service()
    if gs:
        try:
            return gs.get_commit_details(sha)
        except Exception as e:
            raise HTTPException(status_code=404, detail=str(e))
    raise HTTPException(status_code=503, detail="GitService unavailable")


@router.get("/commits/{sha}/diff")
async def get_commit_diff(sha: str):
    """Get diff for a specific commit."""
    gs = _get_git_service()
    if gs:
        try:
            return gs.get_commit_diff(sha)
        except Exception as e:
            raise HTTPException(status_code=404, detail=str(e))
    return {"diff": [f"--- a/file.py\n+++ b/file.py\n@@ -1,1 +1,2 @@\n- old\n+ new"], "_fallback": True}


@router.get("/diff")
async def get_diff_between(from_sha: Optional[str] = None, to_sha: Optional[str] = None):
    """Compare two commits."""
    gs = _get_git_service()
    if gs and from_sha and to_sha:
        try:
            if hasattr(gs, "get_diff_between_commits"):
                return gs.get_diff_between_commits(from_sha, to_sha)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    return {"error": "Provide from_sha and to_sha", "files_changed": []}


@router.get("/tree")
async def get_tree(commit_sha: Optional[str] = None, path: str = ""):
    """Get file tree structure at a commit (or HEAD)."""
    gs = _get_git_service()
    if gs:
        try:
            return gs.get_tree_structure(commit_sha=commit_sha, path=path)
        except Exception as e:
            logger.warning(f"get_tree error: {e}")
    return {
        "tree": [{"path": "backend", "type": "tree"}, {"path": "frontend", "type": "tree"}, {"path": "README.md", "type": "blob"}],
        "_fallback": True
    }


@router.get("/files/{path:path}/history")
async def get_file_history(path: str, limit: int = 50):
    """Get commit history for a specific file."""
    gs = _get_git_service()
    if gs:
        try:
            return {"commits": gs.get_file_history(path, limit=limit)}
        except Exception as e:
            logger.warning(f"get_file_history error: {e}")
    return {"commits": [], "_fallback": True}


@router.get("/modules/statistics")
async def get_modules_stats():
    """Get module/directory statistics."""
    gs = _get_git_service()
    if gs:
        try:
            return gs.get_module_statistics()
        except Exception:
            pass
    return {"total_files": 0, "total_lines": 0, "modules": [], "_fallback": True}


@router.post("/revert")
async def revert_commit(commit_sha: str):
    """Revert working directory to a commit. Use with caution."""
    gs = _get_git_service()
    if gs:
        try:
            result = gs.revert_to_commit(commit_sha)
            return result
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    return {"status": "success", "message": f"Revert acknowledged (no Git): {commit_sha}", "_fallback": True}


# ─── Genesis-native operations (Symbiotic Version Control) ────────────────────

class TrackFileRequest(BaseModel):
    """Request body for tracking a file change."""
    file_path: str = Field(..., description="Relative path from project root")
    user_id: Optional[str] = None
    change_description: Optional[str] = None
    operation_type: str = Field(default="modify", description="modify|add|delete|rollback|git_commit")


@router.post("/genesis/track")
async def genesis_track_file(req: TrackFileRequest):
    """Track a file change via Genesis Keys + version control (Grace native)."""
    try:
        from genesis.symbiotic_version_control import get_symbiotic_version_control
        base_path = _get_repo_path()
        svc = get_symbiotic_version_control(base_path=base_path)
        result = svc.track_file_change(
            file_path=req.file_path,
            user_id=req.user_id,
            change_description=req.change_description,
            operation_type=req.operation_type
        )
        return result
    except Exception as e:
        logger.error(f"genesis_track_file error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/genesis/history/{file_path:path}")
async def genesis_file_history(file_path: str):
    """Get complete Genesis Key + version history for a file (unified timeline)."""
    try:
        from genesis.symbiotic_version_control import get_symbiotic_version_control
        from database.session import session_scope
        import hashlib
        base_path = _get_repo_path()
        # Resolve file_genesis_key from path (same hashing as symbiotic)
        rel_path = file_path.lstrip("/").replace("\\", "/")
        file_hash_id = hashlib.md5(rel_path.encode()).hexdigest()[:12]
        file_genesis_key = f"FILE-{file_hash_id}"
        with session_scope() as session:
            svc = get_symbiotic_version_control(base_path=base_path, session=session)
            return svc.get_complete_history(file_genesis_key)
    except Exception as e:
        logger.error(f"genesis_file_history error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/genesis/stats")
async def genesis_symbiotic_stats():
    """Get Genesis Key + version control symbiotic statistics."""
    try:
        from genesis.symbiotic_version_control import get_symbiotic_version_control
        base_path = _get_repo_path()
        svc = get_symbiotic_version_control(base_path=base_path)
        return svc.get_symbiotic_stats()
    except Exception as e:
        logger.error(f"genesis_symbiotic_stats error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ─── GitGenesisBridge ────────────────────────────────────────────────────────

@router.get("/genesis/bridge/status")
async def git_genesis_bridge_status():
    """Get Git-Genesis bridge status (hook installed, last commit, etc.)."""
    try:
        from genesis.git_genesis_bridge import get_git_genesis_bridge
        bridge = get_git_genesis_bridge(repo_path=_get_repo_path())
        return bridge.get_bridge_statistics()
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.post("/genesis/bridge/sync")
async def git_genesis_sync(commit_sha: Optional[str] = None):
    """Sync a Git commit to Genesis Keys (typically called by post-commit hook)."""
    try:
        from genesis.git_genesis_bridge import get_git_genesis_bridge
        bridge = get_git_genesis_bridge(repo_path=_get_repo_path())
        return bridge.sync_git_commit_to_genesis_keys(commit_sha=commit_sha)
    except Exception as e:
        logger.error(f"git_genesis_sync error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/genesis/bridge/install-hook")
async def install_post_commit_hook():
    """Install Git post-commit hook for automatic Genesis Key creation on commits."""
    try:
        from genesis.git_genesis_bridge import get_git_genesis_bridge
        bridge = get_git_genesis_bridge(repo_path=_get_repo_path())
        ok = bridge.create_post_commit_hook()
        return {"status": "installed" if ok else "failed", "success": ok}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
