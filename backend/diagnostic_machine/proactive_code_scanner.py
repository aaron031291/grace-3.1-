"""
Proactive Code Scanner for Self-Healing System
Scans code for bugs BEFORE they cause runtime errors
"""
import ast
import importlib
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class CodeIssue:
    """A code issue detected by proactive scanning."""
    issue_type: str  # 'syntax_error', 'import_error', 'missing_file', 'code_quality'
    severity: str  # 'critical', 'high', 'medium', 'low'
    file_path: str
    line_number: Optional[int] = None
    message: str = ""
    suggested_fix: Optional[str] = None
    detected_at: datetime = field(default_factory=datetime.utcnow)


class ProactiveCodeScanner:
    """
    Proactively scans code for bugs that self-healing should catch.
    
    Detects:
    - Syntax errors (AST parsing)
    - Import errors (try importing modules)
    - Missing files (check imports against filesystem)
    - Code quality issues (bare except, mutable defaults, etc.)
    """
    
    def __init__(self, backend_dir: Optional[Path] = None):
        """Initialize proactive code scanner."""
        if backend_dir is None:
            backend_dir = Path(__file__).parent.parent
        self.backend_dir = backend_dir
        self.issues: List[CodeIssue] = []
    
    def scan_all(self) -> List[CodeIssue]:
        """Scan all Python files for issues."""
        self.issues = []
        
        # 1. Check for syntax errors
        self._scan_syntax_errors()
        
        # 2. Check for import errors
        self._scan_import_errors()
        
        # 3. Check for missing files
        self._scan_missing_files()
        
        # 4. Check for code quality issues
        self._scan_code_quality()
        
        return self.issues
    
    def _scan_syntax_errors(self):
        """Scan for Python syntax errors."""
        python_files = list(self.backend_dir.rglob("*.py"))
        
        # Skip intentional test files
        skip_files = {
            "test_indent.py",
            "test_syntax_error.py",
            "test_type_error.py",
            "test_undefined.py",
            "test_missing_import.py"
        }
        
        for py_file in python_files:
            if py_file.name in skip_files:
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    source = f.read()
                ast.parse(source, filename=str(py_file))
            except SyntaxError as e:
                self.issues.append(CodeIssue(
                    issue_type='syntax_error',
                    severity='critical',
                    file_path=str(py_file.relative_to(self.backend_dir.parent)),
                    line_number=e.lineno or 0,
                    message=str(e),
                    suggested_fix=f"Fix syntax error in {py_file.name} at line {e.lineno}"
                ))
            except Exception as e:
                logger.debug(f"Could not parse {py_file}: {e}")
    
    def _scan_import_errors(self):
        """Scan for import errors by trying to import modules."""
        critical_modules = [
            "app",
            "api.timesense",
            "api.grace_os_api",
            "genesis_ide.core_integration",
            "timesense.engine",
            "diagnostic_machine.diagnostic_engine",
            "grace_os.ide_bridge",
            "database.session",
            "database.connection",
        ]
        
        for module_name in critical_modules:
            try:
                importlib.import_module(module_name)
            except ImportError as e:
                self.issues.append(CodeIssue(
                    issue_type='import_error',
                    severity='critical',
                    file_path=module_name,
                    message=str(e),
                    suggested_fix=f"Fix import error in {module_name}: {e}"
                ))
            except Exception as e:
                self.issues.append(CodeIssue(
                    issue_type='import_error',
                    severity='high',
                    file_path=module_name,
                    message=f"Unexpected error importing {module_name}: {e}",
                    suggested_fix=f"Investigate import issue in {module_name}"
                ))
    
    def _scan_missing_files(self):
        """Scan for missing files that are imported."""
        # Check grace_os imports
        grace_os_init = self.backend_dir / "grace_os" / "__init__.py"
        if grace_os_init.exists():
            content = grace_os_init.read_text()
            # Check if it's trying to import a non-existent file
            if "from .self_healing_ide" in content and "# from .self_healing_ide" not in content:
                healing_ide_file = self.backend_dir / "grace_os" / "self_healing_ide.py"
                if not healing_ide_file.exists():
                    self.issues.append(CodeIssue(
                        issue_type='missing_file',
                        severity='high',
                        file_path=str(grace_os_init.relative_to(self.backend_dir.parent)),
                        message="Imports self_healing_ide but file doesn't exist",
                        suggested_fix="Either create self_healing_ide.py or comment out the import"
                    ))
    
    def _scan_code_quality(self):
        """Scan for code quality issues."""
        python_files = list(self.backend_dir.rglob("*.py"))
        
        for py_file in python_files[:100]:  # Check first 100 files
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                for i, line in enumerate(lines, 1):
                    stripped = line.strip()
                    
                    # Bare except clause
                    if stripped == "except:":
                        self.issues.append(CodeIssue(
                            issue_type='code_quality',
                            severity='medium',
                            file_path=str(py_file.relative_to(self.backend_dir.parent)),
                            line_number=i,
                            message="Bare except clause (specify exception)",
                            suggested_fix="Change 'except:' to 'except Exception:'"
                        ))
                    
                    # Mutable default arguments
                    if "def " in stripped and "=[]" in stripped:
                        self.issues.append(CodeIssue(
                            issue_type='code_quality',
                            severity='medium',
                            file_path=str(py_file.relative_to(self.backend_dir.parent)),
                            line_number=i,
                            message="Mutable default argument (use None instead)",
                            suggested_fix="Use 'param=None' and check 'if param is None: param = []'"
                        ))
            except Exception:
                pass
    
    def get_critical_issues(self) -> List[CodeIssue]:
        """Get only critical issues."""
        return [i for i in self.issues if i.severity == 'critical']
    
    def get_high_issues(self) -> List[CodeIssue]:
        """Get high and critical issues."""
        return [i for i in self.issues if i.severity in ['critical', 'high']]


def get_proactive_scanner(backend_dir: Optional[Path] = None) -> ProactiveCodeScanner:
    """Get or create proactive code scanner instance."""
    return ProactiveCodeScanner(backend_dir=backend_dir)
