"""
Test Grace's database connection (SQLite or PostgreSQL).

Run from project root:  ..\test_postgres_connection.ps1   (PowerShell)
Or from backend dir:   python scripts/test_postgres_connection.py  (with venv active)

Uses .env by default. To test PostgreSQL without changing .env, set env vars first:

  PowerShell:
    $env:DATABASE_TYPE="postgresql"; $env:DATABASE_HOST="localhost"; $env:DATABASE_PORT="5432"
    $env:DATABASE_USER="postgres"; $env:DATABASE_PASSWORD="your_password"; $env:DATABASE_NAME="grace"
    $env:DATABASE_SSLMODE=""
    python scripts/test_postgres_connection.py

  Cmd:
    set DATABASE_TYPE=postgresql & set DATABASE_HOST=localhost & ... & python scripts/test_postgres_connection.py

If you see "password authentication failed", fix DATABASE_USER/DATABASE_PASSWORD (use the same as pgAdmin/stGIS).
"""
import sys
from pathlib import Path

# Ensure backend root is on path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

def main():
    from dotenv import load_dotenv
    load_dotenv(backend_dir / ".env")

    from database.config import DatabaseConfig, DatabaseType
    from database.connection import DatabaseConnection

    config = DatabaseConfig.from_env()
    db_type = config.db_type.value if hasattr(config.db_type, "value") else str(config.db_type)

    print(f"Database type: {db_type}")
    if db_type == "postgresql":
        print(f"  Host: {config.host}:{config.port or 5432}")
        print(f"  User: {config.username}")
        print(f"  Database: {config.database}")
        # Don't print password
    else:
        print(f"  Path: {config.database_path}")

    try:
        DatabaseConnection.initialize(config)
        ok = DatabaseConnection.health_check()
        if ok:
            print("\n[OK] Connection successful.")
            return 0
        print("\n[FAIL] Health check returned False.")
        return 1
    except Exception as e:
        print(f"\n[FAIL] {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
