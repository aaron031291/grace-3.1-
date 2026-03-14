import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path
from backend.genesis.whitelist_learning_pipeline import (
    WhitelistLearningPipeline,
    WhitelistEntry,
    PipelineStage,
    DataCategory,
    TrustLevel,
    get_whitelist_pipeline,
    process_whitelist_entry
)

@pytest.fixture
def mock_storage_dir(tmp_path):
    return str(tmp_path / "whitelist")

@pytest.fixture
def mock_dependencies():
    with patch('backend.genesis.whitelist_learning_pipeline.get_genesis_key_service') as genesis, \
         patch('backend.genesis.whitelist_learning_pipeline.get_cognitive_engine') as cog, \
         patch('backend.genesis.whitelist_learning_pipeline.get_mirror_system') as mirror, \
         patch('backend.genesis.whitelist_learning_pipeline.get_active_learning') as active, \
         patch('backend.genesis.whitelist_learning_pipeline.get_memory_mesh_learner') as mesh, \
         patch('backend.genesis.whitelist_learning_pipeline.get_contradiction_detector') as contradict, \
         patch('backend.genesis.whitelist_learning_pipeline.get_proactive_learner') as proactive, \
         patch('backend.genesis.whitelist_learning_pipeline.get_embedder') as embedder, \
         patch('backend.genesis.whitelist_learning_pipeline.get_librarian_pipeline') as lib, \
         patch('backend.genesis.whitelist_learning_pipeline.get_learning_memory') as memory, \
         patch('backend.genesis.whitelist_learning_pipeline.get_ml_intelligence') as ml:
        
        # Setup async mocks where needed
        cog.return_value.process = AsyncMock(return_value={"result": "valid"})
        lib.return_value.ingest_content = AsyncMock(return_value=MagicMock(success=True, destination="/fake/path.md"))
        embedder.return_value.add_document = AsyncMock(return_value=True)
        
        yield {
            "genesis": genesis,
            "cognitive": cog,
            "librarian": lib,
            "embedder": embedder
        }

@pytest.mark.asyncio
async def test_pipeline_initialization_and_process(mock_storage_dir, mock_dependencies):
    pipeline = WhitelistLearningPipeline(storage_dir=mock_storage_dir)
    
    # Act
    result = await pipeline.process(
        content="This is a crucial architecture decision.",
        source="human_admin",
        category=DataCategory.DOCUMENTATION,
        trust_level=TrustLevel.HIGH
    )
    
    # Assert
    assert result.success is True
    assert result.stage == PipelineStage.COMPLETE
    assert result.trust_score == 0.75  # HIGH trust level map
    assert "whitelist_entry" in result.stages_completed or "trust_verification" in result.stages_completed
    
    # Ensure dependencies were called
    mock_dependencies["cognitive"].return_value.process.assert_called_once()
    mock_dependencies["librarian"].return_value.ingest_content.assert_called_once()
    mock_dependencies["embedder"].return_value.add_document.assert_called_once()

@pytest.mark.asyncio
async def test_pipeline_low_trust_rejection(mock_storage_dir, mock_dependencies):
    pipeline = WhitelistLearningPipeline(storage_dir=mock_storage_dir)
    
    # Act
    result = await pipeline.process(
        content="Random spam",
        source="unknown_user",
        category=DataCategory.FEEDBACK,
        trust_level=TrustLevel.UNTRUSTED
    )
    
    # Assert
    assert result.success is False
    assert result.stage == PipelineStage.FAILED
    assert "Trust level too low" in result.error

def test_pipeline_statistics(mock_storage_dir, mock_dependencies):
    pipeline = WhitelistLearningPipeline(storage_dir=mock_storage_dir)
    
    # Mock some entries
    pipeline.entries["entry1"] = WhitelistEntry(
        entry_id="entry1", source="test", category=DataCategory.CODE_SNIPPET, 
        content="code", metadata={}, trust_level=TrustLevel.OWNER, created_at="now"
    )
    
    pipeline.results["entry1"] = MagicMock(success=True)
    
    stats = pipeline.get_statistics()
    
    assert stats["total_entries"] == 1
    assert stats["successful"] == 1
    assert stats["success_rate"] == 1.0
    assert stats["by_category"][DataCategory.CODE_SNIPPET.value] == 1
    assert stats["by_trust_level"][TrustLevel.OWNER.value] == 1

if __name__ == "__main__":
    pytest.main(['-v', __file__])
