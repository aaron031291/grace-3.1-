#!/usr/bin/env python3
"""
Trigger Code Analyzer Self-Healing

Run this script to:
1. Analyze codebase for issues
2. Automatically apply safe fixes based on trust level
3. Track fixes in Genesis keys
4. Integrate with autonomous healing system
"""

import sys
import logging
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from cognitive.code_analyzer_self_healing import trigger_code_healing
from cognitive.autonomous_healing_system import TrustLevel

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Trigger GRACE code analyzer self-healing'
    )
    parser.add_argument(
        '--directory',
        default='backend',
        help='Directory to analyze (default: backend)'
    )
    parser.add_argument(
        '--trust-level',
        type=int,
        default=3,
        help='Trust level (0-9, default: 3 = MEDIUM_RISK_AUTO)'
    )
    parser.add_argument(
        '--no-auto-fix',
        action='store_true',
        help='Disable automatic fixing (analysis only)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be fixed without applying changes'
    )
    
    args = parser.parse_args()
    
    # Convert trust level
    try:
        trust_level = TrustLevel(args.trust_level)
    except ValueError:
        print(f"Invalid trust level: {args.trust_level}. Must be 0-9")
        return 1
    
    print("=" * 70)
    print("GRACE Code Analyzer Self-Healing")
    print("=" * 70)
    print()
    print(f"Directory: {args.directory}")
    print(f"Trust Level: {trust_level.name} ({trust_level.value})")
    print(f"Auto-Fix: {not args.no_auto_fix}")
    print(f"Dry Run: {args.dry_run}")
    print()
    
    if args.dry_run:
        print("[DRY RUN] Would analyze and show fixes without applying...")
        # TODO: Implement dry-run mode
        auto_fix = False
    else:
        auto_fix = not args.no_auto_fix
    
    # Trigger healing
    try:
        results = trigger_code_healing(
            directory=args.directory,
            trust_level=trust_level,
            auto_fix=auto_fix
        )
        
        # Print results
        print()
        print("=" * 70)
        print("RESULTS")
        print("=" * 70)
        print()
        print(f"Issues found: {results['issues_found']}")
        print(f"  Critical: {results['issues_by_severity'].get('critical', 0)}")
        print(f"  High: {results['issues_by_severity'].get('high', 0)}")
        print(f"  Medium: {results['issues_by_severity'].get('medium', 0)}")
        print(f"  Low: {results['issues_by_severity'].get('low', 0)}")
        print()
        print(f"Fixable issues: {results['fixable_issues']}")
        print(f"Fixes applied: {results['fixes_applied']}")
        print(f"Health status: {results['health_status']}")
        print()
        
        if results['healing_results']:
            print("Files modified:")
            for result in results['healing_results']:
                status = "[OK]" if result['status'] == 'success' else "[ERROR]"
                print(f"  {status} {result['file']}: {result['fixes_applied']} fixes")
        
        print()
        print("=" * 70)
        print("Self-healing triggered successfully!")
        print("=" * 70)
        
        return 0
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
