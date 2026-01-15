"""
Show Grace's Recent Activity Logs

This script shows Grace's recent self-healing activity from the logs.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

print("=" * 80)
print("GRACE'S RECENT SELF-HEALING ACTIVITY")
print("=" * 80)
print()

def show_grace_logs():
    """Show Grace's recent activity from logs."""
    
    log_file = Path("logs/grace_self_healing_background.log")
    
    if not log_file.exists():
        print(f"[ERROR] Log file not found: {log_file}")
        return
    
    print(f"Reading log file: {log_file}")
    print()
    
    # Read last 300 lines
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            recent_lines = lines[-300:] if len(lines) > 300 else lines
        
        # Filter for important events
        important_patterns = [
            'HEALING CYCLE',
            'Issue',
            'Fix',
            'FIXED',
            'ERROR',
            'detect',
            'healing',
            'Diagnostic',
            'Converted error',
            'Processing',
            'Attempting to fix'
        ]
        
        print("=" * 80)
        print("KEY EVENTS (Last 300 lines filtered)")
        print("=" * 80)
        print()
        
        for line in recent_lines:
            line_lower = line.lower()
            if any(pattern.lower() in line_lower for pattern in important_patterns):
                # Clean up the line
                clean_line = line.strip()
                if clean_line:
                    # Extract timestamp if present
                    if ' - ' in clean_line:
                        parts = clean_line.split(' - ', 2)
                        if len(parts) >= 3:
                            timestamp = parts[0]
                            logger = parts[1]
                            message = parts[2]
                            print(f"[{timestamp}] {message}")
                        else:
                            print(clean_line)
                    else:
                        print(clean_line)
        
        print()
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print()
        
        # Count events
        issues_detected = sum(1 for line in recent_lines if 'Converted error to issue' in line or 'Issues list now has' in line)
        fixes_attempted = sum(1 for line in recent_lines if 'Attempting to fix' in line or 'Detected issue' in line)
        cycles = sum(1 for line in recent_lines if 'HEALING CYCLE' in line or 'SELF-HEALING CYCLE' in line)
        
        print(f"Total Healing Cycles: {cycles}")
        print(f"Issues Detected: {issues_detected}")
        print(f"Fix Attempts: {fixes_attempted}")
        print()
        print("Grace is actively monitoring and attempting to fix issues!")
        print()
        
    except Exception as e:
        print(f"[ERROR] Failed to read log file: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    show_grace_logs()
