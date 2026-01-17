#!/usr/bin/env python3
"""
Test Code Analyzer Self-Healing

Run this script to test the self-healing integration.
"""

import sys
import logging
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from cognitive.code_analyzer_self_healing import CodeAnalyzerSelfHealing
from cognitive.autonomous_healing_system import TrustLevel
from cognitive.grace_code_analyzer import GraceCodeAnalyzer
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)


def main():
    """Main test function"""
    print("=" * 70)
    print("GRACE Code Analyzer Self-Healing - Test Run")
    print("=" * 70)
    print()
    print("Running analysis (auto-fix disabled for testing)...")
    print()
    
    try:
        # Resolve directory path relative to project root
        project_root = Path(__file__).parent.parent
        backend_dir = project_root / 'backend'
        
        # Test with a few sample files for faster results
        sample_files = [
            str(backend_dir / 'app.py'),
            str(backend_dir / 'settings.py'),
            str(backend_dir / 'api' / 'retrieve.py'),
            str(backend_dir / 'api' / 'file_ingestion.py'),
        ]
        
        print("Analyzing sample files:")
        for file in sample_files:
            print(f"  - {Path(file).relative_to(project_root)}")
        print()
        
        # Create analyzer and analyze sample files
        analyzer = GraceCodeAnalyzer()
        all_issues = []
        results_dict = {}
        
        for file_path in sample_files:
            if Path(file_path).exists():
                issues = analyzer.analyze_file(file_path)
                if issues:
                    results_dict[file_path] = issues
                    all_issues.extend(issues)
        
        # Create self-healing instance for evaluation
        self_healing = CodeAnalyzerSelfHealing(
            healing_system=None,
            trust_level=TrustLevel.MEDIUM_RISK_AUTO,
            enable_auto_fix=False
        )
        
        # Evaluate fixable issues
        fixable_issues = self_healing._evaluate_fixable_issues(all_issues, min_confidence=0.8)
        
        # Build results
        from cognitive.code_analyzer_self_healing import Severity
        issues_by_severity = {}
        for issue in all_issues:
            sev = issue.severity.value
            issues_by_severity[sev] = issues_by_severity.get(sev, 0) + 1
        
        results = {
            'issues_found': len(all_issues),
            'issues_by_severity': issues_by_severity,
            'fixable_issues': len(fixable_issues),
            'fixes_applied': 0,
            'healing_results': [],
            'health_status': self_healing._determine_health_status(all_issues)
        }
        
        # Print results
        print()
        print("=" * 70)
        print("TEST RESULTS")
        print("=" * 70)
        print()
        print(f"Issues found: {results['issues_found']}")
        print()
        print("Issues by severity:")
        for severity, count in results['issues_by_severity'].items():
            print(f"  {severity.upper()}: {count}")
        print()
        
        # Show sample issues
        if all_issues:
            print("Sample issues found (first 5):")
            for i, issue in enumerate(all_issues[:5], 1):
                print(f"  {i}. [{issue.rule_id}] {issue.message}")
                print(f"     File: {Path(issue.file_path).name}:{issue.line_number}")
                if issue.suggested_fix:
                    print(f"     Fix: {issue.suggested_fix}")
                else:
                    print(f"     Fix: No auto-fix available")
                print()
        
        print(f"Fixable issues: {results['fixable_issues']}")
        if fixable_issues:
            print(f"  Auto-fixable rules: {set(i.rule_id for i in fixable_issues)}")
        print(f"Fixes applied: {results['fixes_applied']}")
        print(f"Health status: {results['health_status']}")
        print()
        
        if results.get('healing_results'):
            print("Files that would be modified:")
            for result in results['healing_results']:
                status = "[OK]" if result['status'] == 'success' else "[ERROR]"
                print(f"  {status} {result['file']}: {result.get('fixes_applied', 0)} fixes")
        
        print()
        print("=" * 70)
        print("Test completed successfully!")
        print("=" * 70)
        
        return 0
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
