"""
Tests for TransformationPatternMiner

Tests:
1. Git diff parsing (_parse_git_diff)
2. Pattern extraction from diffs (_extract_patterns_from_diff)
3. File pattern analysis (_analyze_file_patterns)
4. Pattern format validation
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
import atexit

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


# Windows-compatible temp file cleanup
_temp_files_to_cleanup = []


def _cleanup_temp_files():
    for f in _temp_files_to_cleanup:
        try:
            if os.path.exists(f):
                os.unlink(f)
        except Exception:
            pass


atexit.register(_cleanup_temp_files)


@pytest.fixture
def temp_python_file():
    """Create a temporary Python file for testing (Windows-compatible)."""
    def _create(content):
        fd, path = tempfile.mkstemp(suffix='.py', text=True)
        _temp_files_to_cleanup.append(path)
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(content)
        return path
    return _create


@pytest.fixture
def temp_binary_file():
    """Create a temporary binary file for testing (Windows-compatible)."""
    def _create(content):
        fd, path = tempfile.mkstemp(suffix='.py')
        _temp_files_to_cleanup.append(path)
        with os.fdopen(fd, 'wb') as f:
            f.write(content)
        return path
    return _create


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    return Mock()


@pytest.fixture
def mock_outcome_ledger():
    """Create a mock OutcomeLedger."""
    ledger = Mock()
    ledger.get_by_layer.return_value = []
    return ledger


@pytest.fixture
def pattern_miner(mock_session, mock_outcome_ledger):
    """Create a PatternMiner instance with mocked dependencies."""
    with patch('cognitive.transformation_library.pattern_miner.MagmaMemorySystem'):
        with patch('cognitive.transformation_library.pattern_miner.MemoryMeshIntegration'):
            from cognitive.transformation_library.pattern_miner import TransformationPatternMiner
            return TransformationPatternMiner(
                session=mock_session,
                outcome_ledger=mock_outcome_ledger,
                magma_memory=None,
                memory_mesh=None
            )


class TestParseGitDiff:
    """Tests for _parse_git_diff method."""

    def test_extracts_added_lines(self, pattern_miner):
        """Test that added lines are extracted correctly."""
        diff_output = """diff --git a/test.py b/test.py
--- a/test.py
+++ b/test.py
@@ -1,3 +1,4 @@
 def hello():
+    print("added line")
     return "hello"
"""
        result = pattern_miner._parse_git_diff(diff_output, "abc123")
        
        assert len(result) == 1
        assert '    print("added line")' in result[0]["added"]

    def test_extracts_removed_lines(self, pattern_miner):
        """Test that removed lines are extracted correctly."""
        diff_output = """diff --git a/test.py b/test.py
--- a/test.py
+++ b/test.py
@@ -1,4 +1,3 @@
 def hello():
-    print("removed line")
     return "hello"
"""
        result = pattern_miner._parse_git_diff(diff_output, "abc123")
        
        assert len(result) == 1
        assert '    print("removed line")' in result[0]["removed"]

    def test_extracts_context_lines(self, pattern_miner):
        """Test that context lines are extracted correctly."""
        diff_output = """diff --git a/test.py b/test.py
--- a/test.py
+++ b/test.py
@@ -1,4 +1,4 @@
 def hello():
-    old_line = 1
+    new_line = 2
     return "hello"
"""
        result = pattern_miner._parse_git_diff(diff_output, "abc123")
        
        assert len(result) == 1
        assert "def hello():" in result[0]["context"]
        assert '    return "hello"' in result[0]["context"]

    def test_handles_multiple_files(self, pattern_miner):
        """Test that multiple files in a diff are parsed separately."""
        diff_output = """diff --git a/file1.py b/file1.py
--- a/file1.py
+++ b/file1.py
@@ -1,2 +1,3 @@
 def func1():
+    pass
diff --git a/file2.py b/file2.py
--- a/file2.py
+++ b/file2.py
@@ -1,2 +1,3 @@
 def func2():
+    return None
"""
        result = pattern_miner._parse_git_diff(diff_output, "abc123")
        
        assert len(result) == 2
        assert result[0]["file"] == "file1.py"
        assert result[1]["file"] == "file2.py"
        assert "    pass" in result[0]["added"]
        assert "    return None" in result[1]["added"]

    def test_includes_commit_hash(self, pattern_miner):
        """Test that commit hash is included in parsed result."""
        diff_output = """diff --git a/test.py b/test.py
--- a/test.py
+++ b/test.py
@@ -1,2 +1,3 @@
 def hello():
+    pass
"""
        result = pattern_miner._parse_git_diff(diff_output, "commit123hash")
        
        assert result[0]["commit"] == "commit123hash"

    def test_handles_empty_diff(self, pattern_miner):
        """Test that empty diff returns empty list."""
        result = pattern_miner._parse_git_diff("", "abc123")
        assert result == []


class TestExtractPatternsFromDiff:
    """Tests for _extract_patterns_from_diff method."""

    def test_detects_error_handling_pattern(self, pattern_miner):
        """Test detection of added error handling (try/except)."""
        diff_info = {
            "file": "handler.py",
            "added": [
                "try:",
                "    result = process()",
                "except Exception as e:",
                "    logger.error(e)"
            ],
            "removed": [
                "result = process()"
            ]
        }
        
        patterns = pattern_miner._extract_patterns_from_diff(diff_info)
        
        signatures = [p["signature"] for p in patterns]
        assert "add_error_handling" in signatures

    def test_detects_logging_additions(self, pattern_miner):
        """Test detection of added logging statements."""
        diff_info = {
            "file": "service.py",
            "added": [
                "logger.info('Processing started')",
                "logger.debug('Value: %s', value)"
            ],
            "removed": []
        }
        
        patterns = pattern_miner._extract_patterns_from_diff(diff_info)
        
        signatures = [p["signature"] for p in patterns]
        assert "add_logging" in signatures

    def test_detects_type_hint_additions(self, pattern_miner):
        """Test detection of added type hints."""
        diff_info = {
            "file": "utils.py",
            "added": [
                "def calculate(x: int, y: int) -> float:",
                "    return x / y"
            ],
            "removed": [
                "def calculate(x, y):",
                "    return x / y"
            ]
        }
        
        patterns = pattern_miner._extract_patterns_from_diff(diff_info)
        
        signatures = [p["signature"] for p in patterns]
        assert "add_type_hints" in signatures

    def test_detects_docstring_additions(self, pattern_miner):
        """Test detection of added docstrings."""
        diff_info = {
            "file": "module.py",
            "added": [
                '    """',
                '    Process the input data.',
                '    ',
                '    Args:',
                '        data: Input data to process',
                '    """'
            ],
            "removed": []
        }
        
        patterns = pattern_miner._extract_patterns_from_diff(diff_info)
        
        signatures = [p["signature"] for p in patterns]
        assert "add_docstring" in signatures

    def test_ignores_non_python_files(self, pattern_miner):
        """Test that non-Python files are ignored."""
        diff_info = {
            "file": "config.json",
            "added": ["try:", "except:"],
            "removed": []
        }
        
        patterns = pattern_miner._extract_patterns_from_diff(diff_info)
        
        assert patterns == []

    def test_detects_async_conversion(self, pattern_miner):
        """Test detection of async function conversion."""
        diff_info = {
            "file": "api.py",
            "added": [
                "async def fetch_data():",
                "    result = await client.get()"
            ],
            "removed": [
                "def fetch_data():",
                "    result = client.get()"
            ]
        }
        
        patterns = pattern_miner._extract_patterns_from_diff(diff_info)
        
        signatures = [p["signature"] for p in patterns]
        assert "convert_to_async" in signatures


class TestAnalyzeFilePatterns:
    """Tests for _analyze_file_patterns method."""

    def test_detects_try_except_patterns(self, pattern_miner, temp_python_file):
        """Test detection of try/except blocks."""
        code = '''
def safe_divide(a, b):
    try:
        return a / b
    except ZeroDivisionError:
        return 0
'''
        path = temp_python_file(code)
        patterns = pattern_miner._analyze_file_patterns(path)
        
        assert patterns["exception_handling"]["count"] == 1
        assert len(patterns["exception_handling"]["examples"]) >= 1

    def test_detects_list_comprehensions(self, pattern_miner, temp_python_file):
        """Test detection of list comprehensions."""
        code = '''
def get_squares(numbers):
    return [x * x for x in numbers]
    
def get_evens(numbers):
    return [x for x in numbers if x % 2 == 0]
'''
        path = temp_python_file(code)
        patterns = pattern_miner._analyze_file_patterns(path)
        
        assert patterns["list_comprehension"]["count"] == 2

    def test_detects_decorators(self, pattern_miner, temp_python_file):
        """Test detection of decorated functions."""
        code = '''
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_func(x):
    return x * 2

@property
def value(self):
    return self._value
'''
        path = temp_python_file(code)
        patterns = pattern_miner._analyze_file_patterns(path)
        
        assert patterns["decorator_usage"]["count"] == 2
        assert patterns["property_decorator"]["count"] == 1

    def test_detects_async_functions(self, pattern_miner, temp_python_file):
        """Test detection of async functions."""
        code = '''
async def fetch_data():
    return await get_response()

async def process_items(items):
    for item in items:
        await process(item)
'''
        path = temp_python_file(code)
        patterns = pattern_miner._analyze_file_patterns(path)
        
        assert patterns["async_function"]["count"] == 2

    def test_detects_context_managers(self, pattern_miner, temp_python_file):
        """Test detection of context manager usage (with statements)."""
        code = '''
def read_file(path):
    with open(path, 'r') as f:
        return f.read()

def safe_transaction(conn):
    with conn.begin():
        execute_query()
'''
        path = temp_python_file(code)
        patterns = pattern_miner._analyze_file_patterns(path)
        
        assert patterns["context_manager"]["count"] == 2

    def test_detects_dataclass_usage(self, pattern_miner, temp_python_file):
        """Test detection of dataclass decorators."""
        code = '''
from dataclasses import dataclass

@dataclass
class User:
    name: str
    age: int

@dataclass
class Product:
    id: int
    price: float
'''
        path = temp_python_file(code)
        patterns = pattern_miner._analyze_file_patterns(path)
        
        assert patterns["dataclass_usage"]["count"] == 2

    def test_handles_syntax_errors(self, pattern_miner, temp_python_file):
        """Test that syntax errors in files are handled gracefully."""
        code = '''
def broken(
    # missing closing paren
'''
        path = temp_python_file(code)
        patterns = pattern_miner._analyze_file_patterns(path)
        
        # Should return empty patterns without raising exception
        assert patterns["exception_handling"]["count"] == 0


class TestPatternFormat:
    """Tests for pattern output format."""

    def test_pattern_returns_count_and_examples(self, pattern_miner, temp_python_file):
        """Test that patterns include count and examples."""
        code = '''
def func1():
    try:
        pass
    except:
        pass

def func2():
    try:
        pass
    except:
        pass
'''
        path = temp_python_file(code)
        patterns = pattern_miner._analyze_file_patterns(path)
        
        exc_pattern = patterns["exception_handling"]
        assert "count" in exc_pattern
        assert "examples" in exc_pattern
        assert exc_pattern["count"] == 2
        assert len(exc_pattern["examples"]) == 2

    def test_examples_include_file_locations(self, pattern_miner, temp_python_file):
        """Test that examples include file path and line number."""
        code = '''
def example():
    try:
        return 1
    except Exception:
        return 0
'''
        path = temp_python_file(code)
        patterns = pattern_miner._analyze_file_patterns(path)
        
        examples = patterns["exception_handling"]["examples"]
        assert len(examples) >= 1
        assert "file" in examples[0]
        assert "line" in examples[0]
        assert examples[0]["file"] == path

    def test_decorator_examples_include_function_name(self, pattern_miner, temp_python_file):
        """Test that decorator examples include function name."""
        code = '''
@staticmethod
def my_static_method():
    pass
'''
        path = temp_python_file(code)
        patterns = pattern_miner._analyze_file_patterns(path)
        
        examples = patterns["decorator_usage"]["examples"]
        assert len(examples) >= 1
        assert "name" in examples[0]
        assert examples[0]["name"] == "my_static_method"

    def test_async_examples_include_function_name(self, pattern_miner, temp_python_file):
        """Test that async function examples include function name."""
        code = '''
async def my_async_handler():
    await do_something()
'''
        path = temp_python_file(code)
        patterns = pattern_miner._analyze_file_patterns(path)
        
        examples = patterns["async_function"]["examples"]
        assert len(examples) >= 1
        assert "name" in examples[0]
        assert examples[0]["name"] == "my_async_handler"


class TestDiffPatternDetails:
    """Tests for pattern details in diff extraction."""

    def test_error_handling_pattern_has_details(self, pattern_miner):
        """Test that error handling pattern includes details."""
        diff_info = {
            "file": "test.py",
            "added": ["try:", "except Exception:"],
            "removed": []
        }
        
        patterns = pattern_miner._extract_patterns_from_diff(diff_info)
        
        error_pattern = next(p for p in patterns if p["signature"] == "add_error_handling")
        assert "details" in error_pattern
        assert error_pattern["details"]["type"] == "ast"
        assert error_pattern["details"]["language"] == "python"

    def test_logging_pattern_has_details(self, pattern_miner):
        """Test that logging pattern includes details."""
        diff_info = {
            "file": "test.py",
            "added": ["logger.info('message')"],
            "removed": []
        }
        
        patterns = pattern_miner._extract_patterns_from_diff(diff_info)
        
        log_pattern = next(p for p in patterns if p["signature"] == "add_logging")
        assert "details" in log_pattern
        assert log_pattern["details"]["match"] == "function_without_logging"

    def test_type_hints_pattern_has_details(self, pattern_miner):
        """Test that type hints pattern includes details."""
        diff_info = {
            "file": "test.py",
            "added": ["def func(x: int) -> str:"],
            "removed": ["def func(x):"]
        }
        
        patterns = pattern_miner._extract_patterns_from_diff(diff_info)
        
        type_pattern = next(p for p in patterns if p["signature"] == "add_type_hints")
        assert "details" in type_pattern
        assert type_pattern["details"]["match"] == "function_without_types"


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_handles_missing_file_gracefully(self, pattern_miner):
        """Test that missing files are handled gracefully."""
        patterns = pattern_miner._analyze_file_patterns("/nonexistent/path/file.py")
        
        # Should return empty pattern counts without raising
        assert patterns["exception_handling"]["count"] == 0

    def test_handles_binary_file_content(self, pattern_miner, temp_binary_file):
        """Test handling of files with encoding issues."""
        path = temp_binary_file(b'\x80\x81\x82 invalid utf-8')
        patterns = pattern_miner._analyze_file_patterns(path)
        # Should not raise, returns empty patterns
        assert isinstance(patterns, dict)

    def test_diff_with_only_additions(self, pattern_miner):
        """Test diff parsing with only additions (new file)."""
        diff_output = """diff --git a/new_file.py b/new_file.py
--- /dev/null
+++ b/new_file.py
@@ -0,0 +1,3 @@
+def hello():
+    return "world"
"""
        result = pattern_miner._parse_git_diff(diff_output, "abc123")
        
        assert len(result) == 1
        assert "def hello():" in result[0]["added"]
        assert result[0]["removed"] == []

    def test_diff_with_only_deletions(self, pattern_miner):
        """Test diff parsing with only deletions (file removal)."""
        diff_output = """diff --git a/old_file.py b/old_file.py
--- a/old_file.py
+++ /dev/null
@@ -1,3 +0,0 @@
-def goodbye():
-    return "farewell"
"""
        result = pattern_miner._parse_git_diff(diff_output, "abc123")
        
        assert len(result) == 1
        assert "def goodbye():" in result[0]["removed"]
        assert result[0]["added"] == []
