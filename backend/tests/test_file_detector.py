"""
Test script to diagnose file change detection.
Tests CREATE, READ, UPDATE, DELETE operations on knowledge_base folder.
"""

import sys
sys.path.insert(0, '.')

import time
import json
from pathlib import Path
import pytest

from ingestion.file_manager import IngestionFileManager
from embedding import get_embedding_model

# Skip all tests in this module if torch is not available
pytestmark = pytest.mark.skipif(
    get_embedding_model is None,
    reason="Embedding model not available (torch not installed)"
)

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def print_state(fm):
    """Print current state of file manager"""
    print(f"Tracked files in state: {len(fm.file_states)}")
    for filepath, hash_val in fm.file_states.items():
        print(f"  - {filepath}: {hash_val[:8]}...")
    
    if fm.state_file.exists():
        with open(fm.state_file, 'r') as f:
            state = json.load(f)
            print(f"State file contents: {len(state)} files")

def test_file_creation():
    """Test detection of new files"""
    print_section("TEST 1: FILE CREATION")
    
    kb_path = Path('knowledge_base')
    
    # Clean up
    test_file = kb_path / "test_create.txt"
    if test_file.exists():
        test_file.unlink()
    
    # Reload file manager (empty state)
    embedding_model = get_embedding_model()
    fm = IngestionFileManager(kb_path, embedding_model=embedding_model)
    
    print("BEFORE: ")
    print_state(fm)
    
    # Create a file
    print("\nCreating test_create.txt...")
    test_file.write_text("This is a test file created for detection testing.")
    time.sleep(1)
    
    # Scan
    print("\nScanning for changes...")
    results = fm.scan_directory()
    
    print(f"\nScan results: {len(results)} changes")
    for r in results:
        print(f"  {r.change_type}: {r.filepath} - {'✓' if r.success else '✗ ' + (r.error or '')}")
    
    print("\nAFTER: ")
    print_state(fm)
    
    # Cleanup
    test_file.unlink()
    return len(results) > 0

def test_file_modification():
    """Test detection of modified files"""
    print_section("TEST 2: FILE MODIFICATION")
    
    kb_path = Path('knowledge_base')
    test_file = kb_path / "test_modify.txt"
    
    # Clean up and create initial file
    if test_file.exists():
        test_file.unlink()
    
    print("Creating initial file...")
    test_file.write_text("Original content")
    time.sleep(0.5)
    
    # Load file manager
    embedding_model = get_embedding_model()
    fm = IngestionFileManager(kb_path, embedding_model=embedding_model)
    
    # First scan to track the file
    print("\nFirst scan (to establish baseline)...")
    results1 = fm.scan_directory()
    print(f"Results: {len(results1)} changes")
    
    print("\nBEFORE MODIFICATION: ")
    print_state(fm)
    
    # Modify the file
    print("\nModifying test_modify.txt...")
    time.sleep(1)
    test_file.write_text("Original content\nModified with new line")
    time.sleep(0.5)
    
    # Scan again
    print("\nSecond scan (to detect modification)...")
    results2 = fm.scan_directory()
    
    print(f"\nScan results: {len(results2)} changes")
    for r in results2:
        print(f"  {r.change_type}: {r.filepath} - {'✓' if r.success else '✗ ' + (r.error or '')}")
    
    print("\nAFTER MODIFICATION: ")
    print_state(fm)
    
    # Cleanup
    test_file.unlink()
    return any(r.change_type == 'modified' for r in results2)

def test_file_deletion():
    """Test detection of deleted files"""
    print_section("TEST 3: FILE DELETION")
    
    kb_path = Path('knowledge_base')
    test_file = kb_path / "test_delete.txt"
    
    # Clean up and create initial file
    if test_file.exists():
        test_file.unlink()
    
    print("Creating initial file...")
    test_file.write_text("This file will be deleted")
    time.sleep(0.5)
    
    # Load file manager
    embedding_model = get_embedding_model()
    fm = IngestionFileManager(kb_path, embedding_model=embedding_model)
    
    # First scan to track the file
    print("\nFirst scan (to establish baseline)...")
    results1 = fm.scan_directory()
    print(f"Results: {len(results1)} changes")
    
    print("\nBEFORE DELETION: ")
    print_state(fm)
    
    # Delete the file
    print("\nDeleting test_delete.txt...")
    test_file.unlink()
    time.sleep(0.5)
    
    # Scan again
    print("\nSecond scan (to detect deletion)...")
    results2 = fm.scan_directory()
    
    print(f"\nScan results: {len(results2)} changes")
    for r in results2:
        print(f"  {r.change_type}: {r.filepath} - {'✓' if r.success else '✗ ' + (r.error or '')}")
    
    print("\nAFTER DELETION: ")
    print_state(fm)
    
    return any(r.change_type == 'deleted' for r in results2)

def test_existing_file_detection():
    """Test detection of files that exist but aren't in state (like text.txt)"""
    print_section("TEST 4: EXISTING FILE DETECTION (like text.txt)")
    
    kb_path = Path('knowledge_base')
    
    # Clean state file to simulate fresh start
    state_file = kb_path / ".ingestion_state.json"
    if state_file.exists():
        state_file.unlink()
        print("Deleted state file to simulate fresh start")
    
    # Check if text.txt exists
    text_file = kb_path / "text.txt"
    if text_file.exists():
        print(f"\nFound existing text.txt ({text_file.stat().st_size} bytes)")
    else:
        print("\ntext.txt not found, creating it...")
        text_file.write_text("Sample content for testing")
    
    time.sleep(0.5)
    
    # Load file manager with empty state
    embedding_model = get_embedding_model()
    fm = IngestionFileManager(kb_path, embedding_model=embedding_model)
    
    print("\nBEFORE SCAN: ")
    print_state(fm)
    
    # Scan should detect text.txt as new
    print("\nScanning (should detect text.txt as new file)...")
    results = fm.scan_directory()
    
    print(f"\nScan results: {len(results)} changes")
    for r in results:
        print(f"  {r.change_type}: {r.filepath} - {'✓' if r.success else '✗ ' + (r.error or '')}")
    
    print("\nAFTER SCAN: ")
    print_state(fm)
    
    return any('text.txt' in r.filepath for r in results)

if __name__ == '__main__':
    print("🔍 FILE CHANGE DETECTOR DIAGNOSTIC TEST SUITE\n")
    
    # Initialize embedding model once
    print("Loading embedding model (this may take a moment)...")
    get_embedding_model()
    print("✓ Embedding model loaded\n")
    
    results = {}
    
    try:
        results['creation'] = test_file_creation()
    except Exception as e:
        print(f"✗ Creation test failed: {e}")
        import traceback
        traceback.print_exc()
        results['creation'] = False
    
    try:
        results['modification'] = test_file_modification()
    except Exception as e:
        print(f"✗ Modification test failed: {e}")
        import traceback
        traceback.print_exc()
        results['modification'] = False
    
    try:
        results['deletion'] = test_file_deletion()
    except Exception as e:
        print(f"✗ Deletion test failed: {e}")
        import traceback
        traceback.print_exc()
        results['deletion'] = False
    
    try:
        results['existing'] = test_existing_file_detection()
    except Exception as e:
        print(f"✗ Existing file detection test failed: {e}")
        import traceback
        traceback.print_exc()
        results['existing'] = False
    
    print_section("SUMMARY")
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(results.values())
    print(f"\n{'='*60}")
    if all_passed:
        print("✓ ALL TESTS PASSED")
    else:
        print("✗ SOME TESTS FAILED")
    print(f"{'='*60}\n")
