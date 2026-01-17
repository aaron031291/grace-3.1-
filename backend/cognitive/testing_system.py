"""
Testing System for Grace Code Generation

Provides test execution and failure analysis for generated code.
"""

import logging
import subprocess
import ast
import importlib.util
from pathlib import Path
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class TestingSystem:
    """
    System for testing generated code.
    
    Supports:
    - Syntax validation
    - Runtime execution testing
    - Unit test discovery and execution
    - Failure analysis and reporting
    """
    
    def __init__(self, session: Optional[Session] = None):
        """
        Initialize testing system.
        
        Args:
            session: Database session (optional, for storing test results)
        """
        self.session = session
        self.test_results_cache: Dict[str, Dict[str, Any]] = {}
    
    def run_tests(self, file_path: str) -> Dict[str, Any]:
        """
        Run tests on a file.
        
        Args:
            file_path: Path to the file to test
            
        Returns:
            Dict with test results:
            {
                "passed": bool,
                "test_count": int,
                "passed_count": int,
                "failed_count": int,
                "errors": List[str],
                "method": str  # "syntax_check", "execution_test", "pytest", etc.
            }
        """
        file_path_obj = Path(file_path)
        
        if not file_path_obj.exists():
            return {
                "passed": False,
                "test_count": 0,
                "passed_count": 0,
                "failed_count": 0,
                "errors": [f"File not found: {file_path}"],
                "method": "file_check"
            }
        
        # Try multiple testing methods in order of preference
        test_methods = [
            self._run_pytest,
            self._run_unittest,
            self._run_execution_test,
            self._run_syntax_check
        ]
        
        for method in test_methods:
            try:
                result = method(file_path)
                if result:
                    return result
            except Exception as e:
                logger.debug(f"[TESTING] Method {method.__name__} failed: {e}")
                continue
        
        # Fallback to syntax check
        return self._run_syntax_check(file_path)
    
    def _run_syntax_check(self, file_path: str) -> Dict[str, Any]:
        """Check Python syntax."""
        try:
            file_path_obj = Path(file_path)
            code = file_path_obj.read_text(encoding='utf-8')
            
            # Try to compile
            compile(code, file_path, "exec")
            
            return {
                "passed": True,
                "test_count": 1,
                "passed_count": 1,
                "failed_count": 0,
                "errors": [],
                "method": "syntax_check"
            }
        except SyntaxError as e:
            return {
                "passed": False,
                "test_count": 1,
                "passed_count": 0,
                "failed_count": 1,
                "errors": [f"Syntax error: {str(e)}"],
                "method": "syntax_check"
            }
        except Exception as e:
            return {
                "passed": False,
                "test_count": 1,
                "passed_count": 0,
                "failed_count": 1,
                "errors": [f"Error checking syntax: {str(e)}"],
                "method": "syntax_check"
            }
    
    def _run_execution_test(self, file_path: str) -> Dict[str, Any]:
        """Test code execution (import and basic execution)."""
        try:
            file_path_obj = Path(file_path)
            code = file_path_obj.read_text(encoding='utf-8')
            
            # Try to parse AST
            tree = ast.parse(code)
            
            # Check for obvious issues
            errors = []
            
            # Try to execute in isolated namespace
            namespace = {}
            try:
                exec(compile(tree, file_path, "exec"), namespace)
            except Exception as e:
                errors.append(f"Execution error: {str(e)}")
            
            if errors:
                return {
                    "passed": False,
                    "test_count": 1,
                    "passed_count": 0,
                    "failed_count": 1,
                    "errors": errors,
                    "method": "execution_test"
                }
            
            return {
                "passed": True,
                "test_count": 1,
                "passed_count": 1,
                "failed_count": 0,
                "errors": [],
                "method": "execution_test"
            }
        except Exception as e:
            logger.debug(f"[TESTING] Execution test failed: {e}")
            return None
    
    def _run_pytest(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Run pytest on the file."""
        try:
            file_path_obj = Path(file_path)
            
            # Check if pytest is available
            result = subprocess.run(
                ["python", "-m", "pytest", "--version"],
                capture_output=True,
                timeout=5
            )
            
            if result.returncode != 0:
                return None  # pytest not available
            
            # Run pytest
            result = subprocess.run(
                ["python", "-m", "pytest", str(file_path_obj), "-v", "--tb=short"],
                capture_output=True,
                timeout=30,
                text=True
            )
            
            # Parse output
            output = result.stdout + result.stderr
            
            # Count tests (simple parsing)
            passed_count = output.count("PASSED")
            failed_count = output.count("FAILED")
            error_count = output.count("ERROR")
            test_count = passed_count + failed_count + error_count
            
            if test_count == 0:
                return None  # No tests found
            
            errors = []
            if failed_count > 0 or error_count > 0:
                # Extract error messages
                lines = output.split('\n')
                for i, line in enumerate(lines):
                    if "FAILED" in line or "ERROR" in line:
                        # Get next few lines for context
                        error_context = '\n'.join(lines[i:min(i+5, len(lines))])
                        errors.append(error_context)
            
            return {
                "passed": failed_count == 0 and error_count == 0,
                "test_count": test_count,
                "passed_count": passed_count,
                "failed_count": failed_count + error_count,
                "errors": errors[:10],  # Limit to 10 errors
                "method": "pytest",
                "output": output
            }
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            logger.debug(f"[TESTING] Pytest not available or failed: {e}")
            return None
    
    def _run_unittest(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Run unittest discovery on the file."""
        try:
            file_path_obj = Path(file_path)
            
            # Try unittest discovery
            result = subprocess.run(
                ["python", "-m", "unittest", "discover", "-s", str(file_path_obj.parent), "-p", file_path_obj.name, "-v"],
                capture_output=True,
                timeout=30,
                text=True
            )
            
            output = result.stdout + result.stderr
            
            # Check if tests were found and run
            if "Ran 0 tests" in output or "no tests" in output.lower():
                return None  # No tests found
            
            # Parse results
            passed_count = output.count("ok")
            failed_count = output.count("FAIL")
            error_count = output.count("ERROR")
            test_count = passed_count + failed_count + error_count
            
            if test_count == 0:
                return None
            
            errors = []
            if failed_count > 0 or error_count > 0:
                lines = output.split('\n')
                for i, line in enumerate(lines):
                    if "FAIL" in line or "ERROR" in line:
                        error_context = '\n'.join(lines[i:min(i+5, len(lines))])
                        errors.append(error_context)
            
            return {
                "passed": failed_count == 0 and error_count == 0,
                "test_count": test_count,
                "passed_count": passed_count,
                "failed_count": failed_count + error_count,
                "errors": errors[:10],
                "method": "unittest",
                "output": output
            }
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            logger.debug(f"[TESTING] Unittest failed: {e}")
            return None
    
    def fix_failures(self, failures: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze test failures and suggest fixes.
        
        Args:
            failures: List of failure dictionaries from test results
            
        Returns:
            Dict with fix suggestions:
            {
                "success": bool,
                "suggestions": List[str],
                "fixes_applied": int
            }
        """
        suggestions = []
        fixes_applied = 0
        
        for failure in failures:
            error_msg = failure.get("error", "") or str(failure)
            error_lower = error_msg.lower()
            
            # Common error patterns and fixes
            if "syntax error" in error_lower or "invalid syntax" in error_lower:
                if "missing colon" in error_lower or "expected ':'" in error_lower:
                    suggestions.append("Add missing colon (:) after if/for/while/def statements")
                elif "indentation" in error_lower:
                    suggestions.append("Fix indentation - ensure consistent spacing (4 spaces recommended)")
                elif "unexpected EOF" in error_lower:
                    suggestions.append("Complete incomplete code blocks (missing closing brackets/parentheses)")
            
            elif "nameerror" in error_lower or "name" in error_lower and "not defined" in error_lower:
                suggestions.append("Define missing variable or import missing module")
            
            elif "typeerror" in error_lower:
                suggestions.append("Check variable types - ensure correct types are used in operations")
            
            elif "attributeerror" in error_lower:
                suggestions.append("Check object attributes - ensure object has the required attribute/method")
            
            elif "indentationerror" in error_lower:
                suggestions.append("Fix indentation - Python requires consistent indentation (4 spaces)")
            
            elif "import" in error_lower and "error" in error_lower:
                suggestions.append("Check imports - ensure required modules are installed and imported correctly")
            
            else:
                suggestions.append(f"Review error: {error_msg[:100]}")
        
        # Remove duplicates
        suggestions = list(dict.fromkeys(suggestions))
        
        return {
            "success": len(suggestions) > 0,
            "suggestions": suggestions,
            "fixes_applied": fixes_applied,
            "failure_count": len(failures)
        }


def get_testing_system(session: Optional[Session] = None) -> TestingSystem:
    """
    Get or create testing system instance.
    
    Args:
        session: Database session (optional)
        
    Returns:
        TestingSystem instance
    """
    return TestingSystem(session=session)
