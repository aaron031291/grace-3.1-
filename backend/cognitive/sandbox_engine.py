"""
Sandbox Experimentation Engine — Grace's Autonomous Testing Lab

Grace can autonomously propose and run experiments in a sandboxed
environment that runs in parallel with the live system:

1. PROPOSE: Grace identifies an optimization or new approach
2. SANDBOX: Experiment runs in isolation (no live system impact)
3. TRACK: KPIs, metrics, and performance tracked for 30-60 days
4. COMPARE: Sandbox results compared against live system baseline
5. REPORT: Analytics report generated with pros/cons
6. CONSENSUS: Kimi/Opus weigh in on whether to adopt
7. NOTIFY: User gets a notification with the full analysis
8. ADOPT: If approved, sandbox code/config merged into live

Experiments can test:
  - Communication pathways (JSON vs structured text vs hybrid)
  - API routing strategies
  - Learning algorithms
  - Trust scoring formulas
  - LLM prompt templates
  - Memory retrieval strategies
"""

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)

EXPERIMENTS_DIR = Path(__file__).parent.parent / "data" / "experiments"


class ExperimentStatus(str, Enum):
    PROPOSED = "proposed"
    RUNNING = "running"
    TRACKING = "tracking"
    ANALYSING = "analysing"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    ADOPTED = "adopted"


@dataclass
class ExperimentMetric:
    name: str
    baseline_value: float
    current_value: float
    target_value: Optional[float] = None
    improved: bool = False
    delta_percent: float = 0.0


@dataclass
class Experiment:
    id: str
    title: str
    description: str
    hypothesis: str
    domain: str  # communication, routing, learning, trust, prompts, memory
    status: ExperimentStatus
    created_at: str
    tracking_days: int = 60
    end_date: str = ""
    metrics: List[Dict[str, Any]] = field(default_factory=list)
    checkpoints: List[Dict[str, Any]] = field(default_factory=list)
    baseline: Dict[str, float] = field(default_factory=dict)
    current: Dict[str, float] = field(default_factory=dict)
    config_changes: Dict[str, Any] = field(default_factory=dict)
    source: str = "grace"  # grace (autonomous) or user
    consensus_result: Optional[str] = None
    final_report: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "hypothesis": self.hypothesis,
            "domain": self.domain,
            "status": self.status.value if isinstance(self.status, ExperimentStatus) else self.status,
            "created_at": self.created_at,
            "tracking_days": self.tracking_days,
            "end_date": self.end_date,
            "metrics": self.metrics,
            "checkpoints": self.checkpoints,
            "baseline": self.baseline,
            "current": self.current,
            "config_changes": self.config_changes,
            "source": self.source,
            "consensus_result": self.consensus_result,
            "final_report": self.final_report,
        }


def _ensure():
    EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)


def _load_experiment(exp_id: str) -> Optional[Experiment]:
    path = EXPERIMENTS_DIR / f"{exp_id}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        return Experiment(**{k: v for k, v in data.items() if k in Experiment.__dataclass_fields__})
    except Exception:
        return None


def _save_experiment(exp: Experiment):
    _ensure()
    (EXPERIMENTS_DIR / f"{exp.id}.json").write_text(json.dumps(exp.to_dict(), indent=2, default=str))


def propose_experiment(
    title: str,
    description: str,
    hypothesis: str,
    domain: str = "general",
    tracking_days: int = 60,
    config_changes: Dict[str, Any] = None,
    source: str = "grace",
) -> Experiment:
    """
    Propose a new experiment.
    Grace or the user can propose experiments.
    """
    exp = Experiment(
        id=f"exp_{uuid.uuid4().hex[:10]}",
        title=title,
        description=description,
        hypothesis=hypothesis,
        domain=domain,
        status=ExperimentStatus.PROPOSED,
        created_at=datetime.utcnow().isoformat(),
        tracking_days=tracking_days,
        end_date=(datetime.utcnow() + timedelta(days=tracking_days)).isoformat(),
        config_changes=config_changes or {},
        source=source,
    )

    # Capture baseline metrics
    exp.baseline = _capture_baseline_metrics()

    _save_experiment(exp)

    try:
        from api._genesis_tracker import track
        track(
            key_type="system",
            what=f"Experiment proposed: {title}",
            how="sandbox_engine.propose_experiment",
            output_data={"id": exp.id, "domain": domain, "tracking_days": tracking_days},
            tags=["experiment", "proposed", domain],
        )
    except Exception:
        pass

    try:
        from cognitive.event_bus import publish
        publish("experiment.proposed", {"id": exp.id, "title": title, "domain": domain})
    except Exception:
        pass

    return exp


def start_experiment(exp_id: str) -> Dict[str, Any]:
    """Start tracking an experiment."""
    exp = _load_experiment(exp_id)
    if not exp:
        return {"error": "Experiment not found"}

    exp.status = ExperimentStatus.RUNNING
    exp.end_date = (datetime.utcnow() + timedelta(days=exp.tracking_days)).isoformat()

    _save_experiment(exp)
    return {"started": True, "id": exp_id, "end_date": exp.end_date}


def record_checkpoint(exp_id: str) -> Dict[str, Any]:
    """Record a metrics checkpoint for an experiment."""
    exp = _load_experiment(exp_id)
    if not exp:
        return {"error": "Experiment not found"}

    current = _capture_baseline_metrics()
    checkpoint = {
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": current,
        "day": (datetime.utcnow() - datetime.fromisoformat(exp.created_at)).days,
    }

    # Calculate deltas from baseline
    for key in exp.baseline:
        if key in current and exp.baseline[key] != 0:
            delta = ((current[key] - exp.baseline[key]) / abs(exp.baseline[key])) * 100
            checkpoint[f"{key}_delta_pct"] = round(delta, 2)

    exp.checkpoints.append(checkpoint)
    exp.current = current
    _save_experiment(exp)

    return {"checkpoint_recorded": True, "day": checkpoint["day"], "metrics": current}


def analyse_experiment(exp_id: str) -> Dict[str, Any]:
    """
    Analyse an experiment's results.
    Compares baseline to current, identifies improvements/regressions.
    """
    exp = _load_experiment(exp_id)
    if not exp:
        return {"error": "Experiment not found"}

    exp.status = ExperimentStatus.ANALYSING

    # Compare baseline to current
    comparisons = []
    for key in exp.baseline:
        baseline_val = exp.baseline.get(key, 0)
        current_val = exp.current.get(key, 0)
        delta = current_val - baseline_val
        delta_pct = ((delta / abs(baseline_val)) * 100) if baseline_val != 0 else 0
        improved = delta > 0 if key in ("trust_score", "learning_count", "integration_health") else delta < 0

        comparisons.append({
            "metric": key,
            "baseline": baseline_val,
            "current": current_val,
            "delta": round(delta, 3),
            "delta_percent": round(delta_pct, 2),
            "improved": improved,
        })

    # Generate analysis
    improved_count = sum(1 for c in comparisons if c["improved"])
    total_metrics = len(comparisons)

    analysis = {
        "experiment_id": exp_id,
        "title": exp.title,
        "hypothesis": exp.hypothesis,
        "comparisons": comparisons,
        "improved_metrics": improved_count,
        "total_metrics": total_metrics,
        "improvement_rate": round(improved_count / total_metrics, 3) if total_metrics else 0,
        "recommendation": "adopt" if improved_count > total_metrics / 2 else "reject",
        "checkpoints_recorded": len(exp.checkpoints),
        "days_tracked": (datetime.utcnow() - datetime.fromisoformat(exp.created_at)).days,
    }

    exp.final_report = json.dumps(analysis, indent=2)
    exp.status = ExperimentStatus.AWAITING_APPROVAL
    _save_experiment(exp)

    return analysis


def approve_experiment(exp_id: str, approved: bool = True) -> Dict[str, Any]:
    """Approve or reject an experiment for adoption."""
    exp = _load_experiment(exp_id)
    if not exp:
        return {"error": "Experiment not found"}

    exp.status = ExperimentStatus.APPROVED if approved else ExperimentStatus.REJECTED

    try:
        from api._genesis_tracker import track
        track(
            key_type="system",
            what=f"Experiment {'approved' if approved else 'rejected'}: {exp.title}",
            how="sandbox_engine.approve_experiment",
            output_data={"id": exp_id, "approved": approved},
            tags=["experiment", "approved" if approved else "rejected"],
        )
    except Exception:
        pass

    _save_experiment(exp)
    return {"id": exp_id, "status": exp.status.value, "approved": approved}


def list_experiments(status: str = None) -> List[Dict[str, Any]]:
    """List all experiments, optionally filtered by status."""
    _ensure()
    experiments = []
    for f in sorted(EXPERIMENTS_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            data = json.loads(f.read_text())
            if status and data.get("status") != status:
                continue
            experiments.append({
                "id": data["id"],
                "title": data["title"],
                "domain": data.get("domain", ""),
                "status": data.get("status", ""),
                "source": data.get("source", ""),
                "created_at": data.get("created_at", ""),
                "tracking_days": data.get("tracking_days", 0),
                "checkpoints": len(data.get("checkpoints", [])),
            })
        except Exception:
            pass
    return experiments


def _capture_baseline_metrics() -> Dict[str, float]:
    """Capture current system metrics as a baseline."""
    metrics = {}

    try:
        from cognitive.trust_engine import get_trust_engine
        te = get_trust_engine()
        d = te.get_dashboard()
        metrics["trust_score"] = d.get("overall_trust", 0)
    except Exception:
        metrics["trust_score"] = 0

    try:
        from llm_orchestrator.governance_wrapper import get_llm_usage_stats
        stats = get_llm_usage_stats()
        metrics["llm_latency_ms"] = stats.get("avg_latency_ms", 0)
        metrics["llm_error_rate"] = stats.get("error_rate", 0)
        metrics["llm_total_calls"] = stats.get("total_calls", 0)
    except Exception:
        pass

    try:
        from cognitive.central_orchestrator import get_orchestrator
        health = get_orchestrator().check_integration_health()
        metrics["integration_health"] = health.get("health_percent", 0)
    except Exception:
        metrics["integration_health"] = 0

    try:
        from cognitive.unified_memory import get_unified_memory
        mem_stats = get_unified_memory().get_stats()
        total = sum(v.get("count", 0) for v in mem_stats.values() if isinstance(v, dict))
        metrics["memory_entries"] = total
    except Exception:
        metrics["memory_entries"] = 0

    return metrics
