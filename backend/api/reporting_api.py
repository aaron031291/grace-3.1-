"""
Reporting & Sandbox API — System reports and experiment management.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reports", tags=["Reports & Sandbox"])


class ExperimentProposal(BaseModel):
    title: str
    description: str
    hypothesis: str
    domain: str = "general"
    tracking_days: int = 60
    config_changes: Optional[Dict[str, Any]] = None
    source: str = "user"


# ── Reports ───────────────────────────────────────────────────────────

@router.post("/generate")
async def generate_report(period: str = "daily", days: int = 1):
    """Generate a holistic system report (daily/weekly/monthly)."""
    from cognitive.reporting_engine import generate_report
    report = generate_report(period=period, days=days)
    return report


@router.get("/list")
async def list_reports(limit: int = 20):
    """List available reports."""
    from cognitive.reporting_engine import list_reports
    reports = list_reports(limit=limit)
    return {"reports": reports, "total": len(reports)}


@router.get("/{report_id}")
async def get_report(report_id: str):
    """Get a specific report."""
    from cognitive.reporting_engine import get_report
    report = get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.get("/{report_id}/nlp")
async def get_report_nlp(report_id: str):
    """Get the natural language version of a report."""
    from cognitive.reporting_engine import get_report
    report = get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"report_id": report_id, "nlp_report": report.get("nlp_report", "")}


# ── Sandbox Experiments ───────────────────────────────────────────────

@router.post("/experiments/propose")
async def propose_experiment(req: ExperimentProposal):
    """Propose a new experiment for the sandbox."""
    from cognitive.sandbox_engine import propose_experiment
    exp = propose_experiment(
        title=req.title,
        description=req.description,
        hypothesis=req.hypothesis,
        domain=req.domain,
        tracking_days=req.tracking_days,
        config_changes=req.config_changes,
        source=req.source,
    )
    return exp.to_dict()


@router.post("/experiments/{exp_id}/start")
async def start_experiment(exp_id: str):
    """Start tracking an experiment."""
    from cognitive.sandbox_engine import start_experiment
    return start_experiment(exp_id)


@router.post("/experiments/{exp_id}/checkpoint")
async def record_checkpoint(exp_id: str):
    """Record a metrics checkpoint."""
    from cognitive.sandbox_engine import record_checkpoint
    return record_checkpoint(exp_id)


@router.post("/experiments/{exp_id}/analyse")
async def analyse_experiment(exp_id: str):
    """Analyse experiment results vs baseline."""
    from cognitive.sandbox_engine import analyse_experiment
    return analyse_experiment(exp_id)


@router.post("/experiments/{exp_id}/approve")
async def approve_experiment(exp_id: str, approved: bool = True):
    """Approve or reject an experiment."""
    from cognitive.sandbox_engine import approve_experiment
    return approve_experiment(exp_id, approved)


@router.get("/experiments")
async def list_experiments(status: Optional[str] = None):
    """List all experiments."""
    from cognitive.sandbox_engine import list_experiments
    experiments = list_experiments(status=status)
    return {"experiments": experiments, "total": len(experiments)}


@router.get("/experiments/{exp_id}")
async def get_experiment(exp_id: str):
    """Get experiment details."""
    from cognitive.sandbox_engine import _load_experiment
    exp = _load_experiment(exp_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return exp.to_dict()
