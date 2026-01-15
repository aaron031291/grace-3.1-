"""
Trigger Grace to Ingest All Knowledge Needed for Self-Healing

This script asks Grace to ingest:
1. AI Research repositories (data/ai_research) - debugging, DevOps, best practices
2. Knowledge base files - any new or updated files
3. Self-healing documentation - patterns, fixes, solutions

Grace will process these files and make them available for:
- Issue detection
- Fix generation
- Pattern recognition
- Best practice application
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

# Add backend to path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(Path(__file__).parent.parent / 'logs' / 'grace_self_healing_ingestion.log')),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

print("=" * 80)
print("GRACE SELF-HEALING KNOWLEDGE INGESTION")
print("=" * 80)
print()

def trigger_ingestion():
    """Trigger Grace to ingest knowledge for self-healing."""
    
    try:
        # Initialize database
        logger.info("[1/5] Initializing database...")
        from database.connection import DatabaseConnection
        from database.config import DatabaseConfig, DatabaseType
        from database.session import initialize_session_factory, get_db
        
        repo_root = Path(__file__).parent.parent
        db_config = DatabaseConfig(
            db_type=DatabaseType.SQLITE,
            database_path=str(repo_root / "data" / "grace.db")
        )
        DatabaseConnection.initialize(db_config)
        initialize_session_factory()
        session = next(get_db())
        logger.info("[OK] Database initialized")
        
        # Initialize file ingestion manager
        logger.info("\n[2/5] Initializing file ingestion manager...")
        from api.file_ingestion import get_file_manager
        file_manager = get_file_manager()
        logger.info("[OK] File manager initialized")
        
        # Initialize git tracker
        logger.info("\n[3/5] Initializing git repository...")
        file_manager.git_tracker.initialize_git()
        logger.info("[OK] Git repository initialized")
        
        # Scan and ingest knowledge base
        logger.info("\n[4/5] Scanning knowledge base for files to ingest...")
        repo_root = Path(__file__).parent.parent
        kb_path = repo_root / "knowledge_base"
        if kb_path.exists():
            logger.info(f"  Knowledge base path: {kb_path.resolve()}")
            results = file_manager.scan_directory()
            successful = sum(1 for r in results if r.success)
            failed = sum(1 for r in results if not r.success)
            logger.info(f"  [OK] Processed {len(results)} files: {successful} successful, {failed} failed")
        else:
            logger.warning(f"  [WARN] Knowledge base path not found: {kb_path}")
        
        # Scan and ingest AI research (data/ai_research)
        logger.info("\n[5/5] Scanning AI research directory for self-healing knowledge...")
        repo_root = Path(__file__).parent.parent
        ai_research_path = repo_root / "data" / "ai_research"
        if ai_research_path.exists():
            logger.info(f"  AI research path: {ai_research_path.resolve()}")
            
            # Focus on self-healing relevant directories
            self_healing_keywords = [
                "debug", "fix", "error", "heal", "repair", "troubleshoot",
                "devops", "ci/cd", "monitoring", "logging", "testing",
                "best-practices", "patterns", "solutions", "guide"
            ]
            
            # Find relevant files
            relevant_files = []
            total_files = 0
            
            for root, dirs, files in ai_research_path.rglob("*"):
                # Skip hidden and build directories
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'build', 'dist']]
                
                for file in files:
                    total_files += 1
                    file_path = Path(root) / file
                    
                    # Check if file is relevant to self-healing
                    file_str = str(file_path).lower()
                    if any(keyword in file_str for keyword in self_healing_keywords):
                        relevant_files.append(file_path)
                    
                    # Also include common documentation files
                    if file_path.suffix in ['.md', '.rst', '.txt', '.py', '.js', '.ts']:
                        if 'readme' in file.lower() or 'doc' in file.lower() or 'guide' in file.lower():
                            if file_path not in relevant_files:
                                relevant_files.append(file_path)
            
            logger.info(f"  Found {total_files} total files in AI research")
            logger.info(f"  Found {len(relevant_files)} files relevant to self-healing")
            
            # Ingest relevant files (limit to avoid overwhelming)
            if relevant_files:
                logger.info(f"  Ingesting top {min(100, len(relevant_files))} most relevant files...")
                
                # Sort by relevance (files with more keywords first)
                def relevance_score(path):
                    path_str = str(path).lower()
                    score = sum(1 for kw in self_healing_keywords if kw in path_str)
                    # Boost README and docs
                    if 'readme' in path_str or 'doc' in path_str:
                        score += 2
                    return score
                
                relevant_files.sort(key=relevance_score, reverse=True)
                
                ingested_count = 0
                for file_path in relevant_files[:100]:  # Limit to top 100
                    try:
                        # Check if file is already ingested
                        relative_path = file_path.relative_to(ai_research_path)
                        # Use file manager to ingest
                        result = file_manager.ingest_file(
                            file_path=file_path,
                            user_id="grace_self_healing"
                        )
                        if result.success:
                            ingested_count += 1
                            if ingested_count % 10 == 0:
                                logger.info(f"    Ingested {ingested_count} files...")
                    except Exception as e:
                        logger.debug(f"    Skipped {file_path.name}: {e}")
                        continue
                
                logger.info(f"  [OK] Ingested {ingested_count} files from AI research")
            else:
                logger.info("  [INFO] No specifically relevant files found, will ingest on-demand")
        else:
            logger.warning(f"  [WARN] AI research path not found: {ai_research_path}")
        
        # Trigger autonomous learning for ingested content
        logger.info("\n[BONUS] Triggering autonomous learning for ingested knowledge...")
        try:
            from cognitive.ingestion_self_healing_integration import get_ingestion_integration
            repo_root = Path(__file__).parent.parent
            integration = get_ingestion_integration(
                session=session,
                knowledge_base_path=repo_root / "knowledge_base",
                enable_healing=True,
                enable_mirror=True
            )
            logger.info("[OK] Autonomous learning system ready to process ingested content")
        except Exception as e:
            logger.warning(f"[WARN] Autonomous learning not available: {e}")
        
        print()
        print("=" * 80)
        print("INGESTION COMPLETE")
        print("=" * 80)
        print()
        print("Grace has ingested knowledge for self-healing!")
        print()
        print("Grace can now:")
        print("  - Search AI research for similar issues")
        print("  - Find code examples and patterns")
        print("  - Learn from best practices")
        print("  - Apply debugging techniques")
        print("  - Use DevOps knowledge for fixes")
        print()
        print("Knowledge is now available for Grace's self-healing agent!")
        print()
        
    except Exception as e:
        logger.error(f"[ERROR] Ingestion failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = trigger_ingestion()
    sys.exit(0 if success else 1)
