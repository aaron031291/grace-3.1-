"""Drop librarian tables for fresh migration."""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text
from database.config import DatabaseConfig
from database.connection import DatabaseConnection

config = DatabaseConfig.from_env()
DatabaseConnection.initialize(config)
engine = DatabaseConnection.get_engine()

# Drop in reverse order of dependencies
tables_to_drop = [
    'librarian_audit',
    'librarian_actions',
    'librarian_rules',
    'document_relationships',
    'document_tags',
    'librarian_tags'
]

print("Dropping librarian tables...")
with engine.connect() as conn:
    for table in tables_to_drop:
        try:
            conn.execute(text(f'DROP TABLE IF EXISTS {table}'))
            conn.commit()
            print(f'  Dropped {table}')
        except Exception as e:
            print(f'  Error dropping {table}: {e}')

print("Done!")
