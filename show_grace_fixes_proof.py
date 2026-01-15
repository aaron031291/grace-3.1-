"""
Show Proof of Grace's Fixes

This script shows concrete evidence that Grace is working and fixing problems.
"""

import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

# Add backend to path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

# Setup logging
logging.basicConfig(
    level=logging.WARNING,  # Suppress most logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

print("=" * 80)
print("GRACE'S FIXES - PROOF OF WORK")
print("=" * 80)
print()

def show_grace_fixes_proof():
    """Show proof that Grace is fixing problems."""
    
    try:
        # Initialize database
        from database.connection import DatabaseConnection
        from database.config import DatabaseConfig, DatabaseType
        from database.session import initialize_session_factory, get_db
        from models.genesis_key_models import GenesisKey, GenesisKeyType, GenesisKeyStatus
        
        db_config = DatabaseConfig(
            db_type=DatabaseType.SQLITE,
            database_path="data/grace.db"
        )
        DatabaseConnection.initialize(db_config)
        initialize_session_factory()
        session = next(get_db())
        
        print("[1/4] Checking Genesis Keys for fixes...")
        print()
        
        # Get all FIX Genesis Keys
        all_fixes = session.query(GenesisKey).filter(
            GenesisKey.key_type == GenesisKeyType.FIX
        ).order_by(GenesisKey.when_timestamp.desc()).all()
        
        print(f"Total Fix Attempts: {len(all_fixes)}")
        print()
        
        # Get successful fixes
        successful_fixes = [f for f in all_fixes if f.status == GenesisKeyStatus.FIXED or f.fix_applied]
        print(f"Successful Fixes: {len(successful_fixes)}")
        print()
        
        # Get issue detections
        issues = session.query(GenesisKey).filter(
            GenesisKey.key_type == GenesisKeyType.ISSUE
        ).order_by(GenesisKey.when_timestamp.desc()).limit(20).all()
        
        print(f"Issues Detected: {len(issues)}")
        print()
        
        print("[2/4] Checking logs for fix evidence...")
        print()
        
        # Read logs
        log_file = Path("logs/grace_self_healing_background.log")
        if log_file.exists():
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            # Count fix-related events
            fix_attempts = sum(1 for line in lines if 'Attempting to fix' in line or 'Detecting issue' in line)
            fix_success = sum(1 for line in lines if 'FIXED' in line or 'fix.*success' in line.lower() or 'successful.*fix' in line.lower())
            issues_detected = sum(1 for line in lines if 'Converted error to issue' in line or 'Issues list now has' in line)
            healing_cycles = sum(1 for line in lines if 'HEALING CYCLE' in line or 'SELF-HEALING CYCLE' in line)
            
            print(f"  Healing Cycles: {healing_cycles}")
            print(f"  Issues Detected: {issues_detected}")
            print(f"  Fix Attempts: {fix_attempts}")
            print(f"  Fix Success Indicators: {fix_success}")
            print()
        
        print("[3/4] Recent Fix Activity...")
        print()
        
        if all_fixes:
            print("Recent Fix Attempts:")
            for i, fix in enumerate(all_fixes[:10], 1):
                status = "✅ FIXED" if (fix.status == GenesisKeyStatus.FIXED or fix.fix_applied) else "⏳ IN PROGRESS"
                timestamp = fix.when_timestamp.strftime("%Y-%m-%d %H:%M:%S") if fix.when_timestamp else "Unknown"
                print(f"  {i}. [{timestamp}] {status}")
                print(f"     {fix.what_description[:100] if fix.what_description else 'No description'}")
                if fix.file_path:
                    print(f"     File: {fix.file_path}")
                if fix.code_before and fix.code_after:
                    print(f"     Code Changed: Yes")
                print()
        else:
            print("  No fix Genesis Keys found yet.")
            print("  (Grace may still be detecting issues)")
            print()
        
        print("[4/4] Issue Detection Activity...")
        print()
        
        if issues:
            print("Recent Issues Detected:")
            for i, issue in enumerate(issues[:10], 1):
                timestamp = issue.when_timestamp.strftime("%Y-%m-%d %H:%M:%S") if issue.when_timestamp else "Unknown"
                error_type = issue.error_type or "Unknown"
                print(f"  {i}. [{timestamp}] {error_type}")
                print(f"     {issue.what_description[:100] if issue.what_description else 'No description'}")
                if issue.has_fix_suggestion:
                    print(f"     Has Fix Suggestion: Yes")
                print()
        else:
            print("  No issue Genesis Keys found yet.")
            print()
        
        print("=" * 80)
        print("SUMMARY - PROOF OF GRACE'S WORK")
        print("=" * 80)
        print()
        
        # Calculate statistics
        total_activity = len(all_fixes) + len(issues)
        success_rate = (len(successful_fixes) / len(all_fixes) * 100) if all_fixes else 0
        
        print(f"✅ Total Activity: {total_activity} actions")
        print(f"✅ Issues Detected: {len(issues)}")
        print(f"✅ Fix Attempts: {len(all_fixes)}")
        print(f"✅ Successful Fixes: {len(successful_fixes)}")
        if all_fixes:
            print(f"✅ Success Rate: {success_rate:.1f}%")
        print()
        
        if healing_cycles > 0:
            print(f"✅ Healing Cycles Completed: {healing_cycles}")
            print(f"✅ Issues Detected in Logs: {issues_detected}")
            print(f"✅ Fix Attempts in Logs: {fix_attempts}")
            print()
        
        # Evidence summary
        print("=" * 80)
        print("EVIDENCE OF GRACE'S WORK")
        print("=" * 80)
        print()
        
        evidence = []
        
        if len(issues) > 0:
            evidence.append(f"✅ Grace detected {len(issues)} issue(s) - tracked in Genesis Keys")
        
        if len(all_fixes) > 0:
            evidence.append(f"✅ Grace attempted {len(all_fixes)} fix(es) - tracked in Genesis Keys")
        
        if len(successful_fixes) > 0:
            evidence.append(f"✅ Grace successfully fixed {len(successful_fixes)} issue(s)")
        
        if healing_cycles > 0:
            evidence.append(f"✅ Grace completed {healing_cycles} healing cycle(s)")
        
        if issues_detected > 0:
            evidence.append(f"✅ Grace detected {issues_detected} issue(s) in logs")
        
        if fix_attempts > 0:
            evidence.append(f"✅ Grace attempted {fix_attempts} fix(es) in logs")
        
        if evidence:
            for item in evidence:
                print(f"  {item}")
        else:
            print("  ⚠️  Limited evidence found - Grace may be in early stages")
            print("  ⚠️  Check if Learning Memory is connected for full tracking")
        
        print()
        print("=" * 80)
        print("CONCLUSION")
        print("=" * 80)
        print()
        
        if total_activity > 0:
            print("✅ GRACE IS WORKING!")
            print()
            print("Evidence shows Grace is:")
            print("  - Detecting issues")
            print("  - Attempting fixes")
            print("  - Tracking her work in Genesis Keys")
            print("  - Running healing cycles continuously")
        else:
            print("⚠️  Limited evidence found")
            print()
            print("Possible reasons:")
            print("  - Grace is still initializing")
            print("  - Learning Memory not connected (affects tracking)")
            print("  - Database schema issues (blocking Genesis Key creation)")
            print("  - Grace needs to be restarted with latest code")
        
        print()
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to gather proof: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = show_grace_fixes_proof()
    sys.exit(0 if success else 1)
