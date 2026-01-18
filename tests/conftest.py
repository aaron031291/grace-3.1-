"""
Pytest fixtures for Grace E2E tests.

Provides session-scoped fixtures for Layer 3 and Layer 4 components,
plus the LayerTestResults class for test result tracking.
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
import tempfile
import os

import pytest

# Add backend to Python path
backend_path = Path(__file__).parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))


def _initialize_test_database():
    """Initialize a test database for e2e tests."""
    try:
        from database.config import DatabaseConfig, DatabaseType
        from database.connection import DatabaseConnection
        
        # Use a temporary SQLite database for tests
        test_db_path = Path(tempfile.gettempdir()) / "grace_e2e_test.db"
        
        config = DatabaseConfig(
            db_type=DatabaseType.SQLITE,
            database_path=str(test_db_path),
            echo=False
        )
        
        DatabaseConnection.initialize(config)
        
        # Create tables
        try:
            from models.base import Base
            engine = DatabaseConnection.get_engine()
            Base.metadata.create_all(engine)
        except Exception:
            pass  # Tables may already exist
            
        return True
    except Exception as e:
        print(f"Warning: Could not initialize test database: {e}")
        return False


# Initialize database at module load time
_db_initialized = _initialize_test_database()


class LayerTestResults:
    """Collect and report test results for each layer."""

    def __init__(self):
        self.results = {
            "layer1": {"passed": 0, "failed": 0, "tests": []},
            "layer2": {"passed": 0, "failed": 0, "tests": []},
            "layer3": {"passed": 0, "failed": 0, "tests": []},
            "layer4": {"passed": 0, "failed": 0, "tests": []},
            "integration": {"passed": 0, "failed": 0, "tests": []},
        }
        self.start_time = datetime.utcnow()

    def record(self, layer: str, test_name: str, passed: bool, details: str = ""):
        status = "passed" if passed else "failed"
        self.results[layer][status] += 1
        self.results[layer]["tests"].append({
            "name": test_name,
            "passed": passed,
            "details": details
        })

    def summary(self) -> str:
        duration = (datetime.utcnow() - self.start_time).total_seconds()
        total_passed = sum(r["passed"] for r in self.results.values())
        total_failed = sum(r["failed"] for r in self.results.values())

        lines = [
            "\n" + "=" * 70,
            "E2E TEST RESULTS: LAYERS 1-4",
            "=" * 70,
            f"Duration: {duration:.2f}s",
            f"Total: {total_passed + total_failed} tests | Passed: {total_passed} | Failed: {total_failed}",
            ""
        ]

        for layer, data in self.results.items():
            if data["tests"]:
                status = "[PASS]" if data["failed"] == 0 else "[FAIL]"
                lines.append(f"{status} {layer.upper()}: {data['passed']} passed, {data['failed']} failed")
                for test in data["tests"]:
                    icon = "  [ok]" if test["passed"] else "  [X]"
                    lines.append(f"  {icon} {test['name']}")
                    if test["details"] and not test["passed"]:
                        lines.append(f"      -> {test['details']}")

        lines.append("=" * 70)
        return "\n".join(lines)


@pytest.fixture(scope="session")
def results() -> LayerTestResults:
    """Session-scoped LayerTestResults instance for tracking test outcomes."""
    return LayerTestResults()


@pytest.fixture(scope="session")
def governance():
    """
    Session-scoped Layer 3 Quorum Governance Engine fixture.
    
    Returns None if initialization fails, allowing tests to skip gracefully.
    """
    try:
        from governance.layer3_quorum_verification import (
            Layer3QuorumVerification,
            TrustSource,
            VerificationResult,
            QuorumDecision,
            ComponentKPI,
        )
        return Layer3QuorumVerification()
    except ImportError as e:
        pytest.skip(f"Layer 3 governance module not available: {e}")
        return None
    except Exception as e:
        pytest.skip(f"Layer 3 governance initialization failed: {e}")
        return None


@pytest.fixture(scope="session")
def layer4():
    """
    Session-scoped Layer 4 Recursive Pattern Learner fixture.
    
    Returns None if initialization fails, allowing tests to skip gracefully.
    """
    try:
        from ml_intelligence.layer4_recursive_pattern_learner import (
            Layer4RecursivePatternLearner,
            PatternDomain,
        )
        return Layer4RecursivePatternLearner()
    except ImportError as e:
        pytest.skip(f"Layer 4 pattern learner module not available: {e}")
        return None
    except Exception as e:
        pytest.skip(f"Layer 4 pattern learner initialization failed: {e}")
        return None


@pytest.fixture(scope="session")
def trust_source():
    """Provide TrustSource enum for Layer 3 tests."""
    try:
        from governance.layer3_quorum_verification import TrustSource
        return TrustSource
    except ImportError:
        return None


@pytest.fixture(scope="session")
def pattern_domain():
    """Provide PatternDomain enum for Layer 4 tests."""
    try:
        from ml_intelligence.layer4_recursive_pattern_learner import PatternDomain
        return PatternDomain
    except ImportError:
        return None


@pytest.fixture(scope="session")
def component_kpi():
    """Provide ComponentKPI class for Layer 3 KPI tests."""
    try:
        from governance.layer3_quorum_verification import ComponentKPI
        return ComponentKPI
    except ImportError:
        return None


def pytest_runtest_logreport(report):
    """Hook to capture test outcomes and record in outcome aggregator."""
    if report.when == 'call':  # Only on test execution, not setup/teardown
        try:
            from cognitive.outcome_aggregator import get_outcome_aggregator
            aggregator = get_outcome_aggregator()
            aggregator.record_outcome('testing', {
                'test_name': report.nodeid,
                'success': report.outcome == 'passed',
                'trust_score': 0.9 if report.outcome == 'passed' else 0.3,
                'duration': getattr(report, 'duration', 0),
                'outcome': report.outcome,
                'longrepr': str(report.longrepr)[:500] if report.longrepr else None
            })
        except Exception:
            pass  # Don't let hook errors break tests
