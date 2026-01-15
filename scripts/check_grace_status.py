"""
Check if Grace's self-healing agent is running and show status.
"""

import sys
from pathlib import Path
from datetime import datetime
import os

# Add backend to path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

print("=" * 80)
print("GRACE SELF-HEALING AGENT STATUS CHECK")
print("=" * 80)
print()

# Check log files (relative to repo root)
repo_root = Path(__file__).parent.parent
log_files = [
    repo_root / "logs" / "grace_self_healing_background.log",
    repo_root / "backend" / "logs" / "grace_self_healing.log"
]

print("Checking log files...")
for log_path in log_files:
    if log_path.exists():
        # Get last modified time
        mod_time = datetime.fromtimestamp(log_path.stat().st_mtime)
        age = datetime.now() - mod_time
        
        # Get last few lines
        try:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                last_lines = lines[-10:] if len(lines) > 10 else lines
                
            print(f"\n[{log_path.relative_to(repo_root)}]")
            print(f"  Last modified: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  Age: {age}")
            if age.total_seconds() < 120:  # Less than 2 minutes
                print(f"  Status: [RUNNING] - Log updated recently")
            else:
                print(f"  Status: [STOPPED] - Log not updated recently")
            
            print(f"\n  Last 5 log lines:")
            for line in last_lines[-5:]:
                print(f"    {line.strip()}")
        except Exception as e:
            print(f"  Error reading log: {e}")
    else:
        print(f"\n[{log_path.relative_to(repo_root)}]")
        print(f"  Status: [NOT FOUND] - Agent has not run yet")

print("\n" + "=" * 80)
print("HOW TO START GRACE SELF-HEALING")
print("=" * 80)
print()
print("To start Grace's self-healing agent in the background:")
print("  python scripts/start_self_healing_background.py")
print()
print("The agent will:")
print("  1. Initialize (takes ~10-30 seconds)")
print("  2. Start healing cycles (every 60 seconds)")
print("  3. Create snapshots when stable (every 30 minutes)")
print()
print("Startup time: ~10-30 seconds")
print("First healing cycle: ~1-2 minutes after startup")
print()
