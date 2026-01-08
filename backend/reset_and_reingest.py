#!/usr/bin/env python
"""
Complete reset and re-ingestion script for Grace Knowledge Base.

This script:
1. Clears all data from PostgreSQL/SQLite database
2. Clears all data from Qdrant vector database
3. Resets the file ingestion tracking state
4. Triggers fresh auto-ingestion of all files in knowledge_base/

Enhanced logging shows:
- Which files are being ingested
- Progress updates in real-time
- Timestamps for all operations
- Success/failure status for each file
"""

import sys
import logging
from pathlib import Path
from datetime import datetime
import time

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure enhanced logging with timestamps and colors
class ColoredFormatter(logging.Formatter):
    """Formatter that adds colors and better formatting."""
    
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[92m',       # Green
        'WARNING': '\033[93m',    # Yellow
        'ERROR': '\033[91m',      # Red
        'CRITICAL': '\033[95m',   # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        if hasattr(sys.stderr, 'isatty') and sys.stderr.isatty():
            levelname = record.levelname
            if levelname in self.COLORS:
                record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"
        
        # Add timestamp with milliseconds
        record.asctime = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        return super().format(record)


def setup_logging():
    """Configure logging with timestamps and colors."""
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    
    formatter = ColoredFormatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logging.getLogger(__name__)


logger = setup_logging()


def clear_sqlite():
    """Clear all data from SQLite database."""
    logger.info("=" * 80)
    logger.info("[1/4] CLEARING SQLITE DATABASE")
    logger.info("=" * 80)
    
    try:
        from database.config import DatabaseConfig, DatabaseType
        from database.connection import DatabaseConnection
        from database.session import initialize_session_factory
        from models.database_models import Document, DocumentChunk, Chat, ChatHistory
        
        logger.info("Setting up SQLite configuration...")
        config = DatabaseConfig(
            db_type=DatabaseType.SQLITE,
            database_path="grace.db",
            echo=False,
        )
        
        logger.info("Initializing database connection...")
        DatabaseConnection.initialize(config)
        
        logger.info("Creating session factory...")
        session_factory = initialize_session_factory()
        db = session_factory()
        
        try:
            # Delete in correct order (foreign key constraints)
            logger.info("Deleting document chunks...")
            chunk_count = db.query(DocumentChunk).delete()
            logger.info(f"  ✓ Deleted {chunk_count} document chunks")
            
            logger.info("Deleting documents...")
            doc_count = db.query(Document).delete()
            logger.info(f"  ✓ Deleted {doc_count} documents")
            
            logger.info("Deleting chat histories...")
            history_count = db.query(ChatHistory).delete()
            logger.info(f"  ✓ Deleted {history_count} chat history entries")
            
            logger.info("Deleting chats...")
            chat_count = db.query(Chat).delete()
            logger.info(f"  ✓ Deleted {chat_count} chats")
            
            db.commit()
            logger.info("✓ SQLite database cleared successfully")
            return True
            
        except Exception as e:
            if "no such table" in str(e).lower():
                logger.info("✓ Database tables don't exist yet (OK - nothing to clear)")
                return True
            else:
                db.rollback()
                logger.error(f"Error clearing SQLite: {e}", exc_info=True)
                return False
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Failed to clear SQLite: {e}", exc_info=True)
        return False


def clear_qdrant():
    """Clear all data from Qdrant vector database."""
    logger.info("\n" + "=" * 80)
    logger.info("[2/4] CLEARING QDRANT VECTOR DATABASE")
    logger.info("=" * 80)
    
    try:
        from vector_db.client import get_qdrant_client
        
        logger.info("Connecting to Qdrant...")
        client = get_qdrant_client()
        
        collection_name = "documents"
        logger.info(f"Attempting to delete Qdrant collection: '{collection_name}'")
        
        try:
            client.delete_collection(collection_name=collection_name)
            logger.info(f"✓ Qdrant collection '{collection_name}' deleted successfully")
        except Exception as e:
            if "not found" in str(e).lower():
                logger.info(f"✓ Collection '{collection_name}' doesn't exist (OK - nothing to delete)")
            else:
                raise
        
        logger.info("✓ Qdrant vector database cleared successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to clear Qdrant: {e}", exc_info=True)
        return False


def reset_file_tracking():
    """Reset file ingestion tracking state."""
    logger.info("\n" + "=" * 80)
    logger.info("[3/4] RESETTING FILE INGESTION TRACKING")
    logger.info("=" * 80)
    
    try:
        from pathlib import Path
        
        kb_path = Path(__file__).parent / "knowledge_base"
        
        # Find and reset the file states tracker
        tracking_file = kb_path / ".ingestion_state.json"
        
        if tracking_file.exists():
            logger.info(f"Removing file tracking state: {tracking_file}")
            tracking_file.unlink()
            logger.info("✓ File tracking state removed")
        else:
            logger.info("✓ No existing file tracking state found (OK)")
        
        # Also reset git tracking if it exists
        git_dir = kb_path / ".git"
        
        if git_dir.exists():
            logger.info(f"Found git repository at {kb_path}")
            logger.info("Removing git repository to allow clean reinitialization...")
            import shutil
            shutil.rmtree(git_dir)
            logger.info("✓ Git repository removed - will be reinitialized during ingestion")
        else:
            logger.info("✓ No existing git repository found (OK)")
        
        logger.info("✓ File ingestion tracking reset successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to reset file tracking: {e}", exc_info=True)
        return False


def trigger_auto_ingestion():
    """Trigger auto-ingestion of knowledge base files."""
    logger.info("\n" + "=" * 80)
    logger.info("[4/4] TRIGGERING AUTO-INGESTION OF ALL FILES")
    logger.info("=" * 80)
    
    try:
        from api.file_ingestion import get_file_manager
        from database.connection import DatabaseConnection
        from database.session import initialize_session_factory
        from database.migration import create_tables
        
        logger.info("Verifying database connection...")
        try:
            engine = DatabaseConnection.get_engine()
            logger.info("✓ Database engine ready")
        except RuntimeError as e:
            logger.warning(f"Database not yet initialized: {e}")
            logger.info("Waiting 2 seconds for database initialization...")
            time.sleep(2)
        
        logger.info("Initializing session factory...")
        session_factory = initialize_session_factory()
        logger.info("✓ Session factory initialized")
        
        logger.info("Creating database tables...")
        try:
            create_tables()
            logger.info("✓ Database tables created/verified")
        except Exception as e:
            logger.warning(f"Issue with table creation: {e}")
        
        logger.info("Getting file ingestion manager...")
        file_manager = get_file_manager()
        logger.info("✓ File manager initialized")
        
        logger.info("Initializing git repository...")
        file_manager.git_tracker.initialize_git()
        logger.info("✓ Git repository initialized")
        
        # Scan knowledge base for files
        logger.info("\n" + "-" * 80)
        logger.info("SCANNING KNOWLEDGE BASE FOR FILES")
        logger.info("-" * 80)
        
        kb_path = file_manager.knowledge_base_path
        logger.info(f"Knowledge base path: {kb_path}")
        
        # Count files to be ingested
        if kb_path.exists():
            all_files = list(kb_path.rglob("*"))
            files_to_process = [f for f in all_files if f.is_file() and not f.name.startswith(".")]
            logger.info(f"Total files found in knowledge base: {len(files_to_process)}")
            
            if files_to_process:
                logger.info("\nFiles to be ingested:")
                for i, file_path in enumerate(sorted(files_to_process), 1):
                    rel_path = file_path.relative_to(kb_path)
                    size_kb = file_path.stat().st_size / 2048
                    logger.info(f"  {i:3d}. {rel_path} ({size_kb:.1f} KB)")
            else:
                logger.warning("No files found in knowledge base!")
        else:
            logger.warning(f"Knowledge base path does not exist: {kb_path}")
            logger.info("Creating knowledge base directory...")
            kb_path.mkdir(parents=True, exist_ok=True)
            logger.info("✓ Knowledge base directory created")
        
        # Perform initial scan
        logger.info("\n" + "-" * 80)
        logger.info("PERFORMING INITIAL SCAN AND PROCESSING ALL FILES")
        logger.info("-" * 80)
        
        max_retries = 3
        retry_count = 0
        results = []
        
        while retry_count < max_retries:
            try:
                logger.info(f"Scan attempt {retry_count + 1}/{max_retries}...")
                results = file_manager.scan_directory()
                logger.info(f"✓ Scan completed, processed {len(results)} files")
                break
            except Exception as e:
                retry_count += 1
                if retry_count < max_retries:
                    logger.warning(f"Scan attempt {retry_count} failed: {e}")
                    logger.info("Retrying in 2 seconds...")
                    time.sleep(2)
                else:
                    logger.error(f"Initial scan failed after {max_retries} attempts: {e}", exc_info=True)
                    raise
        
        # Report scan results with detailed breakdown
        if results:
            logger.info(f"\nIngestion completed with {len(results)} files processed:")
            logger.info("-" * 80)
            
            added_count = 0
            modified_count = 0
            deleted_count = 0
            success_count = 0
            failed_count = 0
            
            for result in results:
                status = "✓ SUCCESS" if result.success else "✗ FAILED"
                change_type = result.change_type.upper()
                
                # Count changes by type
                if result.change_type == "added":
                    added_count += 1
                elif result.change_type == "modified":
                    modified_count += 1
                elif result.change_type == "deleted":
                    deleted_count += 1
                
                if result.success:
                    success_count += 1
                else:
                    failed_count += 1
                
                logger.info(
                    f"{status} | {change_type:8s} | {result.filepath:50s} | "
                    f"Doc ID: {result.document_id or 'N/A'}"
                )
                
                if result.message:
                    logger.info(f"         | Message: {result.message}")
                if result.error:
                    logger.error(f"         | Error: {result.error}")
            
            logger.info("-" * 80)
            logger.info(f"Summary Statistics:")
            logger.info(f"  Total processed: {len(results)}")
            logger.info(f"  Successful: {success_count}")
            logger.info(f"  Failed: {failed_count}")
            logger.info(f"  Added: {added_count}")
            logger.info(f"  Modified: {modified_count}")
            logger.info(f"  Deleted: {deleted_count}")
        else:
            logger.warning("No files were processed in the scan")
        
        logger.info("\n" + "=" * 80)
        logger.info("✓ AUTO-INGESTION COMPLETED")
        logger.info("=" * 80)
        logger.info("\nNext steps:")
        logger.info("  • The system is ready for use")
        logger.info("  • Auto-ingestion monitor is running (checks every 30 seconds)")
        logger.info("  • New files added to knowledge_base/ will be automatically ingested")
        logger.info("  • Check logs above for ingestion progress and any errors")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to trigger auto-ingestion: {e}", exc_info=True)
        return False


def main():
    """Execute complete reset and re-ingestion flow."""
    start_time = datetime.now()
    
    logger.info("\n")
    logger.info("╔" + "=" * 78 + "╗")
    logger.info("║" + " " * 78 + "║")
    logger.info("║" + "GRACE KNOWLEDGE BASE - COMPLETE RESET & RE-INGESTION".center(78) + "║")
    logger.info("║" + f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}".center(78) + "║")
    logger.info("║" + " " * 78 + "║")
    logger.info("╚" + "=" * 78 + "╝")
    logger.info("")
    
    # Execute clear and re-ingest operations
    steps = [
        ("Clear SQLite", clear_sqlite),
        ("Clear Qdrant", clear_qdrant),
        ("Reset File Tracking", reset_file_tracking),
        ("Trigger Auto-Ingestion", trigger_auto_ingestion),
    ]
    
    success = True
    for step_name, step_func in steps:
        try:
            if not step_func():
                logger.error(f"✗ {step_name} failed")
                success = False
        except Exception as e:
            logger.error(f"✗ {step_name} encountered an error: {e}", exc_info=True)
            success = False
    
    # Final summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    logger.info("\n")
    logger.info("╔" + "=" * 78 + "╗")
    logger.info("║" + " " * 78 + "║")
    
    if success:
        logger.info("║" + "✓ RESET AND RE-INGESTION COMPLETED SUCCESSFULLY".center(78) + "║")
    else:
        logger.info("║" + "✗ RESET AND RE-INGESTION COMPLETED WITH ERRORS".center(78) + "║")
    
    logger.info("║" + f"Duration: {duration:.1f} seconds".center(78) + "║")
    logger.info("║" + f"Ended: {end_time.strftime('%Y-%m-%d %H:%M:%S')}".center(78) + "║")
    logger.info("║" + " " * 78 + "║")
    logger.info("╚" + "=" * 78 + "╝")
    logger.info("")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
