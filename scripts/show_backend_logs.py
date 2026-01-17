#!/usr/bin/env python3
"""Quick script to show backend logs from SQLite database."""
import sqlite3
import sys
from pathlib import Path

db_path = Path("logs/launcher_log.db")
if not db_path.exists():
    print(f"ERROR: Database not found: {db_path}")
    sys.exit(1)

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# Get backend logs
print("\n" + "="*80)
print("BACKEND LOGS (Last 150 entries)")
print("="*80 + "\n")

cursor.execute("""
    SELECT timestamp, level, message, source 
    FROM launcher_log 
    WHERE source LIKE 'backend-%' 
    ORDER BY timestamp DESC 
    LIMIT 150
""")

rows = cursor.fetchall()

for timestamp, level, message, source in reversed(rows):
    ts = timestamp[:19] if len(timestamp) > 19 else timestamp
    # Remove Unicode characters that cause issues
    msg = message.encode('ascii', 'replace').decode('ascii')
    print(f"{ts} [{level:>7}] {msg}")

# Get errors and warnings
print("\n" + "="*80)
print("ERRORS AND WARNINGS (Last 50)")
print("="*80 + "\n")

cursor.execute("""
    SELECT timestamp, level, message 
    FROM launcher_log 
    WHERE (level = 'error' OR level = 'warning' OR message LIKE '%degraded%' OR message LIKE '%unhealthy%')
    ORDER BY timestamp DESC 
    LIMIT 50
""")

rows = cursor.fetchall()

for timestamp, level, message in rows:
    ts = timestamp[:19] if len(timestamp) > 19 else timestamp
    msg = message.encode('ascii', 'replace').decode('ascii')
    print(f"{ts} [{level:>7}] {msg}")

conn.close()
print("\n" + "="*80 + "\n")
