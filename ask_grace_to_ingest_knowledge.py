"""
Ask Grace to Ingest Knowledge for Self-Healing

This script uses Grace's autonomous help requester to ask her to ingest
all knowledge needed for self-healing from:
1. AI Research (data/ai_research) - debugging, DevOps, best practices
2. Knowledge Base - any new or updated files
3. Self-healing documentation

Grace will process this request autonomously through her ingestion system.
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

# Add backend to path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

# Setup logging
Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/grace_ingestion_request.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

print("=" * 80)
print("ASKING GRACE TO INGEST SELF-HEALING KNOWLEDGE")
print("=" * 80)
print()

def ask_grace_to_ingest():
    """Ask Grace to ingest knowledge for self-healing."""
    
    try:
        # Initialize database
        logger.info("[1/4] Initializing database...")
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
        
        # Get Grace's help requester
        logger.info("\n[2/4] Connecting to Grace's autonomous help requester...")
        from cognitive.autonomous_help_requester import get_help_requester, HelpRequestType, HelpPriority
        help_requester = get_help_requester(session=session)
        logger.info("[OK] Help requester connected")
        
        # Create knowledge ingestion request
        logger.info("\n[3/4] Creating knowledge ingestion request for Grace...")
        
        issue_description = """
Grace, please ingest all knowledge needed for self-healing:

1. AI Research Knowledge Base (data/ai_research):
   - Debugging techniques and error resolution
   - DevOps best practices and patterns
   - Code fixing and healing strategies
   - System monitoring and diagnostics
   - CI/CD pipeline knowledge
   - Testing and validation approaches
   - Performance optimization
   - Security best practices

2. Knowledge Base Files:
   - Any new or updated documentation
   - Self-healing patterns and examples
   - Fix templates and solutions
   - Error handling guides

3. Self-Healing Documentation:
   - Common error patterns
   - Fix strategies by issue type
   - Best practices for autonomous healing
   - Pattern recognition examples

Please prioritize:
- Files with keywords: debug, fix, error, heal, repair, troubleshoot, devops, monitoring
- README and documentation files
- Code examples and patterns
- Best practices guides

This knowledge will help Grace:
- Detect issues more accurately
- Generate better fixes
- Learn from past solutions
- Apply industry best practices
- Make more informed healing decisions
"""
        
        # Request help via Grace's autonomous system
        help_request = help_requester.request_help(
            request_type=HelpRequestType.LEARNING,
            priority=HelpPriority.HIGH,
            issue_description=issue_description,
            context={
                "request_type": "knowledge_ingestion",
                "target_directories": [
                    "data/ai_research",
                    "knowledge_base"
                ],
                "focus_areas": [
                    "debugging",
                    "error_resolution",
                    "devops",
                    "self_healing",
                    "best_practices",
                    "monitoring",
                    "testing"
                ],
                "purpose": "Enable Grace's self-healing capabilities with comprehensive knowledge"
            },
            affected_files=[
                "data/ai_research/**/*",
                "knowledge_base/**/*"
            ]
        )
        
        logger.info(f"[OK] Help request created: {help_request.get('help_request', {}).get('request_id', 'unknown')}")
        
        # Also trigger direct ingestion scan if possible
        logger.info("\n[4/4] Triggering direct ingestion scan...")
        try:
            from api.file_ingestion import get_file_manager
            file_manager = get_file_manager()
            file_manager.git_tracker.initialize_git()
            
            # Scan knowledge base
            logger.info("  Scanning knowledge base...")
            results = file_manager.scan_directory()
            successful = sum(1 for r in results if r.success)
            logger.info(f"  [OK] Scanned {len(results)} files: {successful} successful")
            
        except Exception as e:
            logger.warning(f"  [WARN] Direct scan not available: {e}")
            logger.info("  Grace will handle ingestion through her autonomous systems")
        
        print()
        print("=" * 80)
        print("REQUEST SENT TO GRACE")
        print("=" * 80)
        print()
        print("Grace has been asked to ingest knowledge for self-healing!")
        print()
        print("Grace will now:")
        print("  1. Process the ingestion request")
        print("  2. Scan AI research (data/ai_research) for relevant files")
        print("  3. Ingest debugging, DevOps, and self-healing knowledge")
        print("  4. Make knowledge available for her self-healing agent")
        print()
        print("Grace's self-healing agent will use this knowledge to:")
        print("  - Detect issues more accurately")
        print("  - Generate better fixes")
        print("  - Learn from past solutions")
        print("  - Apply industry best practices")
        print()
        print("Check logs/grace_ingestion_request.log for details")
        print()
        
        return True
        
    except Exception as e:
        logger.error(f"[ERROR] Failed to request ingestion: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = ask_grace_to_ingest()
    sys.exit(0 if success else 1)
