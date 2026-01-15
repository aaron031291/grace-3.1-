"""
Start Grace's Self-Healing Agent

This script starts Grace in background mode for continuous self-healing.
"""

import sys
import subprocess
import os
from pathlib import Path

print("=" * 80)
print("STARTING GRACE SELF-HEALING AGENT")
print("=" * 80)
print()

# Check if already running
try:
    import psutil
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = ' '.join(proc.info['cmdline'] or [])
            if 'grace' in cmdline.lower() and 'self_healing' in cmdline.lower():
                print(f"[INFO] Grace is already running (PID {proc.info['pid']})")
                print("       Use check_grace_status.py to verify")
                sys.exit(0)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
except ImportError:
    pass

# Start Grace
script_path = Path(__file__).parent / "backend" / "start_grace_complete_background.py"

if not script_path.exists():
    print(f"[ERROR] Script not found: {script_path}")
    sys.exit(1)

print(f"[1/2] Starting Grace from: {script_path}")
print()

# Start in background
if os.name == 'nt':  # Windows
    subprocess.Popen(
        [sys.executable, str(script_path)],
        creationflags=subprocess.CREATE_NEW_CONSOLE,
        cwd=str(Path(__file__).parent)
    )
else:  # Unix/Linux/Mac
    subprocess.Popen(
        [sys.executable, str(script_path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=str(Path(__file__).parent)
    )

print("[OK] Grace started in background")
print()
print("[2/2] Waiting a few seconds for initialization...")
import time
time.sleep(3)

print()
print("=" * 80)
print("GRACE STARTED")
print("=" * 80)
print()
print("Grace is now running in the background!")
print()
print("To check status: python check_grace_status.py")
print("To view logs: tail -f logs/grace_self_healing.log")
print()
