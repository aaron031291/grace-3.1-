"""
Start Grace's Self-Healing Agent in Background

This script starts Grace's self-healing agent to run continuously in the background.
Grace will:
- Detect and fix issues automatically
- Create snapshots when system is stable
- Request help when needed
- Monitor system health continuously

Usage:
    python start_self_healing_background.py

Press Ctrl+C to stop gracefully.
"""

import sys
import os
import logging
import signal
import time
import threading
from pathlib import Path
from datetime import datetime

# Create logs directory first (relative to repo root)
repo_root = Path(__file__).parent.parent
logs_dir = repo_root / "logs"
logs_dir.mkdir(exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(logs_dir / 'grace_self_healing_background.log')),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Add backend to path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

# Import Grace self-healing agent
from grace_self_healing_agent import initialize_grace, run_healing_cycle

# Global state
shutdown_requested = False
devops_agent = None
help_requester = None


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    global shutdown_requested
    logger.info("\n[SHUTDOWN] Graceful shutdown requested...")
    shutdown_requested = True


def run_continuous_healing():
    """Run self-healing cycles continuously in background."""
    global devops_agent, help_requester, shutdown_requested
    
    try:
        # Initialize Grace
        logger.info("=" * 80)
        logger.info("GRACE SELF-HEALING AGENT - BACKGROUND MODE")
        logger.info("=" * 80)
        
        session, devops_agent, help_requester, layer2_connector, proactive_healing = initialize_grace()
        
        if not devops_agent:
            logger.error("[ERROR] Failed to initialize Grace. Cannot proceed.")
            return
        
        logger.info("\n[OK] Grace self-healing agent initialized successfully!")
        logger.info("[OK] Starting continuous healing cycles...\n")
        
        # Start proactive monitoring in background if available
        if proactive_healing:
            import threading
            logger.info("[START] Starting proactive continuous monitoring...")
            from cicd.proactive_self_healing import PipelineStage
            monitoring_thread = threading.Thread(
                target=lambda: proactive_healing.run_pipeline_check(PipelineStage.CONTINUOUS),
                daemon=True
            )
            monitoring_thread.start()
            logger.info("[OK] Proactive monitoring running in background\n")
        
        # Run continuous healing cycles
        cycle_num = 1
        last_snapshot_check = datetime.now()
        snapshot_check_interval = 1800  # 30 minutes in seconds
        
        logger.info("[RUNNING] Grace is now self-healing in the background!")
        logger.info("[INFO] Healing cycles will run continuously...")
        logger.info("[INFO] Press Ctrl+C to stop gracefully...\n")
        
        while not shutdown_requested:
            try:
                logger.info(f"\n{'='*60}")
                logger.info(f"HEALING CYCLE {cycle_num}")
                logger.info(f"{'='*60}")
                
                result = run_healing_cycle(devops_agent, help_requester, cycle_num)
                
                if result.get("success"):
                    issues_processed = result.get("issues_processed", 0)
                    issues_fixed = result.get("issues_fixed", 0)
                    
                    if issues_processed == 0:
                        logger.info("[OK] No issues detected - system is healthy!")
                    elif issues_fixed > 0:
                        logger.info(f"[OK] Fixed {issues_fixed} issue(s)!")
                    else:
                        logger.info(f"[INFO] Processed {issues_processed} issue(s)")
                else:
                    logger.error(f"[ERROR] Cycle {cycle_num} failed: {result.get('error', 'Unknown error')}")
                
                # Periodic snapshot check (every 30 minutes)
                current_time = datetime.now()
                if (current_time - last_snapshot_check).total_seconds() >= snapshot_check_interval:
                    if devops_agent and hasattr(devops_agent, 'snapshot_system') and devops_agent.snapshot_system:
                        try:
                            if devops_agent.snapshot_system.is_stable_state():
                                snapshot = devops_agent.snapshot_system.create_snapshot(
                                    reason=f"Periodic stable state check - cycle {cycle_num}",
                                    force=False
                                )
                                if snapshot:
                                    logger.info(f"[SNAPSHOT] Created periodic snapshot: {snapshot.snapshot_id}")
                        except Exception as e:
                            logger.warning(f"[SNAPSHOT] Failed to create periodic snapshot: {e}")
                    last_snapshot_check = current_time
                
                cycle_num += 1
                
                # Wait between cycles (60 seconds)
                if not shutdown_requested:
                    time.sleep(60)
                    
            except KeyboardInterrupt:
                shutdown_requested = True
                break
            except Exception as e:
                logger.error(f"[ERROR] Error in healing cycle: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(30)  # Wait 30 seconds before retrying
        
        # Final statistics
        logger.info("\n" + "=" * 80)
        logger.info("FINAL STATISTICS")
        logger.info("=" * 80)
        try:
            if devops_agent:
                stats = devops_agent.get_statistics()
                logger.info(f"Total Issues Detected: {stats.get('total_issues_detected', 0)}")
                logger.info(f"Total Issues Fixed: {stats.get('total_issues_fixed', 0)}")
                logger.info(f"Success Rate: {stats.get('success_rate', 0):.1%}")
                
                # Snapshot info
                snapshot_info = devops_agent.get_snapshot_info()
                if snapshot_info.get("available"):
                    logger.info(f"\nSnapshot System:")
                    logger.info(f"  Active Snapshots: {snapshot_info.get('active_snapshots', 0)}/{snapshot_info.get('max_active', 6)}")
                    logger.info(f"  Backup Snapshots: {snapshot_info.get('backup_snapshots', 0)}")
                    logger.info(f"  System Stable: {snapshot_info.get('is_stable', False)}")
        except Exception as e:
            logger.error(f"[ERROR] Failed to get statistics: {e}")
        
        logger.info("\n[SHUTDOWN] Self-healing agent stopped")
        
    except Exception as e:
        logger.error(f"[FATAL] Error in self-healing agent: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main entry point."""
    global shutdown_requested
    
    # Setup signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    logger.info(f"\n{'='*80}")
    logger.info(f"Grace Self-Healing Agent - Background Mode")
    logger.info(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"{'='*80}\n")
    
    try:
        # Run in main thread (can be moved to background thread if needed)
        run_continuous_healing()
    except KeyboardInterrupt:
        shutdown_requested = True
        logger.info("\n[SHUTDOWN] Interrupted by user")
    except Exception as e:
        logger.error(f"[FATAL] Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        logger.info("\n[SHUTDOWN] Grace self-healing agent shutdown complete")


if __name__ == "__main__":
    main()
