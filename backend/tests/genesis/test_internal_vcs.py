import pytest
import os
import asyncio
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
from models.workspace_models import Workspace, Branch, FileVersion
from genesis.internal_vcs import InternalVCS, create_workspace, list_workspaces, get_vcs

@pytest.fixture
def temp_vcs(tmp_path):
    vcs = InternalVCS("test_ws")
    
    # We patch session_scope to yield a mock session
    class MockSession(MagicMock):
        def query(self, *args, **kwargs):
            return self
        def filter_by(self, *args, **kwargs):
            return self
        def order_by(self, *args, **kwargs):
            return self
        def first(self, *args, **kwargs):
            return getattr(self, "fixed_first", None)
        def all(self, *args, **kwargs):
            return getattr(self, "fixed_all", [])
        def limit(self, *args, **kwargs):
            return self
        def group_by(self, *args, **kwargs):
            return self
    
    session = MockSession()
    
    # Mock workspace lookup globally
    ws = MagicMock()
    ws.id = 1
    ws.workspace_id = "test_ws"
    ws.root_path = str(tmp_path)
    session.fixed_first = ws # Make get_workspace return this initially
    
    cm = MagicMock()
    cm.__enter__.return_value = session
    
    with patch('genesis.internal_vcs.session_scope', return_value=cm) as mock_scope:
        yield vcs, tmp_path, session

@pytest.mark.asyncio
async def test_snapshot(temp_vcs):
    vcs, tmp_path, session = temp_vcs
    
    # We need to hack the session.first to return a workspace, then branch, then version
    ws = MagicMock()
    ws.id = 1
    
    branch = MagicMock()
    branch.id = 1
    branch.name = "main"
    
    def side_effect_first(*args, **kwargs):
        return ws # simplified for test
        
    session.fixed_first = None # no previous version
    
    # Just mock the _get_workspace so it bypasses query lookup
    with patch.object(vcs, '_get_workspace', return_value=ws):
        with patch.object(vcs, '_get_or_create_default_branch', return_value=branch):
            res = await vcs.snapshot("test.txt", "hello world", "init")
            assert res["status"] == "created"
            assert res["version"] == 1

@pytest.mark.asyncio
async def test_history(temp_vcs):
    vcs, tmp_path, session = temp_vcs
    
    ws = MagicMock()
    ws.id = 1
    
    v1 = MagicMock()
    v1.version_number = 1
    v1.content_hash = "abc"
    v1.content_size = 3
    v1.operation = "create"
    v1.commit_message = "init"
    v1.author = "me"
    v1.created_at = None
    v1.id = 10
    
    session.fixed_all = [v1]
    
    with patch.object(vcs, '_get_workspace', return_value=ws):
        hist = await vcs.history("test.txt")
        assert len(hist) == 1
        assert hist[0]["version"] == 1
        assert hist[0]["operation"] == "create"

@pytest.mark.asyncio
async def test_create_workspace(tmp_path):
    with patch('genesis.internal_vcs.session_scope') as mock_scope:
        session = MagicMock()
        mock_scope.return_value.__enter__.return_value = session
        
        session.query().filter_by().first.return_value = None # Doesn't exist
        
        res = await create_workspace("new_ws", "New WS", str(tmp_path / "ws"))
        assert res["status"] == "created"
        assert res["workspace_id"] == "new_ws"
        
        # Check directories created
        assert os.path.exists(tmp_path / "ws" / "knowledge_base")
        assert os.path.exists(tmp_path / "ws" / "data")

if __name__ == "__main__":
    pytest.main(['-v', __file__])
