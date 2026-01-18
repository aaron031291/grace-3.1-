import subprocess
import logging
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class StaticAnalysisIssue:
    """A static analysis issue detected by the sensor."""
    tool: str  # 'mypy', 'pylint', etc.
    file_path: str
    issue_type: str  # 'type_error', 'code_quality', 'security', etc.
    severity: str  # 'low', 'medium', 'high', 'critical'
    message: str
    line_number: Optional[int] = None
    fix_suggestion: Optional[str] = None
    detected_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class StaticAnalysisSensorData:
    """Static analysis sensor data."""
    issues: List[StaticAnalysisIssue] = field(default_factory=list)
    total_issues: int = 0
    critical_issues: int = 0
    high_issues: int = 0
    medium_issues: int = 0
    low_issues: int = 0
    tools_run: List[str] = field(default_factory=list)
    tools_failed: List[str] = field(default_factory=list)
    analysis_passed: bool = True
    timestamp: datetime = field(default_factory=datetime.utcnow)


class StaticAnalysisSensor:
    """
    Sensor that runs static analysis tools to detect code quality issues.
    
    Detects:
    - Type errors (mypy)
    - Code quality issues (pylint)
    - Security issues (bandit)
    - Missing type hints
    - Platform compatibility issues
    """
    
    def __init__(self, backend_dir: Optional[Path] = None):
        """Initialize static analysis sensor."""
        if backend_dir is None:
            backend_dir = Path(__file__).parent.parent
        self.backend_dir = backend_dir
        
    def analyze_all(self) -> StaticAnalysisSensorData:
        """Run all static analysis tools."""
        data = StaticAnalysisSensorData()
        
        # Run mypy type checking
        mypy_issues = self._run_mypy()
        data.issues.extend(mypy_issues)
        if mypy_issues:
            data.tools_run.append("mypy")
        else:
            data.tools_failed.append("mypy")
        
        # Run pylint (if available)
        pylint_issues = self._run_pylint()
        data.issues.extend(pylint_issues)
        if pylint_issues is not None:
            data.tools_run.append("pylint")
        
        # Check for missing type hints
        type_hint_issues = self._check_missing_type_hints()
        data.issues.extend(type_hint_issues)
        
        # Check for common code issues (import paths, logger placement, etc.)
        common_issues = self.check_common_code_issues()
        data.issues.extend(common_issues)
        if common_issues:
            data.tools_run.append("grace_analyzer")
        
        # Calculate totals
        data.total_issues = len(data.issues)
        data.critical_issues = sum(1 for i in data.issues if i.severity == 'critical')
        data.high_issues = sum(1 for i in data.issues if i.severity == 'high')
        data.medium_issues = sum(1 for i in data.issues if i.severity == 'medium')
        data.low_issues = sum(1 for i in data.issues if i.severity == 'low')
        data.analysis_passed = data.critical_issues == 0
        
        return data
    
    def _run_mypy(self) -> List[StaticAnalysisIssue]:
        """Run mypy type checker."""
        issues = []
        
        try:
            # Run mypy with JSON output
            result = subprocess.run(
                [
                    'mypy',
                    str(self.backend_dir),
                    '--ignore-missing-imports',
                    '--no-error-summary',
                    '--show-error-codes',
                    '--pretty'
                ],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(self.backend_dir.parent)
            )
            
            # Parse mypy output
            if result.returncode != 0:
                lines = result.stdout.split('\n') + result.stderr.split('\n')
                for line in lines:
                    if 'error:' in line or 'note:' in line:
                        # Parse mypy error format: file:line: error: message
                        parts = line.split(':', 3)
                        if len(parts) >= 4:
                            file_path = parts[0].strip()
                            try:
                                line_num = int(parts[1].strip())
                            except ValueError:
                                line_num = None
                            error_type = parts[2].strip()
                            message = parts[3].strip()
                            
                            # Determine severity
                            severity = 'medium'
                            if 'error' in error_type.lower():
                                severity = 'high'
                            if 'critical' in message.lower() or 'security' in message.lower():
                                severity = 'critical'
                            
                            issues.append(StaticAnalysisIssue(
                                tool='mypy',
                                file_path=file_path,
                                line_number=line_num,
                                issue_type='type_error',
                                severity=severity,
                                message=message,
                                fix_suggestion=f"Fix type error in {file_path} at line {line_num}"
                            ))
                            
        except FileNotFoundError:
            logger.debug("mypy not installed, skipping type checking")
        except subprocess.TimeoutExpired:
            logger.warning("mypy timed out")
            issues.append(StaticAnalysisIssue(
                tool='mypy',
                file_path='',
                issue_type='timeout',
                severity='low',
                message="mypy analysis timed out",
                fix_suggestion="Increase timeout or run mypy manually"
            ))
        except Exception as e:
            logger.error(f"Failed to run mypy: {e}")
        
        return issues
    
    def _run_pylint(self) -> Optional[List[StaticAnalysisIssue]]:
        """Run pylint code quality checker."""
        issues = []
        
        try:
            # Run pylint with JSON output
            result = subprocess.run(
                [
                    'pylint',
                    str(self.backend_dir),
                    '--output-format=json',
                    '--disable=all',
                    '--enable=E,F'  # Only errors and fatal errors
                ],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(self.backend_dir.parent)
            )
            
            # Parse pylint JSON output
            if result.stdout:
                try:
                    pylint_data = json.loads(result.stdout)
                    for item in pylint_data:
                        issues.append(StaticAnalysisIssue(
                            tool='pylint',
                            file_path=item.get('path', ''),
                            line_number=item.get('line'),
                            issue_type='code_quality',
                            severity='medium' if item.get('type') == 'error' else 'low',
                            message=item.get('message', ''),
                            fix_suggestion=f"Fix {item.get('symbol', 'issue')} in {item.get('path', '')}"
                        ))
                except json.JSONDecodeError:
                    pass
                    
        except FileNotFoundError:
            logger.debug("pylint not installed, skipping code quality check")
            return None
        except Exception as e:
            logger.error(f"Failed to run pylint: {e}")
            return None
        
        return issues
    
    def _check_missing_type_hints(self) -> List[StaticAnalysisIssue]:
        """Check for functions missing type hints."""
        issues = []
        
        # This is a simplified check - in production, use a proper AST parser
        try:
            python_files = list(self.backend_dir.rglob("*.py"))
            
            for py_file in python_files[:50]:  # Limit to first 50 files
                try:
                    content = py_file.read_text(encoding='utf-8')
                    lines = content.split('\n')
                    
                    # Simple heuristic: check for function definitions without type hints
                    for i, line in enumerate(lines, 1):
                        if line.strip().startswith('def ') and '->' not in line:
                            # Check if it's a public function (not private)
                            func_name = line.split('def ')[1].split('(')[0].strip()
                            if not func_name.startswith('_'):
                                # Check if it's in an API file (higher priority)
                                if 'api' in str(py_file):
                                    issues.append(StaticAnalysisIssue(
                                        tool='manual',
                                        file_path=str(py_file.relative_to(self.backend_dir.parent)),
                                        line_number=i,
                                        issue_type='missing_type_hints',
                                        severity='low',
                                        message=f"Function '{func_name}' missing return type hint",
                                        fix_suggestion=f"Add return type hint to function '{func_name}' in {py_file.name}"
                                    ))
                except Exception:
                    pass
                    
        except Exception as e:
            logger.error(f"Failed to check type hints: {e}")
        
        return issues[:20]  # Limit to 20 issues
    
    def check_common_code_issues(self) -> List[StaticAnalysisIssue]:
        """Check for common code issues that cause runtime errors."""
        issues = []
        
        try:
            for py_file in self.backend_dir.rglob('*.py'):
                if '__pycache__' in str(py_file) or '.backup' in str(py_file):
                    continue
                
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        lines = content.split('\n')
                    
                    # Check 1: Wrong import paths (from backend.xxx)
                    for i, line in enumerate(lines, 1):
                        if 'from backend.' in line and 'import' in line:
                            issues.append(StaticAnalysisIssue(
                                tool='grace_analyzer',
                                file_path=str(py_file),
                                line_number=i,
                                issue_type='wrong_import_path',
                                severity='high',
                                message=f"Import uses 'from backend.' prefix which fails when running from backend directory",
                                fix_suggestion="Change 'from backend.xxx' to 'from xxx' for relative imports"
                            ))
                    
                    # Check 2: Logger defined inside class
                    in_class = False
                    class_indent = 0
                    for i, line in enumerate(lines, 1):
                        stripped = line.lstrip()
                        current_indent = len(line) - len(stripped)
                        
                        if stripped.startswith('class ') and stripped.endswith(':'):
                            in_class = True
                            class_indent = current_indent
                        elif in_class and current_indent <= class_indent and stripped and not stripped.startswith('#'):
                            in_class = False
                        
                        if in_class and 'logger = logging.getLogger' in line:
                            issues.append(StaticAnalysisIssue(
                                tool='grace_analyzer',
                                file_path=str(py_file),
                                line_number=i,
                                issue_type='logger_in_class',
                                severity='high',
                                message="Logger defined inside class - will cause Pydantic/Enum errors",
                                fix_suggestion="Move 'logger = logging.getLogger(__name__)' to module level (before class definition)"
                            ))
                    
                    # Check 3: Missing router in FastAPI endpoint files
                    if '_endpoint' in py_file.name or '_api' in py_file.name:
                        has_router_decorator = '@router.' in content
                        has_router_definition = 'router = APIRouter' in content or 'router=APIRouter' in content
                        
                        if has_router_decorator and not has_router_definition:
                            issues.append(StaticAnalysisIssue(
                                tool='grace_analyzer',
                                file_path=str(py_file),
                                line_number=1,
                                issue_type='missing_router_definition',
                                severity='critical',
                                message="FastAPI endpoint uses @router decorators but router is not defined",
                                fix_suggestion="Add 'router = APIRouter(prefix=\"/...\", tags=[\"...\"])' after imports"
                            ))
                    
                    # Check 4: Missing factory function for classes that are imported with get_xxx
                    import re
                    class_matches = re.findall(r'^class (\w+)\s*[:\(]', content, re.MULTILINE)
                    for class_name in class_matches:
                        # Convert to expected factory function name
                        snake_case = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', class_name)
                        snake_case = re.sub('([a-z0-9])([A-Z])', r'\1_\2', snake_case).lower()
                        expected_func = f"get_{snake_case}"
                        
                        # Check if this function is imported elsewhere but doesn't exist
                        if f"def {expected_func}" not in content:
                            # Check if it's a singleton-type class (has a state pattern)
                            if 'Manager' in class_name or 'Integration' in class_name or 'System' in class_name:
                                # These typically need factory functions
                                issues.append(StaticAnalysisIssue(
                                    tool='grace_analyzer',
                                    file_path=str(py_file),
                                    line_number=1,
                                    issue_type='missing_factory_function',
                                    severity='low',
                                    message=f"Class '{class_name}' may need factory function '{expected_func}'",
                                    fix_suggestion=f"Consider adding 'def {expected_func}()' factory function for singleton access"
                                ))
                
                except Exception as e:
                    logger.debug(f"Error checking {py_file}: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to check common code issues: {e}")
        
        return issues
