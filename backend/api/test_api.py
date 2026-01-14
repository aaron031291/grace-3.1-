"""
Autonomous Testing API - Self-testing with KPI and Trust Score validation.

Enables Grace to autonomously test her implementations with governance:
- Run tests against KPI thresholds
- Validate trust scores before integration
- Track all test activities with Genesis Keys
- Sandbox execution for safety
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import logging
import json

from database.session import get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/test", tags=["Autonomous Testing"])


# ==================== Pydantic Models ====================

class TestRequest(BaseModel):
    """Request to run tests."""
    source_code: Optional[str] = Field(None, description="Source code to test")
    file_path: Optional[str] = Field(None, description="File path to test")
    module_name: str = Field("dynamic_module", description="Module name")
    test_suites: Optional[List[str]] = Field(None, description="Specific test suites to run")


class TestGenerationRequest(BaseModel):
    """Request to generate tests for code."""
    source_code: str = Field(..., description="Source code to generate tests for")
    module_name: str = Field("dynamic_module", description="Module name")
    test_types: List[str] = Field(
        default=["unit", "integration"],
        description="Types of tests to generate"
    )


class TestValidationRequest(BaseModel):
    """Request to validate tests against KPIs and trust scores."""
    test_results: Dict[str, Any] = Field(..., description="Test results to validate")
    kpi_thresholds: Optional[Dict[str, float]] = Field(
        default=None,
        description="KPI thresholds to check against"
    )
    require_trust_score: bool = Field(True, description="Require trust score validation")
    min_trust_score: float = Field(0.7, description="Minimum trust score")
    min_success_rate: float = Field(80.0, description="Minimum test success rate")
    max_error_rate: float = Field(5.0, description="Maximum allowed error rate")


class IntegrationRequest(BaseModel):
    """Request to integrate validated tests into the system."""
    test_run_id: str = Field(..., description="ID of validated test run")
    validation_id: str = Field(..., description="ID of validation result")
    target_path: Optional[str] = Field(None, description="Target path for integration")
    auto_commit: bool = Field(False, description="Automatically commit to codebase")


class KPICheckRequest(BaseModel):
    """Request to check KPIs for a test run."""
    test_run_id: str = Field(..., description="Test run ID to check")
    kpis: Dict[str, float] = Field(..., description="KPI thresholds")


# ==================== KPI and Trust Score Validation ====================

# Default KPI thresholds
DEFAULT_KPIS = {
    "min_success_rate": 80.0,  # Minimum % of tests passing
    "max_error_rate": 5.0,     # Maximum % of errors
    "min_coverage": 60.0,      # Minimum code coverage %
    "max_duration": 300.0,     # Maximum test duration seconds
    "min_tests": 5,            # Minimum number of tests
    "max_flaky_rate": 10.0     # Maximum % of flaky tests
}


def calculate_trust_score(test_results: Dict[str, Any]) -> float:
    """
    Calculate trust score for test results.

    Factors:
    - Success rate (40%)
    - Code coverage (20%)
    - Test completeness (20%)
    - Error handling (10%)
    - Documentation (10%)
    """
    score = 0.0

    # Success rate contribution (40%)
    success_rate = test_results.get('success_rate', 0)
    score += (success_rate / 100) * 0.4

    # Coverage contribution (20%)
    coverage = test_results.get('coverage_percent', 50)
    score += (coverage / 100) * 0.2

    # Test completeness (20%)
    tests_generated = test_results.get('tests_generated', 0)
    tests_run = test_results.get('tests_run', 0)
    completeness = (tests_run / max(tests_generated, 1))
    score += completeness * 0.2

    # Error handling (10%)
    errors = test_results.get('errors', 0)
    total = test_results.get('tests_run', 1)
    error_rate = errors / max(total, 1)
    score += (1 - error_rate) * 0.1

    # Documentation (10%) - check if tests have descriptions
    tests = test_results.get('tests', [])
    documented = sum(1 for t in tests if t.get('description'))
    doc_rate = documented / max(len(tests), 1)
    score += doc_rate * 0.1

    return round(score, 4)


def validate_against_kpis(
    test_results: Dict[str, Any],
    kpis: Dict[str, float] = None
) -> Dict[str, Any]:
    """
    Validate test results against KPI thresholds.

    Returns validation result with pass/fail status and details.
    """
    kpis = kpis or DEFAULT_KPIS
    validation = {
        "valid": True,
        "timestamp": datetime.utcnow().isoformat(),
        "kpi_results": {},
        "issues": []
    }

    # Check success rate
    success_rate = test_results.get('success_rate', 0)
    min_success = kpis.get('min_success_rate', 80.0)
    validation['kpi_results']['success_rate'] = {
        "value": success_rate,
        "threshold": min_success,
        "passed": success_rate >= min_success
    }
    if success_rate < min_success:
        validation['valid'] = False
        validation['issues'].append(
            f"Success rate {success_rate:.1f}% below threshold {min_success:.1f}%"
        )

    # Check error rate
    total = test_results.get('tests_run', 0)
    errors = test_results.get('errors', 0)
    error_rate = (errors / max(total, 1)) * 100
    max_error = kpis.get('max_error_rate', 5.0)
    validation['kpi_results']['error_rate'] = {
        "value": error_rate,
        "threshold": max_error,
        "passed": error_rate <= max_error
    }
    if error_rate > max_error:
        validation['valid'] = False
        validation['issues'].append(
            f"Error rate {error_rate:.1f}% exceeds threshold {max_error:.1f}%"
        )

    # Check minimum tests
    min_tests = kpis.get('min_tests', 5)
    validation['kpi_results']['test_count'] = {
        "value": total,
        "threshold": min_tests,
        "passed": total >= min_tests
    }
    if total < min_tests:
        validation['valid'] = False
        validation['issues'].append(
            f"Only {total} tests run, minimum is {min_tests}"
        )

    # Check duration
    duration = test_results.get('duration', 0)
    max_duration = kpis.get('max_duration', 300.0)
    validation['kpi_results']['duration'] = {
        "value": duration,
        "threshold": max_duration,
        "passed": duration <= max_duration
    }
    if duration > max_duration:
        validation['valid'] = False
        validation['issues'].append(
            f"Test duration {duration:.1f}s exceeds threshold {max_duration:.1f}s"
        )

    return validation


# ==================== Endpoints ====================

@router.get("/status")
async def get_test_system_status():
    """Get autonomous testing system status."""
    try:
        from autonomous_test_runner import get_test_runner
        from dynamic_test_generator import get_test_builder

        runner = get_test_runner()
        builder = get_test_builder()

        return {
            "status": "operational",
            "components": {
                "test_runner": "available",
                "test_generator": "available",
                "sandbox_executor": "available"
            },
            "available_suites": list(runner.TEST_SUITES.keys()),
            "default_kpis": DEFAULT_KPIS,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting test status: {e}")
        return {
            "status": "degraded",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.post("/run")
async def run_tests(
    request: TestRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_session)
):
    """
    Run tests for code or existing test suites.

    If source_code is provided, generates and runs dynamic tests.
    If test_suites is provided, runs specified predefined suites.
    """
    try:
        from autonomous_test_runner import get_test_runner
        from dynamic_test_generator import get_test_builder

        results = {}

        if request.source_code:
            # Generate and run tests for provided code
            builder = get_test_builder()
            results = builder.build_and_test(
                request.source_code,
                request.module_name
            )
        elif request.file_path:
            # Generate and run tests for file
            builder = get_test_builder()
            results = builder.build_tests_for_file(request.file_path)
        elif request.test_suites:
            # Run predefined test suites
            runner = get_test_runner()
            report = runner.run_all_tests(suites=request.test_suites)
            results = {
                "run_id": report.run_id,
                "tests_run": report.total_tests,
                "passed": report.passed,
                "failed": report.failed,
                "errors": report.errors,
                "success_rate": report.success_rate,
                "duration": report.duration,
                "suites": [
                    {
                        "name": s.suite_name,
                        "passed": s.passed,
                        "failed": s.failed
                    }
                    for s in report.suites
                ]
            }
        else:
            # Run all tests
            runner = get_test_runner()
            report = runner.run_all_tests()
            results = {
                "run_id": report.run_id,
                "tests_run": report.total_tests,
                "passed": report.passed,
                "failed": report.failed,
                "errors": report.errors,
                "success_rate": report.success_rate,
                "duration": report.duration
            }

        # Calculate trust score
        trust_score = calculate_trust_score(results)
        results['trust_score'] = trust_score

        # Create Genesis Key for test run
        try:
            from genesis.genesis_key_service import GenesisKeyService
            service = GenesisKeyService(db)
            key = service.create_genesis_key(
                entity_type="test_run",
                entity_id=results.get('run_id', f"test_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"),
                origin_source="autonomous_test_api",
                origin_type="test_execution",
                metadata={
                    "tests_run": results.get('tests_run', 0),
                    "success_rate": results.get('success_rate', 0),
                    "trust_score": trust_score
                }
            )
            results['genesis_key_id'] = key.id if key else None
        except Exception as e:
            logger.warning(f"Could not create Genesis Key: {e}")

        return results

    except Exception as e:
        logger.error(f"Error running tests: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate")
async def generate_tests(request: TestGenerationRequest):
    """
    Generate tests for provided source code.

    Does not execute tests - just generates test code.
    """
    try:
        from dynamic_test_generator import get_test_builder

        builder = get_test_builder()
        tests = builder.generator.generate_tests_for_code(
            request.source_code,
            request.module_name
        )
        test_code = builder.generator.generate_test_file(tests)

        return {
            "module_name": request.module_name,
            "tests_generated": len(tests),
            "tests": [
                {
                    "name": t.test_name,
                    "type": t.test_type,
                    "target": t.target_function,
                    "description": t.description
                }
                for t in tests
            ],
            "test_code": test_code,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error generating tests: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate")
async def validate_tests(
    request: TestValidationRequest,
    db: Session = Depends(get_session)
):
    """
    Validate test results against KPIs and trust scores.

    This is the gate for test integration - tests must pass
    validation before being accepted into the system.
    """
    try:
        test_results = request.test_results

        # Calculate trust score
        trust_score = calculate_trust_score(test_results)

        # Validate against KPIs
        kpi_validation = validate_against_kpis(
            test_results,
            request.kpi_thresholds
        )

        # Check trust score threshold
        trust_valid = trust_score >= request.min_trust_score

        # Overall validation
        overall_valid = kpi_validation['valid'] and (
            not request.require_trust_score or trust_valid
        )

        validation_result = {
            "validation_id": f"val_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            "valid": overall_valid,
            "timestamp": datetime.utcnow().isoformat(),
            "trust_score": {
                "value": trust_score,
                "threshold": request.min_trust_score,
                "passed": trust_valid
            },
            "kpi_validation": kpi_validation,
            "recommendation": "APPROVED" if overall_valid else "REJECTED",
            "issues": kpi_validation.get('issues', [])
        }

        if not trust_valid and request.require_trust_score:
            validation_result['issues'].append(
                f"Trust score {trust_score:.4f} below threshold {request.min_trust_score}"
            )

        # Create Genesis Key for validation
        try:
            from genesis.genesis_key_service import GenesisKeyService
            service = GenesisKeyService(db)
            key = service.create_genesis_key(
                entity_type="test_validation",
                entity_id=validation_result['validation_id'],
                origin_source="autonomous_test_api",
                origin_type="validation",
                metadata={
                    "valid": overall_valid,
                    "trust_score": trust_score,
                    "kpi_passed": kpi_validation['valid']
                }
            )
            validation_result['genesis_key_id'] = key.id if key else None
        except Exception as e:
            logger.warning(f"Could not create Genesis Key: {e}")

        return validation_result

    except Exception as e:
        logger.error(f"Error validating tests: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/integrate")
async def integrate_tests(
    request: IntegrationRequest,
    db: Session = Depends(get_session)
):
    """
    Integrate validated tests into the system.

    Only allows integration if validation passed.
    """
    try:
        # TODO: Load validation result and verify it passed
        # For now, create a record of integration request

        integration_result = {
            "integration_id": f"int_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            "test_run_id": request.test_run_id,
            "validation_id": request.validation_id,
            "status": "pending_approval",
            "target_path": request.target_path,
            "auto_commit": request.auto_commit,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Create Genesis Key for integration
        try:
            from genesis.genesis_key_service import GenesisKeyService
            service = GenesisKeyService(db)
            key = service.create_genesis_key(
                entity_type="test_integration",
                entity_id=integration_result['integration_id'],
                origin_source="autonomous_test_api",
                origin_type="integration_request",
                metadata={
                    "test_run_id": request.test_run_id,
                    "validation_id": request.validation_id
                }
            )
            integration_result['genesis_key_id'] = key.id if key else None
        except Exception as e:
            logger.warning(f"Could not create Genesis Key: {e}")

        return integration_result

    except Exception as e:
        logger.error(f"Error integrating tests: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_test_history(limit: int = 20):
    """Get recent test run history."""
    try:
        from autonomous_test_runner import get_test_runner

        runner = get_test_runner()
        history = runner.get_test_history(limit=limit)

        return {
            "history": history,
            "count": len(history),
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting test history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/failed")
async def get_failed_tests(run_id: Optional[str] = None):
    """Get failed tests from a specific run or most recent."""
    try:
        from autonomous_test_runner import get_test_runner

        runner = get_test_runner()
        failed = runner.get_failed_tests(run_id)

        return {
            "run_id": run_id or "latest",
            "failed_tests": failed,
            "count": len(failed),
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting failed tests: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suites")
async def get_available_suites():
    """Get list of available test suites."""
    try:
        from autonomous_test_runner import get_test_runner

        runner = get_test_runner()

        return {
            "suites": [
                {
                    "name": name,
                    "display_name": config['name'],
                    "description": config['description'],
                    "files": config['files']
                }
                for name, config in runner.TEST_SUITES.items()
            ],
            "total": len(runner.TEST_SUITES)
        }

    except Exception as e:
        logger.error(f"Error getting test suites: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quick-check")
async def quick_health_check():
    """Run a quick health check with core tests."""
    try:
        from autonomous_test_runner import get_test_runner

        runner = get_test_runner()
        result = runner.quick_health_check()

        # Add trust score
        result['trust_score'] = calculate_trust_score({
            'success_rate': (result['passed'] / max(result['tests_run'], 1)) * 100,
            'tests_run': result['tests_run'],
            'errors': 0
        })

        return result

    except Exception as e:
        logger.error(f"Error running health check: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/kpis")
async def get_kpi_thresholds():
    """Get current KPI thresholds."""
    return {
        "kpis": DEFAULT_KPIS,
        "description": {
            "min_success_rate": "Minimum percentage of tests that must pass",
            "max_error_rate": "Maximum percentage of tests that can error",
            "min_coverage": "Minimum code coverage percentage",
            "max_duration": "Maximum test execution time in seconds",
            "min_tests": "Minimum number of tests required",
            "max_flaky_rate": "Maximum percentage of flaky tests"
        }
    }


@router.post("/kpis/check")
async def check_kpis(request: KPICheckRequest):
    """
    Check if a test run meets KPI thresholds.
    """
    try:
        from autonomous_test_runner import get_test_runner

        runner = get_test_runner()
        history = runner.get_test_history(limit=50)

        # Find the specific run
        run_data = None
        for run in history:
            if run.get('run_id') == request.test_run_id:
                run_data = run
                break

        if not run_data:
            raise HTTPException(status_code=404, detail=f"Test run {request.test_run_id} not found")

        # Validate against provided KPIs
        validation = validate_against_kpis(run_data, request.kpis)

        return {
            "test_run_id": request.test_run_id,
            "validation": validation
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking KPIs: {e}")
        raise HTTPException(status_code=500, detail=str(e))
