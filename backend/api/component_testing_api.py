"""
API endpoint for comprehensive component testing with self-healing integration.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session

from database.session import get_session
from tests.comprehensive_component_tester import (
    ComprehensiveComponentTester,
    TestSuiteResult,
    TrustLevel
)

router = APIRouter(prefix="/component-testing", tags=["component-testing"])


class TestRequest(BaseModel):
    """Request model for component testing."""
    enable_healing: bool = Field(True, description="Enable self-healing")
    trust_level: int = Field(3, ge=0, le=9, description="Trust level for healing (0-9)")
    category: Optional[str] = Field(None, description="Test only specific category")
    background: bool = Field(False, description="Run in background")


class TestResponse(BaseModel):
    """Response model for component testing."""
    test_id: str
    status: str
    message: str
    total_components: int
    started_at: str


class TestStatusResponse(BaseModel):
    """Response model for test status."""
    test_id: str
    status: str
    progress: Dict[str, Any]
    results: Optional[Dict[str, Any]] = None


# In-memory test status (in production, use Redis or database)
test_statuses: Dict[str, Dict[str, Any]] = {}


@router.post("/test-all", response_model=TestResponse)
async def test_all_components(
    request: TestRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session)
):
    """
    Test all GRACE components and send bugs to self-healing system.
    
    This endpoint:
    1. Tests all 400+ components
    2. Logs bugs/problems
    3. Creates Genesis Keys for tracking
    4. Sends issues to autonomous healing system
    5. Returns comprehensive test results
    """
    test_id = f"test_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    
    def run_tests():
        """Background task to run tests."""
        try:
            tester = ComprehensiveComponentTester(
                session=session,
                enable_healing=request.enable_healing,
                trust_level=TrustLevel(request.trust_level)
            )
            
            # Filter by category if specified
            if request.category:
                tester.components = [
                    c for c in tester.components 
                    if c["category"] == request.category
                ]
            
            # Run tests
            suite_result = tester.test_all_components()
            
            # Generate report
            report_path = Path(__file__).parent.parent / "tests" / f"component_test_report_{test_id}.json"
            tester.generate_report(suite_result, report_path)
            
            # Update status
            test_statuses[test_id] = {
                "status": "completed",
                "suite_result": suite_result,
                "report_path": str(report_path),
                "completed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            test_statuses[test_id] = {
                "status": "error",
                "error": str(e),
                "completed_at": datetime.utcnow().isoformat()
            }
    
    # Initialize tester to get component count
    tester = ComprehensiveComponentTester(
        session=session,
        enable_healing=request.enable_healing,
        trust_level=TrustLevel(request.trust_level)
    )
    
    if request.category:
        tester.components = [
            c for c in tester.components 
            if c["category"] == request.category
        ]
    
    total_components = len(tester.components)
    
    # Initialize status
    test_statuses[test_id] = {
        "status": "running",
        "started_at": datetime.utcnow().isoformat(),
        "total_components": total_components,
        "progress": {
            "tested": 0,
            "passed": 0,
            "failed": 0,
            "errors": 0
        }
    }
    
    if request.background:
        # Run in background
        background_tasks.add_task(run_tests)
        return TestResponse(
            test_id=test_id,
            status="running",
            message=f"Testing {total_components} components in background",
            total_components=total_components,
            started_at=test_statuses[test_id]["started_at"]
        )
    else:
        # Run synchronously
        run_tests()
        status = test_statuses[test_id]
        return TestResponse(
            test_id=test_id,
            status=status["status"],
            message=f"Test completed: {status.get('suite_result', {}).get('passed', 0)} passed",
            total_components=total_components,
            started_at=status["started_at"]
        )


@router.get("/status/{test_id}", response_model=TestStatusResponse)
async def get_test_status(test_id: str):
    """Get status of a running or completed test."""
    if test_id not in test_statuses:
        raise HTTPException(status_code=404, detail="Test ID not found")
    
    status = test_statuses[test_id]
    
    response_data = {
        "test_id": test_id,
        "status": status["status"],
        "progress": status.get("progress", {})
    }
    
    if status["status"] == "completed" and "suite_result" in status:
        suite_result = status["suite_result"]
        response_data["results"] = {
            "total_components": suite_result.total_components,
            "passed": suite_result.passed,
            "failed": suite_result.failed,
            "errors": suite_result.errors,
            "skipped": suite_result.skipped,
            "total_duration_ms": suite_result.total_duration_ms,
            "healing_summary": suite_result.healing_summary,
            "report_path": status.get("report_path")
        }
    
    return TestStatusResponse(**response_data)


@router.get("/categories")
async def get_test_categories():
    """Get list of available component categories for testing."""
    categories = [
        "api",
        "cognitive",
        "genesis",
        "llm_orchestrator",
        "retrieval",
        "ingestion",
        "file_manager",
        "librarian",
        "ml_intelligence",
        "layer1",
        "layer2",
        "diagnostic_machine",
        "timesense",
        "enterprise",
        "ci_cd",
        "autonomous_stress_testing",
        "security",
        "embedding",
        "ollama_client",
        "vector_db",
        "version_control",
        "utils",
        "world_model",
        "agent",
        "confidence_scorer",
        "scraping",
        "models",
        "database"
    ]
    return {"categories": categories}


@router.get("/reports")
async def list_test_reports():
    """List all available test reports."""
    reports_dir = Path(__file__).parent.parent / "tests"
    reports = []
    
    if reports_dir.exists():
        for report_file in reports_dir.glob("component_test_report_*.json"):
            reports.append({
                "filename": report_file.name,
                "path": str(report_file),
                "size": report_file.stat().st_size,
                "modified": datetime.fromtimestamp(report_file.stat().st_mtime).isoformat()
            })
    
    return {"reports": sorted(reports, key=lambda x: x["modified"], reverse=True)}


@router.get("/reports/{report_id}")
async def get_test_report(report_id: str):
    """Get a specific test report by ID."""
    import json
    
    reports_dir = Path(__file__).parent.parent / "tests"
    report_file = reports_dir / f"component_test_report_{report_id}.json"
    
    if not report_file.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    
    with open(report_file, 'r', encoding='utf-8') as f:
        report = json.load(f)
    
    return report
