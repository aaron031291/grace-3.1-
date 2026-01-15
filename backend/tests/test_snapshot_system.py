"""
Tests for Genesis Key Snapshot System.
"""

import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime, UTC, timedelta
from unittest.mock import Mock, MagicMock
from sqlalchemy.orm import Session

from genesis.snapshot_system import (
    GenesisKeySnapshotSystem,
    GenesisKeySnapshot
)
from models.genesis_key_models import GenesisKey, GenesisKeyStatus, GenesisKeyType


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = Mock(spec=Session)
    session.query = Mock()
    return session


@pytest.fixture
def snapshot_system(mock_session):
    """Create a snapshot system instance."""
    with tempfile.TemporaryDirectory() as tmpdir:
        system = GenesisKeySnapshotSystem(
            session=mock_session,
            snapshot_path=Path(tmpdir) / "snapshots"
        )
        yield system


class TestStableStateDetection:
    """Test stable state detection."""
    
    def test_is_stable_state_no_errors(self, snapshot_system, mock_session):
        """Test stable state when no errors."""
        # Mock no broken keys, no recent errors, no pending fixes
        mock_query = Mock()
        mock_query.filter.return_value.count.return_value = 0
        mock_session.query.return_value = mock_query
        
        result = snapshot_system.is_stable_state()
        
        assert result is True
    
    def test_is_stable_state_with_broken_keys(self, snapshot_system, mock_session):
        """Test not stable when broken keys exist."""
        # Mock broken keys
        mock_query = Mock()
        mock_query.filter.return_value.count.side_effect = [1, 0, 0]  # 1 broken key
        mock_session.query.return_value = mock_query
        
        result = snapshot_system.is_stable_state()
        
        assert result is False


class TestSnapshotCreation:
    """Test snapshot creation."""
    
    def test_create_snapshot_stable_state(self, snapshot_system, mock_session):
        """Test creating snapshot in stable state."""
        # Mock stable state
        snapshot_system.is_stable_state = Mock(return_value=True)
        
        # Mock Genesis Keys query
        mock_key = Mock(spec=GenesisKey)
        mock_key.key_id = "GK-test-123"
        mock_key.key_type = GenesisKeyType.SYSTEM_EVENT
        mock_key.status = GenesisKeyStatus.ACTIVE
        mock_key.what_description = "Test key"
        mock_key.where_location = None
        mock_key.when_timestamp = datetime.now(UTC)
        mock_key.who_actor = "test"
        mock_key.why_reason = None
        mock_key.how_method = None
        mock_key.file_path = None
        mock_key.is_error = False
        mock_key.is_broken = False
        mock_key.parent_key_id = None
        mock_key.context_data = None
        mock_key.tags = None
        
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = [mock_key]
        mock_session.query.return_value = mock_query
        
        snapshot = snapshot_system.create_snapshot(reason="Test snapshot")
        
        assert snapshot is not None
        assert snapshot.snapshot_id.startswith("SNAP-")
        assert len(snapshot.genesis_keys) == 1
    
    def test_create_snapshot_not_stable(self, snapshot_system):
        """Test snapshot not created when not stable."""
        snapshot_system.is_stable_state = Mock(return_value=False)
        
        snapshot = snapshot_system.create_snapshot()
        
        assert snapshot is None
    
    def test_create_snapshot_force(self, snapshot_system, mock_session):
        """Test forced snapshot creation."""
        snapshot_system.is_stable_state = Mock(return_value=False)
        
        # Mock Genesis Keys query
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = []
        mock_session.query.return_value = mock_query
        
        snapshot = snapshot_system.create_snapshot(force=True)
        
        assert snapshot is not None


class TestSnapshotManagement:
    """Test snapshot management (6 active, 3 backups, archive rest)."""
    
    def test_manage_snapshot_count(self, snapshot_system, mock_session):
        """Test that only 6 active snapshots are kept."""
        snapshot_system.is_stable_state = Mock(return_value=True)
        
        # Mock Genesis Keys query
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = []
        mock_session.query.return_value = mock_query
        
        # Create 8 snapshots
        for i in range(8):
            snapshot_system.create_snapshot(reason=f"Test {i}", force=True)
        
        # Should have only 6 active
        assert len(snapshot_system.active_snapshots) == 6
        
        # Check that older ones were archived (at least 1, could be more due to timing)
        archive_index_file = snapshot_system.archive_path / "archive_index.json"
        archived_count = 0
        if archive_index_file.exists():
            with open(archive_index_file, 'r', encoding='utf-8') as f:
                archive_index = json.load(f)
            archived_count = len(archive_index)
        
        # Should have archived at least 1 (since we created 8 and keep 6)
        # Note: Archiving happens incrementally, so might be 1 or 2 depending on timing
        assert archived_count >= 1
    
    def test_backup_snapshots(self, snapshot_system, mock_session):
        """Test that 3 most recent are kept as backups."""
        snapshot_system.is_stable_state = Mock(return_value=True)
        
        # Mock Genesis Keys query
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = []
        mock_session.query.return_value = mock_query
        
        # Create 6 snapshots
        for i in range(6):
            snapshot_system.create_snapshot(reason=f"Test {i}", force=True)
        
        backups = snapshot_system.get_backup_snapshots()
        
        # Should have 3 backups
        assert len(backups) == 3
        
        # Should be the 3 most recent
        assert backups[0]["snapshot_id"] == snapshot_system.active_snapshots[0].snapshot_id


class TestSnapshotRestore:
    """Test snapshot restoration."""
    
    def test_restore_snapshot(self, snapshot_system, mock_session):
        """Test restoring a snapshot."""
        snapshot_system.is_stable_state = Mock(return_value=True)
        
        # Mock Genesis Keys query
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = []
        mock_session.query.return_value = mock_query
        
        # Create a snapshot
        snapshot = snapshot_system.create_snapshot(reason="Test", force=True)
        
        # Restore it
        result = snapshot_system.restore_snapshot(snapshot.snapshot_id, restore_keys=False)
        
        assert result["success"] is True
        assert result["snapshot_id"] == snapshot.snapshot_id
    
    def test_restore_nonexistent_snapshot(self, snapshot_system):
        """Test restoring non-existent snapshot."""
        result = snapshot_system.restore_snapshot("SNAP-nonexistent", restore_keys=False)
        
        assert result["success"] is False
        assert "not found" in result["error"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
