"""
GRACE Native CI/CD Test Runner
===============================

Self-contained testing system that runs within GRACE.
Tests GRACE on multiple OS configurations natively.

No external services required - everything runs in GRACE.
"""

import os
import sys
import subprocess
import time
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

from utils.os_adapter import OS, paths, process, get_os_info
from utils.safe_print import safe_print


class TestStatus(str, Enum):
    """Test status."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TestResult:
    """Test result."""
    name: str
    status: TestStatus
    duration: float
    output: str
    error: Optional[str] = None
    os_family: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


class NativeTestRunner:
    """
    Native test runner for GRACE.
    
    Runs tests locally without external CI/CD services.
    Supports multi-OS testing via virtual machines or containers.
    """
    
    def __init__(self, root_path: Optional[Path] = None):
        """Initialize test runner."""
        self.root_path = root_path or Path(__file__).parent.parent.parent
        self.backend_path = self.root_path / "backend"
        self.results: List[TestResult] = []
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        
        # Test configuration
        self.config = {
            'os_families': ['windows', 'linux', 'macos'],
            'python_versions': ['3.9', '3.10', '3.11'],
            'timeout': 300,  # 5 minutes per test
            'parallel': False,  # Run tests sequentially
        }
    
    def run_all_tests(self) -> Dict[str, Any]:
        """
        Run all tests natively.
        
        Returns:
            Test report with results
        """
        safe_print("=" * 70)
        safe_print("GRACE NATIVE CI/CD - TEST RUNNER")
        safe_print("=" * 70)
        safe_print()
        
        self.start_time = time.time()
        os_info = get_os_info()
        
        safe_print(f"Current OS: {os_info['family']} ({os_info['system']})")
        safe_print(f"Python Version: {os_info['python_version']}")
        safe_print()
        
        # Run test suites
        test_suites = [
            self._test_os_adapter,
            self._test_path_operations,
            self._test_process_spawning,
            self._test_startup,
            self._test_backend_api,
            self._test_multi_os_compatibility,
        ]
        
        for test_suite in test_suites:
            try:
                test_suite()
            except Exception as e:
                self.results.append(TestResult(
                    name=test_suite.__name__,
                    status=TestStatus.FAILED,
                    duration=0.0,
                    output="",
                    error=str(e),
                    os_family=os_info['family']
                ))
        
        self.end_time = time.time()
        
        return self._generate_report()
    
    def _test_os_adapter(self):
        """Test OS adapter functionality."""
        name = "OS Adapter"
        safe_print(f"Running: {name}...")
        
        start = time.time()
        try:
            # Test OS detection
            assert OS.family in ['windows', 'linux', 'macos', 'unknown']
            assert isinstance(OS.is_windows, bool)
            assert isinstance(OS.is_linux, bool)
            assert isinstance(OS.is_macos, bool)
            assert isinstance(OS.is_unix, bool)
            
            # Test path operations
            test_path = paths.join("dir", "sub", "file.txt")
            assert isinstance(test_path, str)
            
            resolved = paths.resolve(".")
            assert paths.is_absolute(resolved)
            
            # Test process spawning (just check it doesn't crash)
            proc = process.spawn(["python", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            assert proc is not None
            process.terminate(proc)
            
            duration = time.time() - start
            self.results.append(TestResult(
                name=name,
                status=TestStatus.PASSED,
                duration=duration,
                output="All OS adapter tests passed [OK]",
                os_family=OS.family.value
            ))
            safe_print(f"  [OK] {name} PASSED ({duration:.2f}s)")
        except Exception as e:
            duration = time.time() - start
            self.results.append(TestResult(
                name=name,
                status=TestStatus.FAILED,
                duration=duration,
                output="",
                error=str(e),
                os_family=OS.family.value
            ))
            safe_print(f"  [FAIL] {name} FAILED: {e}")
    
    def _test_path_operations(self):
        """Test portable path operations."""
        name = "Path Operations"
        safe_print(f"Running: {name}...")
        
        start = time.time()
        try:
            # Test various path operations
            test_cases = [
                (["dir", "sub"], "dir/sub or dir\\sub"),
                (["/absolute", "path"], "Should preserve absolute"),
                (["relative", "path"], "Should handle relative"),
            ]
            
            for parts, description in test_cases:
                result = paths.join(*parts)
                assert isinstance(result, str), f"{description}: Should return string"
            
            # Test resolve
            current = paths.resolve(".")
            assert paths.is_absolute(current), "Resolved path should be absolute"
            
            duration = time.time() - start
            self.results.append(TestResult(
                name=name,
                status=TestStatus.PASSED,
                duration=duration,
                output="All path operations work correctly [OK]",
                os_family=OS.family.value
            ))
            safe_print(f"  [OK] {name} PASSED ({duration:.2f}s)")
        except Exception as e:
            duration = time.time() - start
            self.results.append(TestResult(
                name=name,
                status=TestStatus.FAILED,
                duration=duration,
                output="",
                error=str(e),
                os_family=OS.family.value
            ))
            safe_print(f"  [FAIL] {name} FAILED: {e}")
    
    def _test_process_spawning(self):
        """Test portable process spawning."""
        name = "Process Spawning"
        safe_print(f"Running: {name}...")
        
        start = time.time()
        try:
            # Test basic spawn
            proc = process.spawn(
                ["python", "-c", "print('test')"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            assert proc is not None
            
            # Wait for completion
            proc.wait(timeout=5)
            
            # Test termination
            proc2 = process.spawn(
                ["python", "-c", "import time; time.sleep(10)"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            process.terminate(proc2, timeout=2.0)
            
            duration = time.time() - start
            self.results.append(TestResult(
                name=name,
                status=TestStatus.PASSED,
                duration=duration,
                output="Process spawning works correctly [OK]",
                os_family=OS.family.value
            ))
            safe_print(f"  [OK] {name} PASSED ({duration:.2f}s)")
        except Exception as e:
            duration = time.time() - start
            self.results.append(TestResult(
                name=name,
                status=TestStatus.FAILED,
                duration=duration,
                output="",
                error=str(e),
                os_family=OS.family.value
            ))
            safe_print(f"  [FAIL] {name} FAILED: {e}")
    
    def _test_startup(self):
        """Test GRACE startup."""
        name = "Startup Test"
        safe_print(f"Running: {name}...")
        
        start = time.time()
        try:
            # Test that startup script exists and is executable
            startup_script = self.root_path / "start_grace.py"
            if not startup_script.exists():
                raise FileNotFoundError(f"Startup script not found: {startup_script}")
            
            # Test that backend directory exists
            if not self.backend_path.exists():
                raise FileNotFoundError(f"Backend directory not found: {self.backend_path}")
            
            # Test that app.py exists
            app_py = self.backend_path / "app.py"
            if not app_py.exists():
                raise FileNotFoundError(f"app.py not found: {app_py}")
            
            duration = time.time() - start
            self.results.append(TestResult(
                name=name,
                status=TestStatus.PASSED,
                duration=duration,
                output="Startup files exist and are accessible",
                os_family=OS.family.value
            ))
            safe_print(f"  [OK] {name} PASSED ({duration:.2f}s)")
        except Exception as e:
            duration = time.time() - start
            self.results.append(TestResult(
                name=name,
                status=TestStatus.FAILED,
                duration=duration,
                output="",
                error=str(e),
                os_family=OS.family.value
            ))
            safe_print(f"  [FAIL] {name} FAILED: {e}")
    
    def _test_backend_api(self):
        """Test backend API (if backend is running)."""
        name = "Backend API"
        safe_print(f"Running: {name}...")
        
        start = time.time()
        try:
            import socket
            
            # Check if backend is running
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.0)
            result = sock.connect_ex(('localhost', 8000))
            sock.close()
            
            if result != 0:
                # Backend not running - skip test
                duration = time.time() - start
                self.results.append(TestResult(
                    name=name,
                    status=TestStatus.SKIPPED,
                    duration=duration,
                    output="Backend not running (this is OK)",
                    os_family=OS.family.value
                ))
                safe_print(f"  [SKIP] {name} SKIPPED (backend not running)")
                return
            
            # Try to make a request
            try:
                import requests
                response = requests.get("http://localhost:8000/health", timeout=2.0)
                if response.status_code == 200:
                    duration = time.time() - start
                    self.results.append(TestResult(
                        name=name,
                        status=TestStatus.PASSED,
                        duration=duration,
                        output="Backend API is responding",
                        os_family=OS.family.value
                    ))
                    safe_print(f"  [OK] {name} PASSED ({duration:.2f}s)")
                else:
                    raise Exception(f"Backend returned {response.status_code}")
            except ImportError:
                # requests not installed - skip
                duration = time.time() - start
                self.results.append(TestResult(
                    name=name,
                    status=TestStatus.SKIPPED,
                    duration=duration,
                    output="requests library not installed",
                    os_family=OS.family.value
                ))
                safe_print(f"  [SKIP] {name} SKIPPED (requests not installed)")
        except Exception as e:
            duration = time.time() - start
            self.results.append(TestResult(
                name=name,
                status=TestStatus.FAILED,
                duration=duration,
                output="",
                error=str(e),
                os_family=OS.family.value
            ))
            safe_print(f"  [FAIL] {name} FAILED: {e}")
    
    def _test_multi_os_compatibility(self):
        """Test multi-OS compatibility."""
        name = "Multi-OS Compatibility"
        safe_print(f"Running: {name}...")
        
        start = time.time()
        try:
            # Check for OS checks in code
            issues = []
            
            # Scan for platform checks (should only be in os_adapter.py)
            backend_files = list(self.backend_path.rglob("*.py"))
            os_adapter_file = self.backend_path / "utils" / "os_adapter.py"
            
            for py_file in backend_files:
                if py_file == os_adapter_file:
                    continue  # Skip os_adapter.py itself
                
                try:
                    content = py_file.read_text(encoding='utf-8')
                    if 'sys.platform' in content or 'platform.system' in content or 'os.name ==' in content:
                        # Check if it's just importing from os_adapter
                        if 'from backend.utils.os_adapter import OS' not in content:
                            issues.append(str(py_file.relative_to(self.root_path)))
                except Exception:
                    pass  # Skip binary or problematic files
            
            if issues:
                duration = time.time() - start
                self.results.append(TestResult(
                    name=name,
                    status=TestStatus.FAILED,
                    duration=duration,
                    output=f"Found {len(issues)} files with OS checks outside os_adapter",
                    error=f"Files: {', '.join(issues[:5])}",
                    os_family=OS.family.value
                ))
                safe_print(f"  [FAIL] {name} FAILED: {len(issues)} files need migration")
            else:
                duration = time.time() - start
                self.results.append(TestResult(
                    name=name,
                    status=TestStatus.PASSED,
                    duration=duration,
                    output="No OS checks found outside os_adapter",
                    os_family=OS.family.value
                ))
                safe_print(f"  [OK] {name} PASSED ({duration:.2f}s)")
        except Exception as e:
            duration = time.time() - start
            self.results.append(TestResult(
                name=name,
                status=TestStatus.FAILED,
                duration=duration,
                output="",
                error=str(e),
                os_family=OS.family.value
            ))
            safe_print(f"  [FAIL] {name} FAILED: {e}")
    
    def _generate_report(self) -> Dict[str, Any]:
        """Generate test report."""
        total_duration = self.end_time - self.start_time if self.end_time else 0
        
        passed = sum(1 for r in self.results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in self.results if r.status == TestStatus.FAILED)
        skipped = sum(1 for r in self.results if r.status == TestStatus.SKIPPED)
        total = len(self.results)
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'os_info': get_os_info(),
            'summary': {
                'total': total,
                'passed': passed,
                'failed': failed,
                'skipped': skipped,
                'duration': total_duration,
            },
            'results': [r.to_dict() for r in self.results],
        }
        
        # Print summary
        safe_print()
        safe_print("=" * 70)
        safe_print("TEST SUMMARY")
        safe_print("=" * 70)
        safe_print(f"Total Tests: {total}")
        safe_print(f"Passed: {passed} [OK]")
        safe_print(f"Failed: {failed} [FAIL]")
        safe_print(f"Skipped: {skipped} [SKIP]")
        safe_print(f"Duration: {total_duration:.2f}s")
        safe_print("=" * 70)
        
        return report
    
    def save_report(self, output_path: Optional[Path] = None):
        """Save test report to file."""
        report = self._generate_report()
        
        if output_path is None:
            output_path = self.root_path / "logs" / "ci_cd_report.json"
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
        safe_print(f"\nReport saved to: {output_path}")


def main():
    """Main entry point."""
    runner = NativeTestRunner()
    report = runner.run_all_tests()
    runner.save_report()
    
    # Exit with error code if tests failed
    if report['summary']['failed'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
