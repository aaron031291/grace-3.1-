"""
Restart Grace's Self-Healing Agent

This script:
1. Finds and stops the current Grace process (if running)
2. Waits for graceful shutdown
3. Restarts Grace with the new code
4. Verifies it's running correctly
"""

import sys
import os
import time
import subprocess
from pathlib import Path
from datetime import datetime

print("=" * 80)
print("GRACE SELF-HEALING AGENT - RESTART")
print("=" * 80)
print()

# Step 1: Check if Grace is running
print("[STEP 1] Checking if Grace is running...")
print()

repo_root = Path(__file__).parent.parent
log_file = repo_root / "logs" / "grace_self_healing_background.log"
is_running = False

if log_file.exists():
    # Check if log was updated recently (within last 2 minutes)
    mod_time = datetime.fromtimestamp(log_file.stat().st_mtime)
    age = (datetime.now() - mod_time).total_seconds()
    
    if age < 120:  # Less than 2 minutes
        is_running = True
        print(f"  [FOUND] Grace appears to be running (log updated {age:.0f} seconds ago)")
    else:
        print(f"  [STOPPED] Grace appears to be stopped (log updated {age:.0f} seconds ago)")
else:
    print("  [NOT FOUND] No log file found - Grace hasn't run yet")

print()

# Step 2: Try to find and stop the process
if is_running:
    print("[STEP 2] Attempting to stop Grace...")
    print()
    
    # Try to find Python processes running Grace using tasklist (Windows) or ps (Unix)
    try:
        if os.name == 'nt':  # Windows
            # Use tasklist to find processes
            result = subprocess.run(
                ['tasklist', '/FI', 'IMAGENAME eq python.exe', '/FO', 'CSV'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # Try to find processes with Grace-related command lines
                # On Windows, we'll need to use wmic or just ask user to stop manually
                print("  [INFO] On Windows, please stop Grace manually:")
                print("    1. Open Task Manager (Ctrl+Shift+Esc)")
                print("    2. Find 'python.exe' processes")
                print("    3. Look for one running 'start_self_healing_background.py'")
                print("    4. End that process")
                print()
                response = input("  Have you stopped Grace manually? (y/n): ")
                if response.lower() != 'y':
                    print("  [CANCELLED] Please stop Grace first, then run this script again")
                    sys.exit(1)
            else:
                print("  [INFO] No Python processes found or couldn't check")
                response = input("  Have you stopped Grace manually? (y/n): ")
                if response.lower() != 'y':
                    print("  [CANCELLED] Please stop Grace first, then run this script again")
                    sys.exit(1)
        else:  # Unix/Linux/Mac
            # Use ps to find processes
            result = subprocess.run(
                ['ps', 'aux'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                grace_processes = [l for l in lines if 'start_self_healing_background.py' in l or 'grace_self_healing_agent.py' in l]
                
                if grace_processes:
                    print(f"  [FOUND] {len(grace_processes)} Grace process(es) found:")
                    for proc in grace_processes:
                        print(f"    {proc}")
                    print()
                    print("  Attempting to stop processes...")
                    
                    for proc in grace_processes:
                        parts = proc.split()
                        if len(parts) > 1:
                            pid = parts[1]
                            try:
                                subprocess.run(['kill', pid], timeout=2)
                                print(f"    - Sent kill signal to PID {pid}")
                            except:
                                pass
                    
                    time.sleep(3)
                else:
                    print("  [INFO] No Grace processes found (may have already stopped)")
            else:
                print("  [INFO] Could not check for processes")
                response = input("  Have you stopped Grace manually? (y/n): ")
                if response.lower() != 'y':
                    print("  [CANCELLED] Please stop Grace first, then run this script again")
                    sys.exit(1)
                    
    except Exception as e:
        print(f"  [WARNING] Could not automatically find processes: {e}")
        print("  [MANUAL] Please stop Grace manually:")
        if os.name == 'nt':
            print("    - Open Task Manager and end Python processes running Grace")
        else:
            print("    - Use 'ps aux | grep grace' to find and kill the process")
        print()
        response = input("  Have you stopped Grace manually? (y/n): ")
        if response.lower() != 'y':
            print("  [CANCELLED] Please stop Grace first, then run this script again")
            sys.exit(1)
    
    print()
    print("  [OK] Grace stopped (or stopping)")
    print()

# Step 3: Wait a moment for cleanup
print("[STEP 3] Waiting for cleanup...")
time.sleep(2)
print("  [OK] Ready to restart")
print()

# Step 4: Start Grace with new code
print("[STEP 4] Starting Grace with new code...")
print()

start_script = Path(__file__).parent.parent / "scripts" / "start_self_healing_background.py"
if not start_script.exists():
    print(f"  [ERROR] Start script not found: {start_script}")
    sys.exit(1)

try:
    # Start Grace in background
    print(f"  Starting: python {start_script}")
    
    # Use subprocess to start in background
    if os.name == 'nt':  # Windows
        # Start in new window (detached)
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
    
    # Step 5: Verify it's running
    print("[STEP 5] Verifying Grace is running...")
    print()
    
    print("  Waiting for Grace to initialize (10 seconds)...")
    time.sleep(10)
    
    # Check log file
    if log_file.exists():
        mod_time = datetime.fromtimestamp(log_file.stat().st_mtime)
        age = (datetime.now() - mod_time).total_seconds()
        
        if age < 30:  # Updated in last 30 seconds
            print(f"  [OK] Grace is running! (log updated {age:.0f} seconds ago)")
            
            # Show last few log lines
            try:
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    last_lines = lines[-5:] if len(lines) > 5 else lines
                    print()
                    print("  Last log lines:")
                    for line in last_lines:
                        print(f"    {line.strip()}")
            except Exception as e:
                print(f"  [WARNING] Could not read log: {e}")
        else:
            print(f"  [WARNING] Log not updated recently ({age:.0f} seconds ago)")
            print("  Grace may still be initializing...")
    else:
        print("  [WARNING] Log file not found yet - Grace may still be initializing")
    
    print()
    print("=" * 80)
    print("RESTART COMPLETE")
    print("=" * 80)
    print()
    print("Grace should now be running with the new code fixes!")
    print()
    print("To verify:")
    print("  1. Wait ~60 seconds for first healing cycle")
    print("  2. Check status: python scripts/check_grace_status.py")
    print("  3. Check fixes: python scripts/show_grace_fixes.py")
    print()
    
except Exception as e:
    print(f"  [ERROR] Failed to start Grace: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
