"""
Teach Grace About Detected Errors

This script teaches Grace about the errors she's detecting so she can learn
from them and fix similar issues in the future.
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
print("TEACHING GRACE ABOUT DETECTED ERRORS")
print("=" * 80)
print()

def teach_grace_errors():
    """Teach Grace about the errors she's detecting."""
    
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
        from cognitive.devops_healing_agent import get_devops_healing_agent, DevOpsLayer, IssueCategory
        
        knowledge_base_path = Path("knowledge_base").resolve()
        ai_research_path = Path("data/ai_research")
        
        devops_agent = get_devops_healing_agent(
            session=session,
            knowledge_base_path=knowledge_base_path,
            ai_research_path=ai_research_path
        )
        logger.info("[OK] DevOps Healing Agent ready")
        
        # Check if learning memory is connected
        if not hasattr(devops_agent, 'learning_memory') or not devops_agent.learning_memory:
            print("\n[WARN] Learning Memory not connected - cannot teach Grace")
            print("       Grace will learn automatically when Learning Memory is connected")
            return False
        
        # Teach Grace about common errors
        logger.info("\n[3/3] Teaching Grace about detected errors...")
        print()
        
        errors_to_teach = [
            {
                "description": "cannot import name 'check_ollama_running' from 'backend.ollama_client.client'",
                "error_type": "ImportError",
                "layer": DevOpsLayer.BACKEND,
                "category": IssueCategory.DEPENDENCY,
                "fix_suggestion": "Add missing function or update import path"
            },
            {
                "description": "table genesis_key has no column named change_origin",
                "error_type": "OperationalError",
                "layer": DevOpsLayer.DATABASE,
                "category": IssueCategory.DATABASE,
                "fix_suggestion": "Run database migration to add missing column"
            },
            {
                "description": "Object of type ImportError is not JSON serializable",
                "error_type": "TypeError",
                "layer": DevOpsLayer.BACKEND,
                "category": IssueCategory.CODE_ERROR,
                "fix_suggestion": "Convert exception objects to strings before JSON serialization"
            },
            {
                "description": "'DevOpsHealingAgent' object has no attribute 'file_health_monitor'",
                "error_type": "AttributeError",
                "layer": DevOpsLayer.BACKEND,
                "category": IssueCategory.CODE_ERROR,
                "fix_suggestion": "Initialize file_health_monitor in _initialize_full_architecture"
            },
            {
                "description": "'HealthReport' object has no attribute 'overall_status'",
                "error_type": "AttributeError",
                "layer": DevOpsLayer.BACKEND,
                "category": IssueCategory.CODE_ERROR,
                "fix_suggestion": "Use 'health_status' attribute instead of 'overall_status'"
            }
        ]
        
        print(f"Teaching Grace about {len(errors_to_teach)} error patterns...")
        print()
        
        for i, error_info in enumerate(errors_to_teach, 1):
            print(f"[{i}/{len(errors_to_teach)}] Teaching: {error_info['error_type']}")
            print(f"  Description: {error_info['description'][:80]}...")
            
            # Create a mock error for teaching
            error = None
            if error_info['error_type'] == 'ImportError':
                error = ImportError(error_info['description'])
            elif error_info['error_type'] == 'OperationalError':
                from sqlite3 import OperationalError
                error = OperationalError(error_info['description'])
            elif error_info['error_type'] == 'TypeError':
                error = TypeError(error_info['description'])
            elif error_info['error_type'] == 'AttributeError':
                error = AttributeError(error_info['description'])
            
            # Teach Grace about this error
            devops_agent._teach_error_detected(
                issue_description=error_info['description'],
                error=error,
                affected_layer=error_info['layer'],
                issue_category=error_info['category'],
                context={
                    "fix_suggestion": error_info['fix_suggestion'],
                    "taught_at": datetime.now().isoformat(),
                    "source": "manual_teaching"
                }
            )
            
            print(f"  [OK] Grace learned about {error_info['error_type']}")
        
        print()
        print("=" * 80)
        print("TEACHING COMPLETE")
        print("=" * 80)
        print()
        print(f"Grace has been taught about {len(errors_to_teach)} error patterns!")
        print()
        print("Grace can now:")
        print("  - Recognize these error types")
        print("  - Apply learned fixes when similar errors occur")
        print("  - Reference these patterns when fixing issues")
        print()
        print("Check learning memory for stored error patterns")
        print()
        
        return True
        
    except Exception as e:
        logger.error(f"[ERROR] Teaching failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = teach_grace_errors()
    sys.exit(0 if success else 1)
