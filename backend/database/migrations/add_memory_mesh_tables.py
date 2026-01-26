"""
Database Migration: Add Memory Mesh Tables (Simplified)

Creates the missing tables for Episodic and Procedural Memory using direct SQL.
"""
import sqlite3
from pathlib import Path


def run_migration():
    """Create episodes and procedures tables using direct SQL."""
    print("="*60)
    print("Memory Mesh Tables Migration")
    print("="*60)
    
    # Database path
    db_path = Path(__file__).parent.parent.parent / "data" / "grace.db"
    
    if not db_path.exists():
        print(f"\n❌ Database not found: {db_path}")
        return False
    
    print(f"\n✓ Found database: {db_path}")
    
    # Connect to database
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Create episodes table
    print("\nCreating 'episodes' table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS episodes (
            id TEXT PRIMARY KEY,
            problem TEXT NOT NULL,
            action TEXT NOT NULL,
            outcome TEXT NOT NULL,
            predicted_outcome TEXT,
            prediction_error REAL DEFAULT 0.0,
            trust_score REAL DEFAULT 0.5 NOT NULL,
            source TEXT NOT NULL,
            genesis_key_id TEXT,
            decision_id TEXT,
            timestamp DATETIME NOT NULL,
            embedding TEXT,
            episode_metadata TEXT,
            created_at DATETIME,
            updated_at DATETIME
        )
    """)
    print("  ✓ Created 'episodes' table")
    
    # Create procedures table
    print("\nCreating 'procedures' table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS procedures (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            goal TEXT NOT NULL,
            procedure_type TEXT NOT NULL,
            steps TEXT NOT NULL,
            preconditions TEXT NOT NULL,
            trust_score REAL DEFAULT 0.5 NOT NULL,
            success_rate REAL DEFAULT 0.0 NOT NULL,
            usage_count INTEGER DEFAULT 0,
            success_count INTEGER DEFAULT 0,
            supporting_examples TEXT,
            learned_from_episode_id TEXT,
            embedding TEXT,
            procedure_metadata TEXT,
            created_at DATETIME,
            updated_at DATETIME
        )
    """)
    print("  ✓ Created 'procedures' table")
    
    # Commit changes
    conn.commit()
    
    # Verify tables exist
    print("\nVerifying tables...")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('episodes', 'procedures')")
    tables = cursor.fetchall()
    
    if len(tables) == 2:
        print("  ✅ Both tables verified!")
        
        # Show table schemas
        for table_name in ['episodes', 'procedures']:
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            print(f"\n  {table_name} ({len(columns)} columns):")
            for col in columns[:5]:  # Show first 5 columns
                print(f"    - {col[1]} ({col[2]})")
            if len(columns) > 5:
                print(f"    ... and {len(columns) - 5} more")
    else:
        print("  ❌ Table verification failed!")
        conn.close()
        return False
    
    # Check row counts
    print("\nChecking row counts...")
    for table_name in ['episodes', 'procedures']:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"  {table_name}: {count} rows")
    
    conn.close()
    
    print("\n" + "="*60)
    print("✅ Migration completed successfully!")
    print("="*60)
    
    return True


if __name__ == "__main__":
    try:
        success = run_migration()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
