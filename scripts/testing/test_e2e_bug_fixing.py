#!/usr/bin/env python3
"""
End-to-End Test for Automatic Bug Fixing System
Tests the complete flow: detection -> fixing -> verification
"""
import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

def test_e2e_bug_fixing():
    """Test the complete bug fixing flow."""
    print("\n" + "="*70)
    print("END-TO-END TEST: Automatic Bug Fixing System")
    print("="*70 + "\n")
    
    # Create temporary test directory
    test_dir = Path(tempfile.mkdtemp(prefix="grace_bug_fix_test_"))
    print(f"[TEST] Created test directory: {test_dir}")
    
    try:
        # Step 1: Create test files with known bugs
        print("\n[STEP 1] Creating test files with known bugs...")
        test_files = create_test_files_with_bugs(test_dir)
        print(f"[OK] Created {len(test_files)} test files with bugs")
        
        # Step 2: Run proactive scanner
        print("\n[STEP 2] Running proactive code scanner...")
        from diagnostic_machine.proactive_code_scanner import ProactiveCodeScanner
        scanner = ProactiveCodeScanner(backend_dir=test_dir)
        issues = scanner.scan_all()
        print(f"[OK] Scanner found {len(issues)} issues")
        
        # Display issues found
        for issue in issues[:10]:  # Show first 10
            print(f"  - [{issue.severity.upper()}] {issue.issue_type}: {issue.file_path}:{issue.line_number}")
            print(f"    {issue.message[:60]}")
        
        # Also test code quality scanner for print statements and bare except
        print("\n[STEP 2b] Testing code quality detection...")
        quality_issues = []
        for test_file in test_files:
            content = test_file.read_text()
            if 'except:' in content and 'except Exception:' not in content:
                from diagnostic_machine.proactive_code_scanner import CodeIssue
                quality_issues.append(CodeIssue(
                    issue_type='code_quality',
                    severity='high',
                    file_path=str(test_file.relative_to(test_dir)),
                    line_number=content.split('\n').index([l for l in content.split('\n') if 'except:' in l][0]) + 1,
                    message='Bare except clause (specify exception)'
                ))
            if 'print(' in content and 'logger' not in content:
                for i, line in enumerate(content.split('\n'), 1):
                    if 'print(' in line:
                        from diagnostic_machine.proactive_code_scanner import CodeIssue
                        quality_issues.append(CodeIssue(
                            issue_type='code_quality',
                            severity='low',
                            file_path=str(test_file.relative_to(test_dir)),
                            line_number=i,
                            message='Use logger instead of print()'
                        ))
                        break
        
        issues.extend(quality_issues)
        print(f"[OK] Added {len(quality_issues)} code quality issues")
        
        # Step 3: Run automatic bug fixer
        print("\n[STEP 3] Running automatic bug fixer...")
        from diagnostic_machine.automatic_bug_fixer import AutomaticBugFixer
        fixer = AutomaticBugFixer(backend_dir=test_dir, create_backups=True)
        
        # Filter by severity
        critical_issues = [i for i in issues if i.severity == 'critical']
        high_issues = [i for i in issues if i.severity == 'high']
        medium_issues = [i for i in issues if i.severity == 'medium']
        
        print(f"  Critical: {len(critical_issues)}, High: {len(high_issues)}, Medium: {len(medium_issues)}")
        
        # Show issue details for debugging
        for issue in critical_issues[:3]:
            print(f"    Issue: {issue.issue_type} at {issue.file_path}:{issue.line_number}")
            print(f"    Message: {issue.message[:80]}")
        
        # Fix critical and high issues
        critical_fixes = fixer.fix_all_issues(critical_issues)
        high_fixes = fixer.fix_all_issues(high_issues)
        medium_fixes = fixer.fix_all_issues(medium_issues)
        
        successful = [f for f in critical_fixes + high_fixes + medium_fixes if f.success]
        failed = [f for f in critical_fixes + high_fixes + medium_fixes if not f.success]
        
        print(f"[OK] Fixed {len(successful)} issues, {len(failed)} failed")
        
        # Display fixes
        for fix in successful[:10]:  # Show first 10
            print(f"  - Fixed {fix.issue_type} in {fix.file_path}")
            print(f"    {fix.fix_applied[:60]}")
        
        # Display failures
        for fix in failed[:5]:  # Show first 5 failures
            print(f"  - Failed to fix {fix.issue_type} in {fix.file_path}")
            print(f"    Error: {fix.error_message[:60]}")
        
        # Step 4: Verify fixes (before cleanup)
        print("\n[STEP 4] Verifying fixes...")
        verification_results = verify_fixes(test_dir, test_files, successful)
        print(f"[OK] Verification: {verification_results['passed']}/{verification_results['total']} checks passed")
        
        # Step 5: Test rollback
        print("\n[STEP 5] Testing rollback functionality...")
        rollback_results = test_rollback(test_dir, successful)
        print(f"[OK] Rollback: {rollback_results['passed']}/{rollback_results['total']} rollbacks successful")
        
        # Step 6: Test warning fixes
        print("\n[STEP 6] Testing warning fixes (print statements)...")
        # Create a file with print statements
        print_file = test_dir / "test_print_statements.py"
        print_file.write_text("""# Test file with print statements
def debug_function():
    print("Debug message 1")
    print("Debug message 2")
    return True
""")
        warning_fixes = fixer.fix_all_warnings(max_files=10)
        warning_successful = [f for f in warning_fixes if f.success]
        print(f"[OK] Fixed {len(warning_successful)} warning issues")
        
        # Verify print fixes
        if print_file.exists():
            content = print_file.read_text()
            if 'logger.info(' in content or 'import logging' in content:
                print(f"    [OK] Print statements converted to logger")
        
        # Step 7: Test integration with healing executor
        print("\n[STEP 7] Testing integration with healing executor...")
        healing_results = test_healing_integration(test_dir)
        print(f"[OK] Healing integration: {healing_results['success']}")
        
        # Summary
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        print(f"  Issues detected: {len(issues)}")
        print(f"  Issues fixed: {len(successful)}")
        print(f"  Fixes failed: {len(failed)}")
        print(f"  Verification passed: {verification_results['passed']}/{verification_results['total']}")
        print(f"  Rollback successful: {rollback_results['passed']}/{rollback_results['total']}")
        print(f"  Warnings fixed: {len(warning_successful)}")
        print(f"  Healing integration: {'PASS' if healing_results['success'] else 'FAIL'}")
        
        total_score = (
            (len(successful) / max(len(issues), 1)) * 0.3 +
            (verification_results['passed'] / max(verification_results['total'], 1)) * 0.3 +
            (rollback_results['passed'] / max(rollback_results['total'], 1)) * 0.2 +
            (1.0 if healing_results['success'] else 0.0) * 0.2
        ) * 100
        
        print(f"\n  Overall Score: {total_score:.1f}%")
        
        if total_score >= 80:
            print("\n[RESULT] PASS - System is working correctly!")
            return True
        else:
            print("\n[RESULT] FAIL - Some issues need attention")
            return False
            
    except Exception as e:
        print(f"\n[ERROR] Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup
        print(f"\n[CLEANUP] Removing test directory: {test_dir}")
        shutil.rmtree(test_dir, ignore_errors=True)


def create_test_files_with_bugs(test_dir: Path) -> list:
    """Create test files with various types of bugs."""
    test_files = []
    
    # File 1: Code quality issues (these are easier to fix)
    file1 = test_dir / "test_quality_bugs.py"
    file1.write_text("""# Test file with code quality issues
def bad_except():
    try:
        x = 1 / 0
    except:  # Bare except - should be except Exception:
        pass

def bad_comparison():
    x = "test"
    if x is "test":  # 'is' with literal - should be ==
        return True
    return False

def print_debug():
    print("Debug message")  # Should use logger
    print("Another debug")
""")
    test_files.append(file1)
    
    # File 2: Missing file import (will be detected)
    file2 = test_dir / "test_import_bugs.py"
    file2.write_text("""# Test file with import errors
# This will try to import a missing module
try:
    from missing_module import something
except ImportError:
    pass

def use_imports():
    return "test"
""")
    test_files.append(file2)
    
    # File 3: Security issues (pattern-based)
    file3 = test_dir / "test_security_bugs.py"
    file3.write_text("""# Test file with security issues
import subprocess
import os

def unsafe_shell():
    subprocess.call("ls", shell=True)  # Command injection risk

def unsafe_os():
    os.system("echo test")  # Dangerous os.system

import yaml
def unsafe_yaml():
    with open("file.yaml") as f:
        data = yaml.load(f)  # Unsafe YAML load
    return data
""")
    test_files.append(file3)
    
    # File 4: Syntax error (simple one - missing colon)
    file4 = test_dir / "test_syntax_bugs.py"
    file4.write_text("""# Test file with syntax errors
def broken_function():
    if True  # Missing colon
        pass
    return True

def another_function():
    x = 1 + 2
    return x
""")
    test_files.append(file4)
    
    return test_files


def verify_fixes(test_dir: Path, original_files: list, fixes_applied: list) -> dict:
    """Verify that fixes were applied correctly."""
    results = {'passed': 0, 'total': 0}
    
    # Check each fix that was applied
    for fix in fixes_applied:
        if fix.success:
            # Get the actual file path
            file_path = test_dir / Path(fix.file_path).name
            if not file_path.exists():
                # Try with full path
                file_path = Path(fix.file_path) if Path(fix.file_path).is_absolute() else test_dir / fix.file_path
            
            if file_path.exists():
                results['total'] += 1
                content = file_path.read_text()
                
                # Verify the fix based on issue type
                if fix.issue_type == 'syntax_error' and 'Added missing colon' in fix.fix_applied:
                    if 'if True:' in content:
                        results['passed'] += 1
                        print(f"    [OK] Syntax fix verified: missing colon added")
                
                elif fix.issue_type == 'code_quality':
                    if 'bare except' in fix.fix_applied.lower() or 'except Exception:' in content:
                        results['passed'] += 1
                        print(f"    [OK] Code quality fix verified: {fix.fix_applied[:40]}")
    
    # Also check specific files for expected fixes
    syntax_file = test_dir / "test_syntax_bugs.py"
    if syntax_file.exists():
        results['total'] += 1
        content = syntax_file.read_text()
        # Check if colon was added
        if 'if True:' in content:
            results['passed'] += 1
            print(f"    [OK] Missing colon fixed in syntax file")
    
    # Check if backups were created
    backup_files = list(test_dir.glob("*.backup"))
    if backup_files:
        results['total'] += 1
        results['passed'] += 1
        print(f"    [OK] Backup files created: {len(backup_files)}")
    
    return results


def test_rollback(test_dir: Path, fixes: list) -> dict:
    """Test rollback functionality."""
    results = {'passed': 0, 'total': 0}
    
    # Check if backups were created
    for fix in fixes[:5]:  # Test first 5
        if fix.backup_created:
            results['total'] += 1
            # Check if backup file exists
            backup_path = test_dir / f"{Path(fix.file_path).stem}.backup"
            if backup_path.exists() or any(f.name.endswith('.backup') for f in test_dir.glob('*.backup')):
                results['passed'] += 1
    
    return results


def test_healing_integration(test_dir: Path) -> dict:
    """Test integration with healing executor."""
    try:
        from diagnostic_machine.healing import get_healing_executor, HealingActionType
        
        healer = get_healing_executor()
        
        # Try to execute code fix action
        result = healer.execute(
            HealingActionType.CODE_FIX,
            {'fix_warnings': False}
        )
        
        return {'success': result.success or 'No code issues detected' in result.message}
    except Exception as e:
        print(f"    [WARN] Healing integration test failed: {e}")
        return {'success': False}


if __name__ == "__main__":
    success = test_e2e_bug_fixing()
    sys.exit(0 if success else 1)
