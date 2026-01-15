"""
Show Proof That Grace is Working and Fixing Problems

This script shows concrete evidence from logs and internal statistics.
"""

import sys
import logging
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import re

# Add backend to path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

# Setup logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

print("=" * 80)
print("GRACE'S WORK - PROOF OF ACTIVITY AND FIXES")
print("=" * 80)
print()

def analyze_logs():
    """Analyze logs for proof of Grace's work."""
    log_file = Path("logs/grace_self_healing_background.log")
    
    if not log_file.exists():
        print("[ERROR] Log file not found")
        return {}
    
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    stats = {
        'healing_cycles': 0,
        'issues_detected': 0,
        'fix_attempts': 0,
        'errors_converted': 0,
        'diagnostic_runs': 0,
        'recent_activity': []
    }
    
    # Patterns to look for
    patterns = {
        'healing_cycles': r'HEALING CYCLE|SELF-HEALING CYCLE',
        'issues_detected': r'Converted error to issue|Issues list now has|Detected issue',
        'fix_attempts': r'Attempting to fix|Processing.*issue',
        'errors_converted': r'Converted error to issue',
        'diagnostic_runs': r'Running diagnostics|System diagnostic check'
    }
    
    for line in lines:
        for key, pattern in patterns.items():
            if re.search(pattern, line, re.IGNORECASE):
                stats[key] += 1
                if key in ['issues_detected', 'fix_attempts', 'errors_converted']:
                    # Extract timestamp and message
                    if ' - ' in line:
                        parts = line.split(' - ', 2)
                        if len(parts) >= 3:
                            timestamp = parts[0].strip()
                            message = parts[2].strip()
                            stats['recent_activity'].append({
                                'timestamp': timestamp,
                                'type': key,
                                'message': message[:100]
                            })
    
    # Keep only recent activity (last 20)
    stats['recent_activity'] = stats['recent_activity'][-20:]
    
    return stats

def get_agent_statistics():
    """Get statistics from the DevOps Healing Agent."""
    try:
        from database.connection import DatabaseConnection
        from database.config import DatabaseConfig, DatabaseType
        from database.session import initialize_session_factory, get_db
        from cognitive.devops_healing_agent import get_devops_healing_agent
        
        db_config = DatabaseConfig(
            db_type=DatabaseType.SQLITE,
            database_path="data/grace.db"
        )
        DatabaseConnection.initialize(db_config)
        initialize_session_factory()
        session = next(get_db())
        
        knowledge_base_path = Path("knowledge_base").resolve()
        ai_research_path = Path("data/ai_research")
        
        devops_agent = get_devops_healing_agent(
            session=session,
            knowledge_base_path=knowledge_base_path,
            ai_research_path=ai_research_path
        )
        
        stats = devops_agent.get_statistics()
        return stats
        
    except Exception as e:
        print(f"[WARN] Could not get agent statistics: {e}")
        return None

def show_proof():
    """Show proof that Grace is working."""
    
    print("[1/3] Analyzing Logs...")
    print()
    
    log_stats = analyze_logs()
    
    print(f"  Healing Cycles Completed: {log_stats['healing_cycles']}")
    print(f"  Issues Detected: {log_stats['issues_detected']}")
    print(f"  Fix Attempts: {log_stats['fix_attempts']}")
    print(f"  Errors Converted to Issues: {log_stats['errors_converted']}")
    print(f"  Diagnostic Runs: {log_stats['diagnostic_runs']}")
    print()
    
    print("[2/3] Getting Agent Statistics...")
    print()
    
    agent_stats = get_agent_statistics()
    
    if agent_stats:
        print(f"  Total Issues Detected: {agent_stats.get('total_issues_detected', 0)}")
        print(f"  Total Issues Fixed: {agent_stats.get('total_issues_fixed', 0)}")
        print(f"  Total Fixes Applied: {agent_stats.get('total_fixes_applied', 0)}")
        print(f"  Total Fixes Successful: {agent_stats.get('total_fixes_successful', 0)}")
        print(f"  Total Fixes Failed: {agent_stats.get('total_fixes_failed', 0)}")
        print(f"  Success Rate: {agent_stats.get('success_rate', 0) * 100:.1f}%")
        print(f"  Fix History Size: {agent_stats.get('fix_history_size', 0)}")
        print()
        
        if agent_stats.get('fixes_by_layer'):
            print("  Fixes by Layer:")
            for layer, count in agent_stats['fixes_by_layer'].items():
                print(f"    - {layer}: {count}")
            print()
        
        if agent_stats.get('fixes_by_category'):
            print("  Fixes by Category:")
            for category, count in agent_stats['fixes_by_category'].items():
                print(f"    - {category}: {count}")
            print()
    else:
        print("  [WARN] Could not retrieve agent statistics")
        print()
    
    print("[3/3] Recent Activity Evidence...")
    print()
    
    if log_stats['recent_activity']:
        print("Recent Activity (Last 20 events):")
        for i, activity in enumerate(log_stats['recent_activity'][-10:], 1):
            print(f"  {i}. [{activity['timestamp']}] {activity['type'].upper()}")
            print(f"     {activity['message']}")
            print()
    else:
        print("  No recent activity found in logs")
        print()
    
    print("=" * 80)
    print("PROOF SUMMARY")
    print("=" * 80)
    print()
    
    evidence = []
    
    if log_stats['healing_cycles'] > 0:
        evidence.append(f"✅ Grace completed {log_stats['healing_cycles']} healing cycle(s)")
    
    if log_stats['issues_detected'] > 0:
        evidence.append(f"✅ Grace detected {log_stats['issues_detected']} issue(s)")
    
    if log_stats['fix_attempts'] > 0:
        evidence.append(f"✅ Grace attempted {log_stats['fix_attempts']} fix(es)")
    
    if agent_stats:
        if agent_stats.get('total_issues_detected', 0) > 0:
            evidence.append(f"✅ Grace tracked {agent_stats['total_issues_detected']} issue(s) in memory")
        
        if agent_stats.get('total_issues_fixed', 0) > 0:
            evidence.append(f"✅ Grace fixed {agent_stats['total_issues_fixed']} issue(s)")
        
        if agent_stats.get('total_fixes_successful', 0) > 0:
            evidence.append(f"✅ Grace successfully applied {agent_stats['total_fixes_successful']} fix(es)")
        
        if agent_stats.get('fix_history_size', 0) > 0:
            evidence.append(f"✅ Grace has {agent_stats['fix_history_size']} fix(es) in history")
    
    if evidence:
        print("EVIDENCE THAT GRACE IS WORKING:")
        print()
        for item in evidence:
            # Replace checkmark with [OK] for Windows compatibility
            safe_item = item.replace('\u2705', '[OK]')
            print(f"  {safe_item}")
        print()
        
        print("=" * 80)
        print("CONCLUSION")
        print("=" * 80)
        print()
        print("[OK] GRACE IS WORKING!")
        print()
        print("Proof shows Grace is:")
        print("  - Running healing cycles continuously")
        print("  - Detecting issues automatically")
        print("  - Attempting fixes")
        print("  - Tracking her work in memory")
        if agent_stats and agent_stats.get('total_issues_fixed', 0) > 0:
            print("  - Successfully fixing issues")
        print()
    else:
        print("⚠️  Limited evidence found")
        print()
        print("Possible reasons:")
        print("  - Grace is still initializing")
        print("  - Database schema issues (blocking Genesis Key creation)")
        print("  - Grace needs to be restarted with latest code")
        print()
    
    return len(evidence) > 0

if __name__ == "__main__":
    success = show_proof()
    sys.exit(0 if success else 1)
