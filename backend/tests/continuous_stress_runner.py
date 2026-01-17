import sys
import logging
import time
import signal
import os
from pathlib import Path
from datetime import datetime
import threading
class ContinuousStressRunner:
    logger = logging.getLogger(__name__)
    """Runs stress tests continuously every 30 minutes."""
    
    def __init__(self, interval_minutes: int = 30, test_duration_minutes: int = 60):
        self.interval_minutes = interval_minutes
        self.test_duration_minutes = test_duration_minutes
        self.running = False
        self.cycle_count = 0
        
    def run_stress_tests(self):
        """Run one cycle of aggressive stress tests."""
        try:
            # Try to import aggressive tests
            try:
                from backend.tests.aggressive_stress_tests import run_aggressive_stress_tests
            except ImportError:
                from tests.aggressive_stress_tests import run_aggressive_stress_tests
            
            logger.info(f"[CONTINUOUS-RUNNER] Starting stress test cycle #{self.cycle_count + 1}")
            logger.info(f"[CONTINUOUS-RUNNER] Test duration: {self.test_duration_minutes} minutes")
            logger.info(f"[CONTINUOUS-RUNNER] 💥 AGGRESSIVE MODE - Trying to BREAK Grace...")
            
            summary = run_aggressive_stress_tests(self.test_duration_minutes)
            
            logger.info(f"[CONTINUOUS-RUNNER] Cycle #{self.cycle_count + 1} complete:")
            logger.info(f"  - Tests passed: {summary.get('passed', 0)}/{summary.get('total_tests', 0)}")
            logger.info(f"  - Issues found: {summary.get('issues_found', 0)}")
            
            self.cycle_count += 1
            
            return summary
            
        except Exception as e:
            logger.error(f"[CONTINUOUS-RUNNER] Error running stress tests: {e}", exc_info=True)
            return None
    
    def start(self):
        """Start the continuous stress test runner."""
        logger.info("=" * 80)
        logger.info("CONTINUOUS STRESS TEST RUNNER - STARTING")
        logger.info("=" * 80)
        logger.info(f"Interval: Every {self.interval_minutes} minutes")
        logger.info(f"Test duration: {self.test_duration_minutes} minutes per cycle")
        logger.info(f"Running until shutdown signal received...")
        logger.info("=" * 80)
        
        self.running = True
        
        # Run initial test immediately
        logger.info("[CONTINUOUS-RUNNER] Running initial stress test...")
        self.run_stress_tests()
        
        # Then run every 30 minutes
        interval_seconds = self.interval_minutes * 60
        
        while not shutdown_flag.is_set():
            try:
                # Wait for interval (check shutdown flag every 10 seconds)
                waited = 0
                while waited < interval_seconds and not shutdown_flag.is_set():
                    time.sleep(min(10, interval_seconds - waited))
                    waited += 10
                
                if shutdown_flag.is_set():
                    break
                
                # Run stress tests
                self.run_stress_tests()
                
            except KeyboardInterrupt:
                logger.info("[CONTINUOUS-RUNNER] Keyboard interrupt received")
                break
            except Exception as e:
                logger.error(f"[CONTINUOUS-RUNNER] Error in main loop: {e}", exc_info=True)
                # Continue running even if one cycle fails
                time.sleep(60)  # Wait 1 minute before retrying
        
        self.running = False
        logger.info("[CONTINUOUS-RUNNER] Stopped")
    
    def stop(self):
        """Stop the continuous stress test runner."""
        logger.info("[CONTINUOUS-RUNNER] Stopping...")
        shutdown_flag.set()
        self.running = False


def main():
    """Main entry point."""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and start runner
    runner = ContinuousStressRunner(
        interval_minutes=30,  # Run every 30 minutes
        test_duration_minutes=60  # Each test runs for 60 minutes
    )
    
    try:
        runner.start()
    except Exception as e:
        logger.error(f"Fatal error in stress test runner: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
