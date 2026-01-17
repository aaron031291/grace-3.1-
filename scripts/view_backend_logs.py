#!/usr/bin/env python3
"""
View Backend Logs
=================
View recent backend logs from SQLite database or directly from process.
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime
import argparse


def view_sqlite_logs(db_path: Path, limit: int = 100, stream: str = None):
    """View logs from SQLite database."""
    if not db_path.exists():
        print(f"[ERROR] Log database not found: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Build query
        if stream:
            query = """
                SELECT timestamp, level, message, source
                FROM launcher_log
                WHERE source = ? OR message LIKE ?
                ORDER BY timestamp DESC
                LIMIT ?
            """
            cursor.execute(query, (stream, f"%{stream}%", limit))
        else:
            query = """
                SELECT timestamp, level, message, source
                FROM launcher_log
                ORDER BY timestamp DESC
                LIMIT ?
            """
            cursor.execute(query, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            print(f"[INFO] No logs found in database")
            return
        
        print(f"\n{'='*80}")
        print(f"Backend Logs (Last {len(rows)} entries)")
        print(f"{'='*80}\n")
        
        # Print in reverse order (oldest first)
        for timestamp, level, message, source in reversed(rows):
            # Format timestamp
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                ts_str = dt.strftime('%H:%M:%S')
            except:
                ts_str = timestamp[:8] if len(timestamp) > 8 else timestamp
            
            # Color code by level
            level_color = {
                'error': '\033[91m',  # Red
                'warning': '\033[93m',  # Yellow
                'info': '\033[92m',  # Green
                'debug': '\033[96m',  # Cyan
            }
            reset = '\033[0m'
            color = level_color.get(level.lower(), '')
            
            # Print log entry
            source_tag = f"[{source}]" if source else ""
            print(f"{ts_str} {color}[{level.upper()}]{reset} {source_tag} {message}")
        
        print(f"\n{'='*80}\n")
        
    except Exception as e:
        print(f"[ERROR] Failed to read logs: {e}")
        import traceback
        traceback.print_exc()


def view_backend_stderr_stdout(db_path: Path, limit: int = 100):
    """View backend stderr and stdout from captured streams."""
    if not db_path.exists():
        print(f"[ERROR] Log database not found: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check if stream_log table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='stream_log'
        """)
        
        if not cursor.fetchone():
            print("[INFO] Stream logs not available (stream_log table not found)")
            conn.close()
            return
        
        # Get backend stream logs
        query = """
            SELECT timestamp, stream_name, line
            FROM stream_log
            WHERE stream_name LIKE 'backend-%'
            ORDER BY timestamp DESC
            LIMIT ?
        """
        cursor.execute(query, (limit,))
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            print("[INFO] No backend stream logs found")
            return
        
        print(f"\n{'='*80}")
        print(f"Backend Process Output (Last {len(rows)} lines)")
        print(f"{'='*80}\n")
        
        # Group by stream
        stdout_lines = []
        stderr_lines = []
        
        for timestamp, stream_name, line in rows:
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                ts_str = dt.strftime('%H:%M:%S')
            except:
                ts_str = timestamp[:8] if len(timestamp) > 8 else timestamp
            
            if 'stderr' in stream_name:
                stderr_lines.append((ts_str, line))
            else:
                stdout_lines.append((ts_str, line))
        
        # Print stdout first
        if stdout_lines:
            print("[STDOUT]")
            print("-" * 80)
            for ts, line in reversed(stdout_lines):
                print(f"{ts} {line}")
        
        # Print stderr
        if stderr_lines:
            print("\n[STDERR]")
            print("-" * 80)
            for ts, line in reversed(stderr_lines):
                print(f"\033[91m{ts} {line}\033[0m")  # Red for stderr
        
        print(f"\n{'='*80}\n")
        
    except Exception as e:
        print(f"[ERROR] Failed to read stream logs: {e}")
        import traceback
        traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(description="View backend logs")
    parser.add_argument(
        "-n", "--lines", type=int, default=100,
        help="Number of log lines to show (default: 100)"
    )
    parser.add_argument(
        "-f", "--follow", action="store_true",
        help="Follow logs (continuously update)"
    )
    parser.add_argument(
        "-s", "--stream", choices=["backend-stdout", "backend-stderr", "launcher"],
        help="Filter by stream type"
    )
    parser.add_argument(
        "--db", type=str,
        help="Path to launcher log database (default: auto-detect)"
    )
    
    args = parser.parse_args()
    
    # Find database
    if args.db:
        db_path = Path(args.db)
    else:
        # Auto-detect: check common locations
        possible_paths = [
            Path("logs/launcher_log.db"),
            Path("launcher/logs/launcher_log.db"),
            Path("backend/logs/launcher_log.db"),
        ]
        
        db_path = None
        for path in possible_paths:
            if path.exists():
                db_path = path
                break
        
        if not db_path:
            print("[ERROR] Could not find launcher log database")
            print("[INFO] Searched in:")
            for path in possible_paths:
                print(f"  - {path.absolute()}")
            print("\n[INFO] Specify database path with --db option")
            sys.exit(1)
    
    print(f"[INFO] Reading logs from: {db_path}")
    
    # View stream logs (backend stdout/stderr)
    view_backend_stderr_stdout(db_path, limit=args.lines)
    
    # View general logs
    view_sqlite_logs(db_path, limit=args.lines, stream=args.stream)
    
    if args.follow:
        print("[INFO] Follow mode not yet implemented")
        print("[INFO] Use: watch -n 1 python scripts/view_backend_logs.py -n 50")


if __name__ == "__main__":
    main()
