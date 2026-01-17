#!/usr/bin/env python3
"""Apply G012 (missing logger) fixes using AST transformer"""

import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from cognitive.code_analyzer_self_healing import CodeAnalyzerSelfHealing, CodeFixApplicator
from cognitive.grace_code_analyzer import GraceCodeAnalyzer, CodeIssue

print("=" * 70)
print("Applying G012 (missing logger) fixes using AST transformer")
print("=" * 70)

# Step 1: Find all G012 issues
print("\n[*] Scanning codebase for G012 issues...")
analyzer = GraceCodeAnalyzer()
results = analyzer.analyze_directory('backend')

# Collect G012 issues
g012_issues = []
for file_path, issues in results.items():
    for issue in issues:
        if issue.rule_id == 'G012':
            g012_issues.append((file_path, issue))

print(f"[*] Found {len(g012_issues)} G012 issues")

if not g012_issues:
    print("[OK] No G012 issues found!")
    sys.exit(0)

# Step 2: Apply fixes
print(f"\n[*] Applying AST transformer fixes...")
fix_applicator = CodeFixApplicator()
fixed_count = 0
failed_count = 0

for file_path, issue in g012_issues:  # Apply fixes to all G012 issues
    file_path_obj = Path(file_path)
    if not file_path_obj.exists():
        print(f"[!] File not found: {file_path}")
        continue
    
    try:
        # Read original source
        with open(file_path_obj, 'r', encoding='utf-8') as f:
            original_source = f.read()
        
        # Apply fix
        success, fixed_code = fix_applicator.apply_fix(issue, original_source)
        
        if success:
            # Write fixed code back
            with open(file_path_obj, 'w', encoding='utf-8') as f:
                f.write(fixed_code)
            fixed_count += 1
            print(f"[OK] Fixed: {file_path}:{issue.line_number}")
        else:
            failed_count += 1
            print(f"[!] Failed to fix: {file_path}:{issue.line_number}")
    except Exception as e:
        failed_count += 1
        print(f"[ERROR] Error fixing {file_path}: {e}")

print("\n" + "=" * 70)
print(f"Fix Summary:")
print(f"  - Total G012 issues: {len(g012_issues)}")
print(f"  - Fixed: {fixed_count}")
print(f"  - Failed: {failed_count}")
print("=" * 70)
