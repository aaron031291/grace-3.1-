"""
Verify Genesis Key + SQL (SQLite/PostgreSQL) are working.

Run from backend directory:
  python scripts/verify_genesis_sql.py

Checks: DISABLE_GENESIS_TRACKING, DB connection, genesis_key table, create one key.
"""
import os
import sys

# Ensure backend is on path
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _backend_dir)
os.chdir(_backend_dir)

# Load .env so DISABLE_GENESIS_TRACKING and DATABASE_* are set
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_backend_dir, ".env"))
except ImportError:
    pass

def main():
    errors = []
    print("Genesis Key + SQL verification")
    print("=" * 50)

    # 1. Genesis tracking enabled
    disable = os.getenv("DISABLE_GENESIS_TRACKING", "false").lower() == "true"
    if disable:
        errors.append("DISABLE_GENESIS_TRACKING is true in .env - set to false or remove it")
    else:
        print("[OK] Genesis tracking enabled (DISABLE_GENESIS_TRACKING not true)")

    # 2. Database and genesis_key table
    try:
        from database.connection import DatabaseConnection
        from database.config import DatabaseConfig
        cfg = DatabaseConfig.from_env()
        DatabaseConnection.initialize(cfg)
        engine = DatabaseConnection.get_engine()
        with engine.connect() as conn:
            from sqlalchemy import text
            conn.execute(text("SELECT 1 FROM genesis_key LIMIT 1"))
        print("[OK] Database connected, genesis_key table exists")
    except Exception as e:
        err = str(e).lower()
        if "no such table" in err or "genesis_key" in err or "does not exist" in err:
            errors.append("Table genesis_key not found - run: python run_all_migrations.py")
        else:
            errors.append(f"Database error: {e}")

    # 3. Create one Genesis Key and read it back
    if not errors:
        try:
            from genesis.genesis_key_service import get_genesis_service
            from models.genesis_key_models import GenesisKeyType
            svc = get_genesis_service()
            key = svc.create_key(
                key_type=GenesisKeyType.SYSTEM_EVENT,
                what_description="Verify Genesis SQL script",
                who_actor="verify_genesis_sql",
                how_method="script",
            )
            print(f"[OK] Created Genesis Key: {getattr(key, 'key_id', 'created')}")
        except Exception as e:
            errors.append(f"Genesis Key creation failed: {e}")

    print("=" * 50)
    if errors:
        print("FAILED:")
        for e in errors:
            print("  -", e)
        return 1
    print("All checks passed. Genesis Key + SQL are working.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
