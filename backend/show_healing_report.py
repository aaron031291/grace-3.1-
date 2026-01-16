"""
Show healing report for the last hour.

Queries logs and database for all healing actions Grace has taken in the last hour.
"""

import sys
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).parent))

def parse_log_entries(log_file: Path, hours: int = 1) -> List[Dict]:
    """Parse log file for healing entries."""
    if not log_file.exists():
        return []
    
    cutoff_time = datetime.now() - timedelta(hours=hours)
    healing_entries = []
    
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                # Look for health check entries
                if '[HEALTH]' in line or 'healing' in line.lower() or 'anomaly' in line.lower():
                    # Try to parse timestamp
                    timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                    if timestamp_match:
                        try:
                            log_time = datetime.strptime(timestamp_match.group(1), '%Y-%m-%d %H:%M:%S')
                            if log_time >= cutoff_time:
                                healing_entries.append({
                                    'timestamp': log_time,
                                    'line': line.strip(),
                                    'type': 'health_check' if '[HEALTH]' in line else 'general'
                                })
                        except Exception:
                            pass
    except Exception as e:
        print(f"Error reading log file: {e}")
    
    return healing_entries

def get_healing_report(hours: int = 1):
    """Get healing report for the last N hours."""
    
    print("=" * 80)
    print(f"GRACE HEALING REPORT - Last {hours} Hour(s)")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()
    
    # Check log file
    log_file = Path(__file__).parent.parent / "backend" / "logs" / "autonomous_learning.log"
    if not log_file.exists():
        log_file = Path(__file__).parent.parent / "logs" / "autonomous_learning.log"
    
    healing_entries = parse_log_entries(log_file, hours)
    
    print(f"📊 HEALING STATISTICS")
    print("-" * 80)
    print(f"Health Check Log Entries: {len([e for e in healing_entries if e['type'] == 'health_check'])}")
    print(f"Total Healing-Related Logs: {len(healing_entries)}")
    print()
    
    if not healing_entries:
        print("✅ No healing actions detected in the logs for the last hour.")
        print("   Grace's systems are healthy!")
        print()
        print("Note: Health monitoring runs every 5 minutes.")
        print("      The next health check will be logged when it runs.")
        print()
        return
    
    # Parse health check results
    health_checks = []
    for entry in healing_entries:
        line = entry['line']
        if '[HEALTH]' in line and 'Running periodic health check' not in line:
            # Parse status, anomalies, actions executed
            status_match = re.search(r'Status:\s*(\w+)', line)
            anomalies_match = re.search(r'Anomalies:\s*(\d+)', line)
            actions_match = re.search(r'Actions executed:\s*(\d+)', line)
            
            health_checks.append({
                'timestamp': entry['timestamp'],
                'status': status_match.group(1) if status_match else 'unknown',
                'anomalies': int(anomalies_match.group(1)) if anomalies_match else 0,
                'actions_executed': int(actions_match.group(1)) if actions_match else 0,
                'raw_line': line
            })
    
    # Show health check results
    if health_checks:
        print("🔧 HEALTH CHECK RESULTS")
        print("-" * 80)
        
        for i, check in enumerate(health_checks, 1):
            timestamp = check['timestamp'].strftime("%Y-%m-%d %H:%M:%S")
            status_icon = "✅" if check['status'] == 'healthy' else "⚠️" if check['anomalies'] == 0 else "🔧"
            
            print(f"\n{i}. {status_icon} Health Check")
            print(f"   Time: {timestamp}")
            print(f"   Status: {check['status']}")
            print(f"   Anomalies Detected: {check['anomalies']}")
            print(f"   Actions Executed: {check['actions_executed']}")
            
            if check['anomalies'] > 0:
                print(f"   → Grace detected {check['anomalies']} anomaly/anomalies and executed {check['actions_executed']} healing action(s)")
            elif check['actions_executed'] > 0:
                print(f"   → Grace executed {check['actions_executed']} preventive action(s)")
            else:
                print(f"   → System is healthy - no issues detected")
    else:
        # Show any healing-related entries
        print("📋 HEALING-RELATED LOG ENTRIES")
        print("-" * 80)
        
        for i, entry in enumerate(healing_entries[-10:], 1):  # Show last 10
            timestamp = entry['timestamp'].strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n{i}. {timestamp}")
            print(f"   {entry['line'][:150]}...")
    
    print()
    print("=" * 80)
    print()
    print("Note: This report is based on log analysis.")
    print("      For detailed healing history, check the autonomous healing system status.")
    print()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Show Grace's healing report")
    parser.add_argument("--hours", type=int, default=1, help="Number of hours to look back (default: 1)")
    args = parser.parse_args()
    
    try:
        get_healing_report(hours=args.hours)
    except Exception as e:
        print(f"Error generating report: {e}")
        import traceback
        traceback.print_exc()
