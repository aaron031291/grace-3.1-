#!/usr/bin/env python3
"""
View Recent Database Errors

Quick script to view the last N lines of database error logs.
Usage: python view_db_errors.py [--lines N]
"""

import sys
from pathlib import Path
import argparse

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from settings import KNOWLEDGE_BASE_PATH


def view_db_errors(num_lines=100):
    """View recent database errors from log file."""
    log_file = Path(KNOWLEDGE_BASE_PATH).parent / "backend" / "logs" / "database_errors.log"
    
    if not log_file.exists():
        print(f"No error log file found at: {log_file}")
        print("No database errors have been recorded yet.")
        return
    
    print(f"Reading last {num_lines} lines from: {log_file}")
    print("=" * 80)
    
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            recent_lines = lines[-num_lines:] if len(lines) > num_lines else lines
        
        print("".join(recent_lines))
        
        print("=" * 80)
        print(f"Total lines in log: {len(lines)}")
        print(f"Displayed: {len(recent_lines)}")
        
    except Exception as e:
        print(f"Error reading log file: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="View recent database errors")
    parser.add_argument(
        "--lines", "-n",
        type=int,
        default=100,
        help="Number of lines to display (default: 100)"
    )
    
    args = parser.parse_args()
    view_db_errors(args.lines)
