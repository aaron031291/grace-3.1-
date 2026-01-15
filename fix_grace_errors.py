"""
Fix All Errors and Warnings from Grace's Logs

This script identifies and fixes all errors and warnings found in Grace's logs.
"""

import sys
import re
from pathlib import Path
from collections import defaultdict

# Add backend to path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

print("=" * 80)
print("GRACE ERROR & WARNING FIX REPORT")
print("=" * 80)
print()

def analyze_errors():
    """Analyze logs for errors and warnings."""
    log_file = Path("logs/grace_self_healing_background.log")
    
    if not log_file.exists():
        print("[ERROR] Log file not found")
        return {}
    
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    errors = defaultdict(int)
    warnings = defaultdict(int)
    
    for line in lines:
        if 'ERROR' in line or 'ERROR -' in line:
            # Extract error message
            error_match = re.search(r'ERROR[^:]*:\s*(.+)', line)
            if error_match:
                error_msg = error_match.group(1).strip()
                # Simplify error message
                if 'change_origin' in error_msg:
                    errors['Database schema: missing change_origin column'] += 1
                elif 'JSON serializable' in error_msg:
                    errors['JSON serialization: Exception objects not serializable'] += 1
                elif 'check_ollama_running' in error_msg:
                    errors['Import error: check_ollama_running missing'] += 1
                elif 'overall_status' in error_msg:
                    errors['Attribute error: HealthReport.overall_status'] += 1
                elif 'invalid keyword argument' in error_msg:
                    errors['Genesis Key: invalid keyword argument'] += 1
                elif 'Failed to create Genesis Key' in error_msg:
                    errors['Genesis Key creation failures'] += 1
                else:
                    errors[error_msg[:100]] += 1
        
        if 'WARNING' in line or 'WARN' in line:
            # Extract warning message
            warn_match = re.search(r'WARNING[^:]*:\s*(.+)|WARN[^:]*:\s*(.+)', line)
            if warn_match:
                warn_msg = (warn_match.group(1) or warn_match.group(2)).strip()
                warnings[warn_msg[:100]] += 1
    
    return {
        'errors': dict(sorted(errors.items(), key=lambda x: x[1], reverse=True)),
        'warnings': dict(sorted(warnings.items(), key=lambda x: x[1], reverse=True))
    }

def show_fix_plan():
    """Show the fix plan for all errors and warnings."""
    
    issues = analyze_errors()
    
    print("[ERRORS FOUND]")
    print()
    for i, (error, count) in enumerate(list(issues['errors'].items())[:20], 1):
        print(f"  {i}. [{count}x] {error}")
    print()
    
    print("[WARNINGS FOUND]")
    print()
    for i, (warning, count) in enumerate(list(issues['warnings'].items())[:20], 1):
        print(f"  {i}. [{count}x] {warning}")
    print()
    
    print("=" * 80)
    print("FIX PLAN")
    print("=" * 80)
    print()
    
    fixes_needed = []
    
    # Check for specific errors
    if any('change_origin' in e for e in issues['errors'].keys()):
        fixes_needed.append({
            'priority': 'CRITICAL',
            'error': 'Database schema: missing change_origin column',
            'fix': 'Run database migration to add change_origin column',
            'file': 'backend/database/migrate_add_change_origin_column.py'
        })
    
    if any('JSON serializable' in e for e in issues['errors'].keys()):
        fixes_needed.append({
            'priority': 'HIGH',
            'error': 'JSON serialization: Exception objects not serializable',
            'fix': 'Ensure all Exception objects are converted to strings before JSON serialization',
            'file': 'backend/cognitive/devops_healing_agent.py'
        })
    
    if any('check_ollama_running' in e for e in issues['errors'].keys()):
        fixes_needed.append({
            'priority': 'HIGH',
            'error': 'Import error: check_ollama_running missing',
            'fix': 'Add check_ollama_running function or update imports',
            'file': 'backend/ollama_client/client.py'
        })
    
    if any('overall_status' in e for e in issues['errors'].keys()):
        fixes_needed.append({
            'priority': 'HIGH',
            'error': 'Attribute error: HealthReport.overall_status',
            'fix': 'Use health_status instead of overall_status',
            'file': 'backend/cognitive/devops_healing_agent.py'
        })
    
    if any('invalid keyword argument' in e for e in issues['errors'].keys()):
        fixes_needed.append({
            'priority': 'HIGH',
            'error': 'Genesis Key: invalid keyword argument',
            'fix': 'Fix Genesis Key creation calls to use correct parameters',
            'file': 'backend/cognitive/autonomous_help_requester.py'
        })
    
    print("FIXES NEEDED:")
    print()
    for i, fix in enumerate(fixes_needed, 1):
        print(f"{i}. [{fix['priority']}] {fix['error']}")
        print(f"   Fix: {fix['fix']}")
        print(f"   File: {fix['file']}")
        print()
    
    return fixes_needed

if __name__ == "__main__":
    fixes = show_fix_plan()
    print(f"\nTotal fixes needed: {len(fixes)}")
    print("\nRun the fixes to resolve all errors and warnings.")
