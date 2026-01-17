"""
Run Enterprise Stress Tests and Auto-Fix Issues

This script:
1. Runs all 15 enterprise stress tests
2. Logs all results
3. Analyzes logs for issues
4. Attempts to fix issues automatically
5. Upgrades diagnostic engine and self-healing agent if new issues found
"""

import sys
import logging
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

# Import after path setup
import importlib.util

# Load modules directly
enterprise_tests_path = project_root / "backend" / "tests" / "enterprise_stress_tests.py"
analyzer_path = project_root / "backend" / "tests" / "stress_test_analyzer.py"
fixer_path = project_root / "backend" / "tests" / "stress_test_fixer.py"

spec1 = importlib.util.spec_from_file_location("enterprise_stress_tests", enterprise_tests_path)
enterprise_stress_tests = importlib.util.module_from_spec(spec1)
spec1.loader.exec_module(enterprise_stress_tests)
run_enterprise_stress_tests = enterprise_stress_tests.run_enterprise_stress_tests

spec2 = importlib.util.spec_from_file_location("stress_test_analyzer", analyzer_path)
stress_test_analyzer = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(stress_test_analyzer)
StressTestAnalyzer = stress_test_analyzer.StressTestAnalyzer

spec3 = importlib.util.spec_from_file_location("stress_test_fixer", fixer_path)
stress_test_fixer = importlib.util.module_from_spec(spec3)
spec3.loader.exec_module(stress_test_fixer)
StressTestFixer = stress_test_fixer.StressTestFixer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Run stress tests and fix issues."""
    logger.info("=" * 80)
    logger.info("ENTERPRISE STRESS TEST SUITE")
    logger.info("=" * 80)
    
    # Step 1: Run all stress tests
    logger.info("\n[STEP 1] Running 15 enterprise stress tests...")
    summary = run_enterprise_stress_tests()
    
    if "error" in summary:
        logger.error(f"[STEP 1] Error: {summary['error']}")
        logger.info("Continuing with analysis of any existing test results...")
        summary = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "pass_rate": 0.0,
            "issues_found": 0,
            "results": {}
        }
    else:
        logger.info(f"\n[STEP 1] Complete: {summary.get('passed', 0)}/{summary.get('total_tests', 0)} tests passed")
        logger.info(f"[STEP 1] Issues found: {summary.get('issues_found', 0)}")
    
    # Step 2: Analyze results
    logger.info("\n[STEP 2] Analyzing test results...")
    analyzer = StressTestAnalyzer()
    analysis = analyzer.analyze_test_results()
    
    logger.info(f"[STEP 2] Analysis complete:")
    logger.info(f"  - Critical issues: {len(analysis.get('critical_issues', []))}")
    logger.info(f"  - Warnings: {len(analysis.get('warnings', []))}")
    logger.info(f"  - New issue types: {len(analysis.get('new_issue_types', []))}")
    
    # Step 3: Fix issues
    logger.info("\n[STEP 3] Attempting to fix issues...")
    fixer = StressTestFixer()
    fix_results = fixer.fix_all_issues(analysis)
    
    logger.info(f"[STEP 3] Fix results:")
    logger.info(f"  - Fixed: {fix_results.get('fixed_count', 0)}")
    logger.info(f"  - Failed: {fix_results.get('failed_count', 0)}")
    logger.info(f"  - Requires upgrade: {fix_results.get('requires_upgrade', False)}")
    
    # Step 4: Upgrade diagnostic engine and self-healing if needed
    if fix_results.get('requires_upgrade', False) or len(analysis.get('new_issue_types', [])) > 0:
        logger.info("\n[STEP 4] Upgrading diagnostic engine and self-healing agent...")
        try:
            from backend.tests.upgrade_diagnostic_systems import upgrade_diagnostic_systems
        except ImportError:
            from tests.upgrade_diagnostic_systems import upgrade_diagnostic_systems
        upgrade_results = upgrade_diagnostic_systems(analysis)
        
        logger.info(f"[STEP 4] Upgrade complete:")
        logger.info(f"  - Diagnostic engine updated: {upgrade_results.get('diagnostic_updated', False)}")
        logger.info(f"  - Self-healing agent updated: {upgrade_results.get('healing_updated', False)}")
        logger.info(f"  - New patterns added: {len(upgrade_results.get('new_patterns', []))}")
    else:
        logger.info("\n[STEP 4] No upgrades needed")
    
    # Final summary
    logger.info("\n" + "=" * 80)
    logger.info("STRESS TEST SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Tests Passed: {summary.get('passed', 0)}/{summary.get('total_tests', 0)}")
    logger.info(f"Issues Found: {summary.get('issues_found', 0)}")
    logger.info(f"Issues Fixed: {fix_results.get('fixed_count', 0)}")
    logger.info(f"Systems Upgraded: {fix_results.get('requires_upgrade', False)}")
    logger.info("=" * 80)
    
    return {
        "summary": summary,
        "analysis": analysis,
        "fix_results": fix_results
    }


if __name__ == "__main__":
    main()
