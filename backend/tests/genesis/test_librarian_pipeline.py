import pytest
import os
import json
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path
from backend.genesis.librarian_pipeline import LibrarianPipeline, ContentType

@pytest.fixture
def librarian(tmp_path):
    with patch('backend.genesis.librarian_pipeline.get_genesis_key_service') as mock_gk, \
         patch('backend.genesis.librarian_pipeline.get_mirror_system') as mock_mirror:
        
        # Mock GK Service
        gk_service = MagicMock()
        mock_key = MagicMock()
        mock_key.genesis_key = "gk-test-123"
        gk_service.create_key.return_value = mock_key
        mock_gk.return_value = gk_service
        
        mock_mirror.return_value = MagicMock()
        
        lib = LibrarianPipeline(storage_dir=str(tmp_path / "storage"))
        return lib

def test_initialization(librarian, tmp_path):
    assert os.path.exists(tmp_path / "storage" / "documents")
    assert os.path.exists(tmp_path / "storage" / "code")
    assert librarian._genesis_service is not None

def test_detect_content_type(librarian):
    assert librarian._detect_content_type("script.py") == ContentType.CODE
    assert librarian._detect_content_type("docs.md") == ContentType.DOCUMENT
    assert librarian._detect_content_type("data.json") == ContentType.DATA
    assert librarian._detect_content_type("unknown.xyz") == ContentType.UNKNOWN

@pytest.mark.asyncio
async def test_ingest_content(librarian):
    content = b"print('hello librarian')"
    filename = "hello.py"
    
    # Mock indexer and memory
    with patch.object(librarian, '_index_content', new_callable=AsyncMock) as mock_index, \
         patch.object(librarian, '_store_in_memory', new_callable=AsyncMock) as mock_memory:
        
        mock_index.return_value = "idx-1"
        mock_memory.return_value = "mem-1"
        
        result = await librarian.ingest_content(content, filename)
        
        assert result.success is True
        assert result.genesis_key.startswith("gk-")
        assert result.status == "complete"
        assert result.index_id == "idx-1"
        assert result.memory_id == "mem-1"
        
        # Verify file was written
        assert os.path.exists(result.destination)
        with open(result.destination, "rb") as f:
            assert f.read() == content
            
        # Verify registry was updated
        assert result.ingestion_id in librarian.registry
        record = librarian.registry[result.ingestion_id]
        assert record.content_type == ContentType.CODE

@pytest.mark.asyncio
async def test_ingest_file(librarian, tmp_path):
    test_file = tmp_path / "sample.txt"
    test_file.write_text("sample content")
    
    with patch.object(librarian, '_index_content', new=AsyncMock()), \
         patch.object(librarian, '_store_in_memory', new=AsyncMock()):
             
        result = await librarian.ingest_file(str(test_file))
        assert result.success is True
        assert result.status == "complete"
        
        missing_result = await librarian.ingest_file(str(tmp_path / "notfound.txt"))
        assert missing_result.success is False
        assert missing_result.status == "failed"

if __name__ == "__main__":
    pytest.main(['-v', __file__])
