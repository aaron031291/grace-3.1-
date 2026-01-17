"""
Auto-fix E2E Test Issues

Uses enhanced diagnostic engine and self-healing system to automatically
detect and fix the remaining issues found in e2e tests.
"""

import sys
import logging
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Run auto-fix for e2e issues."""
    logger.info("="*70)
    logger.info("AUTO-FIX E2E TEST ISSUES")
    logger.info("="*70)
    
    # Initialize diagnostic systems
    from diagnostic_machine.proactive_code_scanner import get_proactive_scanner
    from diagnostic_machine.automatic_bug_fixer import AutomaticBugFixer
    
    scanner = get_proactive_scanner(backend_dir=backend_dir)
    fixer = AutomaticBugFixer(backend_dir=backend_dir, create_backups=True)
    
    # Scan for issues
    logger.info("\n[1/3] Scanning for code issues...")
    issues = scanner.scan_all()
    
    logger.info(f"Found {len(issues)} issues")
    
    # Filter for Pydantic logger issues and other critical issues
    pydantic_issues = [i for i in issues if i.issue_type == 'pydantic_logger']
    critical_issues = [i for i in issues if i.severity == 'critical']
    
    logger.info(f"  - Pydantic logger issues: {len(pydantic_issues)}")
    logger.info(f"  - Critical issues: {len(critical_issues)}")
    
    # Fix issues
    logger.info("\n[2/3] Fixing issues...")
    all_fixes = []
    
    # Fix Pydantic logger issues first
    if pydantic_issues:
        logger.info(f"Fixing {len(pydantic_issues)} Pydantic logger issues...")
        fixes = fixer.fix_all_issues(pydantic_issues)
        all_fixes.extend(fixes)
        successful = sum(1 for f in fixes if f.success)
        logger.info(f"  Fixed: {successful}/{len(fixes)}")
    
    # Fix critical issues
    if critical_issues:
        logger.info(f"Fixing {len(critical_issues)} critical issues...")
        fixes = fixer.fix_all_issues(critical_issues)
        all_fixes.extend(fixes)
        successful = sum(1 for f in fixes if f.success)
        logger.info(f"  Fixed: {successful}/{len(fixes)}")
    
    # Summary
    logger.info("\n[3/3] Summary")
    logger.info("="*70)
    total_fixes = len(all_fixes)
    successful_fixes = sum(1 for f in all_fixes if f.success)
    
    logger.info(f"Total fixes attempted: {total_fixes}")
    logger.info(f"Successful: {successful_fixes}")
    logger.info(f"Failed: {total_fixes - successful_fixes}")
    
    if successful_fixes > 0:
        logger.info("\nSuccessful fixes:")
        for fix in all_fixes:
            if fix.success:
                logger.info(f"  ✓ {fix.file_path}: {fix.fix_applied}")
    
    if total_fixes - successful_fixes > 0:
        logger.info("\nFailed fixes:")
        for fix in all_fixes:
            if not fix.success:
                logger.info(f"  ✗ {fix.file_path}: {fix.error_message}")
    
    logger.info("\n" + "="*70)
    logger.info("AUTO-FIX COMPLETE")
    logger.info("="*70)
    
    return 0 if successful_fixes == total_fixes else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
