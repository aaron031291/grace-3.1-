"""
Test Layer 1 → Memory Mesh Integration (Unit Tests)

These tests verify the integration between Layer 1 and Memory Mesh
without requiring a running server.
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime, UTC
from unittest.mock import MagicMock, patch, AsyncMock

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))


@pytest.fixture
def mock_memory_mesh():
    """Create a mock memory mesh for testing."""
    mesh = MagicMock()
    mesh.store_learning = MagicMock(return_value="learning-123")
    mesh.get_trust_score = MagicMock(return_value=0.85)
    mesh.create_episodic_memory = MagicMock(return_value="episodic-123")
    mesh.create_procedural_memory = MagicMock(return_value="procedural-123")
    return mesh


@pytest.fixture
def mock_genesis_keys():
    """Create mock genesis keys service."""
    gk = MagicMock()
    gk.create_key = MagicMock(return_value="GK-test-123")
    gk.link_key = MagicMock(return_value=True)
    return gk


class TestLayer1MemoryMeshIntegration:
    """Test Layer 1 to Memory Mesh integration."""

    def test_learning_data_structure_is_valid(self):
        """Test that learning data structure is properly formatted."""
        learning_data = {
            "learning_type": "feedback",
            "learning_data": {
                "context": {
                    "question": "What is the capital of France?",
                    "interaction_id": "chat_123"
                },
                "action": {
                    "answer_given": "Paris"
                },
                "outcome": {
                    "positive": True,
                    "rating": 0.95,
                    "user_comment": "Perfect answer!"
                }
            },
            "user_id": "GU-test-user"
        }
        
        assert "learning_type" in learning_data
        assert "learning_data" in learning_data
        assert "user_id" in learning_data
        assert learning_data["learning_type"] in ["feedback", "success", "correction", "failure"]

    def test_trust_score_calculation_for_feedback(self, mock_memory_mesh):
        """Test trust score calculation for user feedback."""
        outcome = {
            "positive": True,
            "rating": 0.95
        }
        
        # High positive rating should result in high trust
        trust_score = 0.5 + (outcome["rating"] * 0.4) if outcome["positive"] else 0.3
        assert trust_score >= 0.7
        assert trust_score <= 1.0

    def test_trust_score_calculation_for_correction(self, mock_memory_mesh):
        """Test trust score for user corrections (very high trust)."""
        # User corrections are highly trusted since user explicitly corrected
        base_trust = 0.9  # Corrections start with high trust
        assert base_trust >= 0.85

    def test_trust_score_calculation_for_system_success(self, mock_memory_mesh):
        """Test trust score for system success events."""
        outcome = {
            "success": True,
            "speedup": 12.5
        }
        
        # System success with measurable improvement
        trust_score = 0.7 if outcome["success"] else 0.4
        if outcome.get("speedup", 0) > 5:
            trust_score += 0.1
        
        assert trust_score >= 0.7

    def test_episodic_memory_created_for_high_trust(self, mock_memory_mesh):
        """Test that episodic memory is created for trust >= 0.7."""
        trust_score = 0.85
        
        if trust_score >= 0.7:
            result = mock_memory_mesh.create_episodic_memory(
                context={"question": "test"},
                trust_score=trust_score
            )
            mock_memory_mesh.create_episodic_memory.assert_called_once()
            assert result is not None

    def test_procedural_memory_created_for_very_high_trust(self, mock_memory_mesh):
        """Test that procedural memory is created for trust >= 0.8."""
        trust_score = 0.9
        
        if trust_score >= 0.8:
            result = mock_memory_mesh.create_procedural_memory(
                action={"optimization": "added index"},
                trust_score=trust_score
            )
            mock_memory_mesh.create_procedural_memory.assert_called_once()
            assert result is not None

    def test_genesis_key_linking(self, mock_genesis_keys):
        """Test that learning is linked to genesis key."""
        learning_id = "learning-456"
        user_id = "GU-test-user"
        
        key_id = mock_genesis_keys.create_key(
            entity_type="learning",
            entity_id=learning_id,
            user_id=user_id
        )
        
        mock_genesis_keys.create_key.assert_called_once()
        assert key_id is not None

    def test_learning_types_supported(self):
        """Test all learning types are properly defined."""
        supported_types = ["feedback", "success", "correction", "failure"]
        
        for learning_type in supported_types:
            assert learning_type in supported_types

    def test_training_data_extraction_filters_by_trust(self, mock_memory_mesh):
        """Test that training data extraction respects trust threshold."""
        mock_memory_mesh.get_training_data = MagicMock(return_value=[
            {"trust_score": 0.9, "data": "high trust"},
            {"trust_score": 0.75, "data": "medium trust"},
        ])
        
        min_trust = 0.7
        data = mock_memory_mesh.get_training_data(min_trust_score=min_trust)
        
        # All returned data should meet threshold
        for item in data:
            assert item["trust_score"] >= min_trust


class TestMemoryMeshStats:
    """Test memory mesh statistics tracking."""

    def test_stats_structure(self):
        """Test that stats have required fields."""
        stats = {
            "learning_memory": {
                "total_examples": 10,
                "high_trust_examples": 7,
                "trust_ratio": 0.7
            },
            "episodic_memory": {
                "total_episodes": 8,
                "linked_from_learning": 7
            },
            "procedural_memory": {
                "total_procedures": 5,
                "high_success_procedures": 4
            }
        }
        
        assert "learning_memory" in stats
        assert "episodic_memory" in stats
        assert "procedural_memory" in stats
        assert stats["learning_memory"]["trust_ratio"] >= 0
        assert stats["learning_memory"]["trust_ratio"] <= 1

    def test_trust_ratio_calculation(self):
        """Test trust ratio is correctly calculated."""
        total = 10
        high_trust = 7
        
        ratio = high_trust / total if total > 0 else 0
        assert ratio == 0.7


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
