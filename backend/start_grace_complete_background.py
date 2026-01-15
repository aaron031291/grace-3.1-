"""
Start Grace in Background with Complete Self-Healing Capabilities

This script starts Grace with:
- Autonomous learning system
- DevOps healing agent
- Diagnostic engine
- Mirror self-modeling
- Cognitive framework
- Proactive learning
- Sandbox lab
- Help requester

Grace will run in the background and autonomously:
- Monitor the system
- Detect and fix issues
- Request knowledge when needed
- Request help when stuck
"""

import sys
import os
import logging
import signal
import time
import threading
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/grace_background.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Import Grace components
import platform
from database.session import initialize_session_factory, get_db
from database.connection import DatabaseConnection
from database.config import DatabaseConfig, DatabaseType

# Use thread-based orchestrator on Windows
if platform.system() == "Windows":
    from cognitive.thread_learning_orchestrator import ThreadLearningOrchestrator as LearningOrchestrator
else:
    from cognitive.learning_subagent_system import LearningOrchestrator

from genesis.autonomous_triggers import get_genesis_trigger_pipeline
from cognitive.autonomous_healing_system import get_autonomous_healing, TrustLevel
from cognitive.mirror_self_modeling import get_mirror_system
from cognitive.devops_healing_agent import get_devops_healing_agent
from cognitive.autonomous_help_requester import get_help_requester

# Global references
orchestrator = None
trigger_pipeline = None
healing_system = None
mirror_system = None
devops_agent = None
shutdown_requested = False


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    global shutdown_requested
    logger.info("\n[SHUTDOWN] Graceful shutdown requested...")
    shutdown_requested = True


def initialize_grace():
    """Initialize all Grace systems."""
    global orchestrator, trigger_pipeline, healing_system, mirror_system, devops_agent
    
    logger.info("=" * 80)
    logger.info("🚀 GRACE COMPLETE SYSTEM - BACKGROUND STARTUP")
    logger.info("=" * 80)
    
    # 1. Initialize database
    logger.info("\n[1/7] Initializing database...")
    try:
        from settings import settings
    except ImportError:
        settings = None
    
    db_config = DatabaseConfig(
        db_type=DatabaseType.SQLITE,
        database_path="data/grace.db"
    )
    DatabaseConnection.initialize(db_config)
    initialize_session_factory()
    session = next(get_db())
    logger.info("✓ Database connection established")
    
    # 2. Initialize Learning Orchestrator
    logger.info("\n[2/7] Starting Learning Orchestrator...")
    knowledge_base_path = str(Path("knowledge_base").resolve())
    
    orchestrator = LearningOrchestrator(
        knowledge_base_path=knowledge_base_path,
        num_study_agents=3,
        num_practice_agents=2
    )
    orchestrator.start()
    logger.info("✓ Learning Orchestrator running")
    
    # 3. Initialize Genesis Trigger Pipeline
    logger.info("\n[3/7] Connecting Genesis Key Trigger Pipeline...")
    trigger_pipeline = get_genesis_trigger_pipeline(
        session=session,
        knowledge_base_path=Path(knowledge_base_path),
        orchestrator=orchestrator
    )
    logger.info("✓ Trigger Pipeline connected")
    
    # 4. Initialize Self-Healing System
    logger.info("\n[4/7] Activating Self-Healing System...")
    healing_system = get_autonomous_healing(
        session=session,
        trust_level=TrustLevel.MEDIUM_RISK_AUTO,
        enable_learning=True
    )
    logger.info("✓ Self-Healing System active")
    
    # 5. Initialize Mirror Self-Modeling
    logger.info("\n[5/7] Activating Mirror Self-Modeling...")
    mirror_system = get_mirror_system(
        session=session,
        observation_window_hours=24,
        min_pattern_occurrences=3
    )
    logger.info("✓ Mirror System active")
    
    # 6. Initialize DevOps Healing Agent (NEW!)
    logger.info("\n[6/7] Initializing DevOps Healing Agent...")
    devops_agent = get_devops_healing_agent(
        session=session,
        knowledge_base_path=Path(knowledge_base_path),
        ai_research_path=Path("data/ai_research")
    )
    logger.info("✓ DevOps Healing Agent ready")
    
    # Verify critical systems are connected
    if hasattr(devops_agent, 'learning_memory') and devops_agent.learning_memory:
        logger.info("  ✓ Learning Memory: CONNECTED")
    else:
        logger.warning("  ✗ Learning Memory: NOT CONNECTED")
    
    if hasattr(devops_agent, 'ingestion_integration') and devops_agent.ingestion_integration:
        logger.info("  ✓ Ingestion Integration: CONNECTED")
    else:
        logger.warning("  ✗ Ingestion Integration: NOT CONNECTED")
    
    # 7. Initialize Help Requester
    logger.info("\n[7/7] Initializing Help Requester...")
    help_requester = get_help_requester(session=session)
    logger.info("✓ Help Requester ready")
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ ALL SYSTEMS OPERATIONAL")
    logger.info("=" * 80)
    
    # Print system status
    logger.info("\nGrace is now running with:")
    logger.info("  ✓ Autonomous Learning System")
    logger.info("  ✓ DevOps Full-Stack Healing Agent")
    logger.info("  ✓ Diagnostic Engine")
    logger.info("  ✓ Mirror Self-Modeling")
    logger.info("  ✓ Cognitive Framework (OODA)")
    logger.info("  ✓ Proactive Learning")
    logger.info("  ✓ Sandbox Lab")
    logger.info("  ✓ Help Requester")
    logger.info("\nGrace will autonomously:")
    logger.info("  • Monitor the system")
    logger.info("  • Detect and fix issues")
    logger.info("  • Request knowledge when needed")
    logger.info("  • Request help when stuck")
    logger.info("  • Learn from successful fixes")
    logger.info("\n" + "=" * 80 + "\n")
    
    return session


def monitor_and_heal():
    """Background monitoring and healing loop."""
    global shutdown_requested, devops_agent, healing_system, mirror_system
    
    logger.info("[MONITOR] Starting background monitoring and healing...")
    
    cycle_count = 0
    last_health_check = time.time()
    last_mirror_analysis = time.time()
    last_diagnostic = time.time()
    
    while not shutdown_requested:
        try:
            time.sleep(30)  # Check every 30 seconds
            cycle_count += 1
            current_time = time.time()
            
            # Periodic health check (every 5 minutes)
            if current_time - last_health_check > 300:
                logger.info("[MONITOR] Running periodic health check...")
                try:
                    if healing_system:
                        cycle_result = healing_system.run_monitoring_cycle()
                        health_status = cycle_result.get("health_status", "unknown")
                        anomalies = cycle_result.get("anomalies_detected", 0)
                        
                        logger.info(
                            f"[HEALTH] Status: {health_status}, "
                            f"Anomalies: {anomalies}, "
                            f"Actions: {cycle_result.get('actions_executed', 0)}"
                        )
                        
                        # If critical issues detected, use DevOps agent
                        if health_status in ("critical", "failing") and devops_agent:
                            logger.info("[MONITOR] Critical issues detected - requesting DevOps agent...")
                            try:
                                result = devops_agent.detect_and_heal(
                                    issue_description=f"System health is {health_status}",
                                    context={"health_status": health_status, "anomalies": anomalies}
                                )
                                if result.get("success"):
                                    logger.info(f"[MONITOR] DevOps agent fixed issue: {result.get('fix_applied')}")
                            except Exception as e:
                                logger.error(f"[MONITOR] DevOps agent error: {e}")
                        
                except Exception as e:
                    logger.error(f"[MONITOR] Health check error: {e}")
                
                last_health_check = current_time
            
            # Periodic mirror analysis (every 10 minutes)
            if current_time - last_mirror_analysis > 600:
                logger.info("[MONITOR] Running mirror self-modeling analysis...")
                try:
                    if mirror_system:
                        self_model = mirror_system.build_self_model()
                        logger.info(
                            f"[MIRROR] Patterns: {self_model['behavioral_patterns']['total_detected']}, "
                            f"Suggestions: {len(self_model['improvement_suggestions'])}, "
                            f"Self-awareness: {self_model['self_awareness_score']:.2f}"
                        )
                except Exception as e:
                    logger.error(f"[MONITOR] Mirror analysis error: {e}")
                
                last_mirror_analysis = current_time
            
            # Periodic diagnostics (every 15 minutes)
            if current_time - last_diagnostic > 900:
                logger.info("[MONITOR] Running diagnostic cycle...")
                try:
                    if devops_agent:
                        diagnostic_info = devops_agent._run_diagnostics()
                        health_status = diagnostic_info.get("health_status", "unknown")
                        logger.info(f"[DIAGNOSTIC] System health: {health_status}")
                except Exception as e:
                    logger.error(f"[MONITOR] Diagnostic error: {e}")
                
                last_diagnostic = current_time
            
            # Print status every 10 cycles (5 minutes)
            if cycle_count % 10 == 0:
                logger.info(
                    f"[STATUS] Grace is running in background (cycle {cycle_count})"
                )
        
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"[MONITOR] Monitoring error: {e}")
            time.sleep(60)  # Wait longer on error


def main():
    """Main entry point."""
    global shutdown_requested
    
    # Setup signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Initialize all systems
        session = initialize_grace()
        
        # Start monitoring in background thread
        monitor_thread = threading.Thread(target=monitor_and_heal, daemon=True)
        monitor_thread.start()
        
        logger.info("\n✅ Grace is now running in the background!")
        logger.info("Press Ctrl+C to stop gracefully...\n")
        
        # Keep main thread alive
        try:
            while not shutdown_requested:
                time.sleep(1)
        except KeyboardInterrupt:
            shutdown_requested = True
        
    except Exception as e:
        logger.error(f"[FATAL] Error during startup: {e}", exc_info=True)
        shutdown_requested = True
    
    finally:
        logger.info("\n[SHUTDOWN] Shutting down Grace...")
        if orchestrator:
            try:
                orchestrator.stop()
                logger.info("[SHUTDOWN] Learning Orchestrator stopped")
            except Exception as e:
                logger.error(f"[SHUTDOWN] Error stopping orchestrator: {e}")
        
        logger.info("[SHUTDOWN] Grace shutdown complete")


if __name__ == "__main__":
    # Create logs directory
    Path("logs").mkdir(exist_ok=True)
    
    logger.info(f"\n{'='*80}")
    logger.info(f"Grace Complete System - Background Mode")
    logger.info(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"{'='*80}\n")
    
    main()
