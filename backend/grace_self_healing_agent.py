"""
Grace Self-Healing Agent - Proactive Issue Detection and Fixing

This is Grace's self-healing agent that actively detects and fixes issues in the system.
Grace will:
1. Run diagnostics to find issues
2. Attempt to fix them automatically
3. Request knowledge if needed
4. Request help if stuck
"""

import sys
import logging
import time
from pathlib import Path
from datetime import datetime, UTC, timedelta

# Setup logging
Path("logs").mkdir(exist_ok=True)  # Ensure logs directory exists
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/grace_self_healing.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from database.connection import DatabaseConnection
from database.config import DatabaseConfig, DatabaseType
from database.session import initialize_session_factory, get_db
from cognitive.devops_healing_agent import get_devops_healing_agent
from cognitive.autonomous_help_requester import get_help_requester, HelpPriority, HelpRequestType
from llm_orchestrator.llm_orchestrator import LLMOrchestrator
from embedding import get_embedding_model
from layer2.self_healing_connector import SelfHealingConnector
from layer1.message_bus import get_message_bus
from cicd.proactive_self_healing import ProactiveSelfHealing, PipelineStage

# Export for use in background script
__all__ = ['initialize_grace', 'run_healing_cycle']


def initialize_grace():
    """Initialize Grace's self-healing systems."""
    logger.info("=" * 80)
    logger.info("GRACE SELF-HEALING AGENT - INITIALIZING")
    logger.info("=" * 80)
    
    # Initialize database
    logger.info("\n[1/3] Initializing database...")
    session = None
    session_generator = None
    try:
        db_config = DatabaseConfig(
            db_type=DatabaseType.SQLITE,
            database_path="data/grace.db"
        )
        DatabaseConnection.initialize(db_config)
        initialize_session_factory()
        # CRITICAL: Use context manager to ensure session is properly closed
        session_generator = get_db()
        session = next(session_generator)
        logger.info("[OK] Database initialized")
    except Exception as e:
        logger.error(f"✗ Database initialization failed: {e}")
        # Try to continue anyway - Grace might be able to fix this
        try:
            initialize_session_factory()
            session_generator = get_db()
            session = next(session_generator)
            logger.info("✓ Session factory initialized (database may have issues)")
        except Exception as e2:
            logger.error(f"✗ Complete failure: {e2}")
            # Clean up session if it was created
            if session:
                try:
                    session.close()
                except:
                    pass
            return None, None, None, None, None
    
    # Initialize DevOps Healing Agent
    logger.info("\n[2/5] Initializing DevOps Healing Agent...")
    try:
        knowledge_base_path = Path("knowledge_base").resolve()
        ai_research_path = Path("data/ai_research")
        
        devops_agent = get_devops_healing_agent(
            session=session,
            knowledge_base_path=knowledge_base_path,
            ai_research_path=ai_research_path
        )
        logger.info("[OK] DevOps Healing Agent ready")
        
        # Verify critical systems are connected
        if hasattr(devops_agent, 'learning_memory') and devops_agent.learning_memory:
            logger.info("  [OK] Learning Memory: CONNECTED")
        else:
            logger.warning("  [WARN] Learning Memory: NOT CONNECTED")
        
        if hasattr(devops_agent, 'ingestion_integration') and devops_agent.ingestion_integration:
            logger.info("  [OK] Ingestion Integration: CONNECTED")
        else:
            logger.warning("  [WARN] Ingestion Integration: NOT CONNECTED")
    except Exception as e:
        logger.error(f"✗ DevOps agent initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return session, None, None, None, None, None, None
    
    # Initialize LLM Orchestrator
    logger.info("\n[3/5] Initializing LLM Orchestrator...")
    try:
        embedding_model = get_embedding_model()
        llm_orchestrator = LLMOrchestrator(
            session=session,
            embedding_model=embedding_model,
            knowledge_base_path=str(knowledge_base_path)
        )
        logger.info("[OK] LLM Orchestrator ready")
    except Exception as e:
        logger.warning(f"[WARN] LLM orchestrator initialization failed: {e}")
        llm_orchestrator = None
    
    # Initialize Layer 2 Self-Healing Connector
    logger.info("\n[4/5] Initializing Layer 2 Self-Healing Connector...")
    try:
        message_bus = get_message_bus()
        layer2_connector = SelfHealingConnector(
            self_healing_agent=devops_agent,
            llm_orchestrator=llm_orchestrator,
            message_bus=message_bus
        )
        logger.info("✓ Layer 2 Connector ready")
    except Exception as e:
        logger.warning(f"✗ Layer 2 connector initialization failed: {e}")
        layer2_connector = None
    
    # Initialize Proactive Self-Healing (CI/CD Integration)
    logger.info("\n[5/5] Initializing Proactive Self-Healing...")
    try:
        proactive_healing = ProactiveSelfHealing(
            devops_agent=devops_agent,
            llm_orchestrator=llm_orchestrator,
            session=session
        )
        logger.info("[OK] Proactive Self-Healing ready")
    except Exception as e:
        logger.warning(f"✗ Proactive healing initialization failed: {e}")
        proactive_healing = None
    
    # Initialize Help Requester
    logger.info("\n[6/6] Initializing Help Requester...")
    try:
        help_requester = get_help_requester(session=session)
        logger.info("[OK] Help Requester ready")
    except Exception as e:
        logger.error(f"✗ Help requester initialization failed: {e}")
        help_requester = None
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ GRACE SELF-HEALING AGENT READY")
    logger.info("  - DevOps Healing Agent: [OK]")
    logger.info("  - LLM Orchestration: [OK]" if llm_orchestrator else "  - LLM Orchestration: [SKIP]")
    logger.info("  - Layer 2 Connector: [OK]" if layer2_connector else "  - Layer 2 Connector: [SKIP]")
    logger.info("  - Proactive CI/CD: [OK]" if proactive_healing else "  - Proactive CI/CD: [SKIP]")
    logger.info("=" * 80 + "\n")
    
    # NOTE: Session is intentionally NOT closed here because it's used by the returned components
    # The session will be managed by the components that use it, or should be closed by the caller
    # when done. This is a long-lived session for the self-healing agent lifecycle.
    
    return session, devops_agent, help_requester, layer2_connector, proactive_healing


def run_healing_cycle(devops_agent, help_requester, cycle_num=1):
    """Run a single self-healing cycle."""
    logger.info(f"\n{'='*80}")
    logger.info(f"SELF-HEALING CYCLE #{cycle_num}")
    logger.info(f"{'='*80}\n")
    
    try:
        # Step 1: Run diagnostics
        logger.info("[STEP 1] Running diagnostics...")
        diagnostic_info = devops_agent._run_diagnostics()
        
        health_status = diagnostic_info.get("health_status", "unknown")
        issues_found = diagnostic_info.get("issues", [])
        anomalies = diagnostic_info.get("anomalies", [])
        
        # Also check for diagnostic errors as issues
        if diagnostic_info.get("error"):
            issues_found.append({
                "description": f"Diagnostic error: {diagnostic_info.get('error')}",
                "type": "diagnostic_error",
                "severity": "high",
                "error": Exception(diagnostic_info.get("error"))
            })
        
        logger.info(f"  Health Status: {health_status}")
        logger.info(f"  Issues Found: {len(issues_found)}")
        logger.info(f"  Anomalies: {len(anomalies)}")
        
        # Step 2: Process each issue
        if issues_found or anomalies:
            logger.info(f"\n[STEP 2] Processing {len(issues_found) + len(anomalies)} issue(s)...")
            
            all_issues = issues_found + anomalies
            fixed_count = 0
            help_requested = False
            
            for i, issue in enumerate(all_issues, 1):
                logger.info(f"\n  Issue #{i}: {issue.get('description', issue.get('type', 'Unknown'))}")
                
                # Determine issue type
                issue_description = issue.get('description', str(issue))
                issue_type = issue.get('type', 'unknown')
                affected_files = issue.get('files', [])
                error = issue.get('error')
                
                # Classify layer and category
                layer = None
                category = None
                
                if 'database' in issue_description.lower() or 'db' in issue_description.lower():
                    from cognitive.devops_healing_agent import DevOpsLayer, IssueCategory
                    layer = DevOpsLayer.DATABASE
                    if 'recursion' in issue_description.lower() or 'recursive' in issue_description.lower():
                        category = IssueCategory.RUNTIME_ERROR
                    elif 'connection' in issue_description.lower():
                        category = IssueCategory.RUNTIME_ERROR
                    else:
                        category = IssueCategory.RUNTIME_ERROR
                
                # Attempt to fix
                logger.info(f"  Attempting to fix via self-healing agent...")
                try:
                    result = devops_agent.detect_and_heal(
                        issue_description=issue_description,
                        error=error,
                        affected_layer=layer,
                        issue_category=category,
                        context={
                            "issue": issue,
                            "affected_files": affected_files,
                            "diagnostic_info": diagnostic_info
                        }
                    )
                    
                    if result.get("success"):
                        fixed_count += 1
                        logger.info(f"  [FIXED] {result.get('fix_applied', 'Issue resolved')}")
                    else:
                        logger.warning(f"  [FAILED] Could not fix automatically: {result.get('reason', 'Unknown')}")
                        
                        # Request help if critical
                        if health_status in ("critical", "failing") and not help_requested:
                            logger.info(f"  Requesting help for critical issue...")
                            if help_requester:
                                help_requester.request_help(
                                    request_type=HelpRequestType.DEBUGGING,
                                    priority=HelpPriority.HIGH,
                                    issue_description=f"Failed to fix: {issue_description}",
                                    context={
                                        "issue": issue,
                                        "diagnostic_info": diagnostic_info,
                                        "fix_attempt": result
                                    }
                                )
                            help_requested = True
                
                except Exception as e:
                    logger.error(f"  [ERROR] Error during fix attempt: {e}")
                    import traceback
                    traceback.print_exc()
                    
                    # Request help for errors
                    if help_requester and not help_requested:
                        logger.info(f"  Requesting help due to error...")
                        help_requester.request_help(
                            request_type=HelpRequestType.ERROR_RESOLUTION,
                            priority=HelpPriority.HIGH,
                            issue_description=f"Error while fixing: {issue_description}",
                            context={
                                "issue": issue,
                                "error": str(e),
                                "traceback": traceback.format_exc()
                            }
                        )
                        help_requested = True
            
            logger.info(f"\n[STEP 3] Summary:")
            logger.info(f"  Issues processed: {len(all_issues)}")
            logger.info(f"  Issues fixed: {fixed_count}")
            logger.info(f"  Help requested: {help_requested}")
            
            # ========== CHECK FOR STABLE STATE AND CREATE SNAPSHOT ==========
            if devops_agent and hasattr(devops_agent, 'snapshot_system') and devops_agent.snapshot_system:
                try:
                    if devops_agent.snapshot_system.is_stable_state():
                        snapshot = devops_agent.snapshot_system.create_snapshot(
                            reason=f"Stable state after healing cycle - {fixed_count} issues fixed",
                            force=False
                        )
                        if snapshot:
                            logger.info(f"[HEALING-CYCLE] Created stable state snapshot: {snapshot.snapshot_id}")
                except Exception as e:
                    logger.warning(f"[HEALING-CYCLE] Failed to create snapshot: {e}")
            
            return {
                "success": True,
                "issues_processed": len(all_issues),
                "issues_fixed": fixed_count,
                "help_requested": help_requested
            }
        else:
            logger.info("\n[STEP 2] No issues detected - system is healthy!")
            
            # ========== CHECK FOR STABLE STATE AND CREATE SNAPSHOT ==========
            if devops_agent and hasattr(devops_agent, 'snapshot_system') and devops_agent.snapshot_system:
                try:
                    if devops_agent.snapshot_system.is_stable_state():
                        snapshot = devops_agent.snapshot_system.create_snapshot(
                            reason="Stable state - no issues detected",
                            force=False
                        )
                        if snapshot:
                            logger.info(f"[HEALING-CYCLE] Created stable state snapshot: {snapshot.snapshot_id}")
                except Exception as e:
                    logger.warning(f"[HEALING-CYCLE] Failed to create snapshot: {e}")
            
            return {
                "success": True,
                "issues_processed": 0,
                "issues_fixed": 0,
                "help_requested": False
            }
    
    except Exception as e:
        logger.error(f"\n[ERROR] Self-healing cycle failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Request help for cycle failure
        if help_requester:
            try:
                help_requester.request_help(
                    request_type=HelpRequestType.ERROR_RESOLUTION,
                    priority=HelpPriority.CRITICAL,
                    issue_description=f"Self-healing cycle failed: {str(e)}",
                    context={
                        "error": str(e),
                        "traceback": traceback.format_exc(),
                        "cycle_num": cycle_num
                    }
                )
            except Exception as e2:
                logger.error(f"Failed to request help: {e2}")
        
        return {
            "success": False,
            "error": str(e)
        }


def main():
    """Main entry point for Grace's self-healing agent."""
    logger.info(f"\n{'='*80}")
    logger.info(f"Grace Self-Healing Agent")
    logger.info(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"{'='*80}\n")
    
    # Initialize
    session, devops_agent, help_requester, layer2_connector, proactive_healing = initialize_grace()
    
    if not devops_agent:
        logger.error("Failed to initialize Grace. Cannot proceed.")
        return
    
    # Start proactive continuous monitoring in background
    if proactive_healing:
        import threading
        logger.info("\n🚀 Starting proactive continuous monitoring...")
        monitoring_thread = threading.Thread(
            target=lambda: proactive_healing.run_pipeline_check(PipelineStage.CONTINUOUS),
            daemon=True
        )
        monitoring_thread.start()
        logger.info("✓ Proactive monitoring running in background\n")
    
    # Run initial healing cycle
    logger.info("\n[START] Starting self-healing agent...\n")
    
    cycle_num = 1
    max_cycles = 5  # Run up to 5 cycles (for foreground mode)
    last_snapshot_check = datetime.now(UTC)
    snapshot_check_interval = timedelta(minutes=30)  # Check for snapshots every 30 minutes
    
    while cycle_num <= max_cycles:
        result = run_healing_cycle(devops_agent, help_requester, cycle_num)
        
        if result.get("success"):
            if result.get("issues_processed", 0) == 0:
                logger.info("\n[OK] No issues found - system appears healthy!")
                break
            elif result.get("issues_fixed", 0) > 0:
                logger.info(f"\n[OK] Fixed {result['issues_fixed']} issue(s)!")
                # Continue to check if there are more issues
                if cycle_num < max_cycles:
                    logger.info("Running another cycle to check for remaining issues...")
                    time.sleep(2)
        else:
            logger.error(f"\n[ERROR] Cycle {cycle_num} failed")
            if cycle_num < max_cycles:
                logger.info("Retrying...")
                time.sleep(5)
        
        # Periodic snapshot check (every 30 minutes)
        if datetime.now(UTC) - last_snapshot_check >= snapshot_check_interval:
            if devops_agent and hasattr(devops_agent, 'snapshot_system') and devops_agent.snapshot_system:
                try:
                    if devops_agent.snapshot_system.is_stable_state():
                        snapshot = devops_agent.snapshot_system.create_snapshot(
                            reason=f"Periodic stable state check - cycle {cycle_num}",
                            force=False
                        )
                        if snapshot:
                            logger.info(f"[HEALING-CYCLE] Created periodic snapshot: {snapshot.snapshot_id}")
                except Exception as e:
                    logger.warning(f"[HEALING-CYCLE] Failed to create periodic snapshot: {e}")
            last_snapshot_check = datetime.now(UTC)
        
        cycle_num += 1
    
    # Final statistics
    logger.info("\n" + "=" * 80)
    logger.info("FINAL STATISTICS")
    logger.info("=" * 80)
    try:
        stats = devops_agent.get_statistics()
        logger.info(f"Total Issues Detected: {stats.get('total_issues_detected', 0)}")
        logger.info(f"Total Issues Fixed: {stats.get('total_issues_fixed', 0)}")
        logger.info(f"Success Rate: {stats.get('success_rate', 0):.1%}")
        logger.info(f"Knowledge Requests: {stats.get('total_knowledge_requests', 0)}")
        
        # Snapshot info
        snapshot_info = devops_agent.get_snapshot_info()
        if snapshot_info.get("available"):
            logger.info(f"\nSnapshot System:")
            logger.info(f"  Active Snapshots: {snapshot_info.get('active_snapshots', 0)}/{snapshot_info.get('max_active', 6)}")
            logger.info(f"  Backup Snapshots: {snapshot_info.get('backup_snapshots', 0)}")
            logger.info(f"  System Stable: {snapshot_info.get('is_stable', False)}")
        
        if proactive_healing:
            proactive_stats = proactive_healing.get_statistics()
            logger.info(f"\nProactive Self-Healing:")
            logger.info(f"  Total Checks: {proactive_stats.get('total_checks', 0)}")
            logger.info(f"  Issues Prevented: {proactive_stats.get('issues_prevented', 0)}")
            logger.info(f"  Issues Fixed Proactively: {proactive_stats.get('issues_fixed_proactively', 0)}")
            logger.info(f"  Prevention Rate: {proactive_stats.get('prevention_rate', 0):.1%}")
        
        if layer2_connector:
            layer2_stats = layer2_connector.get_statistics()
            logger.info(f"\nLayer 2 Connector:")
            logger.info(f"  Layer 1 Issues: {layer2_stats.get('total_layer1_issues', 0)}")
            logger.info(f"  Connected to LLM: {layer2_stats.get('connected_to_llm', False)}")
            logger.info(f"  Connected to Layer 1: {layer2_stats.get('connected_to_layer1', False)}")
    except Exception as e:
        logger.error(f"Could not get statistics: {e}")
    
    logger.info("=" * 80 + "\n")
    logger.info("[OK] Grace self-healing agent complete!")
    logger.info("[OK] Proactive monitoring continues in background!")


if __name__ == "__main__":
    # Create logs directory
    Path("logs").mkdir(exist_ok=True)
    
    main()
