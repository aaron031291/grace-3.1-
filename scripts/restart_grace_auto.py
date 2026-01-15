"""
Automatically restart Grace's Self-Healing Agent

This script:
1. Stops any running Grace processes
2. Waits briefly
3. Restarts Grace with the new code
4. Verifies it's running

Usage:
    python restart_grace_auto.py
"""

import sys
import os
import time
import subprocess
from pathlib import Path
from datetime import datetime

print("=" * 80)
print("GRACE SELF-HEALING AGENT - AUTO RESTART")
print("=" * 80)
print()

# Step 1: Stop any running Grace processes
print("[STEP 1] Stopping any running Grace processes...")
print()

if os.name == 'nt':  # Windows
    # Try to kill processes by finding them via command line
    try:
        # Use wmic to find processes with our script name
        result = subprocess.run(
            ['wmic', 'process', 'where', 'commandline like "%start_self_healing_background.py%"', 'get', 'processid'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0 and 'ProcessId' in result.stdout:
            lines = result.stdout.strip().split('\n')
            pids = []
            for line in lines[1:]:  # Skip header
                line = line.strip()
                if line and line.isdigit():
                    pids.append(line)
            
            if pids:
                print(f"  [FOUND] {len(pids)} Grace process(es) to stop")
                for pid in pids:
                    try:
                        subprocess.run(['taskkill', '/F', '/PID', pid], timeout=3, capture_output=True)
                        print(f"    - Stopped PID {pid}")
                    except:
                        pass
            else:
                print("  [INFO] No Grace processes found running")
        else:
            print("  [INFO] No Grace processes found (or couldn't check)")
    except Exception as e:
        print(f"  [INFO] Could not automatically find processes: {e}")
        print("  [NOTE] If Grace is running, please stop it manually via Task Manager")
else:  # Unix/Linux/Mac
    try:
        # Use pkill to kill processes
        subprocess.run(['pkill', '-f', 'start_self_healing_background.py'], timeout=3, capture_output=True)
        print("  [OK] Sent stop signal to Grace processes")
    except:
        print("  [INFO] Could not automatically stop processes")

print()
print("  Waiting 3 seconds for cleanup...")
time.sleep(3)
print("  [OK] Ready to restart")
print()

# Step 2: Start Grace with new code
print("[STEP 2] Starting Grace with new code...")
print()

start_script = Path(__file__).parent.parent / "scripts" / "start_self_healing_background.py"
if not start_script.exists():
    print(f"  [ERROR] Start script not found: {start_script}")
    sys.exit(1)

try:
    print(f"  Starting: python {start_script}")
    
    # Start in background
    if os.name == 'nt':  # Windows
        # Start in new console window
        subprocess.Popen(
            [sys.executable, str(start_script)],
            creationflags=subprocess.CREATE_NEW_CONSOLE,
            cwd=str(Path.cwd())
        )
    else:  # Unix/Linux/Mac
        # Start in background
        subprocess.Popen(
            [sys.executable, str(start_script)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            cwd=str(Path.cwd())
        )
    
    print("  [OK] Grace started in background")
    print()
    
    # Step 3: Verify it's running
    print("[STEP 3] Verifying Grace is running...")
    print()
    
    print("  Waiting for Grace to initialize (15 seconds)...")
    time.sleep(15)
    
    repo_root = Path(__file__).parent.parent
    log_file = repo_root / "logs" / "grace_self_healing_background.log"
    if log_file.exists():
        mod_time = datetime.fromtimestamp(log_file.stat().st_mtime)
        age = (datetime.now() - mod_time).total_seconds()
        
        if age < 30:
            print(f"  [OK] Grace is running! (log updated {age:.0f} seconds ago)")
            
            # Show last few log lines
            try:
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    last_lines = lines[-3:] if len(lines) > 3 else lines
                    print()
                    print("  Last log lines:")
                    for line in last_lines:
                        print(f"    {line.strip()}")
            except Exception as e:
                print(f"  [WARNING] Could not read log: {e}")
        else:
            print(f"  [INFO] Log updated {age:.0f} seconds ago - Grace may still be initializing")
    else:
        print("  [INFO] Log file not found yet - Grace may still be initializing")
    
    print()
    print("=" * 80)
    print("RESTART COMPLETE")
    print("=" * 80)
    print()
    print("Grace should now be running with the new code fixes!")
    print()
    print("Next steps:")
    print("  1. Wait ~60 seconds for first healing cycle")
    print("  2. Check status: python scripts/check_grace_status.py")
    print("  3. Check fixes: python scripts/show_grace_fixes.py")
    print()
    
except Exception as e:
    print(f"  [ERROR] Failed to start Grace: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
