"""
Start GRACE with Watchdog Self-Healing

This script starts GRACE with a watchdog that can:
- Monitor the main process
- Detect crashes
- Diagnose and fix issues
- Automatically restart the system

Usage:
    python start_watchdog.py
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from cognitive.watchdog_healing import WatchdogHealing
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [WATCHDOG] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

def main():
    """Start GRACE with watchdog."""
    logger.info("=" * 80)
    logger.info("GRACE Watchdog Self-Healing System")
    logger.info("=" * 80)
    logger.info("")
    logger.info("This watchdog will:")
    logger.info("  - Monitor the main GRACE process")
    logger.info("  - Start the frontend (Vite dev server)")
    logger.info("  - Detect crashes and failures")
    logger.info("  - Diagnose root causes")
    logger.info("  - Apply automatic fixes")
    logger.info("  - Restart the system when needed")
    logger.info("")
    logger.info("The watchdog runs independently and can fix issues even if")
    logger.info("the main runtime crashes completely.")
    logger.info("")
    logger.info("Frontend will be available at: http://localhost:5173")
    logger.info("Backend will be available at: http://localhost:8000")
    logger.info("")
    
    # Find launcher script
    launcher_script = Path(__file__).parent / "launch_grace.py"
    if not launcher_script.exists():
        logger.error(f"Launcher script not found: {launcher_script}")
        sys.exit(1)
    
    # Create watchdog
    watchdog = WatchdogHealing(
        main_script_path=str(launcher_script),
        check_interval=30,  # Check every 30 seconds
        max_restarts=10,    # Allow up to 10 restarts
        restart_delay=5,   # Wait 5 seconds before restarting
        start_frontend=True  # Also start the frontend
    )
    
    try:
        logger.info("Starting watchdog...")
        watchdog.start()
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
        watchdog.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        watchdog.stop()
        sys.exit(1)

if __name__ == "__main__":
    main()
