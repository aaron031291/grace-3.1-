"""
Minimal test of auto-ingestion flow with database initialized.
"""

import sys
import pytest
sys.path.insert(0, '.')

# Initialize database FIRST
print("[TEST] Initializing database...")
from database.connection import DatabaseConnection, DatabaseConfig, DatabaseType
from database.session import initialize_session_factory
from database.migration import create_tables
from settings import settings

db_config = DatabaseConfig(
    db_type=DatabaseType.SQLITE,
    database_path=settings.DATABASE_PATH,
)
DatabaseConnection.initialize(db_config)
initialize_session_factory()
create_tables()
print("[TEST] ✓ Database initialized\n")

# Now test the file manager
print("[TEST] Setting up file manager...")
from ingestion.file_manager import IngestionFileManager
from pathlib import Path

try:
    from embedding.embedder import get_embedding_model
    embedding_model = get_embedding_model()
except (OSError, Exception) as e:
    pytest.skip(f"Embedding model not available: {e}")

kb_path = Path('knowledge_base')

# Clear state
state_file = kb_path / ".ingestion_state.json"
if state_file.exists():
    state_file.unlink()
    print("[TEST] Cleared state file")

fm = IngestionFileManager(kb_path, embedding_model=embedding_model)
print(f"[TEST] File manager created")
print(f"[TEST] Tracked files: {len(fm.file_states)}\n")

# Run scan
print("[TEST] Running scan_directory()...")
results = fm.scan_directory()

print(f"\n[TEST] Scan results: {len(results)} changes")
for r in results:
    status = "✓" if r.success else "✗"
    error_msg = f" ({r.error})" if r.error else ""
    print(f"  {status} {r.change_type}: {r.filepath}{error_msg}")

# Check database
print("\n[TEST] Checking database...")
from database.session import SessionLocal
from models.database_models import Document

db = SessionLocal()
docs = db.query(Document).all()
print(f"[TEST] Documents in database: {len(docs)}")
for doc in docs:
    print(f"  - {doc.filename} (path: {doc.file_path})")
db.close()

# Check state file
print("\n[TEST] Checking state file...")
import json
if state_file.exists():
    with open(state_file, 'r') as f:
        state = json.load(f)
    print(f"[TEST] State file contains: {len(state)} files")
    for filepath in state:
        print(f"  - {filepath}")
else:
    print("[TEST] State file NOT created")
