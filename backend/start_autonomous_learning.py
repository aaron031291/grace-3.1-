"""
Grace Autonomous Learning System - Startup Script

This script activates Grace's complete autonomous learning cycle:
1. Learning Orchestrator (8 subagent processes)
2. Genesis Key Trigger Pipeline
3. Self-Healing System
4. Mirror Self-Modeling
5. Autonomous Ingestion Tracking

Usage:
    python start_autonomous_learning.py

Press Ctrl+C to gracefully shutdown all processes.
"""

import logging
import signal
import sys
import time
from pathlib import Path
from datetime import datetime

# Setup logging
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
from database.session import initialize_session_factory, get_db
from cognitive.learning_subagent_system import LearningOrchestrator
from genesis.autonomous_triggers import get_genesis_trigger_pipeline
from cognitive.autonomous_healing_system import get_autonomous_healing, TrustLevel
from cognitive.mirror_self_modeling import get_mirror_system

# Global references for cleanup
orchestrator = None
trigger_pipeline = None
healing_system = None
mirror_system = None
shutdown_requested = False


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    global shutdown_requested
    logger.info("\n[SHUTDOWN] Graceful shutdown requested...")
    shutdown_requested = True


def initialize_systems():
    """Initialize all autonomous learning systems."""
    global orchestrator, trigger_pipeline, healing_system, mirror_system

    logger.info("=" * 80)
    logger.info("🚀 GRACE AUTONOMOUS LEARNING SYSTEM - INITIALIZATION")
    logger.info("=" * 80)

    # 1. Initialize database session
    logger.info("\n[1/5] Initializing database connection...")
    from database.config import DatabaseConfig
    from database.connection import DatabaseConnection

    db_config = DatabaseConfig()
    DatabaseConnection.initialize(db_config)
    initialize_session_factory()
    session = next(get_db())
    logger.info("✓ Database connection established")

    # 2. Initialize Learning Orchestrator (8 processes)
    logger.info("\n[2/5] Starting Learning Orchestrator...")
    knowledge_base_path = str(Path("knowledge_base").resolve())

    orchestrator = LearningOrchestrator(
        knowledge_base_path=knowledge_base_path,
        num_study_agents=3,     # 3 study processes
        num_practice_agents=2   # 2 practice processes
    )

    # Start all subagent processes
    orchestrator.start()
    logger.info("✓ Learning Orchestrator running with 8 subagents:")
    logger.info("  - 3 Study Agents (autonomous concept extraction)")
    logger.info("  - 2 Practice Agents (skill validation)")
    logger.info("  - 1 Mirror Agent (self-reflection)")
    logger.info("  - 1 Trust Scorer (confidence tracking)")
    logger.info("  - 1 Predictive Context Agent (pre-fetching)")

    # 3. Initialize Genesis Key Trigger Pipeline
    logger.info("\n[3/5] Connecting Genesis Key Trigger Pipeline...")
    trigger_pipeline = get_genesis_trigger_pipeline(
        session=session,
        knowledge_base_path=Path(knowledge_base_path),
        orchestrator=orchestrator
    )
    logger.info("✓ Trigger Pipeline connected to Genesis Keys")
    logger.info("  - File ingestion triggers autonomous learning")
    logger.info("  - Practice failures trigger gap-filling study")
    logger.info("  - User queries trigger predictive prefetch")

    # 4. Initialize Self-Healing System
    logger.info("\n[4/5] Activating Self-Healing System...")
    healing_system = get_autonomous_healing(
        session=session,
        trust_level=TrustLevel.MEDIUM_RISK_AUTO,
        enable_learning=True
    )
    logger.info("✓ Self-Healing System active")
    logger.info("  - Trust Level: MEDIUM_RISK_AUTO")
    logger.info("  - Autonomous healing enabled for safe actions")
    logger.info("  - Learning from healing outcomes enabled")

    # 5. Initialize Mirror Self-Modeling
    logger.info("\n[5/5] Activating Mirror Self-Modeling...")
    mirror_system = get_mirror_system(
        session=session,
        observation_window_hours=24,
        min_pattern_occurrences=3
    )
    logger.info("✓ Mirror System active")
    logger.info("  - Observing last 24 hours of operations")
    logger.info("  - Pattern detection threshold: 3 occurrences")
    logger.info("  - Self-awareness tracking enabled")

    logger.info("\n" + "=" * 80)
    logger.info("✅ ALL SYSTEMS OPERATIONAL")
    logger.info("=" * 80)

    return session


def monitor_learning_cycle():
    """Monitor and display learning activity."""
    logger.info("\n🔄 AUTONOMOUS LEARNING CYCLE ACTIVE\n")
    logger.info("Grace is now autonomously:")
    logger.info("  • Learning from ingested files")
    logger.info("  • Practicing new skills")
    logger.info("  • Healing from failures")
    logger.info("  • Observing her own behavior")
    logger.info("  • Improving recursively\n")
    logger.info("Press Ctrl+C to shutdown gracefully...\n")

    cycle_count = 0
    last_health_check = time.time()
    last_mirror_analysis = time.time()

    while not shutdown_requested:
        try:
            time.sleep(10)  # Check every 10 seconds
            cycle_count += 1
            current_time = time.time()

            # Get orchestrator stats
            if orchestrator:
                stats = orchestrator.get_stats()

                if cycle_count % 6 == 0:  # Every minute
                    logger.info(
                        f"[STATS] Tasks: {stats['total_submitted']} submitted, "
                        f"{stats['total_completed']} completed, "
                        f"Study queue: {stats['study_queue_size']}, "
                        f"Practice queue: {stats['practice_queue_size']}"
                    )

            # Periodic health check (every 5 minutes)
            if current_time - last_health_check > 300:
                logger.info("[HEALTH] Running periodic health check...")
                if healing_system:
                    cycle_result = healing_system.run_monitoring_cycle()
                    logger.info(
                        f"[HEALTH] Status: {cycle_result['health_status']}, "
                        f"Anomalies: {cycle_result['anomalies_detected']}, "
                        f"Actions executed: {cycle_result['actions_executed']}"
                    )
                last_health_check = current_time

            # Periodic mirror analysis (every 10 minutes)
            if current_time - last_mirror_analysis > 600:
                logger.info("[MIRROR] Running self-modeling analysis...")
                if mirror_system and orchestrator:
                    self_model = mirror_system.build_self_model()
                    improvement_result = mirror_system.trigger_improvement_actions(orchestrator)
                    logger.info(
                        f"[MIRROR] Patterns: {self_model['behavioral_patterns']['total_detected']}, "
                        f"Suggestions: {len(self_model['improvement_suggestions'])}, "
                        f"Actions triggered: {improvement_result['actions_triggered']}, "
                        f"Self-awareness: {self_model['self_awareness_score']:.2f}"
                    )
                last_mirror_analysis = current_time

        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"[ERROR] Monitoring error: {e}")


def shutdown_systems():
    """Gracefully shutdown all systems."""
    logger.info("\n" + "=" * 80)
    logger.info("🛑 SHUTTING DOWN AUTONOMOUS LEARNING SYSTEM")
    logger.info("=" * 80)

    # Shutdown orchestrator (stops all subagent processes)
    if orchestrator:
        logger.info("\n[1/3] Stopping Learning Orchestrator...")
        try:
            orchestrator.stop()
            logger.info("✓ All subagent processes stopped")
        except Exception as e:
            logger.error(f"Error stopping orchestrator: {e}")

    # Trigger pipeline cleanup
    if trigger_pipeline:
        logger.info("\n[2/3] Disconnecting Trigger Pipeline...")
        try:
            status = trigger_pipeline.get_status()
            logger.info(f"✓ Pipeline stats: {status['triggers_fired']} triggers fired")
        except Exception as e:
            logger.error(f"Error getting trigger stats: {e}")

    # Final statistics
    logger.info("\n[3/3] Final Statistics...")
    if orchestrator:
        try:
            stats = orchestrator.get_stats()
            logger.info(f"  Total tasks submitted: {stats['total_submitted']}")
            logger.info(f"  Total tasks completed: {stats['total_completed']}")
            logger.info(f"  Total study tasks: {stats['study_completed']}")
            logger.info(f"  Total practice tasks: {stats['practice_completed']}")
        except Exception as e:
            logger.error(f"Error getting final stats: {e}")

    logger.info("\n" + "=" * 80)
    logger.info("✅ SHUTDOWN COMPLETE")
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
        logger.error(f"[FATAL] Error during initialization: {e}", exc_info=True)
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
