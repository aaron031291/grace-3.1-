"""
Grace Active Healing - Proactive Issue Detection and Fixing

This script activates Grace to actively detect and fix issues in the system.
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
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/grace_active_healing.log'),
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


def initialize_grace():
    """Initialize Grace's systems."""
    logger.info("=" * 80)
    logger.info("GRACE ACTIVE HEALING - INITIALIZING")
    logger.info("=" * 80)
    
    # Initialize database
    logger.info("\n[1/3] Initializing database...")
    try:
        db_config = DatabaseConfig(
            db_type=DatabaseType.SQLITE,
            database_path="data/grace.db"
        )
        DatabaseConnection.initialize(db_config)
        initialize_session_factory()
        session = next(get_db())
        logger.info("✓ Database initialized")
    except Exception as e:
        logger.error(f"✗ Database initialization failed: {e}")
        # Try to continue anyway - Grace might be able to fix this
        try:
            initialize_session_factory()
            session = next(get_db())
            logger.info("✓ Session factory initialized (database may have issues)")
        except Exception as e2:
            logger.error(f"✗ Complete failure: {e2}")
            return None, None, None
    
    # Initialize DevOps Healing Agent
    logger.info("\n[2/3] Initializing DevOps Healing Agent...")
    try:
        knowledge_base_path = Path("knowledge_base").resolve()
        ai_research_path = Path("data/ai_research")
        
        devops_agent = get_devops_healing_agent(
            session=session,
            knowledge_base_path=knowledge_base_path,
            ai_research_path=ai_research_path
        )
        logger.info("✓ DevOps Healing Agent ready")
    except Exception as e:
        logger.error(f"✗ DevOps agent initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return session, None, None
    
    # Initialize Help Requester
    logger.info("\n[3/3] Initializing Help Requester...")
    try:
        help_requester = get_help_requester(session=session)
        logger.info("✓ Help Requester ready")
    except Exception as e:
        logger.error(f"✗ Help requester initialization failed: {e}")
        help_requester = None
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ GRACE READY FOR ACTIVE HEALING")
    logger.info("=" * 80 + "\n")
    
    return session, devops_agent, help_requester


def run_healing_cycle(devops_agent, help_requester, cycle_num=1):
    """Run a single healing cycle."""
    logger.info(f"\n{'='*80}")
    logger.info(f"HEALING CYCLE #{cycle_num}")
    logger.info(f"{'='*80}\n")
    
    try:
        # Step 1: Run diagnostics
        logger.info("[STEP 1] Running diagnostics...")
        diagnostic_info = devops_agent._run_diagnostics()
        
        health_status = diagnostic_info.get("health_status", "unknown")
        issues_found = diagnostic_info.get("issues", [])
        anomalies = diagnostic_info.get("anomalies", [])
        
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
                logger.info(f"  Attempting to fix via DevOps agent...")
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
                        logger.info(f"  ✓ Fixed! {result.get('fix_applied', 'Issue resolved')}")
                    else:
                        logger.warning(f"  ✗ Could not fix automatically: {result.get('reason', 'Unknown')}")
                        
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
                    logger.error(f"  ✗ Error during fix attempt: {e}")
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
            
            return {
                "success": True,
                "issues_processed": len(all_issues),
                "issues_fixed": fixed_count,
                "help_requested": help_requested
            }
        else:
            logger.info("\n[STEP 2] No issues detected - system is healthy!")
            return {
                "success": True,
                "issues_processed": 0,
                "issues_fixed": 0,
                "help_requested": False
            }
    
    except Exception as e:
        logger.error(f"\n[ERROR] Healing cycle failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Request help for cycle failure
        if help_requester:
            try:
                help_requester.request_help(
                    request_type=HelpRequestType.ERROR_RESOLUTION,
                    priority=HelpPriority.CRITICAL,
                    issue_description=f"Healing cycle failed: {str(e)}",
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
    """Main entry point."""
    logger.info(f"\n{'='*80}")
    logger.info(f"Grace Active Healing System")
    logger.info(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"{'='*80}\n")
    
    # Initialize
    session, devops_agent, help_requester = initialize_grace()
    
    if not devops_agent:
        logger.error("Failed to initialize Grace. Cannot proceed.")
        return
    
    # Run initial healing cycle
    logger.info("\n🚀 Starting active healing...\n")
    
    cycle_num = 1
    max_cycles = 5  # Run up to 5 cycles
    
    while cycle_num <= max_cycles:
        result = run_healing_cycle(devops_agent, help_requester, cycle_num)
        
        if result.get("success"):
            if result.get("issues_processed", 0) == 0:
                logger.info("\n✅ No issues found - system appears healthy!")
                break
            elif result.get("issues_fixed", 0) > 0:
                logger.info(f"\n✅ Fixed {result['issues_fixed']} issue(s)!")
                # Continue to check if there are more issues
                if cycle_num < max_cycles:
                    logger.info("Running another cycle to check for remaining issues...")
                    time.sleep(2)
        else:
            logger.error(f"\n✗ Cycle {cycle_num} failed")
            if cycle_num < max_cycles:
                logger.info("Retrying...")
                time.sleep(5)
        
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
    except Exception as e:
        logger.error(f"Could not get statistics: {e}")
    
    logger.info("=" * 80 + "\n")
    logger.info("✅ Grace active healing complete!")


if __name__ == "__main__":
    # Create logs directory
    Path("logs").mkdir(exist_ok=True)
    
    main()
