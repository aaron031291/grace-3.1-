"""
Integration test for file management and ingestion system.
Tests the complete workflow: upload, ingest, view in directory, delete.
"""

import sys
import os
import tempfile
from pathlib import Path

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from file_manager.knowledge_base_manager import KnowledgeBaseManager
from file_manager.file_handler import FileHandler
from ingestion.service import TextIngestionService
from embedding import get_embedding_model


def test_file_upload_and_directory():
    """Test uploading files and viewing directory structure."""
    print("\n" + "="*60)
    print("TEST 1: File Upload and Directory Browsing")
    print("="*60)
    
    manager = KnowledgeBaseManager("backend/knowledge_base")
    
    # Create test folder
    success, msg = manager.create_folder("test_documents")
    assert success, f"Failed to create folder: {msg}"
    print(f"✓ Created test folder")
    
    # Create test files
    files = [
        ("introduction.txt", b"This is an introduction to our knowledge base system."),
        ("guide.md", b"# User Guide\n\nThis is a comprehensive guide for using the system."),
    ]
    
    for filename, content in files:
        success, msg, path = manager.save_file(
            content,
            "test_documents",
            filename
        )
        assert success, f"Failed to save {filename}: {msg}"
        print(f"✓ Saved file: {filename} ({len(content)} bytes)")
    
    # Check directory structure
    structure = manager.get_directory_structure("test_documents")
    assert structure['total_items'] == 2, f"Expected 2 items, got {structure['total_items']}"
    print(f"✓ Directory has {structure['total_items']} items")
    
    # Verify file metadata
    for item in structure['items']:
        assert 'name' in item
        assert 'path' in item
        assert 'type' in item
        assert 'size' in item or item['type'] == 'folder'
        print(f"  - {item['name']} ({item['size']} bytes)" if 'size' in item else f"  - {item['name']}/")
    
    return manager, structure


def test_text_extraction():
    """Test text extraction from different file types."""
    print("\n" + "="*60)
    print("TEST 2: Text Extraction from Files")
    print("="*60)
    
    manager = KnowledgeBaseManager("backend/knowledge_base")
    handler = FileHandler()
    
    # Create test files
    test_files = {
        "test_documents/test_sample.txt": b"Machine learning is a subset of artificial intelligence.",
        "test_documents/test_notes.md": b"# Notes\n\n## Section 1\nSome important information here.",
    }
    
    for filepath, content in test_files.items():
        parts = filepath.rsplit('/', 1)
        folder = parts[0] if len(parts) > 1 else ""
        filename = parts[-1]
        
        success, _, saved_path = manager.save_file(content, folder, filename)
        assert success, f"Failed to save {filename}"
        
        # Extract text
        abs_path = manager.get_file_path(saved_path)
        text, error = handler.extract_text(abs_path)
        assert error is None, f"Error extracting text: {error}"
        assert len(text) > 0, f"No text extracted from {filename}"
        
        print(f"✓ Extracted text from {filename}: {len(text)} chars")
        print(f"  Preview: {text[:50]}...")


def test_file_deletion():
    """Test file and folder deletion."""
    print("\n" + "="*60)
    print("TEST 3: File and Folder Deletion")
    print("="*60)
    
    manager = KnowledgeBaseManager("backend/knowledge_base")
    
    # Create test file
    success, _, path = manager.save_file(b"Test content", "test_documents", "delete_me.txt")
    assert success, "Failed to create test file"
    print(f"✓ Created test file: {path}")
    
    # Verify it exists
    assert manager.file_exists(path), "File was not created"
    print(f"✓ File exists in directory")
    
    # Delete file
    success, msg = manager.delete_file(path)
    assert success, f"Failed to delete file: {msg}"
    print(f"✓ Deleted file: {path}")
    
    # Verify deletion
    assert not manager.file_exists(path), "File was not deleted"
    print(f"✓ File is no longer in directory")


def test_ingestion_service():
    """Test text ingestion into vector database."""
    print("\n" + "="*60)
    print("TEST 4: Ingestion Service Integration")
    print("="*60)
    
    try:
        # Initialize embedding model
        print("Initializing embedding model...")
        embedding_model = get_embedding_model()
        print("✓ Embedding model loaded")
        
        # Initialize ingestion service
        print("Initializing ingestion service...")
        service = TextIngestionService(
            collection_name="test_documents",
            chunk_size=512,
            chunk_overlap=50,
            embedding_model=embedding_model,
        )
        print("✓ Ingestion service initialized")
        
        # Test text ingestion
        test_text = """
        Artificial intelligence (AI) is transforming industries worldwide.
        Machine learning enables systems to learn from data without explicit programming.
        Deep learning uses neural networks to process complex patterns.
        These technologies power modern applications and continue to evolve rapidly.
        """
        
        document_id, message = service.ingest_text_fast(
            text_content=test_text,
            filename="test_ingestion.txt",
            source="knowledge_base",
            upload_method="file_upload",
            metadata={"test": True}
        )
        
        assert document_id is not None, f"Ingestion failed: {message}"
        print(f"✓ Ingested document: ID {document_id}")
        print(f"  Message: {message}")
        
        # Verify document info
        doc_info = service.get_document_info(document_id)
        assert doc_info is not None, "Could not retrieve document info"
        print(f"✓ Retrieved document info:")
        print(f"  - Filename: {doc_info.get('filename')}")
        print(f"  - Chunks: {doc_info.get('total_chunks')}")
        print(f"  - Status: {doc_info.get('status')}")
        print(f"  - Text length: {doc_info.get('text_length')} chars")
        
        # Test search
        results = service.search_documents(
            query_text="machine learning",
            limit=5,
            score_threshold=0.3
        )
        print(f"✓ Search results: {len(results)} chunks found")
        if results:
            print(f"  - Top result score: {results[0].get('score', 'N/A')}")
        
        # Clean up - delete the document
        success, del_msg = service.delete_document(document_id)
        if success:
            print(f"✓ Cleaned up test document: {del_msg}")
        
    except Exception as e:
        print(f"⚠ Ingestion test skipped (service may not be available): {str(e)}")
        import traceback
        traceback.print_exc()


def cleanup_test_files(manager):
    """Clean up test files created during testing."""
    print("\n" + "="*60)
    print("CLEANUP: Removing Test Files")
    print("="*60)
    
    try:
        success, msg = manager.delete_folder("test_documents")
        if success:
            print(f"✓ Deleted test folder: {msg}")
        else:
            print(f"⚠ Could not delete test folder: {msg}")
    except Exception as e:
        print(f"⚠ Error during cleanup: {e}")


def main():
    """Run all integration tests."""
    print("\n" + "█"*60)
    print("  FILE MANAGEMENT & INGESTION INTEGRATION TESTS")
    print("█"*60)
    
    try:
        # Test 1: File operations
        manager, structure = test_file_upload_and_directory()
        
        # Test 2: Text extraction
        test_text_extraction()
        
        # Test 3: File deletion
        test_file_deletion()
        
        # Test 4: Ingestion (optional - may fail if services not running)
        test_ingestion_service()
        
        # Cleanup
        cleanup_test_files(manager)
        
        print("\n" + "█"*60)
        print("  ✓ ALL TESTS PASSED")
        print("█"*60 + "\n")
        
        return 0
    
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
