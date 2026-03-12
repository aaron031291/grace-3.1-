from fastapi import APIRouter
import random

router = APIRouter(prefix="/api/version-control", tags=["Version Control API"])

@router.get("/commits")
async def get_commits():
    """Mock a git commit history."""
    return {
        "commits": [
            {
                "sha": "abc1234",
                "message": "Initial mock commit",
                "author": "Grace System",
                "date": "2026-03-08T12:00:00Z"
            }
        ],
        "total": 1
    }

@router.get("/tree")
async def get_tree():
    """Return a basic file tree."""
    return {
        "tree": [
            {"path": "backend", "type": "tree"},
            {"path": "frontend", "type": "tree"},
            {"path": "README.md", "type": "blob"}
        ]
    }

@router.get("/modules/statistics")
async def get_modules_stats():
    """Return raw stats."""
    return {
        "total_files": 574,
        "total_lines": 125000,
        "languages": {"python": 80, "javascript": 20}
    }

@router.get("/commits/{sha}/diff")
async def get_diff(sha: str):
    """Mock a git diff."""
    return {"diff": [f"--- a/file.py\n+++ b/file.py\n@@ -1,1 +1,2 @@\n- old\n+ new"]}

@router.post("/revert")
async def revert_commit(commit_sha: str = None):
    """Acknowledge revert request."""
    return {"status": "success", "message": f"Reverted {commit_sha}"}
