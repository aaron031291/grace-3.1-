#!/usr/bin/env python3
"""Test the silent degradation detector."""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from cognitive.silent_degradation_detector import SilentDegradationDetector

def main():
    print("=" * 70)
    print("Silent Degradation Detector Test")
    print("=" * 70)
    
    detector = SilentDegradationDetector()
    
    # Scan cognitive directory
    print("\nScanning backend/cognitive for silent failures...")
    issues = detector.scan_for_silent_failures(directory="cognitive")
    print(f"Found {len(issues)} silent failure patterns\n")
    
    # Show first 10
    for i, issue in enumerate(issues[:10], 1):
        severity = issue.severity.value if hasattr(issue.severity, 'value') else issue.severity
        issue_type = issue.issue_type.value if hasattr(issue.issue_type, 'value') else issue.issue_type
        print(f"{i}. [{severity.upper()}] {issue_type}")
        print(f"   File: {issue.file_path}:{issue.line_number}")
        desc = issue.description[:80] if issue.description else "No description"
        print(f"   {desc}...")
        print()
    
    # Get full report
    print("-" * 70)
    report = detector.get_degradation_report()
    summary = report.get("summary", {})
    print(f"Total issues: {summary.get('total_issues', 0)}")
    print(f"Avg health impact: {summary.get('average_health_impact', 0):.1%}")
    print(f"By severity: {summary.get('by_severity', {})}")
    print(f"By type: {summary.get('by_type', {})}")
    
    print("\n" + "=" * 70)
    print("Test complete!")
    print("=" * 70)

if __name__ == "__main__":
    main()
