"""
Autonomous Test Runner for Grace Self-Testing

This module enables Grace to autonomously run tests to verify her own
implementation and logic. Integrates with the sandbox lab and can be
triggered via API, scheduled tasks, or autonomous actions.

Features:
- Run all tests or specific test suites
- Generate detailed reports
- Track test history and trends
- Integrate with Genesis Keys for change tracking
- Sandbox isolation for safe execution
"""

import subprocess
import json
import os
import sys
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass, field, asdict
import asyncio

logger = logging.getLogger(__name__)

# Add backend to path
BACKEND_DIR = Path(__file__).parent
sys.path.insert(0, str(BACKEND_DIR))


@dataclass
class TestResult:
    """Individual test result."""
    test_name: str
    test_file: str
    status: str  # passed, failed, skipped, error
    duration: float
    message: Optional[str] = None
    traceback: Optional[str] = None


@dataclass
class TestSuiteResult:
    """Result of a test suite run."""
    suite_name: str
    total_tests: int
    passed: int
    failed: int
    skipped: int
    errors: int
    duration: float
    timestamp: str
    results: List[TestResult] = field(default_factory=list)
    coverage_percent: Optional[float] = None


@dataclass
class TestRunReport:
    """Complete test run report."""
    run_id: str
    timestamp: str
    total_suites: int
    total_tests: int
    passed: int
    failed: int
    skipped: int
    errors: int
    duration: float
    success_rate: float
    suites: List[TestSuiteResult] = field(default_factory=list)
    genesis_key_id: Optional[str] = None


class AutonomousTestRunner:
    """
    Autonomous test runner for Grace self-testing.

    Enables Grace to verify her own implementations by running
    tests autonomously and reporting results.
    """

    # Test suite definitions
    TEST_SUITES = {
        "core": {
            "name": "Core API Tests",
            "files": ["tests/test_app.py"],
            "description": "Core application and health endpoints"
        },
        "layer1": {
            "name": "Layer 1 Tests",
            "files": ["tests/test_api_layer1.py"],
            "description": "Layer 1 and whitelist functionality"
        },
        "cognitive": {
            "name": "Cognitive System Tests",
            "files": ["tests/test_api_cognitive.py", "tests/test_cognitive_engine.py"],
            "description": "Cognitive engine and memory mesh"
        },
        "ml_intelligence": {
            "name": "ML Intelligence Tests",
            "files": ["tests/test_api_ml_intelligence.py"],
            "description": "Machine learning and trust scoring"
        },
        "genesis": {
            "name": "Genesis Keys Tests",
            "files": ["tests/test_api_genesis.py"],
            "description": "Genesis key tracking and verification"
        },
        "governance": {
            "name": "Governance Tests",
            "files": ["tests/test_api_governance.py"],
            "description": "Governance rules and approvals"
        },
        "librarian": {
            "name": "Librarian Tests",
            "files": ["tests/test_api_librarian.py"],
            "description": "Document organization and tagging"
        },
        "retrieval": {
            "name": "Retrieval Tests",
            "files": ["tests/test_api_retrieval.py", "tests/test_reranker.py"],
            "description": "RAG retrieval and reranking"
        },
        "codebase": {
            "name": "Codebase Tests",
            "files": ["tests/test_api_codebase.py"],
            "description": "Codebase browsing and analysis"
        },
        "monitoring": {
            "name": "Monitoring Tests",
            "files": ["tests/test_api_monitoring.py"],
            "description": "System monitoring and metrics"
        },
        "security": {
            "name": "Security Tests",
            "files": ["tests/test_security.py", "tests/test_rate_limiting.py"],
            "description": "Security and rate limiting"
        },
        "database": {
            "name": "Database Tests",
            "files": ["tests/test_database.py"],
            "description": "Database models and operations"
        }
    }

    def __init__(self, backend_dir: str = None):
        """Initialize the test runner."""
        self.backend_dir = Path(backend_dir) if backend_dir else BACKEND_DIR
        self.reports_dir = self.backend_dir / "test_reports"
        self.reports_dir.mkdir(exist_ok=True)
        self.history: List[TestRunReport] = []

    def _generate_run_id(self) -> str:
        """Generate unique run ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"test_run_{timestamp}"

    def run_suite(
        self,
        suite_name: str,
        verbose: bool = True,
        coverage: bool = False
    ) -> TestSuiteResult:
        """
        Run a specific test suite.

        Args:
            suite_name: Name of the test suite to run
            verbose: Enable verbose output
            coverage: Enable coverage reporting

        Returns:
            TestSuiteResult with test outcomes
        """
        if suite_name not in self.TEST_SUITES:
            raise ValueError(f"Unknown test suite: {suite_name}")

        suite_config = self.TEST_SUITES[suite_name]
        test_files = suite_config["files"]

        logger.info(f"Running test suite: {suite_config['name']}")

        # Build pytest command
        cmd = ["python", "-m", "pytest"]

        if verbose:
            cmd.append("-v")

        if coverage:
            cmd.extend(["--cov=.", "--cov-report=json"])

        # Add JSON output for parsing
        json_output = self.reports_dir / f"{suite_name}_result.json"
        cmd.extend(["--json-report", f"--json-report-file={json_output}"])

        # Add test files
        for test_file in test_files:
            test_path = self.backend_dir / test_file
            if test_path.exists():
                cmd.append(str(test_path))

        start_time = datetime.now()

        try:
            # Run tests
            result = subprocess.run(
                cmd,
                cwd=str(self.backend_dir),
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )

            duration = (datetime.now() - start_time).total_seconds()

            # Parse results
            test_results = self._parse_pytest_output(result.stdout, result.stderr)

            # Try to load JSON report if available
            if json_output.exists():
                with open(json_output) as f:
                    json_data = json.load(f)
                    test_results = self._parse_json_report(json_data)

            # Calculate stats
            passed = sum(1 for r in test_results if r.status == "passed")
            failed = sum(1 for r in test_results if r.status == "failed")
            skipped = sum(1 for r in test_results if r.status == "skipped")
            errors = sum(1 for r in test_results if r.status == "error")

            suite_result = TestSuiteResult(
                suite_name=suite_config["name"],
                total_tests=len(test_results),
                passed=passed,
                failed=failed,
                skipped=skipped,
                errors=errors,
                duration=duration,
                timestamp=datetime.now().isoformat(),
                results=test_results
            )

            logger.info(
                f"Suite {suite_name}: {passed}/{len(test_results)} passed "
                f"({failed} failed, {skipped} skipped) in {duration:.2f}s"
            )

            return suite_result

        except subprocess.TimeoutExpired:
            logger.error(f"Test suite {suite_name} timed out")
            return TestSuiteResult(
                suite_name=suite_config["name"],
                total_tests=0,
                passed=0,
                failed=0,
                skipped=0,
                errors=1,
                duration=600.0,
                timestamp=datetime.now().isoformat(),
                results=[TestResult(
                    test_name="timeout",
                    test_file="",
                    status="error",
                    duration=600.0,
                    message="Test suite timed out after 10 minutes"
                )]
            )
        except Exception as e:
            logger.error(f"Error running test suite {suite_name}: {e}")
            return TestSuiteResult(
                suite_name=suite_config["name"],
                total_tests=0,
                passed=0,
                failed=0,
                skipped=0,
                errors=1,
                duration=0.0,
                timestamp=datetime.now().isoformat(),
                results=[TestResult(
                    test_name="error",
                    test_file="",
                    status="error",
                    duration=0.0,
                    message=str(e)
                )]
            )

    def run_all_tests(
        self,
        suites: List[str] = None,
        verbose: bool = True,
        coverage: bool = False,
        parallel: bool = False
    ) -> TestRunReport:
        """
        Run all test suites or specified suites.

        Args:
            suites: List of suite names to run (None for all)
            verbose: Enable verbose output
            coverage: Enable coverage reporting
            parallel: Run suites in parallel (experimental)

        Returns:
            TestRunReport with complete results
        """
        run_id = self._generate_run_id()
        start_time = datetime.now()

        suites_to_run = suites or list(self.TEST_SUITES.keys())
        suite_results = []

        logger.info(f"Starting test run {run_id} with {len(suites_to_run)} suites")

        for suite_name in suites_to_run:
            try:
                result = self.run_suite(suite_name, verbose, coverage)
                suite_results.append(result)
            except Exception as e:
                logger.error(f"Error running suite {suite_name}: {e}")

        # Calculate totals
        total_tests = sum(s.total_tests for s in suite_results)
        passed = sum(s.passed for s in suite_results)
        failed = sum(s.failed for s in suite_results)
        skipped = sum(s.skipped for s in suite_results)
        errors = sum(s.errors for s in suite_results)
        duration = (datetime.now() - start_time).total_seconds()

        success_rate = (passed / total_tests * 100) if total_tests > 0 else 0.0

        report = TestRunReport(
            run_id=run_id,
            timestamp=datetime.now().isoformat(),
            total_suites=len(suite_results),
            total_tests=total_tests,
            passed=passed,
            failed=failed,
            skipped=skipped,
            errors=errors,
            duration=duration,
            success_rate=round(success_rate, 2),
            suites=suite_results
        )

        # Save report
        self._save_report(report)

        # Track in history
        self.history.append(report)

        # Create Genesis Key for the test run
        try:
            report.genesis_key_id = self._create_genesis_key(report)
        except Exception as e:
            logger.warning(f"Could not create Genesis Key for test run: {e}")

        logger.info(
            f"Test run {run_id} complete: {passed}/{total_tests} passed "
            f"({success_rate:.1f}% success rate) in {duration:.2f}s"
        )

        return report

    def _parse_pytest_output(self, stdout: str, stderr: str) -> List[TestResult]:
        """Parse pytest console output to extract results."""
        results = []

        # Simple parsing of pytest output
        lines = stdout.split('\n')
        for line in lines:
            if '::' in line and (' PASSED' in line or ' FAILED' in line or ' SKIPPED' in line):
                parts = line.split('::')
                if len(parts) >= 2:
                    test_file = parts[0].strip()
                    rest = '::'.join(parts[1:])

                    if ' PASSED' in rest:
                        test_name = rest.split(' PASSED')[0].strip()
                        status = 'passed'
                    elif ' FAILED' in rest:
                        test_name = rest.split(' FAILED')[0].strip()
                        status = 'failed'
                    elif ' SKIPPED' in rest:
                        test_name = rest.split(' SKIPPED')[0].strip()
                        status = 'skipped'
                    else:
                        continue

                    results.append(TestResult(
                        test_name=test_name,
                        test_file=test_file,
                        status=status,
                        duration=0.0
                    ))

        return results

    def _parse_json_report(self, json_data: Dict) -> List[TestResult]:
        """Parse pytest-json-report output."""
        results = []

        tests = json_data.get('tests', [])
        for test in tests:
            results.append(TestResult(
                test_name=test.get('nodeid', '').split('::')[-1],
                test_file=test.get('nodeid', '').split('::')[0],
                status=test.get('outcome', 'unknown'),
                duration=test.get('duration', 0.0),
                message=test.get('call', {}).get('longrepr')
            ))

        return results

    def _save_report(self, report: TestRunReport):
        """Save test report to file."""
        report_path = self.reports_dir / f"{report.run_id}.json"

        # Convert to dict for JSON serialization
        report_dict = {
            'run_id': report.run_id,
            'timestamp': report.timestamp,
            'total_suites': report.total_suites,
            'total_tests': report.total_tests,
            'passed': report.passed,
            'failed': report.failed,
            'skipped': report.skipped,
            'errors': report.errors,
            'duration': report.duration,
            'success_rate': report.success_rate,
            'suites': [
                {
                    'suite_name': s.suite_name,
                    'total_tests': s.total_tests,
                    'passed': s.passed,
                    'failed': s.failed,
                    'skipped': s.skipped,
                    'errors': s.errors,
                    'duration': s.duration,
                    'timestamp': s.timestamp,
                    'results': [
                        {
                            'test_name': r.test_name,
                            'test_file': r.test_file,
                            'status': r.status,
                            'duration': r.duration,
                            'message': r.message
                        }
                        for r in s.results
                    ]
                }
                for s in report.suites
            ]
        }

        with open(report_path, 'w') as f:
            json.dump(report_dict, f, indent=2)

        logger.info(f"Report saved to {report_path}")

    def _create_genesis_key(self, report: TestRunReport) -> Optional[str]:
        """Create Genesis Key for test run."""
        try:
            from genesis.genesis_key_service import GenesisKeyService
            from database.session import get_session

            with get_session() as db:
                service = GenesisKeyService(db)
                key = service.create_genesis_key(
                    entity_type="test_run",
                    entity_id=report.run_id,
                    origin_source="autonomous_test_runner",
                    origin_type="self_test",
                    metadata={
                        'total_tests': report.total_tests,
                        'passed': report.passed,
                        'failed': report.failed,
                        'success_rate': report.success_rate
                    }
                )
                return key.id if key else None
        except Exception as e:
            logger.warning(f"Could not create Genesis Key: {e}")
            return None

    def get_test_history(self, limit: int = 10) -> List[Dict]:
        """Get recent test run history."""
        # Load from saved reports
        reports = []
        report_files = sorted(
            self.reports_dir.glob("test_run_*.json"),
            reverse=True
        )[:limit]

        for report_file in report_files:
            try:
                with open(report_file) as f:
                    reports.append(json.load(f))
            except Exception as e:
                logger.warning(f"Could not load report {report_file}: {e}")

        return reports

    def get_failed_tests(self, run_id: str = None) -> List[Dict]:
        """Get failed tests from a specific run or most recent."""
        if run_id:
            report_path = self.reports_dir / f"{run_id}.json"
        else:
            # Get most recent
            report_files = sorted(self.reports_dir.glob("test_run_*.json"), reverse=True)
            if not report_files:
                return []
            report_path = report_files[0]

        if not report_path.exists():
            return []

        with open(report_path) as f:
            report = json.load(f)

        failed = []
        for suite in report.get('suites', []):
            for result in suite.get('results', []):
                if result.get('status') == 'failed':
                    failed.append({
                        'suite': suite['suite_name'],
                        'test': result['test_name'],
                        'file': result['test_file'],
                        'message': result.get('message')
                    })

        return failed

    def quick_health_check(self) -> Dict[str, Any]:
        """
        Run a quick health check with minimal tests.

        Returns:
            Dict with health check results
        """
        logger.info("Running quick health check...")

        # Run just core tests
        result = self.run_suite("core", verbose=False)

        return {
            'status': 'healthy' if result.failed == 0 else 'unhealthy',
            'tests_run': result.total_tests,
            'passed': result.passed,
            'failed': result.failed,
            'duration': result.duration,
            'timestamp': result.timestamp
        }


# Singleton instance
_test_runner: Optional[AutonomousTestRunner] = None


def get_test_runner() -> AutonomousTestRunner:
    """Get or create the autonomous test runner instance."""
    global _test_runner
    if _test_runner is None:
        _test_runner = AutonomousTestRunner()
    return _test_runner


# CLI interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Grace Autonomous Test Runner")
    parser.add_argument("--suite", "-s", help="Run specific test suite")
    parser.add_argument("--all", "-a", action="store_true", help="Run all test suites")
    parser.add_argument("--quick", "-q", action="store_true", help="Quick health check")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--coverage", "-c", action="store_true", help="Enable coverage")
    parser.add_argument("--history", action="store_true", help="Show test history")
    parser.add_argument("--failed", action="store_true", help="Show failed tests")
    parser.add_argument("--list", "-l", action="store_true", help="List available suites")

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    runner = get_test_runner()

    if args.list:
        print("\nAvailable Test Suites:")
        print("-" * 50)
        for name, config in runner.TEST_SUITES.items():
            print(f"  {name:15} - {config['description']}")
        print()

    elif args.quick:
        result = runner.quick_health_check()
        print(f"\nHealth Check: {result['status'].upper()}")
        print(f"Tests: {result['passed']}/{result['tests_run']} passed")
        print(f"Duration: {result['duration']:.2f}s")

    elif args.history:
        history = runner.get_test_history()
        print("\nRecent Test Runs:")
        print("-" * 60)
        for run in history:
            print(f"  {run['run_id']}: {run['passed']}/{run['total_tests']} passed "
                  f"({run['success_rate']}%) - {run['duration']:.2f}s")

    elif args.failed:
        failed = runner.get_failed_tests()
        if failed:
            print("\nFailed Tests:")
            print("-" * 60)
            for test in failed:
                print(f"  [{test['suite']}] {test['file']}::{test['test']}")
                if test.get('message'):
                    print(f"    -> {test['message'][:100]}...")
        else:
            print("\nNo failed tests!")

    elif args.suite:
        result = runner.run_suite(args.suite, verbose=args.verbose, coverage=args.coverage)
        print(f"\nSuite: {result.suite_name}")
        print(f"Tests: {result.passed}/{result.total_tests} passed")
        print(f"Failed: {result.failed}, Skipped: {result.skipped}")
        print(f"Duration: {result.duration:.2f}s")

    elif args.all:
        report = runner.run_all_tests(verbose=args.verbose, coverage=args.coverage)
        print(f"\n{'='*60}")
        print(f"TEST RUN COMPLETE: {report.run_id}")
        print(f"{'='*60}")
        print(f"Total Tests: {report.total_tests}")
        print(f"Passed: {report.passed}")
        print(f"Failed: {report.failed}")
        print(f"Skipped: {report.skipped}")
        print(f"Success Rate: {report.success_rate}%")
        print(f"Duration: {report.duration:.2f}s")
        print(f"{'='*60}")

    else:
        parser.print_help()
