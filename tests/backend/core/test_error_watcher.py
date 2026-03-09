import time
import threading
from pathlib import Path
from backend.core.error_watcher import ErrorLogWatcher
from backend.cognitive_framework.cognitive_framework import CognitiveFramework

def simulate_crash():
    root = Path(__file__).parent.parent.parent
    crash_log = root / "crash.log"
    
    # Wait for the watcher to start monitoring
    time.sleep(1)
    
    with open(crash_log, "a") as f:
        f.write("2025-01-01 10:00:00 - ERROR - Example Crash Signature\n")
        f.write("Traceback (most recent call last):\n")
        f.write("  File 'main.py', line 10\n")
        f.write("ZeroDivisionError: division by zero\n")

if __name__ == "__main__":
    root = Path(__file__).parent.parent.parent
    test_log = str(root / "crash.log")
    
    print("Initializing Framework...")
    framework = CognitiveFramework()
    watcher = ErrorLogWatcher([test_log], framework)
    
    print("Starting Watcher...")
    watcher.start()
    
    # Thread to simulate a background crash
    t = threading.Thread(target=simulate_crash)
    t.start()
    
    # Let the watcher catch it
    time.sleep(3)
    
    print("Verification Completed. Stopping Watcher.")
    watcher.stop()
