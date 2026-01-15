"""
Test Grace's Self-Healing Capabilities

This script triggers Grace to detect and fix issues.
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

# Add backend to path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

print("=" * 80)
print("TESTING GRACE'S SELF-HEALING CAPABILITIES")
print("=" * 80)
print()

def test_grace_healing():
    """Test Grace's self-healing by triggering a healing cycle."""
    
    try:
        # Initialize database
        logger.info("[1/3] Initializing database...")
        from database.connection import DatabaseConnection
        from database.config import DatabaseConfig, DatabaseType
        from database.session import initialize_session_factory, get_db
        
        db_config = DatabaseConfig(
            db_type=DatabaseType.SQLITE,
            database_path="data/grace.db"
        )
        DatabaseConnection.initialize(db_config)
        initialize_session_factory()
        session = next(get_db())
        logger.info("[OK] Database initialized")
        
        # Get DevOps Healing Agent
        logger.info("\n[2/3] Getting DevOps Healing Agent...")
        from cognitive.devops_healing_agent import get_devops_healing_agent
        
        knowledge_base_path = Path("knowledge_base").resolve()
        ai_research_path = Path("data/ai_research")
        
        devops_agent = get_devops_healing_agent(
            session=session,
            knowledge_base_path=knowledge_base_path,
            ai_research_path=ai_research_path
        )
        logger.info("[OK] DevOps Healing Agent ready")
        
        # Verify systems
        print("\n[SYSTEMS] Verifying connected systems...")
        if hasattr(devops_agent, 'learning_memory') and devops_agent.learning_memory:
            print("  [OK] Learning Memory: CONNECTED")
        else:
            print("  [WARN] Learning Memory: NOT CONNECTED")
        
        if hasattr(devops_agent, 'ingestion_integration') and devops_agent.ingestion_integration:
            print("  [OK] Ingestion Integration: CONNECTED")
        else:
            print("  [WARN] Ingestion Integration: NOT CONNECTED")
        
        # Trigger healing cycle
        logger.info("\n[3/3] Triggering Grace's self-healing cycle...")
        print("\n" + "=" * 80)
        print("GRACE IS NOW DETECTING AND FIXING ISSUES...")
        print("=" * 80)
        print()
        
        # Run diagnostics first to detect issues
        diagnostic_info = devops_agent._run_diagnostics()
        issues = diagnostic_info.get('issues', [])
        
        if not issues:
            print("No issues detected - system is healthy!")
            result = {
                'issues_detected': 0,
                'fixes_applied': 0,
                'issues_fixed': 0,
                'issues_remaining': 0
            }
        else:
            # Process the first issue found
            issue = issues[0]
            issue_description = issue.get('description', 'Unknown issue')
            
            print(f"Detected issue: {issue_description}")
            print(f"  Layer: {issue.get('layer', 'Unknown')}")
            print(f"  Category: {issue.get('category', 'Unknown')}")
            print(f"  Severity: {issue.get('severity', 'Unknown')}")
            print()
            
            # Run detect_and_heal with the issue
            result = devops_agent.detect_and_heal(
                issue_description=issue_description,
                error=issue.get('error'),
                affected_layer=issue.get('layer'),
                issue_category=issue.get('category'),
                context=issue
            )
        
        print("\n" + "=" * 80)
        print("HEALING CYCLE COMPLETE")
        print("=" * 80)
        print()
        
        # Show results
        print("Results:")
        print(f"  Issues Detected: {result.get('issues_detected', 0)}")
        print(f"  Fixes Applied: {result.get('fixes_applied', 0)}")
        print(f"  Issues Fixed: {result.get('issues_fixed', 0)}")
        print(f"  Issues Remaining: {result.get('issues_remaining', 0)}")
        
        if result.get('issues'):
            print("\nIssues Found:")
            for i, issue in enumerate(result.get('issues', [])[:5], 1):  # Show first 5
                print(f"  {i}. {issue.get('description', 'Unknown')[:80]}")
                print(f"     Layer: {issue.get('layer', 'Unknown')}")
                print(f"     Category: {issue.get('category', 'Unknown')}")
                print(f"     Severity: {issue.get('severity', 'Unknown')}")
        
        if result.get('fixes'):
            print("\nFixes Applied:")
            for i, fix in enumerate(result.get('fixes', [])[:5], 1):  # Show first 5
                print(f"  {i}. {fix.get('description', 'Unknown')[:80]}")
                print(f"     Status: {fix.get('status', 'Unknown')}")
        
        # Get statistics
        stats = devops_agent.get_statistics()
        print("\nStatistics:")
        print(f"  Total Issues Detected: {stats.get('total_issues_detected', 0)}")
        print(f"  Total Fixes Applied: {stats.get('total_fixes_applied', 0)}")
        print(f"  Total Fixes Successful: {stats.get('total_fixes_successful', 0)}")
        print(f"  Total Fixes Failed: {stats.get('total_fixes_failed', 0)}")
        
        print("\n" + "=" * 80)
        print("TEST COMPLETE")
        print("=" * 80)
        print()
        print("Check logs/grace_self_healing_background.log for detailed information")
        print()
        
        return True
        
    except Exception as e:
        logger.error(f"[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_grace_healing()
    sys.exit(0 if success else 1)
