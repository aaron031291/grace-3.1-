#!/usr/bin/env python3
"""
Master script to run comprehensive E2E and stress testing on all components.
This script:
1. Runs E2E tests on all components
2. Runs stress tests on all components
3. Logs all problems, warnings, skips, and failures
4. Updates self-healing system to recognize and fix issues
5. Updates diagnostic engine to recognize issues
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def main():
    """Run comprehensive testing."""
    print("\n" + "="*80)
    print("COMPREHENSIVE COMPONENT TESTING - MASTER RUNNER")
    print("="*80)
    print(f"Started at: {datetime.now().isoformat()}")
    print("="*80 + "\n")
    
    try:
        # Import and run comprehensive testing
        from comprehensive_component_testing import ComprehensiveTestRunner
        
        runner = ComprehensiveTestRunner()
        report = runner.run_all_tests()
        
        # Print final summary
        print("\n" + "="*80)
        print("TESTING COMPLETE")
        print("="*80)
        print(f"Components tested: {report.components_tested}")
        print(f"Components passed: {report.components_passed}")
        print(f"Components failed: {report.components_failed}")
        print(f"\nIssues found:")
        print(f"  Problems: {report.total_issues}")
        print(f"  Warnings: {report.total_warnings}")
        print(f"  Skips: {report.total_skips}")
        print(f"  Failures: {report.total_failures}")
        print(f"\nDuration: {report.duration_seconds:.2f} seconds")
        print("="*80)
        
        # Check if integration was successful
        try:
            from diagnostic_machine.test_issue_integration import get_test_issue_integration
            integration = get_test_issue_integration()
            patterns = integration.get_recognized_patterns()
            print(f"\nIntegration Status:")
            print(f"  Patterns registered: {patterns['total_patterns']}")
            print(f"  Healing connected: {patterns['healing_connected']}")
            print(f"  Diagnostic connected: {patterns['diagnostic_connected']}")
        except Exception as e:
            print(f"\n[WARNING] Could not verify integration status: {e}")
        
        # Exit with appropriate code
        if report.components_failed > 0 or report.total_failures > 0:
            print("\n[RESULT] Some tests failed - check logs for details")
            return 1
        else:
            print("\n[RESULT] All tests passed!")
            return 0
            
    except Exception as e:
        print(f"\n[ERROR] Testing failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
