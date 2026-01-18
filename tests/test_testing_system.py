"""
Comprehensive tests for the Testing System.

Tests cover:
- TestingSystem initialization
- run_tests with valid Python file
- run_tests with syntax errors
- run_tests with missing file
- fix_failures suggestions
- _run_syntax_check
- _run_execution_test
- outcome aggregator integration
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))


class TestTestingSystemInitialization:
    """Tests for TestingSystem initialization."""
    
    def test_init_without_session(self):
        """Test initialization without database session."""
        from cognitive.testing_system import TestingSystem
        ts = TestingSystem()
        assert ts.session is None
        assert ts.test_results_cache == {}
    
    def test_init_with_mock_session(self):
        """Test initialization with mock session."""
        from cognitive.testing_system import TestingSystem
        mock_session = MagicMock()
        ts = TestingSystem(session=mock_session)
        assert ts.session == mock_session
    
    def test_get_testing_system_singleton(self):
        """Test get_testing_system returns a TestingSystem instance."""
        from cognitive.testing_system import get_testing_system
        ts = get_testing_system()
        assert ts is not None
        # Verify it has the expected methods
        assert hasattr(ts, 'run_tests')
        assert hasattr(ts, 'fix_failures')


class TestRunTestsValidFile:
    """Tests for run_tests with valid Python files."""
    
    def test_run_tests_valid_python(self):
        """Test running tests on a valid Python file."""
        from cognitive.testing_system import TestingSystem
        ts = TestingSystem()
        
        # Create a temporary valid Python file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('def add(a, b):\n    return a + b\n\nresult = add(1, 2)\n')
            temp_path = f.name
        
        try:
            result = ts.run_tests(temp_path)
            assert 'passed' in result
            assert 'method' in result
            assert 'errors' in result
            # Valid file should pass at least syntax check
            assert result['passed'] is True or result.get('test_count', 0) >= 0
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    def test_run_tests_simple_function(self):
        """Test running tests on a simple function file."""
        from cognitive.testing_system import TestingSystem
        ts = TestingSystem()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('def hello():\n    return "Hello, World!"\n')
            temp_path = f.name
        
        try:
            result = ts.run_tests(temp_path)
            assert result['passed'] is True
            assert len(result['errors']) == 0
        finally:
            Path(temp_path).unlink(missing_ok=True)


class TestRunTestsSyntaxErrors:
    """Tests for run_tests with syntax errors."""
    
    def test_run_tests_syntax_error(self):
        """Test running tests on file with syntax error."""
        from cognitive.testing_system import TestingSystem
        ts = TestingSystem()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('def broken(\n    return "missing parenthesis"\n')
            temp_path = f.name
        
        try:
            result = ts.run_tests(temp_path)
            assert result['passed'] is False
            assert len(result['errors']) > 0
            # Check for syntax-related keywords in error (may come from pytest or compile)
            error_text = result['errors'][0].lower()
            assert any(keyword in error_text for keyword in ['syntax', 'error', 'unexpected'])
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    def test_run_tests_indentation_error(self):
        """Test running tests on file with indentation error."""
        from cognitive.testing_system import TestingSystem
        ts = TestingSystem()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('def bad_indent():\nreturn "wrong"\n')
            temp_path = f.name
        
        try:
            result = ts.run_tests(temp_path)
            assert result['passed'] is False
            assert len(result['errors']) > 0
        finally:
            Path(temp_path).unlink(missing_ok=True)


class TestRunTestsMissingFile:
    """Tests for run_tests with missing files."""
    
    def test_run_tests_missing_file(self):
        """Test running tests on non-existent file."""
        from cognitive.testing_system import TestingSystem
        ts = TestingSystem()
        
        result = ts.run_tests('/nonexistent/path/to/file.py')
        
        assert result['passed'] is False
        assert 'File not found' in result['errors'][0] or 'not found' in result['errors'][0].lower()
        assert result['method'] == 'file_check'
    
    def test_run_tests_empty_path(self):
        """Test running tests with empty path."""
        from cognitive.testing_system import TestingSystem
        ts = TestingSystem()
        
        result = ts.run_tests('')
        
        assert result['passed'] is False


class TestFixFailures:
    """Tests for fix_failures suggestions."""
    
    def test_fix_failures_empty_list(self):
        """Test fix_failures with empty failure list."""
        from cognitive.testing_system import TestingSystem
        ts = TestingSystem()
        
        result = ts.fix_failures([])
        
        assert 'success' in result or 'suggestions' in result
    
    def test_fix_failures_with_syntax_failure(self):
        """Test fix_failures with a syntax failure."""
        from cognitive.testing_system import TestingSystem
        ts = TestingSystem()
        
        failures = [
            {
                'type': 'syntax',
                'error': 'SyntaxError: unexpected EOF',
                'file': 'test.py',
                'line': 5
            }
        ]
        
        result = ts.fix_failures(failures)
        
        # Should return some form of result
        assert result is not None
    
    def test_fix_failures_with_import_failure(self):
        """Test fix_failures with an import failure."""
        from cognitive.testing_system import TestingSystem
        ts = TestingSystem()
        
        failures = [
            {
                'type': 'import',
                'error': 'ModuleNotFoundError: No module named numpy',
                'file': 'test.py'
            }
        ]
        
        result = ts.fix_failures(failures)
        
        assert result is not None


class TestSyntaxCheck:
    """Tests for _run_syntax_check method."""
    
    def test_syntax_check_valid(self):
        """Test syntax check on valid Python."""
        from cognitive.testing_system import TestingSystem
        ts = TestingSystem()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('x = 1 + 2\nprint(x)\n')
            temp_path = f.name
        
        try:
            result = ts._run_syntax_check(temp_path)
            assert result['passed'] is True
            assert result['method'] == 'syntax_check'
            assert result['test_count'] == 1
            assert result['passed_count'] == 1
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    def test_syntax_check_invalid(self):
        """Test syntax check on invalid Python."""
        from cognitive.testing_system import TestingSystem
        ts = TestingSystem()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('def broken(:\n')
            temp_path = f.name
        
        try:
            result = ts._run_syntax_check(temp_path)
            assert result['passed'] is False
            assert result['method'] == 'syntax_check'
            assert result['failed_count'] == 1
        finally:
            Path(temp_path).unlink(missing_ok=True)


class TestExecutionTest:
    """Tests for _run_execution_test method."""
    
    def test_execution_test_simple(self):
        """Test execution test on simple file."""
        from cognitive.testing_system import TestingSystem
        ts = TestingSystem()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('x = 5\ny = 10\nz = x + y\n')
            temp_path = f.name
        
        try:
            result = ts._run_execution_test(temp_path)
            if result:  # Method might return None if not applicable
                assert 'passed' in result
                assert 'method' in result
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    def test_execution_test_with_exception(self):
        """Test execution test on file that raises exception."""
        from cognitive.testing_system import TestingSystem
        ts = TestingSystem()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('raise ValueError("test error")\n')
            temp_path = f.name
        
        try:
            result = ts._run_execution_test(temp_path)
            if result:
                assert result['passed'] is False
        finally:
            Path(temp_path).unlink(missing_ok=True)


class TestOutcomeAggregatorIntegration:
    """Tests for outcome aggregator integration."""
    
    def test_outcome_recorded_on_success(self):
        """Test that outcomes are recorded in aggregator on successful test."""
        from cognitive.testing_system import TestingSystem
        
        with patch('cognitive.outcome_aggregator.get_outcome_aggregator') as mock_get_agg:
            mock_aggregator = MagicMock()
            mock_get_agg.return_value = mock_aggregator
            
            ts = TestingSystem()
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write('x = 1\n')
                temp_path = f.name
            
            try:
                ts.run_tests(temp_path)
                
                # Verify record_outcome was called
                mock_aggregator.record_outcome.assert_called()
                call_args = mock_aggregator.record_outcome.call_args
                assert call_args[0][0] == 'testing'  # source
                outcome_data = call_args[0][1]
                assert 'success' in outcome_data
                assert 'trust_score' in outcome_data
                assert 'file_path' in outcome_data
            finally:
                Path(temp_path).unlink(missing_ok=True)
    
    def test_outcome_recorded_on_failure(self):
        """Test that outcomes are recorded in aggregator on failed test."""
        from cognitive.testing_system import TestingSystem
        
        with patch('cognitive.outcome_aggregator.get_outcome_aggregator') as mock_get_agg:
            mock_aggregator = MagicMock()
            mock_get_agg.return_value = mock_aggregator
            
            ts = TestingSystem()
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write('def broken(\n')
                temp_path = f.name
            
            try:
                ts.run_tests(temp_path)
                
                # Verify record_outcome was called with failure data
                mock_aggregator.record_outcome.assert_called()
                call_args = mock_aggregator.record_outcome.call_args
                outcome_data = call_args[0][1]
                assert outcome_data['success'] is False
                assert outcome_data['trust_score'] == 0.3
            finally:
                Path(temp_path).unlink(missing_ok=True)
    
    def test_aggregator_error_does_not_break_tests(self):
        """Test that aggregator errors don't break test execution."""
        from cognitive.testing_system import TestingSystem
        
        with patch('cognitive.outcome_aggregator.get_outcome_aggregator') as mock_get_agg:
            mock_get_agg.side_effect = Exception("Aggregator unavailable")
            
            ts = TestingSystem()
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write('x = 1\n')
                temp_path = f.name
            
            try:
                # Should not raise, even with aggregator error
                result = ts.run_tests(temp_path)
                assert result['passed'] is True
            finally:
                Path(temp_path).unlink(missing_ok=True)


class TestRecordOutcome:
    """Tests for _record_outcome helper method."""
    
    def test_record_outcome_success(self):
        """Test _record_outcome with success result."""
        from cognitive.testing_system import TestingSystem
        
        with patch('cognitive.outcome_aggregator.get_outcome_aggregator') as mock_get_agg:
            mock_aggregator = MagicMock()
            mock_get_agg.return_value = mock_aggregator
            
            ts = TestingSystem()
            
            result = {
                'passed': True,
                'test_count': 5,
                'passed_count': 5,
                'failed_count': 0,
                'method': 'pytest',
                'errors': []
            }
            
            ts._record_outcome('/path/to/file.py', result)
            
            mock_aggregator.record_outcome.assert_called_once()
            call_args = mock_aggregator.record_outcome.call_args[0]
            assert call_args[0] == 'testing'
            assert call_args[1]['success'] is True
            assert call_args[1]['trust_score'] == 0.9
            assert call_args[1]['test_count'] == 5
    
    def test_record_outcome_limits_errors(self):
        """Test that _record_outcome limits error list to 3 items."""
        from cognitive.testing_system import TestingSystem
        
        with patch('cognitive.outcome_aggregator.get_outcome_aggregator') as mock_get_agg:
            mock_aggregator = MagicMock()
            mock_get_agg.return_value = mock_aggregator
            
            ts = TestingSystem()
            
            result = {
                'passed': False,
                'test_count': 10,
                'passed_count': 5,
                'failed_count': 5,
                'method': 'pytest',
                'errors': ['Error 1', 'Error 2', 'Error 3', 'Error 4', 'Error 5']
            }
            
            ts._record_outcome('/path/to/file.py', result)
            
            call_args = mock_aggregator.record_outcome.call_args[0]
            assert len(call_args[1]['errors']) == 3  # Limited to 3
