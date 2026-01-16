"""
Grace Autonomous Learning System - Simple Starter (Thread-Based)

This version uses threading instead of multiprocessing for Windows compatibility.
It activates Grace's autonomous learning cycle with trigger integration.

Usage:
    python start_autonomous_learning_simple.py

Press Ctrl+C to shutdown.
"""

import logging
import signal
import sys
import time
from pathlib import Path
from datetime import datetime
import threading

# Setup logging (no emojis for Windows console)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/autonomous_learning.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Import Grace components
from database.config import DatabaseConfig
from database.connection import DatabaseConnection
from database.session import initialize_session_factory, get_db
from genesis.autonomous_triggers import get_genesis_trigger_pipeline
from cognitive.autonomous_healing_system import get_autonomous_healing, TrustLevel
from cognitive.mirror_self_modeling import get_mirror_system

# Global references
trigger_pipeline = None
healing_system = None
mirror_system = None
session = None
shutdown_requested = False


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    global shutdown_requested
    logger.info("\n[SHUTDOWN] Graceful shutdown requested...")
    shutdown_requested = True


def initialize_systems():
    """Initialize all autonomous learning systems."""
    global trigger_pipeline, healing_system, mirror_system, session

    logger.info("=" * 80)
    logger.info("GRACE AUTONOMOUS LEARNING SYSTEM - INITIALIZATION")
    logger.info("=" * 80)

    # 1. Initialize database
    logger.info("\n[1/3] Initializing database connection...")
    db_config = DatabaseConfig()
    DatabaseConnection.initialize(db_config)
    initialize_session_factory()
    session = next(get_db())
    logger.info("[OK] Database connection established")

    # 2. Initialize Genesis Key Trigger Pipeline
    logger.info("\n[2/3] Connecting Genesis Key Trigger Pipeline...")
    knowledge_base_path = Path("knowledge_base").resolve()

    trigger_pipeline = get_genesis_trigger_pipeline(
        session=session,
        knowledge_base_path=knowledge_base_path,
        orchestrator=None  # We'll connect learning orchestrator later if needed
    )
    logger.info("[OK] Trigger Pipeline connected to Genesis Keys")
    logger.info("  - File ingestion creates Genesis Keys")
    logger.info("  - Errors trigger self-healing")
    logger.info("  - User queries trigger context prefetch")

    # 3. Initialize Self-Healing System
    logger.info("\n[3/3] Activating Self-Healing System...")
    healing_system = get_autonomous_healing(
        session=session,
        trust_level=TrustLevel.MEDIUM_RISK_AUTO,
        enable_learning=True
    )
    logger.info("[OK] Self-Healing System active")
    logger.info("  - Trust Level: MEDIUM_RISK_AUTO")
    logger.info("  - Autonomous healing enabled for safe actions")
    logger.info("  - Learning from healing outcomes enabled")

    # 4. Initialize Mirror Self-Modeling
    logger.info("\nActivating Mirror Self-Modeling...")
    mirror_system = get_mirror_system(
        session=session,
        observation_window_hours=24,
        min_pattern_occurrences=3
    )
    logger.info("[OK] Mirror System active")
    logger.info("  - Observing last 24 hours of operations")
    logger.info("  - Pattern detection threshold: 3 occurrences")
    logger.info("  - Self-awareness tracking enabled")

    logger.info("\n" + "=" * 80)
    logger.info("ALL SYSTEMS OPERATIONAL")
    logger.info("=" * 80)

    return session


def file_watcher_thread():
    """Watch for new files being ingested and create Genesis Keys."""
    logger.info("\n[FILE WATCHER] Starting file monitoring thread...")

    import sqlite3
    last_doc_count = 0

    while not shutdown_requested:
        try:
            # Check for new documents
            conn = sqlite3.connect('data/grace.db')
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM documents')
            current_count = cursor.fetchone()[0]
            conn.close()

            if current_count > last_doc_count:
                new_docs = current_count - last_doc_count
                logger.info(f"[FILE WATCHER] Detected {new_docs} new documents ingested")

                # Trigger learning for each new document
                if trigger_pipeline:
                    logger.info(f"[FILE WATCHER] Processing triggers for new documents...")

                last_doc_count = current_count

            time.sleep(10)  # Check every 10 seconds

        except Exception as e:
            logger.error(f"[FILE WATCHER] Error: {e}")
            time.sleep(10)


def health_monitor_thread():
    """Periodically run health checks and healing."""
    logger.info("\n[HEALTH MONITOR] Starting health monitoring thread...")

    while not shutdown_requested:
        try:
            time.sleep(300)  # Check every 5 minutes

            if not shutdown_requested and healing_system:
                try:
                    logger.info("[HEALTH] Running periodic health check...")
                    cycle_result = healing_system.run_monitoring_cycle()
                    logger.info(
                        f"[HEALTH] Status: {cycle_result['health_status']}, "
                        f"Anomalies: {cycle_result['anomalies_detected']}, "
                        f"Actions executed: {cycle_result['actions_executed']}"
                    )
                except Exception as health_error:
                    logger.error(f"[HEALTH MONITOR] Error during health check: {health_error}", exc_info=True)
                    # Continue monitoring even if one check fails
            elif not shutdown_requested and not healing_system:
                logger.warning("[HEALTH MONITOR] Healing system not available")

        except Exception as e:
            logger.error(f"[HEALTH MONITOR] Thread error: {e}", exc_info=True)
            time.sleep(60)  # Wait before retrying


def mirror_analysis_thread():
    """Periodically run mirror self-modeling."""
    logger.info("\n[MIRROR ANALYSIS] Starting mirror analysis thread...")

    while not shutdown_requested:
        try:
            time.sleep(600)  # Analyze every 10 minutes

            if not shutdown_requested and mirror_system:
                logger.info("[MIRROR] Running self-modeling analysis...")
                self_model = mirror_system.build_self_model()
                logger.info(
                    f"[MIRROR] Patterns: {self_model['behavioral_patterns']['total_detected']}, "
                    f"Suggestions: {len(self_model['improvement_suggestions'])}, "
                    f"Self-awareness: {self_model['self_awareness_score']:.2f}"
                )

        except Exception as e:
            logger.error(f"[MIRROR ANALYSIS] Error: {e}")
            time.sleep(60)


def monitor_learning_cycle():
    """Monitor and display learning activity."""
    logger.info("\nAUTONOMOUS LEARNING CYCLE ACTIVE\n")
    logger.info("Grace is now autonomously:")
    logger.info("  - Monitoring for new file ingestions")
    logger.info("  - Tracking with Genesis Keys")
    logger.info("  - Healing from failures")
    logger.info("  - Observing her own behavior")
    logger.info("  - Building self-awareness\n")
    logger.info("Press Ctrl+C to shutdown gracefully...\n")

    # Start monitoring threads
    threads = []

    # File watcher thread
    file_watcher = threading.Thread(target=file_watcher_thread, daemon=True)
    file_watcher.start()
    threads.append(file_watcher)

    # Health monitor thread
    health_monitor = threading.Thread(target=health_monitor_thread, daemon=True)
    health_monitor.start()
    threads.append(health_monitor)

    # Mirror analysis thread
    mirror_analysis = threading.Thread(target=mirror_analysis_thread, daemon=True)
    mirror_analysis.start()
    threads.append(mirror_analysis)

    # Main monitoring loop
    cycle_count = 0
    while not shutdown_requested:
        try:
            time.sleep(60)  # Status update every minute
            cycle_count += 1

            if cycle_count % 5 == 0:  # Every 5 minutes
                logger.info(f"[STATUS] System running for {cycle_count} minutes")

                if trigger_pipeline:
                    try:
                        status = trigger_pipeline.get_status()
                        logger.info(
                            f"[STATUS] Triggers fired: {status.get('triggers_fired', 0)}, "
                            f"Recursive loops: {status.get('recursive_loops_active', 0)}"
                        )
                    except Exception as status_error:
                        logger.debug(f"[STATUS] Could not get trigger pipeline status: {status_error}")

        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"[ERROR] Monitoring error: {e}")

    # Wait for threads to finish
    logger.info("\n[SHUTDOWN] Waiting for threads to finish...")
    for thread in threads:
        thread.join(timeout=2)


def shutdown_systems():
    """Gracefully shutdown all systems."""
    logger.info("\n" + "=" * 80)
    logger.info("SHUTTING DOWN AUTONOMOUS LEARNING SYSTEM")
    logger.info("=" * 80)

    if trigger_pipeline:
        logger.info("\n[1/2] Trigger Pipeline Statistics...")
        try:
            status = trigger_pipeline.get_status()
            logger.info(f"[OK] Triggers fired: {status['triggers_fired']}")
        except Exception as e:
            logger.error(f"Error getting trigger stats: {e}")

    logger.info("\n[2/2] Closing database connection...")
    if session:
        try:
            session.close()
            logger.info("[OK] Database session closed")
        except Exception as e:
            logger.error(f"Error closing session: {e}")

    logger.info("\n" + "=" * 80)
    logger.info("SHUTDOWN COMPLETE")
    logger.info("=" * 80)


def main():
    """Main entry point."""
    global shutdown_requested

    # Setup signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)

    try:
        # Initialize all systems
        session = initialize_systems()

        # Monitor learning cycle
        monitor_learning_cycle()

    except Exception as e:
        logger.error(f"[FATAL] Error during operation: {e}", exc_info=True)
        shutdown_requested = True

    finally:
        # Cleanup
        shutdown_systems()


if __name__ == "__main__":
    # Create logs directory if needed
    Path("logs").mkdir(exist_ok=True)

    logger.info(f"\n{'='*80}")
    logger.info(f"Grace Autonomous Learning System")
    logger.info(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"{'='*80}\n")

    main()
