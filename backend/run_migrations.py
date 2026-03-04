"""
Run all database migrations for Grace.
This script initializes the database connection and creates all necessary tables.
"""

import sys
from database.connection import DatabaseConnection
from database.config import DatabaseConfig
from database.base import BaseModel
from sqlalchemy import inspect

# Import all models to ensure they're registered
from models.database_models import (
    User, Conversation, Embedding, Chat, Message, ChatHistory,
    Document, DocumentChunk
)

try:
    from models.genesis_key_models import (
        GenesisKey, FixSuggestion, GenesisKeyArchive, UserProfile
    )
    genesis_models_available = True
except ImportError as e:
    print(f"Warning: Genesis models not available: {e}")
    genesis_models_available = False

try:
    from models.librarian_models import (
        LibrarianTag, DocumentTag, DocumentRelationship,
        LibrarianRule, LibrarianAction, LibrarianAudit
    )
    librarian_models_available = True
except ImportError as e:
    print(f"Warning: Librarian models not available: {e}")
    librarian_models_available = False

try:
    from models.telemetry_models import (
        OperationLog, PerformanceBaseline, DriftAlert,
        OperationReplay, SystemState
    )
    telemetry_models_available = True
except ImportError as e:
    print(f"Warning: Telemetry models not available: {e}")
    telemetry_models_available = False

try:
    from models.query_intelligence_models import (
        QueryHandlingLog, KnowledgeGap, ContextSubmission
    )
    query_intelligence_models_available = True
except ImportError as e:
    print(f"Warning: Query intelligence models not available: {e}")
    query_intelligence_models_available = False

try:
    from scraping.models import ScrapingJob, ScrapedPage
    scraping_models_available = True
except ImportError as e:
    print(f"Warning: Scraping models not available: {e}")
    scraping_models_available = False

try:
    from models.workspace_models import Workspace, Branch, FileVersion, PipelineRun
    workspace_models_available = True
except ImportError as e:
    print(f"Warning: Workspace models not available: {e}")
    workspace_models_available = False

def run_all_migrations():
    """Run all database migrations."""
    print("=" * 60)
    print("Grace Database Migration Script")
    print("=" * 60)

    # Initialize database connection
    print("\n1. Initializing database connection...")
    config = DatabaseConfig.from_env()
    print(f"   Database: {config.db_type}")
    print(f"   Path: {config.database_path if config.db_type.value == 'sqlite' else f'{config.host}:{config.port}/{config.database}'}")

    DatabaseConnection.initialize(config)
    engine = DatabaseConnection.get_engine()

    # Check existing tables
    print("\n2. Checking existing tables...")
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    print(f"   Found {len(existing_tables)} existing tables:")
    for table in sorted(existing_tables):
        print(f"      - {table}")

    # Create all tables
    print("\n3. Creating/updating all tables...")
    BaseModel.metadata.create_all(engine)

    # Check what was created
    print("\n4. Verifying tables...")
    inspector = inspect(engine)
    all_tables = inspector.get_table_names()
    new_tables = set(all_tables) - set(existing_tables)

    if new_tables:
        print(f"   Created {len(new_tables)} new tables:")
        for table in sorted(new_tables):
            print(f"      + {table}")
    else:
        print("   No new tables created (all tables already exist)")

    print(f"\n   Total tables in database: {len(all_tables)}")

    # Show model availability
    print("\n5. Model Availability:")
    print(f"   [OK] Core models: Available")
    print(f"   [{'OK' if genesis_models_available else 'SKIP'}] Genesis Key models: {'Available' if genesis_models_available else 'Not available'}")
    print(f"   [{'OK' if librarian_models_available else 'SKIP'}] Librarian models: {'Available' if librarian_models_available else 'Not available'}")
    print(f"   [{'OK' if telemetry_models_available else 'SKIP'}] Telemetry models: {'Available' if telemetry_models_available else 'Not available'}")
    print(f"   [{'OK' if query_intelligence_models_available else 'SKIP'}] Query Intelligence models: {'Available' if query_intelligence_models_available else 'Not available'}")
    print(f"   [{'OK' if scraping_models_available else 'SKIP'}] Scraping models: {'Available' if scraping_models_available else 'Not available'}")
    print(f"   [{'OK' if workspace_models_available else 'SKIP'}] Workspace models: {'Available' if workspace_models_available else 'Not available'}")

    print("\n" + "=" * 60)
    print("Migration Complete!")
    print("=" * 60)

    return True

if __name__ == "__main__":
    try:
        run_all_migrations()
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
