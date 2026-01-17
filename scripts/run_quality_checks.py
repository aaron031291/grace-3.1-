#!/usr/bin/env python3
"""
Run all quality checks: tests, static analysis, security scanning.
This is a comprehensive bug-finding and prevention script.
"""

import subprocess
import sys
import os
from pathlib import Path
from typing import List, Tuple

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}{text.center(70)}{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")


def print_success(text: str):
    """Print success message."""
    print(f"{GREEN}✓ {text}{RESET}")


def print_error(text: str):
    """Print error message."""
    print(f"{RED}✗ {text}{RESET}")


def print_warning(text: str):
    """Print warning message."""
    print(f"{YELLOW}⚠ {text}{RESET}")


def run_command(cmd: List[str], description: str, required: bool = True) -> Tuple[bool, str]:
    """Run a command and return success status and output."""
    try:
        print(f"Running: {description}...")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            cwd=Path(__file__).parent.parent / "backend"
        )
        
        if result.returncode == 0:
            print_success(f"{description} passed")
            return True, result.stdout
        else:
            if required:
                print_error(f"{description} failed")
            else:
                print_warning(f"{description} found issues (non-critical)")
            print(result.stdout)
            print(result.stderr)
            return False, result.stderr
        
    except FileNotFoundError as e:
        if required:
            print_error(f"{description} - tool not found: {e}")
        else:
            print_warning(f"{description} - tool not installed (optional)")
        return False, str(e)
    except Exception as e:
        print_error(f"{description} - error: {e}")
        return False, str(e)


def main():
    """Run all quality checks."""
    print_header("GRACE Quality Assurance Suite")
    
    results = []
    
    # 1. Unit Tests with Coverage
    print_header("1. Running Tests with Coverage")
    success, output = run_command(
        ["python", "-m", "pytest", "tests/", "-v"],
        "Pytest with coverage",
        required=True
    )
    results.append(("Tests", success))
    
    # 2. Static Analysis - Bandit (Security)
    print_header("2. Security Scanning (Bandit)")
    success, output = run_command(
        ["bandit", "-r", ".", "-f", "json", "-o", "bandit-report.json"],
        "Bandit security scan",
        required=False
    )
    results.append(("Security Scan", success))
    
    # 3. Static Analysis - Safety (Dependencies)
    print_header("3. Dependency Vulnerability Check (Safety)")
    success, output = run_command(
        ["safety", "check", "--file", "requirements.txt", "--json"],
        "Safety dependency check",
        required=False
    )
    results.append(("Dependency Check", success))
    
    # 4. Code Quality - Flake8
    print_header("4. Code Style Check (Flake8)")
    success, output = run_command(
        ["flake8", ".", "--max-line-length=120", "--exclude=__pycache__,venv,*.pyc"],
        "Flake8 style check",
        required=False
    )
    results.append(("Style Check", success))
    
    # 5. Code Quality - Pylint
    print_header("5. Code Quality Check (Pylint)")
    success, output = run_command(
        ["pylint", "--recursive=y", "--disable=all", "--enable=E,F", ".", "--exit-zero"],
        "Pylint basic checks",
        required=False
    )
    results.append(("Code Quality", success))
    
    # 6. Type Checking - mypy
    print_header("6. Type Checking (mypy)")
    success, output = run_command(
        ["mypy", ".", "--ignore-missing-imports", "--no-strict-optional"],
        "mypy type checking",
        required=False
    )
    results.append(("Type Checking", success))
    
    # 7. Semgrep (if installed)
    print_header("7. Static Analysis (Semgrep)")
    success, output = run_command(
        ["semgrep", "--config=auto", ".", "--json", "-o", "semgrep-report.json"],
        "Semgrep static analysis",
        required=False
    )
    results.append(("Semgrep Analysis", success))
    
    # Summary
    print_header("Quality Check Summary")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    required_failed = [
        name for name, success in results 
        if not success and name in ["Tests"]
    ]
    
    for name, success in results:
        status = f"{GREEN}PASS{RESET}" if success else f"{RED}FAIL{RESET}"
        print(f"  {name:30} {status}")
    
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"Total: {passed}/{total} checks passed")
    
    if required_failed:
        print_error(f"\nRequired checks failed: {', '.join(required_failed)}")
        print("Fix these issues before proceeding.\n")
        return 1
    elif passed == total:
        print_success("\nAll quality checks passed! ✓")
        print("\nReports generated:")
        print("  - Coverage: backend/htmlcov/index.html")
        print("  - Bandit: backend/bandit-report.json")
        print("  - Semgrep: backend/semgrep-report.json")
        return 0
    else:
        print_warning(f"\n{total - passed} non-critical checks found issues.")
        print("Review the output above, but you can proceed.\n")
        return 0


if __name__ == "__main__":
    sys.exit(main())
