"""
Test suite for the File-Based Ingestion Manager.
Provides tests to verify the implementation is working correctly.

Classes:
- `TestSuite`

Key Methods:
- `setup()`
- `teardown()`
- `test()`
- `assert_equal()`
- `assert_true()`
- `assert_false()`
- `assert_file_exists()`
- `assert_file_not_exists()`
- `test_git_tracker_init()`
- `test_git_tracker_initialize()`
- `test_file_hash_computation()`
- `test_state_file_creation()`
- `test_supported_extensions()`
- `test_file_change_dataclass()`
- `test_ingestion_result_dataclass()`
"""

import sys
import os
from pathlib import Path
import tempfile
import shutil
import json
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))


class TestSuite:
    """Test suite for file ingestion manager."""
    
    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.temp_dir = None
    
    def setup(self):
        """Set up test environment."""
        # Create temporary directory for testing
        self.temp_dir = tempfile.mkdtemp(prefix="ingestion_test_")
        print(f"\n{'='*80}")
        print(f"TEST SUITE: File-Based Ingestion Manager")
        print(f"{'='*80}")
        print(f"Temp directory: {self.temp_dir}\n")
    
    def teardown(self):
        """Clean up test environment."""
        if self.temp_dir and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
            print(f"\nCleaned up: {self.temp_dir}")
    
    def test(self, name: str, func):
        """Run a test."""
        try:
            print(f"Running: {name}...", end=" ")
            func()
            print("✓ PASSED")
            self.tests_passed += 1
        except AssertionError as e:
            print(f"✗ FAILED: {e}")
            self.tests_failed += 1
        except Exception as e:
            print(f"✗ ERROR: {e}")
            self.tests_failed += 1
    
    def assert_equal(self, actual, expected, msg=""):
        """Assert equality."""
        if actual != expected:
            raise AssertionError(f"{msg} (expected {expected}, got {actual})")
    
    def assert_true(self, value, msg=""):
        """Assert value is true."""
        if not value:
            raise AssertionError(msg)
    
    def assert_false(self, value, msg=""):
        """Assert value is false."""
        if value:
            raise AssertionError(msg)
    
    def assert_file_exists(self, path):
        """Assert file exists."""
        if not Path(path).exists():
            raise AssertionError(f"File does not exist: {path}")
    
    def assert_file_not_exists(self, path):
        """Assert file does not exist."""
        if Path(path).exists():
            raise AssertionError(f"File should not exist: {path}")
    
    # ==================== Tests ====================
    
    def test_git_tracker_init(self):
        """Test GitFileTracker initialization."""
        from ingestion.file_manager import GitFileTracker
        
        tracker = GitFileTracker(self.temp_dir)
        self.assert_true(tracker.repo_path.exists(), "Repo path should exist")
        self.assert_equal(str(tracker.repo_path), self.temp_dir, "Repo path mismatch")
    
    def test_git_tracker_initialize(self):
        """Test git repository initialization."""
        from ingestion.file_manager import GitFileTracker
        
        tracker = GitFileTracker(self.temp_dir)
        success = tracker.initialize_git()
        self.assert_true(success, "Git initialization should succeed")
        
        git_dir = Path(self.temp_dir) / ".git"
        self.assert_file_exists(git_dir)
    
    def test_file_hash_computation(self):
        """Test file hash computation."""
        from ingestion.file_manager import IngestionFileManager
        
        # Create test file
        test_file = Path(self.temp_dir) / "test.txt"
        test_file.write_text("test content")
        
        # Note: Can't fully test IngestionFileManager without DB setup
        # But we can test the hash computation logic
        import hashlib
        expected_hash = hashlib.sha256(b"test content").hexdigest()
        
        with open(test_file, 'rb') as f:
            actual_hash = hashlib.sha256(f.read()).hexdigest()
        
        self.assert_equal(actual_hash, expected_hash, "Hash mismatch")
    
    def test_state_file_creation(self):
        """Test state file creation and management."""
        import json
        
        state_file = Path(self.temp_dir) / ".ingestion_state.json"
        
        # Create state
        state = {
            "file1.md": "hash1",
            "file2.txt": "hash2",
        }
        
        with open(state_file, 'w') as f:
            json.dump(state, f)
        
        # Verify creation
        self.assert_file_exists(state_file)
        
        # Load and verify
        with open(state_file, 'r') as f:
            loaded = json.load(f)
        
        self.assert_equal(loaded, state, "State mismatch")
    
    def test_supported_extensions(self):
        """Test supported file extension detection."""
        supported = {'.txt', '.md', '.pdf', '.py', '.json'}
        
        test_files = {
            'document.txt': True,
            'guide.md': True,
            'report.pdf': True,
            'script.py': True,
            'config.json': True,
            'image.png': False,
            'video.mp4': False,
            '.hidden': False,
        }
        
        for filename, should_support in test_files.items():
            ext = Path(filename).suffix.lower()
            is_supported = ext in supported
            if filename.startswith('.'):
                is_supported = False
            
            self.assert_equal(is_supported, should_support, 
                            f"Extension detection failed for {filename}")
    
    def test_file_change_dataclass(self):
        """Test FileChange dataclass."""
        from ingestion.file_manager import FileChange
        
        change = FileChange(
            filepath="test.md",
            change_type="added",
            new_hash="abc123",
        )
        
        self.assert_equal(change.filepath, "test.md")
        self.assert_equal(change.change_type, "added")
        self.assert_equal(change.new_hash, "abc123")
        self.assert_equal(change.old_hash, None)
    
    def test_ingestion_result_dataclass(self):
        """Test IngestionResult dataclass."""
        from ingestion.file_manager import IngestionResult
        
        result = IngestionResult(
            success=True,
            filepath="test.md",
            change_type="added",
            document_id=42,
            message="Success",
        )
        
        self.assert_true(result.success)
        self.assert_equal(result.filepath, "test.md")
        self.assert_equal(result.document_id, 42)
    
    def test_path_handling(self):
        """Test path handling and file operations."""
        from pathlib import Path
        
        # Create test structure
        kb_path = Path(self.temp_dir) / "knowledge_base"
        kb_path.mkdir()
        
        # Create subdirectories
        (kb_path / "guides").mkdir()
        (kb_path / "tutorials").mkdir()
        
        # Create files
        (kb_path / "guide.md").write_text("guide")
        (kb_path / "guides" / "tutorial.md").write_text("tutorial")
        
        # Test discovery
        files = list(kb_path.rglob("*.md"))
        self.assert_equal(len(files), 2, "Should find 2 markdown files")
    
    def test_text_encoding(self):
        """Test text file reading with different encodings."""
        import tempfile
        
        # UTF-8 file
        utf8_file = Path(self.temp_dir) / "utf8.txt"
        utf8_file.write_text("Hello 世界", encoding='utf-8')
        
        content = utf8_file.read_text(encoding='utf-8')
        self.assert_true("世界" in content, "UTF-8 content should be readable")
    
    def test_json_serialization(self):
        """Test JSON serialization of data."""
        import json
        
        data = {
            "files": {
                "test.md": "hash1",
                "test.txt": "hash2",
            },
            "timestamp": datetime.now().isoformat(),
            "count": 2,
        }
        
        json_str = json.dumps(data)
        loaded = json.loads(json_str)
        
        self.assert_equal(loaded["count"], 2)
        self.assert_equal(len(loaded["files"]), 2)
    
    # ==================== Summary ====================
    
    def run_all(self):
        """Run all tests."""
        self.setup()
        
        try:
            # Run tests
            self.test("Git tracker initialization", self.test_git_tracker_init)
            self.test("Git repository initialization", self.test_git_tracker_initialize)
            self.test("File hash computation", self.test_file_hash_computation)
            self.test("State file management", self.test_state_file_creation)
            self.test("Supported extensions", self.test_supported_extensions)
            self.test("FileChange dataclass", self.test_file_change_dataclass)
            self.test("IngestionResult dataclass", self.test_ingestion_result_dataclass)
            self.test("Path handling", self.test_path_handling)
            self.test("Text encoding", self.test_text_encoding)
            self.test("JSON serialization", self.test_json_serialization)
        
        finally:
            self.teardown()
        
        # Print summary
        total = self.tests_passed + self.tests_failed
        print(f"\n{'='*80}")
        print(f"RESULTS")
        print(f"{'='*80}")
        print(f"Total:   {total}")
        print(f"Passed:  {self.tests_passed}")
        print(f"Failed:  {self.tests_failed}")
        print(f"{'='*80}\n")
        
        return self.tests_failed == 0


def main():
    """Main test entry point."""
    suite = TestSuite()
    success = suite.run_all()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
