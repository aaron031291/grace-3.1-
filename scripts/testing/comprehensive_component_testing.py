"""
Comprehensive Component Testing Framework
Tests all individual components with E2E and stress testing,
logs all issues, and updates self-healing and diagnostic engine.
"""

import sys
import os
import json
import logging
import traceback
import time
from pathlib import Path
from datetime import datetime, UTC
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import importlib
import inspect

# Add backend to path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

# Setup logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / f"component_testing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class TestStatus(Enum):
    """Test execution status."""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WARNING = "warning"
    ERROR = "error"


class IssueSeverity(Enum):
    """Issue severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class TestIssue:
    """Represents an issue found during testing."""
    component: str
    test_name: str
    issue_type: str  # problem, warning, skip, failure
    severity: IssueSeverity
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    stack_trace: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    fix_suggested: Optional[str] = None
    auto_fixable: bool = False


@dataclass
class ComponentTestResult:
    """Result of testing a component."""
    component_name: str
    component_path: str
    test_type: str  # e2e, stress
    status: TestStatus
    duration_seconds: float
    issues: List[TestIssue] = field(default_factory=list)
    warnings: List[TestIssue] = field(default_factory=list)
    skips: List[TestIssue] = field(default_factory=list)
    failures: List[TestIssue] = field(default_factory=list)
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    warning_tests: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestReport:
    """Complete test report."""
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    components_tested: int
    components_passed: int
    components_failed: int
    components_skipped: int
    total_issues: int
    total_warnings: int
    total_skips: int
    total_failures: int
    component_results: List[ComponentTestResult] = field(default_factory=list)
    all_issues: List[TestIssue] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)


class ComponentTester:
    """Tests individual components."""
    
    def __init__(self):
        self.issues_log: List[TestIssue] = []
        self.component_results: List[ComponentTestResult] = []
        
    def discover_components(self) -> List[Dict[str, str]]:
        """Discover all components in the backend."""
        components = []
        backend_path = Path("backend")
        
        # Core components
        core_components = [
            ("database", "database"),
            ("embedding", "embedding"),
            ("vector_db", "vector_db"),
            ("retrieval", "retrieval"),
            ("ingestion", "ingestion"),
            ("layer1", "layer1"),
            ("cognitive", "cognitive"),
            ("genesis", "genesis"),
            ("llm_orchestrator", "llm_orchestrator"),
            ("ml_intelligence", "ml_intelligence"),
            ("diagnostic_machine", "diagnostic_machine"),
            ("file_manager", "file_manager"),
            ("librarian", "librarian"),
            ("telemetry", "telemetry"),
            ("security", "security"),
            ("version_control", "version_control"),
        ]
        
        for module_name, path_name in core_components:
            module_path = backend_path / path_name
            if module_path.exists():
                components.append({
                    "name": module_name,
                    "path": str(module_path),
                    "module_path": f"{path_name}"
                })
        
        return components
    
    def test_component_e2e(self, component: Dict[str, str]) -> ComponentTestResult:
        """Run E2E test on a component."""
        logger.info(f"[E2E] Testing component: {component['name']}")
        start_time = time.time()
        
        result = ComponentTestResult(
            component_name=component['name'],
            component_path=component['path'],
            test_type="e2e",
            status=TestStatus.PASSED,
            duration_seconds=0.0
        )
        
        try:
            # Try to import the component
            try:
                module = importlib.import_module(component['module_path'])
                result.metadata['import_success'] = True
            except Exception as e:
                issue = TestIssue(
                    component=component['name'],
                    test_name="import",
                    issue_type="failure",
                    severity=IssueSeverity.CRITICAL,
                    message=f"Failed to import module: {e}",
                    stack_trace=traceback.format_exc(),
                    auto_fixable=False
                )
                result.failures.append(issue)
                result.status = TestStatus.FAILED
                result.duration_seconds = time.time() - start_time
                return result
            
            # Test basic functionality
            test_methods = [
                self._test_module_structure,
                self._test_class_instantiation,
                self._test_basic_methods,
                self._test_dependencies,
            ]
            
            for test_method in test_methods:
                try:
                    test_result = test_method(component, module)
                    if test_result:
                        if isinstance(test_result, TestIssue):
                            if test_result.issue_type == "failure":
                                result.failures.append(test_result)
                                result.failed_tests += 1
                            elif test_result.issue_type == "warning":
                                result.warnings.append(test_result)
                                result.warning_tests += 1
                            elif test_result.issue_type == "skip":
                                result.skips.append(test_result)
                                result.skipped_tests += 1
                            else:
                                result.issues.append(test_result)
                        else:
                            result.passed_tests += 1
                except Exception as e:
                    issue = TestIssue(
                        component=component['name'],
                        test_name=test_method.__name__,
                        issue_type="failure",
                        severity=IssueSeverity.HIGH,
                        message=f"Test method failed: {e}",
                        stack_trace=traceback.format_exc()
                    )
                    result.failures.append(issue)
                    result.failed_tests += 1
            
            # Update status based on results
            if result.failures:
                result.status = TestStatus.FAILED
            elif result.warnings:
                result.status = TestStatus.WARNING
            elif result.skips and not result.passed_tests:
                result.status = TestStatus.SKIPPED
            
        except Exception as e:
            issue = TestIssue(
                component=component['name'],
                test_name="e2e_test",
                issue_type="failure",
                severity=IssueSeverity.CRITICAL,
                message=f"E2E test crashed: {e}",
                stack_trace=traceback.format_exc()
            )
            result.failures.append(issue)
            result.status = TestStatus.FAILED
        
        result.duration_seconds = time.time() - start_time
        return result
    
    def test_component_stress(self, component: Dict[str, str]) -> ComponentTestResult:
        """Run stress test on a component."""
        logger.info(f"[STRESS] Testing component: {component['name']}")
        start_time = time.time()
        
        result = ComponentTestResult(
            component_name=component['name'],
            component_path=component['path'],
            test_type="stress",
            status=TestStatus.PASSED,
            duration_seconds=0.0
        )
        
        try:
            # Try to import
            try:
                module = importlib.import_module(component['module_path'])
            except Exception as e:
                issue = TestIssue(
                    component=component['name'],
                    test_name="stress_import",
                    issue_type="failure",
                    severity=IssueSeverity.CRITICAL,
                    message=f"Failed to import for stress test: {e}",
                    stack_trace=traceback.format_exc()
                )
                result.failures.append(issue)
                result.status = TestStatus.FAILED
                result.duration_seconds = time.time() - start_time
                return result
            
            # Stress tests
            stress_tests = [
                self._stress_test_concurrent_access,
                self._stress_test_memory_usage,
                self._stress_test_error_handling,
                self._stress_test_performance,
            ]
            
            for stress_test in stress_tests:
                try:
                    test_result = stress_test(component, module)
                    if test_result:
                        if isinstance(test_result, TestIssue):
                            if test_result.issue_type == "failure":
                                result.failures.append(test_result)
                                result.failed_tests += 1
                            elif test_result.issue_type == "warning":
                                result.warnings.append(test_result)
                                result.warning_tests += 1
                        else:
                            result.passed_tests += 1
                except Exception as e:
                    issue = TestIssue(
                        component=component['name'],
                        test_name=stress_test.__name__,
                        issue_type="failure",
                        severity=IssueSeverity.MEDIUM,
                        message=f"Stress test failed: {e}",
                        stack_trace=traceback.format_exc()
                    )
                    result.failures.append(issue)
                    result.failed_tests += 1
            
            if result.failures:
                result.status = TestStatus.FAILED
            elif result.warnings:
                result.status = TestStatus.WARNING
                
        except Exception as e:
            issue = TestIssue(
                component=component['name'],
                test_name="stress_test",
                issue_type="failure",
                severity=IssueSeverity.CRITICAL,
                message=f"Stress test crashed: {e}",
                stack_trace=traceback.format_exc()
            )
            result.failures.append(issue)
            result.status = TestStatus.FAILED
        
        result.duration_seconds = time.time() - start_time
        return result
    
    def _test_module_structure(self, component: Dict, module: Any) -> Optional[TestIssue]:
        """Test module structure."""
        if not hasattr(module, '__file__'):
            return TestIssue(
                component=component['name'],
                test_name="module_structure",
                issue_type="warning",
                severity=IssueSeverity.LOW,
                message="Module has no __file__ attribute"
            )
        return None
    
    def _test_class_instantiation(self, component: Dict, module: Any) -> Optional[TestIssue]:
        """Test if main classes can be instantiated."""
        classes = [name for name, obj in inspect.getmembers(module, inspect.isclass) 
                  if obj.__module__ == module.__name__]
        
        if not classes:
            return TestIssue(
                component=component['name'],
                test_name="class_instantiation",
                issue_type="skip",
                severity=IssueSeverity.INFO,
                message="No classes found in module"
            )
        
        # Try to instantiate first class if it has a simple constructor
        for class_name in classes[:3]:  # Test first 3 classes
            try:
                cls = getattr(module, class_name)
                # Check if it has a simple constructor
                sig = inspect.signature(cls.__init__)
                if len(sig.parameters) <= 1:  # Only self
                    instance = cls()
            except Exception as e:
                return TestIssue(
                    component=component['name'],
                    test_name="class_instantiation",
                    issue_type="warning",
                    severity=IssueSeverity.MEDIUM,
                    message=f"Could not instantiate {class_name}: {e}"
                )
        
        return None
    
    def _test_basic_methods(self, component: Dict, module: Any) -> Optional[TestIssue]:
        """Test basic methods exist."""
        # This is a placeholder - actual implementation would test specific methods
        return None
    
    def _test_dependencies(self, component: Dict, module: Any) -> Optional[TestIssue]:
        """Test dependencies are available."""
        # Check if module has dependencies that might be missing
        try:
            import importlib.util
            spec = importlib.util.find_spec(component['module_path'])
            if spec is None:
                return TestIssue(
                    component=component['name'],
                    test_name="dependencies",
                    issue_type="failure",
                    severity=IssueSeverity.HIGH,
                    message="Module spec not found"
                )
        except Exception as e:
            return TestIssue(
                component=component['name'],
                test_name="dependencies",
                issue_type="warning",
                severity=IssueSeverity.MEDIUM,
                message=f"Dependency check failed: {e}"
            )
        return None
    
    def _stress_test_concurrent_access(self, component: Dict, module: Any) -> Optional[TestIssue]:
        """Stress test concurrent access."""
        # Placeholder for concurrent access testing
        return None
    
    def _stress_test_memory_usage(self, component: Dict, module: Any) -> Optional[TestIssue]:
        """Stress test memory usage."""
        # Placeholder for memory testing
        return None
    
    def _stress_test_error_handling(self, component: Dict, module: Any) -> Optional[TestIssue]:
        """Stress test error handling."""
        # Placeholder for error handling testing
        return None
    
    def _stress_test_performance(self, component: Dict, module: Any) -> Optional[TestIssue]:
        """Stress test performance."""
        # Placeholder for performance testing
        return None


class IssueLogger:
    """Logs all issues to files and database."""
    
    def __init__(self):
        self.issues_file = Path(f"test_issues_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        self.issues: List[TestIssue] = []
    
    def log_issue(self, issue: TestIssue):
        """Log an issue."""
        self.issues.append(issue)
        logger.info(f"[ISSUE] {issue.component}: {issue.issue_type} - {issue.message}")
    
    def log_all_issues(self, issues: List[TestIssue]):
        """Log all issues."""
        for issue in issues:
            self.log_issue(issue)
    
    def save_issues(self):
        """Save issues to file."""
        issues_data = [asdict(issue) for issue in self.issues]
        # Convert datetime to string
        for issue_data in issues_data:
            if 'timestamp' in issue_data and isinstance(issue_data['timestamp'], datetime):
                issue_data['timestamp'] = issue_data['timestamp'].isoformat()
            if 'severity' in issue_data and isinstance(issue_data['severity'], IssueSeverity):
                issue_data['severity'] = issue_data['severity'].value
        
        self.issues_file.write_text(json.dumps(issues_data, indent=2))
        logger.info(f"[LOGGER] Saved {len(self.issues)} issues to {self.issues_file}")


class SelfHealingUpdater:
    """Updates self-healing system with new issues."""
    
    def __init__(self):
        self.integration = None
        try:
            from diagnostic_machine.test_issue_integration import get_test_issue_integration
            self.integration = get_test_issue_integration()
            logger.info("[HEALING] Connected to self-healing system via integration")
        except Exception as e:
            logger.warning(f"[HEALING] Could not connect to self-healing system: {e}")
    
    def update_with_issues(self, issues: List[TestIssue]):
        """Update self-healing system with test issues."""
        if not self.integration:
            logger.warning("[HEALING] Integration not available")
            return
        
        logger.info(f"[HEALING] Updating with {len(issues)} issues")
        
        # Convert TestIssue to dict format
        issues_dict = [asdict(issue) for issue in issues]
        # Convert enums to strings
        for issue_dict in issues_dict:
            if 'severity' in issue_dict and isinstance(issue_dict['severity'], IssueSeverity):
                issue_dict['severity'] = issue_dict['severity'].value
            if 'timestamp' in issue_dict and isinstance(issue_dict['timestamp'], datetime):
                issue_dict['timestamp'] = issue_dict['timestamp'].isoformat()
        
        self.integration.register_issues_with_healing(issues_dict)


class DiagnosticEngineUpdater:
    """Updates diagnostic engine with new issues."""
    
    def __init__(self):
        self.integration = None
        try:
            from diagnostic_machine.test_issue_integration import get_test_issue_integration
            self.integration = get_test_issue_integration()
            logger.info("[DIAGNOSTIC] Connected to diagnostic engine via integration")
        except Exception as e:
            logger.warning(f"[DIAGNOSTIC] Could not connect to diagnostic engine: {e}")
    
    def update_with_issues(self, issues: List[TestIssue]):
        """Update diagnostic engine with test issues."""
        if not self.integration:
            logger.warning("[DIAGNOSTIC] Integration not available")
            return
        
        logger.info(f"[DIAGNOSTIC] Updating with {len(issues)} issues")
        
        # Convert TestIssue to dict format
        issues_dict = [asdict(issue) for issue in issues]
        # Convert enums to strings
        for issue_dict in issues_dict:
            if 'severity' in issue_dict and isinstance(issue_dict['severity'], IssueSeverity):
                issue_dict['severity'] = issue_dict['severity'].value
            if 'timestamp' in issue_dict and isinstance(issue_dict['timestamp'], datetime):
                issue_dict['timestamp'] = issue_dict['timestamp'].isoformat()
        
        self.integration.register_issues_with_diagnostic(issues_dict)
        self.integration.update_automatic_fixer(issues_dict)


class ComprehensiveTestRunner:
    """Runs comprehensive tests on all components."""
    
    def __init__(self):
        self.tester = ComponentTester()
        self.issue_logger = IssueLogger()
        self.healing_updater = SelfHealingUpdater()
        self.diagnostic_updater = DiagnosticEngineUpdater()
        self.report: Optional[TestReport] = None
    
    def run_all_tests(self) -> TestReport:
        """Run all tests on all components."""
        logger.info("=" * 80)
        logger.info("COMPREHENSIVE COMPONENT TESTING")
        logger.info("=" * 80)
        
        start_time = datetime.now(UTC)
        
        # Discover components
        components = self.tester.discover_components()
        logger.info(f"[DISCOVERY] Found {len(components)} components to test")
        
        # Test each component
        all_issues = []
        component_results = []
        
        for component in components:
            logger.info(f"\n{'='*80}")
            logger.info(f"Testing component: {component['name']}")
            logger.info(f"{'='*80}")
            
            # E2E test
            e2e_result = self.tester.test_component_e2e(component)
            component_results.append(e2e_result)
            all_issues.extend(e2e_result.issues)
            all_issues.extend(e2e_result.warnings)
            all_issues.extend(e2e_result.skips)
            all_issues.extend(e2e_result.failures)
            
            # Stress test
            stress_result = self.tester.test_component_stress(component)
            component_results.append(stress_result)
            all_issues.extend(stress_result.issues)
            all_issues.extend(stress_result.warnings)
            all_issues.extend(stress_result.skips)
            all_issues.extend(stress_result.failures)
        
        # Log all issues
        self.issue_logger.log_all_issues(all_issues)
        self.issue_logger.save_issues()
        
        # Update self-healing
        self.healing_updater.update_with_issues(all_issues)
        
        # Update diagnostic engine
        self.diagnostic_updater.update_with_issues(all_issues)
        
        # Also process the report file through integration
        try:
            from diagnostic_machine.test_issue_integration import get_test_issue_integration
            integration = get_test_issue_integration()
            # Save report first, then process it
            report_file = Path(f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            self._save_report_to_file(report_file)
            integration.process_test_report(report_file)
        except Exception as e:
            logger.warning(f"[INTEGRATION] Failed to process report through integration: {e}")
        
        # Generate report
        end_time = datetime.now(UTC)
        duration = (end_time - start_time).total_seconds()
        
        self.report = TestReport(
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration,
            components_tested=len(components),
            components_passed=sum(1 for r in component_results if r.status == TestStatus.PASSED),
            components_failed=sum(1 for r in component_results if r.status == TestStatus.FAILED),
            components_skipped=sum(1 for r in component_results if r.status == TestStatus.SKIPPED),
            total_issues=len([i for i in all_issues if i.issue_type == "problem"]),
            total_warnings=len([i for i in all_issues if i.issue_type == "warning"]),
            total_skips=len([i for i in all_issues if i.issue_type == "skip"]),
            total_failures=len([i for i in all_issues if i.issue_type == "failure"]),
            component_results=component_results,
            all_issues=all_issues,
            summary=self._generate_summary(component_results, all_issues)
        )
        
        self._save_report()
        self._print_summary()
        
        return self.report
    
    def _generate_summary(self, results: List[ComponentTestResult], issues: List[TestIssue]) -> Dict[str, Any]:
        """Generate summary statistics."""
        return {
            "total_tests": sum(r.passed_tests + r.failed_tests + r.skipped_tests + r.warning_tests for r in results),
            "pass_rate": sum(r.passed_tests for r in results) / max(sum(r.passed_tests + r.failed_tests for r in results), 1) * 100,
            "components_by_status": {
                "passed": sum(1 for r in results if r.status == TestStatus.PASSED),
                "failed": sum(1 for r in results if r.status == TestStatus.FAILED),
                "warning": sum(1 for r in results if r.status == TestStatus.WARNING),
                "skipped": sum(1 for r in results if r.status == TestStatus.SKIPPED)
            },
            "issues_by_severity": {
                severity.value: len([i for i in issues if i.severity == severity])
                for severity in IssueSeverity
            },
            "issues_by_type": {
                issue_type: len([i for i in issues if i.issue_type == issue_type])
                for issue_type in ["problem", "warning", "skip", "failure"]
            }
        }
    
    def _save_report(self):
        """Save test report."""
        if not self.report:
            return
        
        report_file = Path(f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        self._save_report_to_file(report_file)
    
    def _save_report_to_file(self, report_file: Path):
        """Save report to specific file."""
        if not self.report:
            return
        
        # Convert to dict
        report_dict = asdict(self.report)
        
        # Convert enums and datetimes
        def convert_value(v):
            if isinstance(v, (datetime, IssueSeverity, TestStatus)):
                return v.value if hasattr(v, 'value') else str(v)
            elif isinstance(v, dict):
                return {k: convert_value(val) for k, val in v.items()}
            elif isinstance(v, list):
                return [convert_value(item) for item in v]
            return v
        
        report_dict = convert_value(report_dict)
        
        report_file.write_text(json.dumps(report_dict, indent=2, default=str))
        logger.info(f"[REPORT] Saved report to {report_file}")
    
    def _print_summary(self):
        """Print test summary."""
        if not self.report:
            return
        
        logger.info("\n" + "=" * 80)
        logger.info("TEST SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Duration: {self.report.duration_seconds:.2f} seconds")
        logger.info(f"Components tested: {self.report.components_tested}")
        logger.info(f"Components passed: {self.report.components_passed}")
        logger.info(f"Components failed: {self.report.components_failed}")
        logger.info(f"Components skipped: {self.report.components_skipped}")
        logger.info(f"\nIssues:")
        logger.info(f"  Problems: {self.report.total_issues}")
        logger.info(f"  Warnings: {self.report.total_warnings}")
        logger.info(f"  Skips: {self.report.total_skips}")
        logger.info(f"  Failures: {self.report.total_failures}")
        logger.info("=" * 80)


def main():
    """Main entry point."""
    runner = ComprehensiveTestRunner()
    report = runner.run_all_tests()
    
    # Exit with appropriate code
    if report.components_failed > 0:
        sys.exit(1)
    elif report.total_failures > 0:
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
