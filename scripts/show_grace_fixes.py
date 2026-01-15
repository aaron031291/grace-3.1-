"""
Show what Grace has fixed.

This script queries the database to show all fixes that Grace has applied.
"""

import sys
from pathlib import Path
import sqlite3

# Add backend to path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

print("=" * 80)
print("GRACE FIXES REPORT")
print("=" * 80)
print()

# Connect directly to database (relative to repo root)
repo_root = Path(__file__).parent.parent
db_path = repo_root / "data" / "grace.db"
if not db_path.exists():
    print("Database not found. Grace hasn't run yet or database is in a different location.")
    print(f"Expected location: {db_path.absolute()}")
    exit(0)

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# Check if table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='genesis_key'")
if not cursor.fetchone():
    print("Genesis Key table not found. Database may need initialization.")
    conn.close()
    exit(0)

# Get all fixes using raw SQL (avoiding is_broken column if it doesn't exist)
try:
    cursor.execute("""
        SELECT key_id, what_description, status, when_timestamp, file_path, 
               where_location, why_reason, context_data
        FROM genesis_key 
        WHERE key_type = 'FIX'
        ORDER BY when_timestamp DESC
        LIMIT 50
    """)
    fixes = cursor.fetchall()
except sqlite3.OperationalError as e:
    print(f"Error querying database: {e}")
    conn.close()
    exit(1)

print(f"Total Fixes Found: {len(fixes)}")
print()

# Get statistics
cursor.execute("""
    SELECT status, COUNT(*) 
    FROM genesis_key 
    WHERE key_type = 'FIX'
    GROUP BY status
""")
status_counts = dict(cursor.fetchall())

print("Fix Statistics:")
for status, count in status_counts.items():
    icon = "[OK]" if status == "fixed" else "[ERROR]" if status == "error" else "[ROLLBACK]" if status == "rolled_back" else "[PENDING]"
    print(f"  {icon} {status.capitalize()}: {count}")
print()

# Show recent fixes
print("=" * 80)
print("RECENT FIXES (Last 20)")
print("=" * 80)
print()

if fixes:
    for i, fix in enumerate(fixes[:20], 1):
        key_id, what_desc, status, when_ts, file_path, where_loc, why_reason, context_data = fix
        
        status_icon = "[OK]" if status == "fixed" else "[ERROR]" if status == "error" else "[ROLLBACK]" if status == "rolled_back" else "[PENDING]"
        
        print(f"[{i}] {status_icon} {what_desc}")
        print(f"    Status: {status}")
        print(f"    When: {when_ts}")
        if file_path:
            print(f"    File: {file_path}")
        if where_loc:
            print(f"    Location: {where_loc}")
        if why_reason:
            print(f"    Reason: {why_reason}")
        print()
else:
    print("No fixes found yet.")
    print("Grace hasn't applied any fixes yet, or the database is empty.")
    print()

# Get recent issues detected
try:
    cursor.execute("""
        SELECT key_id, what_description, status, when_timestamp, file_path
        FROM genesis_key 
        WHERE key_type = 'ERROR'
        ORDER BY when_timestamp DESC
        LIMIT 10
    """)
    issues = cursor.fetchall()
    
    if issues:
        print("=" * 80)
        print("RECENT ISSUES DETECTED (Last 10)")
        print("=" * 80)
        print()
        
        for i, issue in enumerate(issues, 1):
            key_id, what_desc, status, when_ts, file_path = issue
            status_icon = "[OK]" if status == "fixed" else "[PENDING]"
            
            print(f"[{i}] {status_icon} {what_desc}")
            print(f"    Status: {status}")
            print(f"    When: {when_ts}")
            if file_path:
                print(f"    File: {file_path}")
            print()
except sqlite3.OperationalError:
    pass  # Column might not exist

conn.close()

print("=" * 80)
print("END OF REPORT")
print("=" * 80)
print()
print("Note: This shows fixes tracked in the Genesis Key system.")
print("For detailed logs, check: backend/logs/grace_self_healing.log")
