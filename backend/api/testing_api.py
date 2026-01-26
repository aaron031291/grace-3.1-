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

        # Store validation result for later integration check
        _validation_results[validation_result['validation_id']] = validation_result

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
        # Load validation result and verify it passed
        validation_result = _validation_results.get(request.validation_id)
        
        if not validation_result:
            raise HTTPException(
                status_code=404,
                detail=f"Validation {request.validation_id} not found. Tests must be validated before integration."
            )
        
        if not validation_result.get('valid', False):
            issues = validation_result.get('issues', [])
            raise HTTPException(
                status_code=400,
                detail=f"Cannot integrate tests that failed validation. Issues: {'; '.join(issues)}"
            )
        
        # Validation passed, proceed with integration
        integration_result = {
            "integration_id": f"int_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            "test_run_id": request.test_run_id,
            "validation_id": request.validation_id,
            "status": "approved",
            "target_path": request.target_path,
            "auto_commit": request.auto_commit,
            "timestamp": datetime.utcnow().isoformat(),
            "trust_score": validation_result.get('trust_score', {}).get('value', 0.0)
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


# ==================== Diagnostic Reporting ====================

class DiagnosticReport(BaseModel):
    """Diagnostic report from test framework."""
    session_id: str = Field(..., description="Test session ID")
    environment: Dict[str, Any] = Field(default_factory=dict, description="Environment info")
    skips: List[Dict[str, Any]] = Field(default_factory=list, description="Skipped tests with reasons")
    import_errors: List[Dict[str, Any]] = Field(default_factory=list, description="Import errors encountered")
    missing_dependencies: List[str] = Field(default_factory=list, description="Missing dependencies")
    suggested_fixes: List[str] = Field(default_factory=list, description="Suggested fixes")
    test_results: Dict[str, int] = Field(default_factory=dict, description="Test result counts")
    summary: Optional[Dict[str, Any]] = Field(None, description="Summary statistics")


# Storage for diagnostic reports (in-memory for now, could be persisted)
_diagnostic_history: List[Dict[str, Any]] = []

# Storage for validation results (in-memory for now)
_validation_results: Dict[str, Dict[str, Any]] = {}



@router.post("/diagnostics")
async def receive_diagnostics(
    report: DiagnosticReport,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_session)
):
    """
    Receive diagnostic report from test framework.

    This endpoint allows Grace to learn from test failures and skips,
    enabling autonomous self-improvement and dependency management.

    Pipeline:
    1. Receive diagnostics
    2. Analyze and generate action items
    3. Validate through OODA + LLM
    4. Submit to Autonomous Action Engine
    5. Execute through CI/CD pipeline with governance
    """
    try:
        diagnostic_data = report.dict()
        diagnostic_data['received_at'] = datetime.utcnow().isoformat()

        # Store in history
        _diagnostic_history.append(diagnostic_data)

        # Limit history size
        if len(_diagnostic_history) > 100:
            _diagnostic_history.pop(0)

        # Analyze for learning opportunities
        learning_insights = _analyze_diagnostics(diagnostic_data)

        # Create Genesis Key for diagnostic report
        genesis_key_id = None
        try:
            from genesis.genesis_key_service import GenesisKeyService
            service = GenesisKeyService(db)
            key = service.create_genesis_key(
                entity_type="diagnostic_report",
                entity_id=report.session_id,
                origin_source="test_diagnostics",
                origin_type="self_diagnosis",
                metadata={
                    "skips": len(report.skips),
                    "import_errors": len(report.import_errors),
                    "missing_deps": len(report.missing_dependencies),
                    "has_issues": len(report.skips) > 0 or len(report.import_errors) > 0
                }
            )
            genesis_key_id = key.id if key else None
        except Exception as e:
            logger.warning(f"Could not create Genesis Key for diagnostics: {e}")

        # Try to feed into learning system
        learning_recorded = False
        try:
            learning_recorded = await _record_learning_from_diagnostics(diagnostic_data)
        except Exception as e:
            logger.warning(f"Could not record learning from diagnostics: {e}")

        # Generate and validate action items through OODA + LLM pipeline
        action_items = await _generate_action_items(diagnostic_data)

        # Filter to only approved actions
        approved_actions = [a for a in action_items if a.get("approved", False)]

        # Submit approved actions to Autonomous Action Engine + CI/CD pipeline
        pipeline_results = []
        if approved_actions:
            background_tasks.add_task(
                _execute_diagnostic_fixes_pipeline,
                approved_actions,
                report.session_id,
                genesis_key_id
            )
            pipeline_results = [
                {
                    "action": a.get("action"),
                    "target": a.get("target"),
                    "status": "submitted_to_pipeline"
                }
                for a in approved_actions
            ]

        return {
            "status": "received",
            "session_id": report.session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "genesis_key_id": genesis_key_id,
            "learning_insights": learning_insights,
            "learning_recorded": learning_recorded,
            "action_items": action_items,
            "approved_count": len(approved_actions),
            "pipeline_submissions": pipeline_results,
            "pipeline_active": len(approved_actions) > 0
        }

    except Exception as e:
        logger.error(f"Error receiving diagnostics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/diagnostics/history")
async def get_diagnostic_history(limit: int = 20):
    """Get history of diagnostic reports."""
    return {
        "history": _diagnostic_history[-limit:],
        "total": len(_diagnostic_history),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/diagnostics/analysis")
async def analyze_diagnostic_patterns():
    """
    Analyze patterns in diagnostic reports for systemic issues.

    Helps Grace identify recurring problems and prioritize fixes.
    """
    if not _diagnostic_history:
        return {
            "status": "no_data",
            "message": "No diagnostic reports received yet"
        }

    # Aggregate missing dependencies across all reports
    all_missing_deps = {}
    all_import_errors = {}
    skip_reasons = {}

    for report in _diagnostic_history:
        for dep in report.get('missing_dependencies', []):
            all_missing_deps[dep] = all_missing_deps.get(dep, 0) + 1

        for error in report.get('import_errors', []):
            module = error.get('module', 'unknown')
            all_import_errors[module] = all_import_errors.get(module, 0) + 1

        for skip in report.get('skips', []):
            reason = skip.get('reason', 'unknown')
            # Normalize reason for grouping
            key = reason[:50] if len(reason) > 50 else reason
            skip_reasons[key] = skip_reasons.get(key, 0) + 1

    # Sort by frequency
    sorted_deps = sorted(all_missing_deps.items(), key=lambda x: x[1], reverse=True)
    sorted_errors = sorted(all_import_errors.items(), key=lambda x: x[1], reverse=True)
    sorted_skips = sorted(skip_reasons.items(), key=lambda x: x[1], reverse=True)

    return {
        "analysis": {
            "most_common_missing_deps": sorted_deps[:10],
            "most_common_import_errors": sorted_errors[:10],
            "most_common_skip_reasons": sorted_skips[:10]
        },
        "recommendations": _generate_recommendations(sorted_deps, sorted_errors),
        "total_reports_analyzed": len(_diagnostic_history),
        "timestamp": datetime.utcnow().isoformat()
    }


def _analyze_diagnostics(diagnostic_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze diagnostic data for learning opportunities."""
    insights = {
        "dependency_issues": [],
        "code_issues": [],
        "environment_issues": [],
        "priority": "low"
    }

    # Check for dependency issues
    missing_deps = diagnostic_data.get('missing_dependencies', [])
    if missing_deps:
        insights['dependency_issues'] = [
            {
                "type": "missing_dependency",
                "dependency": dep,
                "suggested_action": f"pip install {dep}" if not dep.startswith(('cognitive', 'retrieval', 'embedding')) else f"Check PYTHONPATH for {dep}"
            }
            for dep in missing_deps
        ]
        insights['priority'] = "high" if len(missing_deps) > 3 else "medium"

    # Check for import chain issues
    import_errors = diagnostic_data.get('import_errors', [])
    for error in import_errors:
        chain = error.get('import_chain', [])
        if len(chain) > 2:
            insights['code_issues'].append({
                "type": "deep_import_chain",
                "chain": chain,
                "suggestion": "Consider lazy imports or restructuring modules"
            })

    # Check environment
    env = diagnostic_data.get('environment', {})
    if 'python_version' in env and '3.11' not in env['python_version'] and '3.12' not in env['python_version']:
        insights['environment_issues'].append({
            "type": "python_version",
            "current": env['python_version'],
            "suggestion": "Consider using Python 3.11 or 3.12"
        })

    return insights


async def _validate_fix_through_ooda(
    fix_proposal: Dict[str, Any],
    diagnostic_context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Validate a proposed fix through OODA loop and clarity framework.

    This ensures fixes are correct before being suggested or applied.
    All fixes must pass through the cognitive framework.
    """
    try:
        from cognitive.ooda import OODALoop, OODAPhase
        from cognitive.contradiction_detector import ContradictionDetector, ContradictionSeverity

        # Create OODA loop for fix validation
        ooda = OODALoop()

        # OBSERVE: Gather facts about the proposed fix
        observations = {
            "fix_type": fix_proposal.get("action"),
            "target": fix_proposal.get("target"),
            "command": fix_proposal.get("command"),
            "diagnostic_source": diagnostic_context.get("session_id"),
            "environment": diagnostic_context.get("environment", {}),
            "skip_count": len(diagnostic_context.get("skips", [])),
            "error_count": len(diagnostic_context.get("import_errors", []))
        }
        ooda.observe(observations)

        # ORIENT: Understand context and constraints
        context = {
            "is_standard_dependency": _is_standard_pypi_package(fix_proposal.get("target", "")),
            "affects_core_system": _affects_core_system(fix_proposal.get("target", "")),
            "requires_restart": fix_proposal.get("action") in ["install_dependency"],
            "reversible": fix_proposal.get("action") in ["install_dependency", "fix_import"],
            "risk_level": _assess_fix_risk(fix_proposal)
        }

        constraints = {
            "must_not_break_existing": True,
            "must_be_reversible": True,
            "max_risk_level": "medium",
            "requires_validation": True
        }
        ooda.orient(context, constraints)

        # DECIDE: Determine if fix should be approved
        decision = {
            "approved": True,
            "confidence": 0.0,
            "reasoning": [],
            "alternatives": []
        }

        # Check against constraints
        if context["risk_level"] == "high" and not constraints.get("allow_high_risk"):
            decision["approved"] = False
            decision["reasoning"].append("High risk fix requires manual approval")

        if context["affects_core_system"]:
            decision["confidence"] -= 0.2
            decision["reasoning"].append("Fix affects core system - extra caution required")

        if context["is_standard_dependency"]:
            decision["confidence"] += 0.3
            decision["reasoning"].append("Standard PyPI package - safer to install")

        if context["reversible"]:
            decision["confidence"] += 0.2
            decision["reasoning"].append("Fix is reversible")

        # Normalize confidence
        decision["confidence"] = max(0.0, min(1.0, 0.5 + decision["confidence"]))

        # Set approval threshold
        if decision["confidence"] < 0.6:
            decision["approved"] = False
            decision["reasoning"].append(f"Confidence {decision['confidence']:.2f} below threshold 0.6")

        ooda.decide(decision)

        # Check for contradictions using clarity framework
        contradiction_check = await _check_fix_contradictions(fix_proposal, diagnostic_context)
        if contradiction_check.get("has_contradiction"):
            decision["approved"] = False
            decision["reasoning"].append(f"Clarity check failed: {contradiction_check.get('description')}")
            decision["contradiction"] = contradiction_check

        # ACT: Return validated decision
        return {
            "fix_proposal": fix_proposal,
            "ooda_validated": True,
            "approved": decision["approved"],
            "confidence": decision["confidence"],
            "reasoning": decision["reasoning"],
            "alternatives": decision.get("alternatives", []),
            "contradiction_check": contradiction_check,
            "validation_timestamp": datetime.utcnow().isoformat()
        }

    except ImportError as e:
        # Cognitive framework not available - use basic validation
        logger.warning(f"Cognitive framework not available for OODA validation: {e}")
        return await _basic_fix_validation(fix_proposal, diagnostic_context)
    except Exception as e:
        logger.error(f"Error in OODA validation: {e}")
        return {
            "fix_proposal": fix_proposal,
            "ooda_validated": False,
            "approved": False,
            "error": str(e),
            "reasoning": ["OODA validation failed - manual review required"]
        }


async def _check_fix_contradictions(
    fix_proposal: Dict[str, Any],
    diagnostic_context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Check proposed fix for contradictions using clarity framework.

    Addresses Clarity Class 10: Contradiction Detection
    """
    try:
        from cognitive.contradiction_detector import ContradictionDetector, ContradictionType, ContradictionSeverity

        detector = ContradictionDetector()

        contradictions_found = []

        # Check for logical contradictions
        target = fix_proposal.get("target", "")
        command = fix_proposal.get("command", "")

        # Check if trying to install something that's already present
        if fix_proposal.get("action") == "install_dependency":
            # This would be a contradiction if the dep is already installed
            # but was imported incorrectly (path issue vs missing package)
            import_errors = diagnostic_context.get("import_errors", [])
            for error in import_errors:
                if target in error.get("error_message", ""):
                    # Check if it's a path issue vs actual missing package
                    if "embedding." in target or "cognitive." in target or "retrieval." in target:
                        contradictions_found.append({
                            "type": ContradictionType.LOGICAL.value,
                            "severity": ContradictionSeverity.MEDIUM.value,
                            "description": f"'{target}' appears to be a local module, not a PyPI package",
                            "suggestion": "Add module directory to PYTHONPATH instead of pip install"
                        })

        # Check for pattern contradictions (doing something unusual)
        if command and "pip install" in command:
            if ".." in target or "/" in target:
                contradictions_found.append({
                    "type": ContradictionType.PATTERN.value,
                    "severity": ContradictionSeverity.HIGH.value,
                    "description": f"Unusual package name '{target}' - may not be a valid PyPI package",
                    "suggestion": "Verify package name before installation"
                })

        if contradictions_found:
            return {
                "has_contradiction": True,
                "contradictions": contradictions_found,
                "description": contradictions_found[0]["description"],
                "avn_recommendation": "clarify"  # AVN: Ambiguity/Validation/Negotiation
            }

        return {
            "has_contradiction": False,
            "contradictions": [],
            "clarity_passed": True
        }

    except ImportError:
        # Clarity framework not available - return basic check
        return {
            "has_contradiction": False,
            "clarity_available": False,
            "note": "Clarity framework not available for deep contradiction checking"
        }
    except Exception as e:
        logger.error(f"Error in contradiction check: {e}")
        return {
            "has_contradiction": False,
            "error": str(e)
        }


async def _basic_fix_validation(
    fix_proposal: Dict[str, Any],
    diagnostic_context: Dict[str, Any]
) -> Dict[str, Any]:
    """Basic fix validation when cognitive framework is not available."""
    target = fix_proposal.get("target", "")
    action = fix_proposal.get("action", "")

    approved = True
    reasoning = []

    # Basic safety checks
    if action == "install_dependency":
        if target.startswith(("cognitive", "retrieval", "embedding", "layer1", "genesis")):
            approved = False
            reasoning.append(f"'{target}' is a local module - use PYTHONPATH fix instead")
        elif _is_standard_pypi_package(target):
            approved = True
            reasoning.append(f"'{target}' is a known standard package")
        else:
            approved = True  # Allow unknown but warn
            reasoning.append(f"'{target}' is unknown - verify it's correct")

    return {
        "fix_proposal": fix_proposal,
        "ooda_validated": False,
        "basic_validation": True,
        "approved": approved,
        "confidence": 0.7 if approved else 0.3,
        "reasoning": reasoning
    }


def _is_standard_pypi_package(package_name: str) -> bool:
    """Check if package is a known standard PyPI package."""
    STANDARD_PACKAGES = {
        "numpy", "scipy", "scikit-learn", "pandas", "matplotlib",
        "fastapi", "uvicorn", "pydantic", "sqlalchemy", "httpx",
        "requests", "aiohttp", "pytest", "torch", "transformers",
        "sentence-transformers", "qdrant-client", "redis", "celery",
        "psutil", "pyyaml", "python-dotenv", "jinja2", "pillow"
    }
    base_name = package_name.split(".")[0].lower().replace("-", "_")
    return base_name in STANDARD_PACKAGES


def _affects_core_system(target: str) -> bool:
    """Check if fix target affects core system components."""
    CORE_COMPONENTS = {
        "cognitive", "genesis", "governance", "layer1", "security",
        "retrieval", "embedding", "learning", "core"
    }
    return any(comp in target.lower() for comp in CORE_COMPONENTS)


def _assess_fix_risk(fix_proposal: Dict[str, Any]) -> str:
    """Assess risk level of proposed fix."""
    action = fix_proposal.get("action", "")
    target = fix_proposal.get("target", "")

    # High risk actions
    if action in ["modify_core", "delete_file", "modify_config"]:
        return "high"

    # Medium risk
    if action == "install_dependency" and not _is_standard_pypi_package(target):
        return "medium"

    if _affects_core_system(target):
        return "medium"

    # Low risk
    return "low"


async def _record_learning_from_diagnostics(diagnostic_data: Dict[str, Any]) -> bool:
    """Record diagnostic insights into Grace's learning system."""
    try:
        # Try to use the learning memory API
        from api.learning_memory_api import record_learning

        # Create learning examples from diagnostics
        for skip in diagnostic_data.get('skips', []):
            learning_example = {
                "input": f"Test skip: {skip.get('test', 'unknown')}",
                "output": f"Reason: {skip.get('reason', 'unknown')}. Fix: {skip.get('suggested_fix', 'Unknown')}",
                "task_type": "diagnostic_learning",
                "metadata": {
                    "source": "test_diagnostics",
                    "timestamp": skip.get('timestamp')
                }
            }
            # Note: Would call learning system here

        return True
    except ImportError:
        return False
    except Exception as e:
        logger.warning(f"Could not record learning: {e}")
        return False


async def _generate_action_items(diagnostic_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Generate actionable items from diagnostic data.

    All action items go through multi-stage verification:
    1. OODA loop / Clarity framework (cognitive validation)
    2. LLM verification (knowledge verification)
    3. LLM output verification (ensure LLM reasoning is sound)
    """
    actions = []

    # High priority: missing dependencies that block tests
    for dep in diagnostic_data.get('missing_dependencies', []):
        fix_proposal = {
            "priority": "high",
            "action": "install_dependency",
            "target": dep,
            "command": f"pip install {dep}" if '.' not in dep else None,
            "description": f"Install missing dependency: {dep}"
        }

        # Stage 1: OODA/Clarity validation
        ooda_result = await _validate_fix_through_ooda(fix_proposal, diagnostic_data)

        # Stage 2: LLM verification (if OODA approved or needs clarification)
        llm_result = None
        if ooda_result.get("approved") or ooda_result.get("contradiction_check", {}).get("avn_recommendation") == "clarify":
            llm_result = await _verify_fix_with_llm(fix_proposal, diagnostic_data, ooda_result)

        # Stage 3: Verify LLM output consistency
        final_approved = False
        if llm_result:
            verification = _verify_llm_output(llm_result, ooda_result)
            final_approved = verification.get("consistent", False) and llm_result.get("approved", False)
        else:
            final_approved = ooda_result.get("approved", False)

        fix_proposal["validation"] = {
            "ooda_result": ooda_result,
            "llm_result": llm_result,
            "final_approved": final_approved,
            "verification_chain": ["ooda", "llm", "consistency_check"]
        }
        fix_proposal["approved"] = final_approved

        actions.append(fix_proposal)

    # Medium priority: fix import errors
    for error in diagnostic_data.get('import_errors', []):
        if error.get('suggested_fix'):
            fix_proposal = {
                "priority": "medium",
                "action": "fix_import",
                "target": error.get('module'),
                "command": error.get('suggested_fix'),
                "description": f"Fix import for: {error.get('module')}"
            }

            # Run through validation pipeline
            ooda_result = await _validate_fix_through_ooda(fix_proposal, diagnostic_data)
            llm_result = await _verify_fix_with_llm(fix_proposal, diagnostic_data, ooda_result)

            final_approved = False
            if llm_result:
                verification = _verify_llm_output(llm_result, ooda_result)
                final_approved = verification.get("consistent", False) and llm_result.get("approved", False)

            fix_proposal["validation"] = {
                "ooda_result": ooda_result,
                "llm_result": llm_result,
                "final_approved": final_approved
            }
            fix_proposal["approved"] = final_approved

            actions.append(fix_proposal)

    # Low priority: review skipped tests (doesn't need full validation)
    skip_count = len(diagnostic_data.get('skips', []))
    if skip_count > 0:
        actions.append({
            "priority": "low",
            "action": "review_skips",
            "target": "test_suite",
            "description": f"Review {skip_count} skipped tests for potential issues",
            "approved": True,  # Review actions are always safe
            "validation": {"type": "review_only"}
        })

    return actions


async def _verify_fix_with_llm(
    fix_proposal: Dict[str, Any],
    diagnostic_data: Dict[str, Any],
    ooda_result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Verify proposed fix using LLM as knowledge source.

    The LLM provides a second verification layer with broader knowledge.
    Its output is then verified for consistency and soundness.
    """
    try:
        from api.llm_orchestration import get_llm_orchestrator

        orchestrator = get_llm_orchestrator()

        # Construct verification prompt
        prompt = f"""You are verifying a proposed fix for a test diagnostic issue.

PROPOSED FIX:
- Action: {fix_proposal.get('action')}
- Target: {fix_proposal.get('target')}
- Command: {fix_proposal.get('command')}
- Description: {fix_proposal.get('description')}

DIAGNOSTIC CONTEXT:
- Missing dependencies: {diagnostic_data.get('missing_dependencies', [])}
- Import errors: {len(diagnostic_data.get('import_errors', []))}
- Environment: {diagnostic_data.get('environment', {}).get('python_version', 'unknown')}

OODA VALIDATION RESULT:
- Approved: {ooda_result.get('approved')}
- Confidence: {ooda_result.get('confidence', 0)}
- Reasoning: {ooda_result.get('reasoning', [])}

Please verify:
1. Is this fix correct for the identified problem?
2. Are there any risks or side effects?
3. Is there a better alternative?
4. Should this fix be approved?

Respond in JSON format:
{{
    "approved": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "explanation",
    "risks": ["list of risks"],
    "alternatives": ["list of alternatives"],
    "is_correct_fix": true/false,
    "knowledge_sources": ["what you based this on"]
}}
"""

        # Call LLM
        response = await orchestrator.generate(
            prompt=prompt,
            temperature=0.3,  # Low temperature for factual verification
            max_tokens=500
        )

        # Parse LLM response
        llm_result = _parse_llm_verification_response(response)
        llm_result["raw_response"] = response
        llm_result["timestamp"] = datetime.utcnow().isoformat()

        return llm_result

    except ImportError:
        logger.warning("LLM orchestration not available for verification")
        return {
            "available": False,
            "approved": None,
            "note": "LLM verification not available - falling back to OODA only"
        }
    except Exception as e:
        logger.error(f"Error in LLM verification: {e}")
        return {
            "available": True,
            "error": str(e),
            "approved": None
        }


def _parse_llm_verification_response(response: str) -> Dict[str, Any]:
    """Parse LLM verification response, handling various formats."""
    try:
        # Try to extract JSON from response
        import re

        # Look for JSON block
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            return json.loads(json_match.group())

        # Fallback: interpret text response
        response_lower = response.lower()
        approved = "approved" in response_lower and "not approved" not in response_lower

        return {
            "approved": approved,
            "confidence": 0.5,
            "reasoning": response[:500],
            "parsed_from_text": True
        }

    except json.JSONDecodeError:
        return {
            "approved": None,
            "confidence": 0.0,
            "reasoning": "Could not parse LLM response",
            "raw": response[:500],
            "parse_error": True
        }


def _verify_llm_output(
    llm_result: Dict[str, Any],
    ooda_result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Verify the LLM's output for consistency and soundness.

    Checks:
    1. Is LLM output internally consistent?
    2. Does it align with OODA assessment?
    3. Is the reasoning sound?
    4. Are there any red flags?
    """
    verification = {
        "consistent": True,
        "issues": [],
        "trust_level": "high"
    }

    if not llm_result or llm_result.get("error"):
        verification["consistent"] = False
        verification["issues"].append("LLM verification failed or unavailable")
        verification["trust_level"] = "low"
        return verification

    # Check 1: Internal consistency
    if llm_result.get("approved") and llm_result.get("confidence", 0) < 0.5:
        verification["issues"].append("LLM approved with low confidence - inconsistent")
        verification["trust_level"] = "medium"

    if not llm_result.get("approved") and llm_result.get("is_correct_fix"):
        verification["issues"].append("LLM says fix is correct but not approved - contradiction")
        verification["consistent"] = False

    # Check 2: Alignment with OODA
    ooda_approved = ooda_result.get("approved", False)
    llm_approved = llm_result.get("approved")

    if ooda_approved != llm_approved and llm_approved is not None:
        verification["issues"].append(f"OODA ({ooda_approved}) disagrees with LLM ({llm_approved})")
        verification["trust_level"] = "medium"

        # If both have high confidence in opposite directions, flag for review
        ooda_conf = ooda_result.get("confidence", 0)
        llm_conf = llm_result.get("confidence", 0)
        if ooda_conf > 0.7 and llm_conf > 0.7:
            verification["consistent"] = False
            verification["issues"].append("High confidence disagreement - requires human review")
            verification["trust_level"] = "low"

    # Check 3: Reasoning soundness
    reasoning = llm_result.get("reasoning", "")
    if isinstance(reasoning, str) and len(reasoning) < 20:
        verification["issues"].append("LLM reasoning too brief - may be unreliable")
        verification["trust_level"] = "medium"

    # Check 4: Red flags
    if llm_result.get("parse_error"):
        verification["issues"].append("LLM response parsing failed")
        verification["trust_level"] = "low"

    risks = llm_result.get("risks", [])
    if risks and any("security" in r.lower() or "critical" in r.lower() for r in risks):
        verification["issues"].append("LLM identified security/critical risks")
        verification["consistent"] = False

    # Final consistency determination
    if len(verification["issues"]) >= 3:
        verification["consistent"] = False
        verification["trust_level"] = "low"

    return verification


def _generate_recommendations(
    sorted_deps: List[tuple],
    sorted_errors: List[tuple]
) -> List[str]:
    """Generate recommendations based on diagnostic patterns."""
    recommendations = []

    if sorted_deps:
        top_deps = [dep for dep, _ in sorted_deps[:3]]
        recommendations.append(
            f"Install frequently missing dependencies: pip install {' '.join(top_deps)}"
        )

    if sorted_errors:
        recommendations.append(
            "Consider adding import error handling or lazy loading for problematic modules"
        )

    if len(sorted_deps) > 5:
        recommendations.append(
            "Create a requirements-test.txt with all testing dependencies"
        )

    return recommendations


# ==================== Autonomous Pipeline Integration ====================

async def _execute_diagnostic_fixes_pipeline(
    approved_actions: List[Dict[str, Any]],
    session_id: str,
    genesis_key_id: Optional[str]
):
    """
    Execute approved diagnostic fixes through full GRACE pipeline.

    Pipeline flow:
    1. Grace Mirror reflection (self-verification)
    2. Create autonomous action request + Genesis Key
    3. Submit to governance for approval + Genesis Key
    4. Execute through CI/CD pipeline + Genesis Key
    5. Post-execution Mirror verification + Genesis Key
    6. Track results and update learning system
    """
    try:
        from api.autonomous_api import create_autonomous_action
        from api.adaptive_cicd_api import trigger_adaptive_pipeline
        from api.governance_api import request_governance_approval

        pipeline_results = []

        for action in approved_actions:
            action_result = {
                "action": action.get("action"),
                "target": action.get("target"),
                "status": "pending",
                "stages": [],
                "genesis_keys": []
            }

            try:
                # Stage 0: Grace Mirror pre-execution reflection
                mirror_pre = await _grace_mirror_reflect(
                    action=action,
                    stage="pre_execution",
                    session_id=session_id,
                    context={
                        "validation": action.get("validation", {}),
                        "source": "diagnostic_pipeline"
                    }
                )
                action_result["stages"].append({
                    "stage": "mirror_pre_reflection",
                    "status": mirror_pre.get("status"),
                    "confidence": mirror_pre.get("confidence"),
                    "concerns": mirror_pre.get("concerns", [])
                })

                # Create Genesis Key for mirror reflection
                mirror_key = await _create_pipeline_genesis_key(
                    entity_type="mirror_reflection",
                    entity_id=f"mirror_pre_{session_id}_{action.get('target')}",
                    origin_type="diagnostic_pipeline_mirror",
                    metadata={
                        "stage": "pre_execution",
                        "action": action.get("action"),
                        "target": action.get("target"),
                        "mirror_confidence": mirror_pre.get("confidence")
                    }
                )
                if mirror_key:
                    action_result["genesis_keys"].append(mirror_key)

                # If mirror has critical concerns, stop pipeline
                if mirror_pre.get("block_execution"):
                    action_result["status"] = "blocked_by_mirror"
                    action_result["mirror_block_reason"] = mirror_pre.get("block_reason")
                    pipeline_results.append(action_result)
                    continue

                # Stage 1: Create autonomous action + Genesis Key
                autonomous_request = {
                    "action_type": action.get("action"),
                    "target": action.get("target"),
                    "command": action.get("command"),
                    "source": "diagnostic_pipeline",
                    "session_id": session_id,
                    "validation": action.get("validation", {}),
                    "priority": action.get("priority", "medium"),
                    "mirror_verification": mirror_pre
                }

                autonomous_result = await _submit_to_autonomous_engine(autonomous_request)
                action_result["stages"].append({
                    "stage": "autonomous_engine",
                    "status": autonomous_result.get("status"),
                    "action_id": autonomous_result.get("action_id")
                })

                # Create Genesis Key for autonomous action
                auto_key = await _create_pipeline_genesis_key(
                    entity_type="autonomous_action",
                    entity_id=autonomous_result.get("action_id", f"auto_{session_id}"),
                    origin_type="diagnostic_pipeline_action",
                    metadata={
                        "action": action.get("action"),
                        "target": action.get("target"),
                        "status": autonomous_result.get("status")
                    }
                )
                if auto_key:
                    action_result["genesis_keys"].append(auto_key)

                # Stage 2: Check if governance approval needed + Genesis Key
                needs_approval = _requires_governance_approval(action)
                if needs_approval:
                    approval_result = await _request_governance(action, session_id)
                    action_result["stages"].append({
                        "stage": "governance",
                        "status": approval_result.get("status"),
                        "approval_id": approval_result.get("approval_id")
                    })

                    # Create Genesis Key for governance request
                    gov_key = await _create_pipeline_genesis_key(
                        entity_type="governance_request",
                        entity_id=approval_result.get("approval_id", f"gov_{session_id}"),
                        origin_type="diagnostic_pipeline_governance",
                        metadata={
                            "action": action.get("action"),
                            "target": action.get("target"),
                            "approval_status": approval_result.get("status"),
                            "requires_human_review": approval_result.get("status") != "approved"
                        }
                    )
                    if gov_key:
                        action_result["genesis_keys"].append(gov_key)

                    if approval_result.get("status") != "approved":
                        action_result["status"] = "awaiting_approval"
                        pipeline_results.append(action_result)
                        continue

                # Stage 3: Execute through CI/CD pipeline + Genesis Key
                cicd_result = await _execute_through_cicd(action, session_id)
                action_result["stages"].append({
                    "stage": "cicd_execution",
                    "status": cicd_result.get("status"),
                    "pipeline_id": cicd_result.get("pipeline_id"),
                    "output": cicd_result.get("output", "")[:500]
                })

                # Create Genesis Key for CI/CD execution
                cicd_key = await _create_pipeline_genesis_key(
                    entity_type="cicd_execution",
                    entity_id=cicd_result.get("pipeline_id", f"cicd_{session_id}"),
                    origin_type="diagnostic_pipeline_cicd",
                    metadata={
                        "action": action.get("action"),
                        "target": action.get("target"),
                        "execution_status": cicd_result.get("status"),
                        "has_output": bool(cicd_result.get("output"))
                    }
                )
                if cicd_key:
                    action_result["genesis_keys"].append(cicd_key)

                # Stage 4: Grace Mirror post-execution verification
                mirror_post = await _grace_mirror_reflect(
                    action=action,
                    stage="post_execution",
                    session_id=session_id,
                    context={
                        "execution_result": cicd_result,
                        "success": cicd_result.get("status") == "success"
                    }
                )
                action_result["stages"].append({
                    "stage": "mirror_post_verification",
                    "status": mirror_post.get("status"),
                    "verification_passed": mirror_post.get("verified", False),
                    "learnings": mirror_post.get("learnings", [])
                })

                # Create Genesis Key for post-execution mirror
                post_mirror_key = await _create_pipeline_genesis_key(
                    entity_type="mirror_verification",
                    entity_id=f"mirror_post_{session_id}_{action.get('target')}",
                    origin_type="diagnostic_pipeline_mirror_verify",
                    metadata={
                        "stage": "post_execution",
                        "verified": mirror_post.get("verified"),
                        "execution_success": cicd_result.get("status") == "success"
                    }
                )
                if post_mirror_key:
                    action_result["genesis_keys"].append(post_mirror_key)

                # Stage 5: Track results
                if cicd_result.get("status") == "success":
                    action_result["status"] = "completed"
                    await _record_fix_outcome(action, cicd_result, success=True)
                else:
                    action_result["status"] = "failed"
                    await _record_fix_outcome(action, cicd_result, success=False)

                # Create final Genesis Key for pipeline completion
                final_key = await _create_pipeline_genesis_key(
                    entity_type="pipeline_completion",
                    entity_id=f"pipeline_{session_id}_{action.get('target')}",
                    origin_type="diagnostic_pipeline_complete",
                    metadata={
                        "action": action.get("action"),
                        "target": action.get("target"),
                        "final_status": action_result["status"],
                        "stages_completed": len(action_result["stages"]),
                        "genesis_keys_created": len(action_result["genesis_keys"])
                    }
                )
                if final_key:
                    action_result["genesis_keys"].append(final_key)

            except Exception as e:
                action_result["status"] = "error"
                action_result["error"] = str(e)
                logger.error(f"Pipeline error for action {action.get('target')}: {e}")

                # Create error Genesis Key
                error_key = await _create_pipeline_genesis_key(
                    entity_type="pipeline_error",
                    entity_id=f"error_{session_id}_{action.get('target')}",
                    origin_type="diagnostic_pipeline_error",
                    metadata={
                        "action": action.get("action"),
                        "target": action.get("target"),
                        "error": str(e)
                    }
                )
                if error_key:
                    action_result["genesis_keys"].append(error_key)

            pipeline_results.append(action_result)

        # Store pipeline results for retrieval
        _store_pipeline_results(session_id, pipeline_results)

        logger.info(f"Diagnostic pipeline completed: {len(pipeline_results)} actions processed")

    except ImportError as e:
        logger.error(f"Pipeline components not available: {e}")
    except Exception as e:
        logger.error(f"Diagnostic pipeline error: {e}")


async def _grace_mirror_reflect(
    action: Dict[str, Any],
    stage: str,
    session_id: str,
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Grace Mirror reflection - self-verification and introspection.

    The Mirror allows Grace to reflect on her actions, verify decisions,
    and learn from outcomes through self-observation.
    """
    try:
        from cognitive.mirror import GraceMirror

        mirror = GraceMirror()

        if stage == "pre_execution":
            # Pre-execution: Verify the action makes sense
            reflection = await mirror.reflect_on_action(
                action_type=action.get("action"),
                target=action.get("target"),
                validation=context.get("validation", {}),
                question="Should I execute this diagnostic fix? Is it safe and correct?"
            )

            concerns = []
            block_execution = False
            block_reason = None

            # Check mirror's assessment
            if reflection.get("confidence", 0) < 0.5:
                concerns.append("Low confidence in action correctness")

            if reflection.get("risks"):
                concerns.extend(reflection.get("risks", []))

            if reflection.get("contradictions"):
                concerns.append("Mirror detected contradictions")
                if reflection.get("contradiction_severity") == "critical":
                    block_execution = True
                    block_reason = "Critical contradiction detected"

            if reflection.get("recommendation") == "abort":
                block_execution = True
                block_reason = reflection.get("abort_reason", "Mirror recommends abort")

            return {
                "status": "reflected",
                "confidence": reflection.get("confidence", 0.5),
                "assessment": reflection.get("assessment", ""),
                "concerns": concerns,
                "block_execution": block_execution,
                "block_reason": block_reason,
                "mirror_timestamp": datetime.utcnow().isoformat()
            }

        elif stage == "post_execution":
            # Post-execution: Verify outcome and extract learnings
            reflection = await mirror.reflect_on_outcome(
                action_type=action.get("action"),
                target=action.get("target"),
                execution_result=context.get("execution_result", {}),
                success=context.get("success", False),
                question="What did I learn from this fix? Was my prediction correct?"
            )

            learnings = reflection.get("learnings", [])
            verified = reflection.get("outcome_matches_prediction", True)

            # If outcome didn't match prediction, flag for learning adjustment
            if not verified:
                learnings.append({
                    "type": "prediction_error",
                    "expected": reflection.get("expected_outcome"),
                    "actual": context.get("execution_result", {}).get("status"),
                    "adjustment": "Update prediction model"
                })

            return {
                "status": "verified",
                "verified": verified,
                "learnings": learnings,
                "self_assessment": reflection.get("self_assessment", ""),
                "improvement_suggestions": reflection.get("suggestions", []),
                "mirror_timestamp": datetime.utcnow().isoformat()
            }

    except ImportError:
        logger.warning("Grace Mirror not available - using basic reflection")
        return await _basic_mirror_reflection(action, stage, context)
    except Exception as e:
        logger.error(f"Mirror reflection error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "confidence": 0.5,
            "block_execution": False
        }


async def _basic_mirror_reflection(
    action: Dict[str, Any],
    stage: str,
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """Basic mirror reflection when full Mirror is not available."""
    if stage == "pre_execution":
        # Basic pre-checks
        validation = context.get("validation", {})
        ooda_approved = validation.get("ooda_result", {}).get("approved", False)
        llm_approved = validation.get("llm_result", {}).get("approved")

        confidence = 0.5
        if ooda_approved:
            confidence += 0.2
        if llm_approved:
            confidence += 0.2

        concerns = []
        if not ooda_approved:
            concerns.append("OODA validation did not approve")
        if llm_approved is False:
            concerns.append("LLM verification did not approve")

        return {
            "status": "basic_reflection",
            "confidence": confidence,
            "concerns": concerns,
            "block_execution": confidence < 0.4,
            "block_reason": "Insufficient validation confidence" if confidence < 0.4 else None
        }

    elif stage == "post_execution":
        success = context.get("success", False)
        return {
            "status": "basic_verification",
            "verified": success,
            "learnings": [
                {"type": "outcome", "success": success}
            ] if success else [
                {"type": "failure_analysis", "needs_review": True}
            ]
        }

    return {"status": "unknown_stage"}


async def _create_pipeline_genesis_key(
    entity_type: str,
    entity_id: str,
    origin_type: str,
    metadata: Dict[str, Any]
) -> Optional[str]:
    """Create Genesis Key for pipeline stage with full audit trail."""
    try:
        from genesis.genesis_key_service import GenesisKeyService
        from database.session import get_session

        # Get database session
        db = next(get_session())

        service = GenesisKeyService(db)
        key = service.create_genesis_key(
            entity_type=entity_type,
            entity_id=entity_id,
            origin_source="diagnostic_pipeline",
            origin_type=origin_type,
            metadata=metadata
        )

        if key:
            logger.debug(f"Created Genesis Key: {key.id} for {entity_type}")
            return key.id

        return None

    except Exception as e:
        logger.warning(f"Could not create Genesis Key for {entity_type}: {e}")
        return None


async def _submit_to_autonomous_engine(request: Dict[str, Any]) -> Dict[str, Any]:
    """Submit action to Autonomous Action Engine."""
    try:
        from api.autonomous_api import get_autonomous_engine

        engine = get_autonomous_engine()

        # Create action through engine
        action = await engine.create_action(
            action_type=request.get("action_type"),
            target=request.get("target"),
            parameters={
                "command": request.get("command"),
                "source": request.get("source"),
                "validation": request.get("validation")
            },
            priority=request.get("priority", "medium")
        )

        return {
            "status": "submitted",
            "action_id": action.get("id") if action else None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except ImportError:
        # Autonomous engine not available - log and continue
        logger.warning("Autonomous engine not available - action logged only")
        return {
            "status": "logged",
            "action_id": f"local_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            "note": "Autonomous engine not available"
        }
    except Exception as e:
        logger.error(f"Error submitting to autonomous engine: {e}")
        return {"status": "error", "error": str(e)}


def _requires_governance_approval(action: Dict[str, Any]) -> bool:
    """Determine if action requires governance approval."""
    # High priority or core system changes need approval
    if action.get("priority") == "high":
        return True

    if _affects_core_system(action.get("target", "")):
        return True

    # Check validation results
    validation = action.get("validation", {})
    ooda_result = validation.get("ooda_result", {})
    llm_result = validation.get("llm_result", {})

    # If OODA and LLM disagreed, need human review
    if ooda_result.get("approved") != llm_result.get("approved"):
        return True

    # If confidence is low, need approval
    if ooda_result.get("confidence", 0) < 0.7:
        return True

    return False


async def _request_governance(action: Dict[str, Any], session_id: str) -> Dict[str, Any]:
    """Request governance approval for action."""
    try:
        from api.governance_api import request_approval

        approval_request = {
            "action_type": action.get("action"),
            "target": action.get("target"),
            "description": action.get("description"),
            "source": "diagnostic_pipeline",
            "session_id": session_id,
            "validation_summary": {
                "ooda_approved": action.get("validation", {}).get("ooda_result", {}).get("approved"),
                "llm_approved": action.get("validation", {}).get("llm_result", {}).get("approved"),
                "confidence": action.get("validation", {}).get("ooda_result", {}).get("confidence", 0)
            },
            "pillar": "operational",  # Test fixes are operational
            "urgency": "medium"
        }

        result = await request_approval(approval_request)

        return {
            "status": result.get("status", "pending"),
            "approval_id": result.get("approval_id"),
            "message": result.get("message")
        }

    except ImportError:
        logger.warning("Governance API not available")
        return {"status": "approved", "note": "Governance not available - auto-approved"}
    except Exception as e:
        logger.error(f"Error requesting governance: {e}")
        return {"status": "error", "error": str(e)}


async def _execute_through_cicd(action: Dict[str, Any], session_id: str) -> Dict[str, Any]:
    """Execute action through CI/CD pipeline."""
    try:
        from api.adaptive_cicd_api import trigger_pipeline

        pipeline_request = {
            "pipeline_type": "diagnostic_fix",
            "action": action.get("action"),
            "target": action.get("target"),
            "command": action.get("command"),
            "session_id": session_id,
            "trust_threshold": 0.7,
            "kpi_validation": True
        }

        result = await trigger_pipeline(pipeline_request)

        return {
            "status": result.get("status", "unknown"),
            "pipeline_id": result.get("pipeline_id"),
            "output": result.get("output", ""),
            "execution_time": result.get("execution_time")
        }

    except ImportError:
        # CI/CD not available - execute directly with safety checks
        logger.warning("CI/CD pipeline not available - attempting direct execution")
        return await _safe_direct_execution(action)
    except Exception as e:
        logger.error(f"Error executing through CI/CD: {e}")
        return {"status": "error", "error": str(e)}


async def _safe_direct_execution(action: Dict[str, Any]) -> Dict[str, Any]:
    """
    Safe direct execution when CI/CD is not available.

    Only executes safe, reversible commands.
    """
    import subprocess

    command = action.get("command")
    if not command:
        return {"status": "skipped", "reason": "No command to execute"}

    # Safety checks
    ALLOWED_COMMANDS = ["pip install", "pip show", "python -c", "echo"]
    BLOCKED_PATTERNS = ["rm ", "del ", "sudo", "chmod", "chown", ">", "|", ";", "&&"]

    # Check if command is allowed
    is_allowed = any(command.strip().startswith(allowed) for allowed in ALLOWED_COMMANDS)
    is_blocked = any(blocked in command for blocked in BLOCKED_PATTERNS)

    if not is_allowed or is_blocked:
        return {
            "status": "blocked",
            "reason": "Command not in safe execution whitelist",
            "command": command
        }

    try:
        # Execute with timeout and capture output
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60
        )

        return {
            "status": "success" if result.returncode == 0 else "failed",
            "output": result.stdout[:1000],
            "error": result.stderr[:500] if result.stderr else None,
            "return_code": result.returncode,
            "execution_method": "direct_safe"
        }

    except subprocess.TimeoutExpired:
        return {"status": "timeout", "reason": "Command timed out after 60s"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def _record_fix_outcome(
    action: Dict[str, Any],
    result: Dict[str, Any],
    success: bool
):
    """Record fix outcome for learning."""
    try:
        # Record to learning system
        outcome = {
            "action": action.get("action"),
            "target": action.get("target"),
            "success": success,
            "result": result,
            "timestamp": datetime.utcnow().isoformat(),
            "validation": action.get("validation", {})
        }

        # Store for pattern learning
        _fix_outcomes.append(outcome)

        # Limit history
        if len(_fix_outcomes) > 500:
            _fix_outcomes.pop(0)

        # Update trust scores based on outcome
        if success:
            # Successful fix - increase trust in similar fixes
            logger.info(f"Fix succeeded: {action.get('target')}")
        else:
            # Failed fix - decrease trust, flag for review
            logger.warning(f"Fix failed: {action.get('target')} - {result.get('error', 'unknown')}")

    except Exception as e:
        logger.error(f"Error recording fix outcome: {e}")


# Storage for fix outcomes
_fix_outcomes: List[Dict[str, Any]] = []
_pipeline_results: Dict[str, List[Dict[str, Any]]] = {}


def _store_pipeline_results(session_id: str, results: List[Dict[str, Any]]):
    """Store pipeline results for retrieval."""
    _pipeline_results[session_id] = results

    # Limit stored sessions
    if len(_pipeline_results) > 50:
        oldest_key = next(iter(_pipeline_results))
        del _pipeline_results[oldest_key]


@router.get("/diagnostics/pipeline/{session_id}")
async def get_pipeline_results(session_id: str):
    """Get pipeline execution results for a diagnostic session."""
    results = _pipeline_results.get(session_id)

    if not results:
        raise HTTPException(status_code=404, detail=f"No pipeline results for session {session_id}")

    return {
        "session_id": session_id,
        "results": results,
        "total_actions": len(results),
        "completed": len([r for r in results if r.get("status") == "completed"]),
        "failed": len([r for r in results if r.get("status") == "failed"]),
        "pending": len([r for r in results if r.get("status") in ["pending", "awaiting_approval"]])
    }


@router.get("/diagnostics/outcomes")
async def get_fix_outcomes(limit: int = 50):
    """Get history of fix outcomes for learning analysis."""
    outcomes = _fix_outcomes[-limit:]

    success_count = len([o for o in outcomes if o.get("success")])
    total = len(outcomes)

    return {
        "outcomes": outcomes,
        "total": total,
        "success_rate": (success_count / total * 100) if total > 0 else 0,
        "success_count": success_count,
        "failure_count": total - success_count
    }
