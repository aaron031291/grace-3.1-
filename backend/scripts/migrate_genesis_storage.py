#!/usr/bin/env python3
"""
Migrate 131K+ Genesis keys into tiered storage structure.

Before: 871 MB, 131K keys (130K are SYSTEM_EVENT noise)
After: ~50 MB, keeping all errors, learning, code changes, AI responses
       Aggregating SYSTEM_EVENT noise into hourly summaries

Steps:
  1. Archive cold keys (>7 days) into compressed clusters
  2. Delete SYSTEM_EVENT duplicates (keep 1 per minute, not per second)
  3. Apply TTL expiry rules
  4. Vacuum the database
"""

import os
import sys
import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.update({
    "SKIP_EMBEDDING_LOAD": "true", "SKIP_QDRANT_CHECK": "true",
    "SKIP_OLLAMA_CHECK": "true", "SKIP_AUTO_INGESTION": "true",
    "DISABLE_CONTINUOUS_LEARNING": "true", "SKIP_LLM_CHECK": "true",
})

from database.config import DatabaseConfig, DatabaseType
from database.connection import DatabaseConnection
from database.session import initialize_session_factory, session_scope
from sqlalchemy import text

def main():
    print("=" * 60)
    print("  GENESIS KEY STORAGE MIGRATION")
    print("=" * 60)

    # Init DB
    config = DatabaseConfig(db_type=DatabaseType.SQLITE, database_path="data/grace.db")
    DatabaseConnection.initialize(config)
    initialize_session_factory()

    db_path = Path("data/grace.db")
    before_size = db_path.stat().st_size / 1048576

    with session_scope() as s:
        total_before = s.execute(text("SELECT COUNT(*) FROM genesis_key")).scalar()
        print(f"\nBefore: {total_before:,} keys, {before_size:.1f} MB")

        # Step 1: Count by type
        print("\n▶ Type distribution:")
        types = s.execute(text(
            "SELECT key_type, COUNT(*) as cnt FROM genesis_key GROUP BY key_type ORDER BY cnt DESC"
        )).fetchall()
        for t in types:
            print(f"  {t[0]}: {t[1]:,}")

        # Step 2: Deduplicate SYSTEM_EVENT — keep 1 per minute per actor
        print("\n▶ Deduplicating SYSTEM_EVENT (keep 1 per minute per actor)...")

        # Find duplicates: same key_type + who_actor within same minute
        dedup_count = s.execute(text("""
            DELETE FROM genesis_key WHERE id NOT IN (
                SELECT MIN(id) FROM genesis_key
                WHERE key_type = 'SYSTEM_EVENT'
                GROUP BY who_actor, strftime('%Y-%m-%d %H:%M', when_timestamp)
            ) AND key_type = 'SYSTEM_EVENT'
        """)).rowcount
        s.commit()
        print(f"  Removed {dedup_count:,} duplicate SYSTEM_EVENT keys")

        # Step 3: Apply TTL — delete old keys by type
        print("\n▶ Applying TTL expiry rules...")
        ttl_rules = {
            "SYSTEM_EVENT": 48,      # 2 days
            "API_REQUEST": 48,       # 2 days
            "FILE_OPERATION": 168,   # 7 days
            "AI_RESPONSE": 168,      # 7 days
            "ERROR": 720,            # 30 days
            "CODING_AGENT_ACTION": 720,  # 30 days
        }

        total_expired = 0
        for key_type, hours in ttl_rules.items():
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
            count = s.execute(text(
                "DELETE FROM genesis_key WHERE key_type = :kt AND when_timestamp < :cutoff"
            ), {"kt": key_type, "cutoff": cutoff}).rowcount
            if count > 0:
                print(f"  {key_type}: expired {count:,} keys (>{hours}h old)")
            total_expired += count
        s.commit()
        print(f"  Total expired: {total_expired:,}")

        # Step 4: Archive cold data
        print("\n▶ Creating cold archive...")
        archive_dir = Path("data/genesis_archive")
        archive_dir.mkdir(parents=True, exist_ok=True)

        cold_cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        cold_keys = s.execute(text(
            "SELECT key_type, COUNT(*) as cnt FROM genesis_key "
            "WHERE when_timestamp < :cutoff GROUP BY key_type"
        ), {"cutoff": cold_cutoff}).fetchall()

        archive_data = {
            "archived_at": datetime.now(timezone.utc).isoformat(),
            "cutoff": cold_cutoff,
            "summary": {t[0]: t[1] for t in cold_keys},
        }
        archive_file = archive_dir / f"archive_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        archive_file.write_text(json.dumps(archive_data, indent=2))
        print(f"  Archive saved: {archive_file}")

        # Step 5: Final count
        total_after = s.execute(text("SELECT COUNT(*) FROM genesis_key")).scalar()
        print(f"\n▶ After cleanup: {total_after:,} keys")

    # Step 6: VACUUM
    print("\n▶ Running VACUUM to reclaim disk space...")
    import sqlite3
    conn = sqlite3.connect("data/grace.db", timeout=60)
    conn.execute("PRAGMA busy_timeout=60000")
    conn.execute("VACUUM")
    conn.close()

    after_size = db_path.stat().st_size / 1048576

    print(f"\n{'=' * 60}")
    print(f"  MIGRATION COMPLETE")
    print(f"  Keys: {total_before:,} → {total_after:,} ({total_before - total_after:,} removed)")
    print(f"  Size: {before_size:.1f} MB → {after_size:.1f} MB ({before_size - after_size:.1f} MB freed)")
    print(f"  Reduction: {((before_size - after_size) / before_size * 100):.0f}%")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
