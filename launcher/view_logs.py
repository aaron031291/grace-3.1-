#!/usr/bin/env python3
"""
View Launcher Logs
==================
Utility script to view recent launcher logs from SQLite database.
"""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime


def view_logs(db_path: Path, limit: int = 30):
    """
    View recent launcher logs.
    
    Args:
        db_path: Path to launcher_log.db
        limit: Number of recent entries to show
    """
    db_path = Path(db_path)
    
    if not db_path.exists():
        print(f"Log database not found at: {db_path}")
        print("The launcher needs to run at least once to create the database.")
        return
    
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT genesis_key, timestamp, level, message
            FROM launcher_log
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            print("No log entries found.")
            return
        
        print(f"\n{'='*80}")
        print(f"Last {len(rows)} launcher log entries")
        print(f"{'='*80}\n")
        
        for row in reversed(rows):  # Show oldest first
            timestamp = row['timestamp']
            level = row['level'].upper()
            message = row['message']
            genesis_key = row['genesis_key']
            
            # Format timestamp for display
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                time_str = timestamp
            
            # Color code by level (simple terminal colors)
            level_colors = {
                'ERROR': '\033[91m',  # Red
                'WARNING': '\033[93m',  # Yellow
                'INFO': '\033[92m',  # Green
                'DEBUG': '\033[94m',  # Blue
            }
            reset = '\033[0m'
            color = level_colors.get(level, '')
            
            print(f"{time_str} [{color}{level:8}{reset}] {message}")
            if genesis_key:
                print(f"  Genesis Key: {genesis_key}")
            print()
        
        print(f"{'='*80}\n")
        
    except Exception as e:
        print(f"Error reading logs: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="View launcher logs from SQLite database")
    parser.add_argument(
        '-n', '--lines',
        type=int,
        default=30,
        help='Number of recent log lines to show (default: 30)'
    )
    parser.add_argument(
        '--db-path',
        type=str,
        help='Path to launcher_log.db (default: logs/launcher_log.db)'
    )
    
    args = parser.parse_args()
    
    # Determine db path
    if args.db_path:
        db_path = Path(args.db_path)
    else:
        # Default to logs/launcher_log.db in project root
        script_dir = Path(__file__).parent
        root_path = script_dir.parent
        db_path = root_path / "logs" / "launcher_log.db"
    
    view_logs(db_path, limit=args.lines)


if __name__ == "__main__":
    main()
