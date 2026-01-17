#!/usr/bin/env python3
"""
Start Grace Stress Test Scheduler
Runs stress tests every 10 minutes as a background process.
"""

import sys
import os
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

from autonomous_stress_testing.scheduler import start_stress_test_scheduler

if __name__ == "__main__":
    print("=" * 80)
    print("STARTING GRACE STRESS TEST SCHEDULER")
    print("=" * 80)
    print("Running stress tests every 10 minutes...")
    print("Press Ctrl+C to stop")
    print("=" * 80)
    print()
    
    scheduler = start_stress_test_scheduler(
        interval_minutes=10,
        base_url="http://localhost:8000",
        enable_genesis_logging=True,
        enable_diagnostic_alerts=True
    )
    
    print(f"[SCHEDULER] Started - running every 10 minutes")
    print(f"[SCHEDULER] Test results logged with Genesis Keys")
    print(f"[SCHEDULER] Diagnostic engine alerted on issues")
    print()
    
    try:
        import time
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("\n[SCHEDULER] Shutting down...")
        scheduler.stop()
        print("[SCHEDULER] Stopped")
