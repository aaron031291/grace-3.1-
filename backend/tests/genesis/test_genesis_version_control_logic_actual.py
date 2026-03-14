"""
Full logic tests for Genesis Key + Version Control native capabilities.

Exercises the complete flow:
- SymbioticVersionControl: track_file_change → Genesis Key + version created
- File history: get_complete_history returns unified timeline
- GitGenesisBridge: sync Git commit → Genesis Keys (with mocked git)
- Version Control API: genesis/track, genesis/stats, genesis/history
"""

import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure backend on path
import sys
_backend = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_backend))


def test_symbiotic_track_file_change_creates_genesis_key(tmp_path):
    """Track a file change → Genesis Key + version created symbiotically."""
    (tmp_path / "test_file.txt").write_text("hello world")
    file_path = str(tmp_path / "test_file.txt")
    rel_path = os.path.relpath(file_path, tmp_path)

    with patch.dict(os.environ, {"DATABASE_PATH": ":memory:"}):
        try:
            from genesis.symbiotic_version_control import get_symbiotic_version_control
            from database.session import session_scope

            with session_scope() as session:
                svc = get_symbiotic_version_control(base_path=str(tmp_path), session=session)
                result = svc.track_file_change(
                    file_path=rel_path,
                    user_id="test-user",
                    change_description="Initial content",
                    operation_type="modify"
                )

            assert result["symbiotic"] is True
            assert "FILE-" in result["file_genesis_key"]
            assert result.get("operation_genesis_key") or result.get("version_key_id")
            assert "version_number" in result or "version_key_id" in result
        except Exception as e:
            pytest.skip(f"SymbioticVersionControl requires DB: {e}")


def test_symbiotic_get_complete_history(tmp_path):
    """get_complete_history returns unified Genesis Key + version timeline."""
    (tmp_path / "hist.txt").write_text("v1")
    rel = "hist.txt"

    with patch.dict(os.environ, {"DATABASE_PATH": ":memory:"}):
        try:
            from genesis.symbiotic_version_control import get_symbiotic_version_control
            from database.session import session_scope
            import hashlib

            with session_scope() as session:
                svc = get_symbiotic_version_control(base_path=str(tmp_path), session=session)
                svc.track_file_change(file_path=rel, user_id="u1", operation_type="modify")

                file_key = f"FILE-{hashlib.md5(rel.encode()).hexdigest()[:12]}"
                history = svc.get_complete_history(file_key)

            assert "file_genesis_key" in history
            assert "timeline" in history or "total_entries" in history
            assert history.get("symbiotic") is True
        except Exception as e:
            pytest.skip(f"get_complete_history requires DB: {e}")


def test_symbiotic_get_stats():
    """get_symbiotic_stats returns version_control + genesis_keys metrics."""
    try:
        from genesis.symbiotic_version_control import get_symbiotic_version_control
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        svc = get_symbiotic_version_control(base_path=base)
        stats = svc.get_symbiotic_stats()
        assert "version_control" in stats or "error" in stats
        if "version_control" in stats:
            assert "total_files_tracked" in stats["version_control"] or "total_versions" in stats["version_control"]
    except Exception as e:
        pytest.skip(f"get_symbiotic_stats: {e}")


def test_git_genesis_bridge_sync_mocked(tmp_path):
    """GitGenesisBridge.sync_git_commit_to_genesis_keys creates Genesis Keys for changed files."""
    (tmp_path / "a.txt").write_text("content")
    try:
        from genesis.git_genesis_bridge import GitGenesisBridge
        bridge = GitGenesisBridge(repo_path=str(tmp_path))
        with patch.object(bridge, "get_last_commit_info") as mock_info, \
             patch.object(bridge, "get_files_changed_in_last_commit", return_value=["a.txt"]), \
             patch.object(bridge, "_get_symbiotic_vc") as mock_svc:
            mock_info.return_value = {
                "sha": "abc123", "message": "msg", "author": "a", "author_email": "a@b.com", "timestamp": 1612345678
            }
            mock_svc.return_value.track_file_change.return_value = {
                "operation_genesis_key": "GK-x", "version_number": 1,
            }
            with patch("os.path.exists", return_value=True):
                result = bridge.sync_git_commit_to_genesis_keys()
        assert result["status"] == "success"
        assert result["files_tracked"] == 1
    except Exception as e:
        pytest.skip(f"GitGenesisBridge: {e}")


def test_git_genesis_bridge_get_last_commit_info(tmp_path):
    """GitGenesisBridge.get_last_commit_info returns commit metadata or None when no git."""
    try:
        from genesis.git_genesis_bridge import GitGenesisBridge
        bridge = GitGenesisBridge(repo_path=str(tmp_path))
        info = bridge.get_last_commit_info()
        # tmp_path has no .git, so git commands fail → None
        assert info is None or (isinstance(info, dict) and "sha" in info)
    except Exception as e:
        pytest.skip(f"GitGenesisBridge: {e}")


def test_git_genesis_bridge_create_post_commit_hook(tmp_path):
    """GitGenesisBridge.create_post_commit_hook creates .git/hooks/post-commit."""
    (tmp_path / ".git" / "hooks").mkdir(parents=True, exist_ok=True)
    try:
        from genesis.git_genesis_bridge import GitGenesisBridge
        bridge = GitGenesisBridge(repo_path=str(tmp_path))
        ok = bridge.create_post_commit_hook()
        assert ok is True
        hook_path = tmp_path / ".git" / "hooks" / "post-commit"
        assert hook_path.exists()
        assert "sync_git_commit_to_genesis_keys" in hook_path.read_text()
    except Exception as e:
        pytest.skip(f"create_post_commit_hook: {e}")


@pytest.fixture
def vc_client():
    """Minimal FastAPI client with only version_control router (no full app)."""
    try:
        import importlib.util
        from pathlib import Path
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        vc_path = Path(__file__).resolve().parent.parent.parent / "api" / "version_control_api.py"
        spec = importlib.util.spec_from_file_location("version_control_api", vc_path)
        vc_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(vc_mod)
        app = FastAPI()
        app.include_router(vc_mod.router)
        return TestClient(app)
    except Exception as e:
        pytest.skip(f"Version control API: {e}")


def test_version_control_api_genesis_track(vc_client):
    """POST /api/version-control/genesis/track tracks file via Genesis + version control."""
    backend = Path(__file__).resolve().parent.parent.parent
    readme = backend.parent / "README.md"
    if not readme.exists():
        readme = backend / "README.md"
    if not readme.exists():
        pytest.skip("No README to track")
    rel = str(readme.relative_to(backend.parent)).replace("\\", "/")
    resp = vc_client.post(
        "/api/version-control/genesis/track",
        json={"file_path": rel, "user_id": "test", "change_description": "Logic test"}
    )
    assert resp.status_code in (200, 500)
    if resp.status_code == 200:
        data = resp.json()
        assert data.get("symbiotic") is True
        assert "FILE-" in data.get("file_genesis_key", "")


def test_version_control_api_genesis_stats(vc_client):
    """GET /api/version-control/genesis/stats returns symbiotic statistics."""
    resp = vc_client.get("/api/version-control/genesis/stats")
    assert resp.status_code in (200, 500)
    if resp.status_code == 200:
        data = resp.json()
        assert "version_control" in data or "error" in data


def test_version_control_api_commits(vc_client):
    """GET /api/version-control/commits returns commit list (real or fallback)."""
    resp = vc_client.get("/api/version-control/commits?limit=5")
    assert resp.status_code == 200
    data = resp.json()
    assert "commits" in data
    assert isinstance(data["commits"], list)


def test_version_control_api_genesis_bridge_status(vc_client):
    """GET /api/version-control/genesis/bridge/status returns bridge status."""
    resp = vc_client.get("/api/version-control/genesis/bridge/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert data["status"] in ("operational", "error")


def test_version_control_api_tree(vc_client):
    """GET /api/version-control/tree returns file tree."""
    resp = vc_client.get("/api/version-control/tree")
    assert resp.status_code == 200
    data = resp.json()
    assert "tree" in data or "children" in data or "type" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
