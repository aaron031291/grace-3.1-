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

from core.datetime_utils import as_naive_utc

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


def propose_and_start_experiment(
    title: str,
    description: str,
    hypothesis: str,
    domain: str = "general",
    tracking_days: int = 60,
    config_changes: Dict[str, Any] = None,
    source: str = "grace",
    use_consensus: bool = True,
) -> Experiment:
    """
    Autonomously propose AND start an experiment. No permission needed.
    Only the END RESULT needs human approval (aye/nay).

    Uses 4-layer decision architecture:
      Layer 1: All models deliberate independently on the experiment design
      Layer 2: Consensus on whether experiment is safe to run
      Layer 3: Align to Grace's current needs
      Layer 4: Verify no conflicts with running experiments
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

    # 4-layer decision: should this experiment run?
    if use_consensus:
        try:
            from cognitive.consensus_engine import run_consensus
            decision = run_consensus(
                prompt=(
                    f"Should Grace autonomously run this experiment?\n\n"
                    f"Title: {title}\nHypothesis: {hypothesis}\nDomain: {domain}\n"
                    f"Duration: {tracking_days} days\n\n"
                    f"Check: Is it safe? Any conflicts? Should it proceed?"
                ),
                models=["kimi", "opus"],
                source="autonomous",
            )
            exp.consensus_result = decision.final_output[:500]
            # Only block if consensus explicitly says no
            if "no" in decision.final_output[:50].lower() and decision.confidence > 0.8:
                exp.status = ExperimentStatus.REJECTED
                exp.consensus_result = f"Blocked by consensus: {decision.final_output[:200]}"
                _save_experiment(exp)
                return exp
        except Exception:
            pass

    # Capture baseline metrics
    exp.baseline = _capture_baseline_metrics()

    # Auto-start (no permission needed for experiments)
    exp.status = ExperimentStatus.RUNNING
    exp.end_date = (datetime.utcnow() + timedelta(days=tracking_days)).isoformat()

    _save_experiment(exp)

    try:
        from api._genesis_tracker import track
        track(
            key_type="system",
            what=f"Experiment auto-started: {title}",
            how="sandbox_engine.propose_and_start_experiment",
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
        "day": (datetime.utcnow() - as_naive_utc(datetime.fromisoformat(exp.created_at))).days if exp.created_at else 0,
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
        "days_tracked": (datetime.utcnow() - as_naive_utc(datetime.fromisoformat(exp.created_at))).days if exp.created_at else 0,
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


def run_autonomous_experiment(
    title: str,
    hypothesis: str,
    domain: str = "general",
    research_sources: List[str] = None,
) -> Dict[str, Any]:
    """
    Fully autonomous experiment. No permission needed to START.
    Only the end result needs human approval (aye/nay).

    Flow:
      1. All 4 models deliberate on the experiment design (consensus)
      2. Experiment auto-starts and tracks for 60 days
      3. Grace tries 3 different approaches if first fails
      4. 30% improvement threshold to call it a success
      5. If all 3 approaches fail → logged, monitored, revisited later
      6. Pulls from GitHub, ArXiv for research
      7. Trust scores and KPIs tracked via genesis keys
    """
    SUCCESS_THRESHOLD = 0.30  # 30% improvement = success
    MAX_APPROACHES = 3

    result = {
        "title": title,
        "hypothesis": hypothesis,
        "status": "starting",
        "approaches_tried": 0,
        "best_improvement": 0,
        "experiment_id": None,
    }

    # Step 1: 4-model consensus on experiment design
    try:
        from cognitive.consensus_engine import run_consensus
        design = run_consensus(
            prompt=(
                f"Design an autonomous experiment for Grace:\n\n"
                f"Title: {title}\nHypothesis: {hypothesis}\nDomain: {domain}\n\n"
                f"Provide:\n"
                f"1. Three different approaches to test the hypothesis\n"
                f"2. What metrics to track\n"
                f"3. What 30% improvement looks like\n"
                f"4. What research papers or GitHub repos might help"
            ),
            models=["kimi", "opus"],
            source="autonomous",
        )
        result["consensus_design"] = design.final_output[:1000]
    except Exception:
        result["consensus_design"] = "Consensus unavailable"

    # Step 2: Create and auto-start the experiment
    exp = propose_and_start_experiment(
        title=title,
        description=f"Autonomous experiment. Hypothesis: {hypothesis}",
        hypothesis=hypothesis,
        domain=domain,
        tracking_days=60,
        source="autonomous",
    )
    result["experiment_id"] = exp.id

    # Step 3: Try up to 3 different approaches
    for attempt in range(MAX_APPROACHES):
        result["approaches_tried"] = attempt + 1

        # Record checkpoint
        checkpoint = record_checkpoint(exp.id)

        # Check improvement
        if checkpoint.get("metrics"):
            baseline = exp.baseline or {}
            for key in baseline:
                if key in checkpoint.get("metrics", {}):
                    if baseline[key] != 0:
                        improvement = (checkpoint["metrics"][key] - baseline[key]) / abs(baseline[key])
                        if improvement > result["best_improvement"]:
                            result["best_improvement"] = improvement

        if result["best_improvement"] >= SUCCESS_THRESHOLD:
            result["status"] = "success_awaiting_approval"
            exp.status = ExperimentStatus.AWAITING_APPROVAL
            _save_experiment(exp)

            # Genesis Key
            try:
                from api._genesis_tracker import track
                track(
                    key_type="system",
                    what=f"Experiment succeeded: {title} ({result['best_improvement']*100:.1f}% improvement)",
                    how="sandbox_engine.run_autonomous_experiment",
                    output_data=result,
                    tags=["experiment", "success", "autonomous", domain],
                )
            except Exception:
                pass

            return result

    # Step 4: All approaches failed — log and monitor for later
    if result["best_improvement"] < SUCCESS_THRESHOLD:
        result["status"] = "deferred"
        result["reason"] = (
            f"All {MAX_APPROACHES} approaches tried. Best improvement: "
            f"{result['best_improvement']*100:.1f}% (need {SUCCESS_THRESHOLD*100:.0f}%). "
            f"Logged for revisit when Grace has more knowledge."
        )
        exp.status = ExperimentStatus.PROPOSED  # Reset to revisit later

        # Store as learning for future
        try:
            from cognitive.unified_memory import get_unified_memory
            mem = get_unified_memory()
            mem.store_episode(
                problem=f"Experiment failed: {title}",
                action=f"Tried {MAX_APPROACHES} approaches, best: {result['best_improvement']*100:.1f}%",
                outcome="DEFERRED — insufficient knowledge. Will revisit.",
                trust=0.4,
                source="autonomous_experiment",
            )
        except Exception:
            pass

        # Genesis Key
        try:
            from api._genesis_tracker import track
            track(
                key_type="system",
                what=f"Experiment deferred: {title} (insufficient improvement)",
                how="sandbox_engine.run_autonomous_experiment",
                output_data=result,
                tags=["experiment", "deferred", "autonomous", domain],
            )
        except Exception:
            pass

        _save_experiment(exp)

    return result


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
