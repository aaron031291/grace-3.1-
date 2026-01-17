#!/usr/bin/env python3
"""
Live Self-Healing Demo - Real-Time Execution

Watch the GRACE code analyzer self-healing system run in real-time,
applying fixes and showing progress as it happens.
"""

import sys
import time
import logging
from pathlib import Path
from typing import List, Dict, Any

# Add backend to path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from cognitive.code_analyzer_self_healing import CodeAnalyzerSelfHealing, CodeFixApplicator
from cognitive.grace_code_analyzer import GraceCodeAnalyzer, CodeIssue, Severity
from cognitive.autonomous_healing_system import TrustLevel

# Configure logging for real-time output
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


class LiveHealingDemo:
    """Real-time self-healing demonstration with live progress"""
    
    def __init__(self, trust_level: TrustLevel = TrustLevel.MEDIUM_RISK_AUTO):
        self.trust_level = trust_level
        self.analyzer = GraceCodeAnalyzer()
        self.fix_applicator = CodeFixApplicator()
        self.start_time = None
        self.pre_flight_mode = False
        self.auto_fix_mode = False
        
    def print_header(self):
        """Print demo header"""
        print("=" * 80)
        print("GRACE CODE ANALYZER - LIVE SELF-HEALING DEMO")
        print("=" * 80)
        print()
        print(f"Trust Level: {self.trust_level.name} ({self.trust_level.value})")
        if self.pre_flight_mode:
            print(f"Mode: PRE-FLIGHT - Analysis and decision preparation (no auto-apply)")
        elif self.auto_fix_mode:
            print(f"Mode: AUTO-FIX - Real-time healing with live progress")
        else:
            print(f"Mode: DRY-RUN - Analysis only (no fixes applied)")
        print()
        print("=" * 80)
        print()
    
    def print_step(self, step: int, description: str):
        """Print a step header"""
        print(f"\n[STEP {step}] {description}")
        print("-" * 80)
        time.sleep(0.3)  # Brief pause for readability
    
    def analyze_file_live(self, file_path: str) -> List[CodeIssue]:
        """Analyze a file and show progress in real-time"""
        print(f"  [*] Analyzing: {Path(file_path).name}")
        time.sleep(0.2)
        
        issues = self.analyzer.analyze_file(file_path)
        
        if issues:
            print(f"  [!] Found {len(issues)} issues")
            # Show first few issues
            for i, issue in enumerate(issues[:3], 1):
                print(f"     {i}. [{issue.rule_id}] {issue.message[:60]}...")
            if len(issues) > 3:
                print(f"     ... and {len(issues) - 3} more")
        else:
            print(f"  [OK] No issues found")
        
        return issues
    
    def evaluate_fixability_live(self, issues: List[CodeIssue]) -> List[CodeIssue]:
        """Evaluate which issues can be fixed and show progress"""
        print(f"\n  [*] Evaluating fixability...")
        time.sleep(0.2)
        
        fixable = []
        fixable_by_rule = {}
        
        for issue in issues:
            if self.fix_applicator.can_auto_fix(issue):
                fixable.append(issue)
                rule_id = issue.rule_id
                fixable_by_rule[rule_id] = fixable_by_rule.get(rule_id, 0) + 1
        
        print(f"  [OK] {len(fixable)} issues are auto-fixable")
        
        if fixable_by_rule:
            print(f"     Breakdown by rule:")
            for rule_id, count in fixable_by_rule.items():
                print(f"       - {rule_id}: {count} fixes")
        
        return fixable
    
    def apply_fix_live(self, issue: CodeIssue, source_code: str, file_path: str) -> tuple[bool, str]:
        """Apply a fix and show progress in real-time"""
        print(f"\n  [*] Fixing [{issue.rule_id}] at line {issue.line_number}...")
        time.sleep(0.3)
        
        success, fixed_code = self.fix_applicator.apply_fix(issue, source_code)
        
        if success:
            print(f"     [OK] Fix applied successfully")
        else:
            print(f"     [!] Fix skipped (requires AST transformation or syntax validation failed)")
        
        return success, fixed_code
    
    def run_live_demo(self, directory: str = 'backend', auto_fix: bool = False, pre_flight: bool = False):
        """Run the live healing demo"""
        self.pre_flight_mode = pre_flight
        self.auto_fix_mode = auto_fix
        self.start_time = time.time()
        self.print_header()
        
        # Get files to analyze
        project_root = Path(__file__).parent.parent
        backend_dir = project_root / directory
        
        # Find all Python files in the directory
        print(f"Scanning {directory} directory for Python files...")
        files_to_analyze = []
        for py_file in backend_dir.rglob('*.py'):
            # Skip certain directories
            skip_paths = ['__pycache__', '.git', 'venv', 'node_modules', '.pytest_cache']
            if any(skip in str(py_file) for skip in skip_paths):
                continue
            files_to_analyze.append(str(py_file))
        
        print(f"Found {len(files_to_analyze)} Python files to analyze\n")
        
        # STEP 1: Analyze files
        self.print_step(1, "CODE ANALYSIS - Scanning files for issues")
        print(f"Analyzing {len(files_to_analyze)} files...\n")
        
        all_issues = []
        issues_by_file = {}
        
        for file_path in files_to_analyze:
            issues = self.analyze_file_live(file_path)
            if issues:
                all_issues.extend(issues)
                issues_by_file[file_path] = issues
        
        # Summary
        print(f"\n  [*] Analysis Summary:")
        print(f"     Total files analyzed: {len(files_to_analyze)}")
        print(f"     Total issues found: {len(all_issues)}")
        
        if all_issues:
            severity_counts = {}
            for issue in all_issues:
                sev = issue.severity.value
                severity_counts[sev] = severity_counts.get(sev, 0) + 1
            
            print(f"     By severity:")
            for sev, count in severity_counts.items():
                print(f"       - {sev.upper()}: {count}")
        
        if not all_issues:
            print("\n  [OK] No issues found! Code is clean.")
            return
        
        # STEP 2: Evaluate fixability
        self.print_step(2, "FIXABILITY EVALUATION - Determining which issues can be auto-fixed")
        
        fixable_issues = self.evaluate_fixability_live(all_issues)
        
        if not fixable_issues:
            print("\n  [i] No auto-fixable issues found.")
            print("     Some issues may require manual fixes or AST transformation.")
            print(f"     Current auto-fixable rules: G006 (print), G007 (bare except), SYNTAX_ERROR")
            return
        
        # STEP 3: Apply fixes (if enabled) or prepare pre-flight decisions
        if pre_flight:
            self.print_step(3, "PRE-FLIGHT PREPARATION - Preparing fixes for approval")
            
            from cognitive.code_analyzer_self_healing import CodeAnalyzerSelfHealing
            
            # Create self-healing instance for pre-flight
            self_healing = CodeAnalyzerSelfHealing(
                healing_system=None,
                trust_level=self.trust_level,
                enable_auto_fix=False
            )
            
            # Prepare pre-flight decisions
            pre_flight_decisions = self_healing._prepare_pre_flight_decisions(
                fixable_issues,
                issues_by_file
            )
            
            print(f"\n  [*] Pre-flight decisions prepared: {len(pre_flight_decisions)} files")
            
            for decision in pre_flight_decisions:
                print(f"\n  File: {Path(decision['file']).name}")
                print(f"     Issues to fix: {decision['issues_count']}")
                print(f"     Rules: {', '.join(decision['rule_ids'])}")
                print(f"     Status: AWAITING APPROVAL")
                print(f"     Preview of fixes:")
                for preview in decision['fix_preview'][:3]:
                    print(f"       Line {preview['line']}: [{preview['rule_id']}]")
                    print(f"         Original: {preview['original'][:60]}...")
                    print(f"         Fixed:    {preview['fix'][:60]}...")
                if len(decision['fix_preview']) > 3:
                    print(f"       ... and {len(decision['fix_preview']) - 3} more fixes")
            
            print(f"\n  [i] Pre-flight complete. Fixes prepared for approval.")
            print(f"     To apply fixes, run with --auto-fix after review")
            
        elif auto_fix:
            self.print_step(3, "APPLYING FIXES - Auto-fixing issues in real-time")
            
            fixes_applied = 0
            fixes_by_file = {}
            
            for file_path, issues in issues_by_file.items():
                file_fixable = [i for i in issues if i in fixable_issues]
                if not file_fixable:
                    continue
                
                print(f"\n  [*] Processing: {Path(file_path).name}")
                print(f"     {len(file_fixable)} fixable issues")
                
                try:
                    # Read source code
                    with open(file_path, 'r', encoding='utf-8') as f:
                        source_code = f.read()
                    
                    fixed_code = source_code
                    file_fixes = 0
                    
                    # Sort by line number (reverse to avoid line shifts)
                    for issue in sorted(file_fixable, key=lambda x: x.line_number, reverse=True):
                        success, fixed_code = self.apply_fix_live(issue, fixed_code, file_path)
                        if success:
                            file_fixes += 1
                            fixes_applied += 1
                    
                    # Write fixed code if changes were made
                    if file_fixes > 0:
                        if not Path(file_path).exists():
                            print(f"     [!] File not found, skipping write")
                        else:
                            print(f"     [*] Writing {file_fixes} fixes to file...")
                            time.sleep(0.2)
                            # Actually write the fixes to file
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(fixed_code)
                            print(f"     [OK] File updated successfully")
                            fixes_by_file[file_path] = file_fixes
                    else:
                        print(f"     [i] No fixes were applied")
                
                except Exception as e:
                    print(f"     [ERROR] Error: {e}")
            
            print(f"\n  [*] Fix Summary:")
            print(f"     Total fixes applied: {fixes_applied}")
            print(f"     Files modified: {len(fixes_by_file)}")
            
            for file_path, count in fixes_by_file.items():
                print(f"       - {Path(file_path).name}: {count} fixes")
        else:
            self.print_step(3, "DRY RUN - Showing what would be fixed (auto-fix disabled)")
            print("\n  [i] Auto-fix is disabled. To apply fixes, run with --auto-fix")
            print(f"     Would fix {len(fixable_issues)} issues")
            
            # Show sample of what would be fixed
            print(f"\n  Sample fixes that would be applied:")
            for i, issue in enumerate(fixable_issues[:5], 1):
                print(f"     {i}. [{issue.rule_id}] Line {issue.line_number}: {issue.message[:50]}")
            if len(fixable_issues) > 5:
                print(f"     ... and {len(fixable_issues) - 5} more")
        
        # Final summary
        elapsed = time.time() - self.start_time
        print("\n" + "=" * 80)
        print("DEMO COMPLETE")
        print("=" * 80)
        print(f"Total time: {elapsed:.2f} seconds")
        print(f"Issues found: {len(all_issues)}")
        print(f"Fixable issues: {len(fixable_issues)}")
        if auto_fix:
            print(f"Fixes applied: {fixes_applied}")
        print("=" * 80)


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Live GRACE code analyzer self-healing demo'
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
        '--auto-fix',
        action='store_true',
        help='Actually apply fixes (default: dry-run mode)'
    )
    parser.add_argument(
        '--pre-flight',
        action='store_true',
        help='Pre-flight mode: Prepare fixes for approval (no auto-apply)'
    )
    
    args = parser.parse_args()
    
    # Convert trust level
    try:
        trust_level = TrustLevel(args.trust_level)
    except ValueError:
        print(f"Invalid trust level: {args.trust_level}. Must be 0-9")
        return 1
    
    # Pre-flight mode takes precedence
    if args.pre_flight:
        auto_fix = False
    
    # Run demo
    demo = LiveHealingDemo(trust_level=trust_level)
    demo.run_live_demo(
        directory=args.directory,
        auto_fix=args.auto_fix,
        pre_flight=args.pre_flight
    )
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
