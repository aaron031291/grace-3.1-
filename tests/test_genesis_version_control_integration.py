"""
Tests for Genesis Key → Version Control Integration.

This test suite verifies that:
1. Genesis Key is ALWAYS the first anchor
2. Version Control takes over after Genesis Key creation for file operations
3. This pattern is enforced throughout the system
4. FILE_OPERATION keys are ONLY created by SymbioticVersionControl
"""

import pytest
import os
import tempfile
import json
from unittest.mock import patch, MagicMock
from datetime import datetime


class TestGenesisVersionControlIntegration:
    """Test the Genesis Key → Version Control integration pattern."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        session = MagicMock()
        session.query.return_value.filter.return_value.first.return_value = None
        session.query.return_value.filter.return_value.all.return_value = []
        return session

    def test_symbiotic_version_control_creates_linked_keys(self, temp_dir, mock_session):
        """Test that SymbioticVersionControl creates both Genesis Key and version entry."""
        # Create a test file
        test_file = os.path.join(temp_dir, "test_file.py")
        with open(test_file, "w") as f:
            f.write("# Test file\nprint('hello')")

        # Import and create symbiotic VC
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        
        from genesis.symbiotic_version_control import SymbioticVersionControl
        
        with patch('genesis.symbiotic_version_control.get_genesis_service') as mock_genesis:
            with patch('genesis.symbiotic_version_control.get_file_version_tracker') as mock_tracker:
                # Setup mocks
                mock_key = MagicMock()
                mock_key.key_id = "GEN-test-123"
                mock_key.context_data = {}
                mock_genesis.return_value.create_key.return_value = mock_key
                
                mock_tracker.return_value.track_file_version.return_value = {
                    "version_key_id": "VER-test-1",
                    "version_number": 1,
                    "changed": True
                }
                
                # Create symbiotic VC
                svc = SymbioticVersionControl(base_path=temp_dir, session=mock_session)
                
                # Track file change
                result = svc.track_file_change(
                    file_path=test_file,
                    user_id="test_user",
                    change_description="Test change",
                    operation_type="modify",
                    event_genesis_key_id="EVENT-123",
                    pipeline_id="PIPE-456"
                )
                
                # Verify Genesis Key was created with FILE_OPERATION type
                mock_genesis.return_value.create_key.assert_called()
                call_kwargs = mock_genesis.return_value.create_key.call_args[1]
                
                # Verify the context includes linkage
                assert "symbiotic" in str(call_kwargs)
                
                # Verify result includes both genesis key and version info
                assert "operation_genesis_key" in result or result.get("symbiotic") is True
                assert result.get("symbiotic") is True

    def test_event_genesis_key_links_to_file_operation(self, temp_dir):
        """Test that event Genesis Key is linked to file operation key."""
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        
        from genesis.symbiotic_version_control import SymbioticVersionControl
        
        with patch('genesis.symbiotic_version_control.get_genesis_service') as mock_genesis:
            with patch('genesis.symbiotic_version_control.get_file_version_tracker') as mock_tracker:
                mock_key = MagicMock()
                mock_key.key_id = "GEN-file-op"
                mock_key.context_data = {}
                mock_genesis.return_value.create_key.return_value = mock_key
                
                mock_tracker.return_value.track_file_version.return_value = {
                    "version_key_id": "VER-1",
                    "version_number": 1,
                    "changed": True
                }
                
                svc = SymbioticVersionControl(base_path=temp_dir, session=None)
                
                # Track with event key linkage
                result = svc.track_file_change(
                    file_path="test.py",
                    event_genesis_key_id="EVENT-first-anchor",
                    pipeline_id="PIPE-test"
                )
                
                # Verify event key ID was passed in context
                call_kwargs = mock_genesis.return_value.create_key.call_args[1]
                context = call_kwargs.get("context_data", {})
                assert context.get("event_genesis_key_id") == "EVENT-first-anchor"
                assert context.get("pipeline_id") == "PIPE-test"

    def test_pipeline_uses_correct_key_types(self):
        """Test that DataPipeline uses correct key types for file vs non-file operations."""
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        
        from genesis.pipeline_integration import DataPipeline
        from models.genesis_key_models import GenesisKeyType
        
        with patch('genesis.pipeline_integration.get_genesis_service') as mock_genesis:
            with patch('genesis.pipeline_integration.get_symbiotic_version_control') as mock_svc:
                with patch('genesis.pipeline_integration.get_kb_integration'):
                    mock_key = MagicMock()
                    mock_key.key_id = "GEN-event"
                    mock_key.key_type = GenesisKeyType.API_REQUEST
                    mock_key.what_description = "Test"
                    mock_key.who_actor = "test"
                    mock_key.where_location = "test"
                    mock_key.when_timestamp = datetime.utcnow()
                    mock_key.why_reason = "test"
                    mock_key.how_method = "test"
                    mock_genesis.return_value.create_key.return_value = mock_key
                    
                    mock_svc.return_value.track_file_change.return_value = {
                        "version_key_id": "VER-1",
                        "version_number": 1,
                        "changed": True,
                        "operation_genesis_key": "GEN-file-op"
                    }
                    
                    pipeline = DataPipeline(session=None)
                    
                    # Process file operation
                    with patch.object(pipeline, '_librarian_organize', return_value={"path": "test", "category": "test"}):
                        with patch.object(pipeline, '_store_in_immutable_memory', return_value={"location": "test"}):
                            with patch.object(pipeline, '_index_for_rag', return_value={"indexed": True}):
                                with patch.object(pipeline, '_integrate_world_model', return_value={"ai_ready": True}):
                                    result = pipeline.process_input(
                                        input_data="test",
                                        input_type="file_change",
                                        file_path="/test/file.py"
                                    )
                    
                    # Verify event key was created with API_REQUEST (not FILE_OPERATION)
                    create_key_calls = mock_genesis.return_value.create_key.call_args_list
                    assert len(create_key_calls) > 0
                    
                    # First call should be API_REQUEST for file operations
                    first_call_kwargs = create_key_calls[0][1]
                    assert first_call_kwargs["key_type"] in [GenesisKeyType.API_REQUEST, GenesisKeyType.USER_INPUT]

    def test_version_control_guard_warns_on_bypass(self):
        """Test that version control guard warns when pattern is bypassed."""
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        
        from genesis.version_control_guard import (
            enforce_version_control_pattern,
            get_bypass_stats,
            reset_bypass_stats,
            set_strict_mode
        )
        
        # Reset stats
        reset_bypass_stats()
        set_strict_mode(False)
        
        # This should warn (caller is not proper)
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = enforce_version_control_pattern(
                operation_type="file_modify",
                file_path="/test/file.py",
                caller="some_random_function"
            )
            
            # Should return False and emit warning
            assert result is False
            assert len(w) == 1
            assert "SymbioticVersionControl" in str(w[0].message)
        
        # Check stats
        stats = get_bypass_stats()
        assert stats["total_bypasses"] == 1
        assert "some_random_function" in stats["callers"]

    def test_version_control_guard_allows_proper_callers(self):
        """Test that version control guard allows proper callers."""
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        
        from genesis.version_control_guard import (
            enforce_version_control_pattern,
            reset_bypass_stats
        )
        
        reset_bypass_stats()
        
        # These should pass (proper callers)
        proper_callers = [
            "symbiotic_version_control.track_file_change",
            "genesis.pipeline_integration",
            "genesis.file_watcher",
            "layer1.components.version_control_connector"
        ]
        
        for caller in proper_callers:
            result = enforce_version_control_pattern(
                operation_type="file_modify",
                file_path="/test/file.py",
                caller=caller
            )
            assert result is True, f"Caller {caller} should be allowed"

    def test_version_control_guard_strict_mode_raises(self):
        """Test that version control guard raises in strict mode."""
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        
        from genesis.version_control_guard import (
            enforce_version_control_pattern,
            reset_bypass_stats
        )
        
        reset_bypass_stats()
        
        # Should raise in strict mode
        with pytest.raises(RuntimeError) as exc_info:
            enforce_version_control_pattern(
                operation_type="file_modify",
                file_path="/test/file.py",
                caller="bad_caller",
                strict=True
            )
        
        assert "SymbioticVersionControl" in str(exc_info.value)


class TestFileOperationKeyEnforcement:
    """Test that FILE_OPERATION keys are only created by SymbioticVersionControl."""

    def test_tracking_middleware_uses_system_event(self):
        """Test that tracking middleware uses SYSTEM_EVENT, not FILE_OPERATION."""
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        
        # Read the source and verify it uses SYSTEM_EVENT
        middleware_path = os.path.join(
            os.path.dirname(__file__), "..", "backend", "genesis", "tracking_middleware.py"
        )
        
        with open(middleware_path, "r") as f:
            content = f.read()
        
        # Should have SYSTEM_EVENT for tracking, not FILE_OPERATION
        assert "GenesisKeyType.SYSTEM_EVENT" in content
        # The tracking middleware should use SYSTEM_EVENT
        assert "file-operation-tracking" in content

    def test_librarian_uses_symbiotic_vc_for_files(self):
        """Test that librarian uses symbiotic VC for file operations."""
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        
        # Read the source and verify it uses symbiotic VC
        librarian_path = os.path.join(
            os.path.dirname(__file__), "..", "backend", "librarian", "genesis_integration.py"
        )
        
        with open(librarian_path, "r") as f:
            content = f.read()
        
        # Should import and use symbiotic version control
        assert "symbiotic_version_control" in content
        assert "track_file_change" in content


class TestChainIntegrity:
    """Test the complete chain: Event Key → FILE_OPERATION Key → Version Entry."""

    def test_complete_chain_for_file_operation(self, tmp_path):
        """Test complete chain from event to version entry."""
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        
        # Create test file
        test_file = tmp_path / "test.py"
        test_file.write_text("print('test')")
        
        from genesis.symbiotic_version_control import SymbioticVersionControl
        
        with patch('genesis.symbiotic_version_control.get_genesis_service') as mock_genesis:
            with patch('genesis.symbiotic_version_control.get_file_version_tracker') as mock_tracker:
                # Setup chain tracking
                created_keys = []
                
                def track_key_creation(**kwargs):
                    key = MagicMock()
                    key.key_id = f"GEN-{len(created_keys)}"
                    key.context_data = kwargs.get("context_data", {})
                    created_keys.append({
                        "key_id": key.key_id,
                        "type": kwargs.get("key_type"),
                        "context": key.context_data
                    })
                    return key
                
                mock_genesis.return_value.create_key.side_effect = track_key_creation
                mock_tracker.return_value.track_file_version.return_value = {
                    "version_key_id": "VER-1",
                    "version_number": 1,
                    "changed": True
                }
                
                svc = SymbioticVersionControl(base_path=str(tmp_path), session=None)
                
                # Track file change with event linkage
                result = svc.track_file_change(
                    file_path=str(test_file),
                    user_id="test",
                    event_genesis_key_id="EVENT-anchor-001",
                    pipeline_id="PIPE-001"
                )
                
                # Verify chain
                assert len(created_keys) >= 1
                
                # The FILE_OPERATION key should reference the event key
                file_op_key = created_keys[0]
                assert file_op_key["context"].get("event_genesis_key_id") == "EVENT-anchor-001"
                assert file_op_key["context"].get("pipeline_id") == "PIPE-001"
                assert file_op_key["context"].get("symbiotic") is True
                
                # Version tracker should have been called
                mock_tracker.return_value.track_file_version.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
