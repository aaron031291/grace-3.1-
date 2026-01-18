"""
Benchmark API - Unified Benchmark Endpoints

Provides API endpoints for running benchmarks:
- HumanEval
- BigCodeBench
- MBPP (future)
- Mercury (future)
- etc.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime

from database.session import get_session
from cognitive.enterprise_coding_agent import get_enterprise_coding_agent
from cognitive.autonomous_healing_system import TrustLevel
from benchmarking.benchmark_harness import get_benchmark_harness
from benchmarking.humaneval_integration import get_humaneval_integration
from pathlib import Path

router = APIRouter(prefix="/benchmark", tags=["benchmark"])


class BenchmarkRunRequest(BaseModel):
    """Request model for running a benchmark."""
    benchmark_name: str = Field(..., description="Name of benchmark to run")
    max_problems: Optional[int] = Field(None, description="Maximum number of problems to evaluate")
    timeout: Optional[int] = Field(10, description="Timeout per problem in seconds")


class BenchmarkRunResponse(BaseModel):
    """Response model for benchmark run."""
    benchmark_name: str
    total: int
    passed: int
    failed: int
    pass_rate: float
    duration_seconds: float
    timestamp: str
    results: Optional[List[Dict[str, Any]]] = None


class BenchmarkListResponse(BaseModel):
    """Response model for listing benchmarks."""
    benchmarks: List[str]
    total: int


@router.get("/list", response_model=BenchmarkListResponse)
async def list_benchmarks():
    """List all available benchmarks."""
    try:
        # Get available benchmarks
        harness = get_benchmark_harness()
        benchmarks = list(harness.benchmarks.keys())
        
        return BenchmarkListResponse(
            benchmarks=benchmarks,
            total=len(benchmarks)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing benchmarks: {str(e)}")


@router.post("/run", response_model=BenchmarkRunResponse)
async def run_benchmark(
    request: BenchmarkRunRequest,
    session = Depends(get_session)
):
    """Run a specific benchmark."""
    try:
        # Initialize coding agent
        coding_agent = get_enterprise_coding_agent(
            session=next(session),
            repo_path=Path.cwd(),
            trust_level=TrustLevel.MEDIUM_RISK_AUTO,
            enable_learning=True,
            enable_sandbox=True
        )
        
        # Get benchmark harness
        harness = get_benchmark_harness(coding_agent=coding_agent)
        
        # Run benchmark
        kwargs = {}
        if request.max_problems:
            kwargs["max_problems"] = request.max_problems
        if request.timeout:
            kwargs["timeout"] = request.timeout
        
        result = harness.run_benchmark(request.benchmark_name, **kwargs)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return BenchmarkRunResponse(
            benchmark_name=result["benchmark_name"],
            total=result.get("total", 0),
            passed=result.get("passed", 0),
            failed=result.get("failed", 0),
            pass_rate=result.get("pass_rate", 0.0),
            duration_seconds=result.get("duration_seconds", 0.0),
            timestamp=result.get("timestamp", datetime.now().isoformat()),
            results=(result.get("results") or [])[:10]  # First 10 results - safer access
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error running benchmark: {str(e)}")


@router.post("/run-all")
async def run_all_benchmarks(
    benchmark_names: Optional[List[str]] = None,
    max_problems: Optional[int] = None,
    session = Depends(get_session)
):
    """Run all benchmarks (or specified ones)."""
    try:
        # Initialize coding agent
        coding_agent = get_enterprise_coding_agent(
            session=next(session),
            repo_path=Path.cwd(),
            trust_level=TrustLevel.MEDIUM_RISK_AUTO,
            enable_learning=True,
            enable_sandbox=True
        )
        
        # Get benchmark harness
        harness = get_benchmark_harness(coding_agent=coding_agent)
        
        # Run all benchmarks
        kwargs = {}
        if max_problems:
            kwargs["max_problems"] = max_problems
        
        results = harness.run_all_benchmarks(
            benchmark_names=benchmark_names,
            **kwargs
        )
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error running benchmarks: {str(e)}")


@router.get("/humaneval/leaderboard")
async def get_humaneval_leaderboard():
    """Get HumanEval leaderboard comparison."""
    try:
        humaneval = get_humaneval_integration()
        
        # Get current pass rate (would need to run evaluation first)
        # For now, return leaderboard info
        leaderboard = {
            "GPT-4": 67.0,
            "GPT-4-Turbo": 74.0,
            "Claude-3-Opus": 84.9,
            "Claude-3.5-Sonnet": 84.9,
            "DeepSeek-Coder-V2": 90.2,
            "Human Expert": 95.0
        }
        
        return {
            "leaderboard": leaderboard,
            "note": "Run /benchmark/run with benchmark_name='humaneval' to get Grace's score"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting leaderboard: {str(e)}")
