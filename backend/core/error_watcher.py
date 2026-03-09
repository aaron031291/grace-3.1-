import os
import time
import threading
import logging
from typing import List, Callable
from pathlib import Path

from backend.cognitive_framework.events import CognitiveEvent
from backend.cognitive_framework.cognitive_framework import CognitiveFramework

logger = logging.getLogger("error_watcher")

class ErrorLogWatcher:
    """
    A daemon that tails log files looking for errors or stack traces.
    When a failure signature is detected, it bundles it into a CognitiveEvent
    and sends it to the CognitiveFramework.
    """
    def __init__(self, log_files: List[str], framework: CognitiveFramework):
        self.log_files = log_files
        self.framework = framework
        self._stop_event = threading.Event()
        self._threads = []
        
    def _tail_file(self, file_path: str):
        path = Path(file_path)
        if not path.exists():
            # Create the file if it doesn't exist so we can watch it
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()

        logger.info(f"Started watching log file: {file_path}")
        with open(path, "r", encoding="utf-8") as file:
            # Go to the end of the file
            file.seek(0, os.SEEK_END)
            
            while not self._stop_event.is_set():
                line = file.readline()
                if not line:
                    time.sleep(0.5)
                    continue
                    
                if "ERROR" in line or "Traceback" in line or "Exception" in line:
                    logger.warning(f"Signature detected in {file_path}: {line.strip()}")
                    
                    # For a real implementation, we might collect the next few lines for full context
                    # Here we dispatch a CognitiveEvent immediately
                    event = CognitiveEvent(
                        type="guardian.log_error",
                        source_component=f"log_watcher[{path.name}]",
                        severity=3, # Base severity
                        payload={
                            "log_file": str(path),
                            "error_signature": line.strip()
                        }
                    )
                    
                    # Dispatch to framework
                    try:
                        self.framework.process_event(event)
                    except Exception as e:
                        logger.error(f"Failed to process event through CognitiveFramework: {e}")

    def start(self):
        """Starts a background thread for each monitored log file."""
        for file_path in self.log_files:
            thread = threading.Thread(target=self._tail_file, args=(file_path,), daemon=True)
            self._threads.append(thread)
            thread.start()

    def stop(self):
        """Signals all watcher threads to stop."""
        self._stop_event.set()
        for thread in self._threads:
            thread.join()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    root = Path(__file__).parent.parent.parent
    
    test_log = str(root / "crash.log")
    framework = CognitiveFramework()
    
    watcher = ErrorLogWatcher([test_log], framework)
    watcher.start()
    
    try:
        print(f"Watching {test_log} for errors. Ctrl+C to stop.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        watcher.stop()
        print("Watcher stopped.")
