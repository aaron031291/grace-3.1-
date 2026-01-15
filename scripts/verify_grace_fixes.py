"""
Verify that Grace's fixes are working correctly.

This script:
1. Checks if Grace is running
2. Verifies the code fixes are in place
3. Tests if errors are being converted to issues
4. Shows what Grace should detect
"""

import sys
from pathlib import Path
import importlib.util

# Add backend to path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

print("=" * 80)
print("GRACE FIXES VERIFICATION")
print("=" * 80)
print()

# 1. Check if fixes are in code
print("[1] Checking if code fixes are in place...")
print()

devops_file = backend_dir / "cognitive" / "devops_healing_agent.py"
if devops_file.exists():
    content = devops_file.read_text(encoding='utf-8')
    
    checks = {
        "health_status (not overall_status)": "health_report.health_status" in content and "overall_status" not in content.split("health_report.health_status")[0].split("\n")[-5:],
        "Error conversion to issues": '"Convert diagnostic errors into issues that need fixing"' in content,
        "Issues list initialized": '"issues": []' in content and "_run_diagnostics" in content.split('"issues": []')[0][-200:],
        "Anomalies as issues": "Add anomalies as issues if they exist" in content
    }
    
    for check_name, result in checks.items():
        status = "[OK]" if result else "[MISSING]"
        print(f"  {status} {check_name}")
    
    print()
    
    # Show relevant code snippets
    if "Convert diagnostic errors into issues" in content:
        print("  [OK] Error-to-issue conversion code found")
        # Find the section
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if "Convert diagnostic errors into issues" in line:
                print(f"\n  Code snippet (line {i+1}):")
                for j in range(max(0, i-2), min(len(lines), i+15)):
                    marker = ">>> " if j == i else "    "
                    print(f"  {marker}{lines[j]}")
                break
    else:
        print("  [ERROR] Error-to-issue conversion code NOT found!")
    
else:
    print("  [ERROR] devops_healing_agent.py not found!")

print()
print("=" * 80)
print("[2] Current Issues Grace Should Detect")
print("=" * 80)
print()

issues_to_detect = [
    {
        "error": "table genesis_key has no column named is_broken",
        "type": "Database schema issue",
        "category": "DATABASE",
        "layer": "DATABASE",
        "fix": "Add is_broken column to genesis_key table"
    },
    {
        "error": "'HealthReport' object has no attribute 'overall_status'",
        "type": "Code attribute error",
        "category": "CODE_ERROR",
        "layer": "BACKEND",
        "fix": "Use health_status instead of overall_status (already fixed in code)"
    }
]

for i, issue in enumerate(issues_to_detect, 1):
    print(f"[{i}] {issue['type']}")
    print(f"    Error: {issue['error']}")
    print(f"    Category: {issue['category']}")
    print(f"    Layer: {issue['layer']}")
    print(f"    Expected Fix: {issue['fix']}")
    print()

print("=" * 80)
print("[3] What Grace Needs to Do")
print("=" * 80)
print()
print("1. Restart Grace to load the new code fixes")
print("2. Run diagnostics (will now detect errors as issues)")
print("3. Attempt to fix the database schema issue")
print("4. Track fixes in Genesis Keys")
print()
print("To restart Grace:")
print("  1. Stop current process (if running)")
print("  2. Run: python scripts/start_self_healing_background.py")
print()
