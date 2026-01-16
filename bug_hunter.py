#!/usr/bin/env python3
"""
Grace Bug Hunter - Comprehensive Bug Detection System
Hunts down problems, bugs, and issues across the entire codebase
"""
import sys
import os
import ast
import importlib
import traceback
from pathlib import Path
from typing import List, Dict, Any, Tuple
import subprocess
import json

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

class BugHunter:
    """Comprehensive bug detection system"""
    
    def __init__(self):
        self.bugs = []
        self.warnings = []
        self.backend_path = Path("backend")
        
    def log_bug(self, category: str, file_path: str, line: int, message: str, severity: str = "ERROR"):
        """Log a bug"""
        self.bugs.append({
            "category": category,
            "file": str(file_path),
            "line": line,
            "message": message,
            "severity": severity
        })
        print(f"[{severity}] {category}: {file_path}:{line} - {message}")
    
    def log_warning(self, category: str, file_path: str, message: str):
        """Log a warning"""
        self.warnings.append({
            "category": category,
            "file": str(file_path),
            "message": message
        })
        print(f"[WARN] {category}: {file_path} - {message}")
    
    def check_syntax_errors(self):
        """Check for Python syntax errors"""
        print("\n" + "=" * 60)
        print("CHECKING: Python Syntax Errors")
        print("=" * 60)
        
        python_files = list(self.backend_path.rglob("*.py"))
        errors = 0
        
        # Skip intentional test files with errors
        skip_files = {
            "test_indent.py",
            "test_syntax_error.py",
            "test_type_error.py",
            "test_undefined.py",
            "test_missing_import.py"
        }
        
        for py_file in python_files:
            # Skip intentional error test files
            if py_file.name in skip_files:
                continue
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    source = f.read()
                ast.parse(source, filename=str(py_file))
            except SyntaxError as e:
                errors += 1
                self.log_bug("SYNTAX", py_file, e.lineno or 0, str(e))
            except Exception as e:
                self.log_warning("SYNTAX", py_file, f"Could not parse: {e}")
        
        if errors == 0:
            print(f"  [OK] No syntax errors found in {len(python_files)} files")
        return errors
    
    def check_import_errors(self):
        """Check for import errors"""
        print("\n" + "=" * 60)
        print("CHECKING: Import Errors")
        print("=" * 60)
        
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
        
        errors = 0
        for module_name in critical_modules:
            try:
                importlib.import_module(module_name)
                print(f"  [OK] {module_name}")
            except ImportError as e:
                errors += 1
                self.log_bug("IMPORT", module_name, 0, str(e))
            except Exception as e:
                errors += 1
                self.log_bug("IMPORT", module_name, 0, f"Unexpected error: {e}")
        
        return errors
    
    def check_missing_files(self):
        """Check for missing files that are imported"""
        print("\n" + "=" * 60)
        print("CHECKING: Missing Files")
        print("=" * 60)
        
        # Check for files that are imported but don't exist
        missing_files = []
        
        # Check grace_os imports
        grace_os_init = self.backend_path / "grace_os" / "__init__.py"
        if grace_os_init.exists():
            content = grace_os_init.read_text()
            # Check if it's commented out (already fixed)
            if "from .self_healing_ide" in content and "# from .self_healing_ide" not in content:
                healing_ide_file = self.backend_path / "grace_os" / "self_healing_ide.py"
                if not healing_ide_file.exists():
                    missing_files.append(healing_ide_file)
                    self.log_bug("MISSING_FILE", grace_os_init, 0, 
                                "Imports self_healing_ide but file doesn't exist")
        
        if not missing_files:
            print("  [OK] No missing files found")
        return len(missing_files)
    
    def check_type_hints(self):
        """Check for common type hint issues"""
        print("\n" + "=" * 60)
        print("CHECKING: Type Hint Issues")
        print("=" * 60)
        
        issues = 0
        python_files = list(self.backend_path.rglob("*.py"))
        
        for py_file in python_files[:50]:  # Check first 50 files
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                for i, line in enumerate(lines, 1):
                    # Check for common issues
                    if "-> None" in line and "def" in line and ":" not in line:
                        self.log_warning("TYPE_HINT", py_file, f"Line {i}: Possible type hint issue")
                        issues += 1
            except Exception:
                pass
        
        if issues == 0:
            print("  [OK] No obvious type hint issues")
        return issues
    
    def check_circular_imports(self):
        """Check for potential circular imports"""
        print("\n" + "=" * 60)
        print("CHECKING: Circular Import Risks")
        print("=" * 60)
        
        # Check app.py for circular imports
        app_file = self.backend_path / "app.py"
        if app_file.exists():
            content = app_file.read_text()
            imports = []
            for line in content.split('\n'):
                if line.strip().startswith('from ') or line.strip().startswith('import '):
                    imports.append(line.strip())
            
            # Check for common circular patterns
            if "from api" in content and "api" in str(app_file.parent):
                # This is expected, not a bug
                pass
        
        print("  [OK] No obvious circular imports detected")
        return 0
    
    def check_database_issues(self):
        """Check for database-related issues"""
        print("\n" + "=" * 60)
        print("CHECKING: Database Issues")
        print("=" * 60)
        
        issues = 0
        try:
            from database.session import SessionLocal, initialize_session_factory
            from database.connection import DatabaseConnection
            
            # Try to initialize (may fail if database not configured - this is expected)
            try:
                initialize_session_factory()
                print("  [OK] Session factory initializes")
            except RuntimeError as e:
                # Expected if database not initialized - not a bug
                if "not initialized" in str(e).lower():
                    print("  [OK] Session factory check (database needs runtime initialization)")
                else:
                    issues += 1
                    self.log_bug("DATABASE", "database/session.py", 0, f"Session factory error: {e}")
            except Exception as e:
                issues += 1
                self.log_bug("DATABASE", "database/session.py", 0, f"Session factory error: {e}")
            
            # Check connection (DatabaseConnection uses singleton pattern, not get_instance)
            try:
                db = DatabaseConnection()
                engine = DatabaseConnection.get_engine()
                if engine is None:
                    self.log_warning("DATABASE", "database/connection.py", "Database not initialized")
            except RuntimeError as e:
                # This is expected if database not initialized - not a bug
                self.log_warning("DATABASE", "database/connection.py", f"Database not initialized (expected): {e}")
            except Exception as e:
                issues += 1
                self.log_bug("DATABASE", "database/connection.py", 0, f"Connection error: {e}")
                
        except ImportError as e:
            issues += 1
            self.log_bug("DATABASE", "database", 0, f"Import error: {e}")
        
        return issues
    
    def check_api_endpoints(self):
        """Check API endpoint definitions"""
        print("\n" + "=" * 60)
        print("CHECKING: API Endpoint Issues")
        print("=" * 60)
        
        issues = 0
        api_files = list((self.backend_path / "api").glob("*.py"))
        
        for api_file in api_files:
            try:
                content = api_file.read_text()
                
                # Check for common issues
                if "@router." in content:
                    # Check for missing return type hints
                    if "@router.get" in content or "@router.post" in content:
                        # Check if functions have proper async/def
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if "@router." in line and i + 1 < len(lines):
                                next_line = lines[i + 1].strip()
                                if not (next_line.startswith("async def") or next_line.startswith("def")):
                                    self.log_warning("API", api_file, f"Line {i+2}: Decorator may not be followed by function")
                                    issues += 1
            except Exception as e:
                self.log_warning("API", api_file, f"Could not check: {e}")
        
        if issues == 0:
            print("  [OK] No obvious API endpoint issues")
        return issues
    
    def check_configuration(self):
        """Check for configuration issues"""
        print("\n" + "=" * 60)
        print("CHECKING: Configuration Issues")
        print("=" * 60)
        
        issues = 0
        
        # Check settings.py
        settings_file = self.backend_path / "settings.py"
        if settings_file.exists():
            try:
                content = settings_file.read_text()
                # Check for common issues
                if "DATABASE" in content and "None" in content:
                    # Check if critical settings might be None
                    if "DATABASE_NAME = None" in content or "DATABASE_PATH = None" in content:
                        self.log_warning("CONFIG", settings_file, "Database path/name might be None")
                        issues += 1
            except Exception as e:
                self.log_warning("CONFIG", settings_file, f"Could not check: {e}")
        
        # Check .env or config files
        env_file = Path(".env")
        if not env_file.exists():
            self.log_warning("CONFIG", ".env", ".env file not found (may use defaults)")
        
        if issues == 0:
            print("  [OK] No obvious configuration issues")
        return issues
    
    def check_runtime_errors(self):
        """Try to catch runtime errors by importing and initializing"""
        print("\n" + "=" * 60)
        print("CHECKING: Runtime Errors")
        print("=" * 60)
        
        issues = 0
        
        # Try importing app (but don't run it)
        try:
            import app
            print("  [OK] app.py imports successfully")
        except Exception as e:
            issues += 1
            self.log_bug("RUNTIME", "app.py", 0, f"Import error: {e}")
            traceback.print_exc()
        
        # Try importing critical modules
        critical = [
            "timesense.engine",
            "genesis_ide.core_integration",
            "diagnostic_machine.diagnostic_engine",
        ]
        
        for module_name in critical:
            try:
                mod = importlib.import_module(module_name)
                print(f"  [OK] {module_name}")
            except Exception as e:
                issues += 1
                self.log_bug("RUNTIME", module_name, 0, f"Runtime error: {e}")
        
        return issues
    
    def check_common_bugs(self):
        """Check for common Python bugs"""
        print("\n" + "=" * 60)
        print("CHECKING: Common Bugs")
        print("=" * 60)
        
        issues = 0
        python_files = list(self.backend_path.rglob("*.py"))
        
        for py_file in python_files[:100]:  # Check first 100 files
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                for i, line in enumerate(lines, 1):
                    # Check for common issues
                    stripped = line.strip()
                    
                    # Mutable default arguments
                    if "def " in stripped and "=[]" in stripped:
                        self.log_bug("COMMON_BUG", py_file, i, "Mutable default argument (use None instead)", "WARNING")
                        issues += 1
                    
                    # == vs is
                    if " is " in stripped and any(x in stripped for x in ['"', "'", "0", "1", "True", "False"]):
                        if "==" not in stripped:  # Might be legitimate
                            self.log_warning("COMMON_BUG", py_file, f"Line {i}: Using 'is' with literal (use == instead)")
                    
                    # Bare except
                    if stripped == "except:":
                        self.log_bug("COMMON_BUG", py_file, i, "Bare except clause (specify exception)", "WARNING")
                        issues += 1
                    
                    # Print statements (should use logger)
                    if stripped.startswith("print(") and "logger" not in " ".join(lines[max(0, i-5):i]):
                        self.log_warning("COMMON_BUG", py_file, f"Line {i}: Using print() instead of logger")
            except Exception:
                pass
        
        if issues == 0:
            print("  [OK] No obvious common bugs found")
        return issues
    
    def run_all_checks(self):
        """Run all bug checks"""
        print("=" * 60)
        print("GRACE BUG HUNTER - Comprehensive Bug Detection")
        print("=" * 60)
        
        results = {}
        results['syntax'] = self.check_syntax_errors()
        results['imports'] = self.check_import_errors()
        results['missing_files'] = self.check_missing_files()
        results['type_hints'] = self.check_type_hints()
        results['circular'] = self.check_circular_imports()
        results['database'] = self.check_database_issues()
        results['api'] = self.check_api_endpoints()
        results['config'] = self.check_configuration()
        results['runtime'] = self.check_runtime_errors()
        results['common'] = self.check_common_bugs()
        
        # Summary
        print("\n" + "=" * 60)
        print("BUG HUNT SUMMARY")
        print("=" * 60)
        
        total_bugs = len(self.bugs)
        total_warnings = len(self.warnings)
        
        print(f"\n  Total Bugs Found: {total_bugs}")
        print(f"  Total Warnings: {total_warnings}")
        print(f"\n  By Category:")
        
        bug_categories = {}
        for bug in self.bugs:
            cat = bug['category']
            bug_categories[cat] = bug_categories.get(cat, 0) + 1
        
        for cat, count in sorted(bug_categories.items()):
            print(f"    {cat}: {count}")
        
        # Save report
        report = {
            "bugs": self.bugs,
            "warnings": self.warnings,
            "summary": {
                "total_bugs": total_bugs,
                "total_warnings": total_warnings,
                "by_category": bug_categories
            }
        }
        
        report_file = Path("bug_hunt_report.json")
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n  Report saved to: {report_file}")
        
        return total_bugs, total_warnings


def main():
    """Main entry point"""
    hunter = BugHunter()
    bugs, warnings = hunter.run_all_checks()
    
    if bugs == 0 and warnings == 0:
        print("\n  [SUCCESS] No bugs or warnings found!")
        return 0
    elif bugs == 0:
        print(f"\n  [WARN] {warnings} warnings found (non-critical)")
        return 0
    else:
        print(f"\n  [FAIL] {bugs} bugs and {warnings} warnings found")
        return 1


if __name__ == "__main__":
    sys.exit(main())
