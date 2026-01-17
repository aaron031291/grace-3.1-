"""
Run Diagnostic Engine and Self-Healing Agent

This script starts both:
1. Diagnostic Engine - 4-layer diagnostic machine with continuous monitoring
2. Self-Healing Agent - Autonomous healing system with AVM/AVN integration

Usage:
    python run_diagnostic_and_healing.py

Press Ctrl+C to gracefully shutdown both systems.
"""

import sys
import signal
import time
import logging
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

# Setup logging - optimized for background execution
log_file = Path('logs/diagnostic_healing.log')
log_file.parent.mkdir(exist_ok=True)

# Use file handler only for background execution (no console output)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        # Only add console handler if running interactively
        logging.StreamHandler(sys.stdout) if sys.stdout.isatty() else logging.NullHandler()
    ]
)

logger = logging.getLogger(__name__)

# Global references for cleanup
diagnostic_engine = None
healing_system = None
shutdown_requested = False


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    global shutdown_requested
    logger.info("\n[SHUTDOWN] Graceful shutdown requested...")
    shutdown_requested = True


def initialize_database():
    """Initialize database connection."""
    logger.info("[1/3] Initializing database connection...")
    
    from database.config import DatabaseConfig
    from database.connection import DatabaseConnection
    from database.session import initialize_session_factory, get_db
    
    db_config = DatabaseConfig()
    DatabaseConnection.initialize(db_config)
    initialize_session_factory()
    session = next(get_db())
    
    logger.info("[OK] Database connection established")
    return session


def start_diagnostic_engine():
    """Start the diagnostic engine."""
    global diagnostic_engine
    
    logger.info("\n[2/3] Starting Diagnostic Engine...")
    
    from diagnostic_machine.diagnostic_engine import start_diagnostic_engine
    
    # Start diagnostic engine with 60-second heartbeat
    diagnostic_engine = start_diagnostic_engine(
        heartbeat_interval=60,
        enable_heartbeat=True,
        enable_cicd=True,
        enable_healing=True,
        enable_freeze=True,
        enable_forensics=True,
        dry_run=False
    )
    
    logger.info("[OK] Diagnostic Engine started")
    logger.info("  - 60-second heartbeat monitoring")
    logger.info("  - 4-layer architecture: Sensors → Interpreters → Judgement → Action Router")
    logger.info("  - CI/CD integration enabled")
    logger.info("  - Healing actions enabled")
    logger.info("  - Forensic analysis enabled")
    
    return diagnostic_engine


def start_healing_system(session):
    """Start the self-healing system."""
    global healing_system
    
    logger.info("\n[3/3] Starting Self-Healing Agent...")
    
    try:
        from cognitive.autonomous_healing_system import get_autonomous_healing, TrustLevel
        
        # Initialize healing system
        healing_system = get_autonomous_healing(
            session=session,
            repo_path=Path("backend").resolve() if Path("backend").exists() else Path.cwd(),
            trust_level=TrustLevel.MEDIUM_RISK_AUTO,
            enable_learning=True
        )
        
        if healing_system:
            logger.info("[OK] Self-Healing Agent started")
            logger.info("  - Trust Level: MEDIUM_RISK_AUTO")
            logger.info("  - Autonomous healing enabled for safe actions")
            logger.info("  - Learning from healing outcomes enabled")
            logger.info("  - AVM/AVN integration active")
            
            # Run initial health check
            logger.info("\n[HEALING] Running initial health check...")
            try:
                initial_check = healing_system.run_monitoring_cycle()
                logger.info(
                    f"[HEALING] Initial check: Status={initial_check['health_status']}, "
                    f"Anomalies={initial_check['anomalies_detected']}, "
                    f"Healing Actions={initial_check['healing_actions_taken']}"
                )
            except Exception as e:
                logger.warning(f"[HEALING] Initial health check error: {e}")
    except Exception as e:
        logger.error(f"[ERROR] Failed to start healing system: {e}")
        logger.info("[INFO] Continuing with diagnostic engine only...")
        import traceback
        logger.debug(traceback.format_exc())
        return None
    
    return healing_system


def monitor_systems():
    """Monitor both systems and run healing cycles."""
    logger.info("\n" + "=" * 80)
    logger.info("[OPERATIONAL] DIAGNOSTIC ENGINE AND SELF-HEALING AGENT OPERATIONAL")
    logger.info("=" * 80)
    logger.info("\nBoth systems are now running:")
    logger.info("  • Diagnostic Engine: Monitoring system health every 60 seconds")
    logger.info("  • Self-Healing Agent: Running monitoring cycles every 2 minutes")
    logger.info("\nPress Ctrl+C to shutdown gracefully...\n")
    
    cycle_count = 0
    last_healing_cycle = time.time()
    healing_interval = 120  # Run healing cycle every 2 minutes
    
    while not shutdown_requested:
        try:
            time.sleep(10)  # Check every 10 seconds
            cycle_count += 1
            current_time = time.time()
            
            # Run healing cycle periodically (if healing system is available)
            if healing_system is not None and (current_time - last_healing_cycle) >= healing_interval:
                logger.info("\n[HEALING] Running monitoring cycle...")
                try:
                    result = healing_system.run_monitoring_cycle()
                    logger.info(
                        f"[HEALING] Cycle complete: Status={result['health_status']}, "
                        f"Anomalies={result['anomalies_detected']}, "
                        f"Actions={result['healing_actions_taken']}"
                    )
                except Exception as e:
                    logger.error(f"[HEALING] Monitoring cycle error: {e}")
                
                last_healing_cycle = current_time
            
            # Display diagnostic engine stats periodically
            if diagnostic_engine and cycle_count % 6 == 0:  # Every minute
                try:
                    stats = diagnostic_engine.stats
                    health = diagnostic_engine.get_health_summary()
                    logger.info(
                        f"[DIAGNOSTIC] Cycles: {stats.total_cycles}, "
                        f"Health: {health.get('status', 'unknown')}, "
                        f"Alerts: {stats.total_alerts}, "
                        f"Healing Actions: {stats.total_healing_actions}"
                    )
                except Exception as e:
                    logger.debug(f"[DIAGNOSTIC] Stats error: {e}")
                    
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Monitoring error: {e}")


def cleanup():
    """Cleanup and shutdown both systems."""
    logger.info("\n[SHUTDOWN] Stopping systems...")
    
    global diagnostic_engine, healing_system
    
    # Stop diagnostic engine
    if diagnostic_engine:
        try:
            diagnostic_engine.stop()
            logger.info("[OK] Diagnostic Engine stopped")
        except Exception as e:
            logger.error(f"Error stopping diagnostic engine: {e}")
    
    # Note: Healing system doesn't have a stop method, it's session-based
    if healing_system is not None:
        logger.info("[OK] Self-Healing Agent shutdown")
    
    logger.info("[SHUTDOWN] All systems stopped")


def main():
    """Main entry point."""
    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Ensure logs directory exists
    Path("logs").mkdir(exist_ok=True)
    
    try:
        # Initialize database
        session = initialize_database()
        
        # Start diagnostic engine
        start_diagnostic_engine()
        
        # Start healing system
        start_healing_system(session)
        
        # Monitor both systems
        monitor_systems()
        
    except KeyboardInterrupt:
        logger.info("\n[SHUTDOWN] Interrupted by user")
    except Exception as e:
        logger.error(f"[FATAL] Error: {e}", exc_info=True)
    finally:
        cleanup()


if __name__ == "__main__":
    main()
