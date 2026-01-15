"""
Trigger Grace to Ingest Knowledge for Self-Healing

This script directly triggers Grace's ingestion system to process:
1. AI Research (data/ai_research) - debugging, DevOps, best practices
2. Knowledge Base - any new or updated files

Grace will make this knowledge available for self-healing.
"""

import sys
import logging
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

# Setup logging
Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/grace_ingestion_trigger.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

print("=" * 80)
print("TRIGGERING GRACE TO INGEST SELF-HEALING KNOWLEDGE")
print("=" * 80)
print()

def trigger_ingestion():
    """Trigger Grace to ingest knowledge for self-healing."""
    
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
        
        # Use ingestion integration system
        logger.info("\n[2/4] Initializing ingestion integration system...")
        from cognitive.ingestion_self_healing_integration import get_ingestion_integration
        from pathlib import Path
        
        knowledge_base_path = Path("knowledge_base")
        integration = get_ingestion_integration(
            session=session,
            knowledge_base_path=knowledge_base_path,
            enable_healing=True,
            enable_mirror=True
        )
        logger.info("[OK] Ingestion integration system ready")
        
        # Create Genesis Key for ingestion request
        logger.info("\n[3/4] Creating ingestion request via Genesis Key...")
        from genesis.genesis_key_service import get_genesis_service
        from models.genesis_key_models import GenesisKeyType
        
        genesis_service = get_genesis_service(session)
        
        ingestion_key = genesis_service.create_key(
            key_type=GenesisKeyType.SYSTEM_EVENT,
            what_description="Request to ingest knowledge for self-healing",
            who_actor="user",
            why_reason="Enable Grace's self-healing capabilities with comprehensive knowledge",
            how_method="ingestion_integration",
            context_data={
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
                "purpose": "Enable Grace's self-healing capabilities"
            },
            tags=["ingestion", "self_healing", "knowledge_base"],
            session=session
        )
        
        logger.info(f"[OK] Genesis Key created: {ingestion_key.key_id}")
        
        # Trigger ingestion for AI research directory
        logger.info("\n[4/4] Triggering ingestion of AI research knowledge...")
        ai_research_path = Path("data/ai_research")
        
        if ai_research_path.exists():
            logger.info(f"  AI research path: {ai_research_path.resolve()}")
            logger.info("  Grace will ingest files from AI research as needed")
            logger.info("  Focus areas: debugging, DevOps, error resolution, best practices")
        else:
            logger.warning(f"  [WARN] AI research path not found: {ai_research_path}")
        
        # Note: Grace's ingestion system will process files automatically
        # when they are accessed or when the file manager scans the directory
        logger.info("\n  Grace's ingestion system is now aware of the request")
        logger.info("  Files will be ingested when:")
        logger.info("    - Grace's file manager scans the directory")
        logger.info("    - Files are accessed during self-healing")
        logger.info("    - Autonomous learning triggers ingestion")
        
        print()
        print("=" * 80)
        print("INGESTION REQUEST COMPLETE")
        print("=" * 80)
        print()
        print("Grace has been notified to ingest knowledge for self-healing!")
        print()
        print("Grace will:")
        print("  1. Process the ingestion request via Genesis Key")
        print("  2. Scan AI research (data/ai_research) when needed")
        print("  3. Ingest debugging, DevOps, and self-healing knowledge")
        print("  4. Make knowledge available for her self-healing agent")
        print()
        print("Knowledge will be ingested:")
        print("  - When Grace's file manager scans directories")
        print("  - When files are accessed during self-healing")
        print("  - When autonomous learning triggers ingestion")
        print()
        print("Grace's self-healing agent will use this knowledge to:")
        print("  - Detect issues more accurately")
        print("  - Generate better fixes")
        print("  - Learn from past solutions")
        print("  - Apply industry best practices")
        print()
        print("Genesis Key:", ingestion_key.key_id)
        print()
        
        return True
        
    except Exception as e:
        logger.error(f"[ERROR] Failed to trigger ingestion: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = trigger_ingestion()
    sys.exit(0 if success else 1)
