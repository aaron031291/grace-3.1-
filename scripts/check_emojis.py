#!/usr/bin/env python
"""
Pre-commit hook to check for emojis in code.

This script checks Python files for emoji usage and fails if any are found.
Emojis are removed to prevent encoding issues and improve debugging.

Usage:
    python scripts/check_emojis.py [file1.py] [file2.py] ...
    
    If no files specified, checks all .py files in backend/
"""

import sys
import os
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from utils.emoji_sanitizer import check_code_for_emojis, EMOJI_PATTERN

def check_file(file_path: Path) -> list:
    """Check a single file for emojis."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        violations = check_code_for_emojis(code, str(file_path))
        return violations
    except Exception as e:
        print(f"Error checking {file_path}: {e}", file=sys.stderr)
        return []


def safe_print(text):
    """Print text safely, handling encoding issues."""
    try:
        print(text)
    except UnicodeEncodeError:
        # Replace problematic characters
        safe_text = text.encode('ascii', 'replace').decode('ascii')
        print(safe_text)


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        # Check specified files
        files_to_check = [Path(f) for f in sys.argv[1:]]
    else:
        # Check all Python files in backend/
        backend_dir = Path(__file__).parent.parent / "backend"
        files_to_check = list(backend_dir.rglob("*.py"))
        # Exclude certain directories and emoji_sanitizer itself
        exclude_dirs = {'__pycache__', '.git', 'node_modules', 'venv', '.venv'}
        files_to_check = [
            f for f in files_to_check 
            if not any(excluded in f.parts for excluded in exclude_dirs)
            and 'emoji_sanitizer' not in str(f)  # Skip the sanitizer itself
        ]
    
    all_violations = []
    
    for file_path in files_to_check:
        if not file_path.exists():
            continue
        
        violations = check_file(file_path)
        all_violations.extend(violations)
    
    if all_violations:
        print("\n" + "=" * 80)
        print("EMOJI VIOLATIONS DETECTED")
        print("=" * 80)
        print("\nEmojis are not allowed in code to prevent encoding issues.")
        print("Replace them with text equivalents: [OK] for success, [ERROR] for failures, etc.\n")
        
        for violation in all_violations:
            # Sanitize emojis for display (replace with text)
            emojis_safe = ['[EMOJI]' for _ in violation['emojis']]  # Just show generic
            emoji_str = ', '.join(emojis_safe)
            safe_print(f"File: {violation['file']}")
            safe_print(f"  Line {violation['line']}: Found emojis")
            # Sanitize code display too
            code_safe = violation['code'][:100].encode('ascii', 'replace').decode('ascii')
            safe_print(f"  Code: {code_safe}")
            safe_print("")
        
        safe_print("=" * 80)
        safe_print(f"\nTotal violations: {len(all_violations)}")
        safe_print("\nPlease remove emojis and use text equivalents instead.")
        sys.exit(1)
    else:
        safe_print("[OK] No emojis detected in code.")
        sys.exit(0)


if __name__ == "__main__":
    main()
