"""
Governance Training Loop — KB → Learning Memory → Oracle → Sandbox → 60d → Report → Approval → +30% → System

Full pipeline for autonomous training with human-readable Oracle and governance:
1. Knowledge base → Learning memory (sync folders / gap fill)
2. Learning memory → Oracle (human-readable files for librarian and file management)
3. New logic → Sandbox environment, test all new logic
4. 60-day trial: live data inputs/outputs, governed by global and local rules + trust score APIs
5. After 60 days: right report, user-in-loop for governance approval
6. If system improvement >= 30% and approved → add to system, then normal governance prevails

Librarian and brains are connected via Oracle export (librarian sees files) and brain actions.
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

TRIAL_DAYS = 60
IMPROVEMENT_THRESHOLD = 0.30  # 30% system improvement to add to system


def run_oracle_export(kb_path: Optional[Path] = None, limit: int = 500, min_trust: float = 0.3) -> Dict[str, Any]:
    """Push learning memory to Oracle (human-readable files). Librarian and file management use this."""
    try:
        from cognitive.oracle_export import export_learning_memory_to_oracle
        return export_learning_memory_to_oracle(limit=limit, min_trust=min_trust, kb_path=kb_path)
    except Exception as e:
        logger.warning("Oracle export failed: %s", e)
        return {"exported": 0, "errors": 1, "error": str(e)}


def run_governance_checks(context: Dict[str, Any]) -> Dict[str, Any]:
    """Governance by global and local rules + trust score APIs."""
    result = {"passed": True, "global_rules": {}, "local_rules": {}, "trust_api": {}}
    try:
        # Global rules (e.g. from core/user_features governance_rules or settings)
        try:
            from core.intelligence import AdaptiveTrust
            trust = AdaptiveTrust.get_all_trust()
            result["trust_api"]["models"] = list(trust.get("models", {}).keys())
            result["trust_api"]["ok"] = bool(trust)
        except Exception as e:
            result["trust_api"]["error"] = str(e)
            result["passed"] = False

        # Local rules / trust score API (learning memory trust, sandbox trust)
        try:
            from cognitive.unified_memory import get_unified_memory
            mem = get_unified_memory()
            stats = mem.get_stats()
            result["local_rules"]["memory_stats"] = {k: (v.get("count", v) if isinstance(v, dict) else v) for k, v in stats.items()}
        except Exception as e:
            result["local_rules"]["error"] = str(e)
    except Exception as e:
        result["passed"] = False
        result["error"] = str(e)
    return result


def run_full_cycle(
    kb_path: Optional[Path] = None,
    export_to_oracle: bool = True,
    run_sandbox_review: bool = True,
) -> Dict[str, Any]:
    """
    One full governance training cycle:
    - Sync learning memory from KB (if mesh integration available)
    - Export learning memory → Oracle (human-readable)
    - Run governance checks (global/local rules, trust APIs)
    - Optionally review sandbox experiments (60-day trial, report, approval queue)
    """
    start = datetime.utcnow()
    result = {
        "cycle_at": start.isoformat(),
        "oracle_export": None,
        "governance": None,
        "sandbox_review": None,
        "errors": [],
    }

    # 1. Learning memory → Oracle (human-readable for librarian)
    if export_to_oracle:
        try:
            result["oracle_export"] = run_oracle_export(kb_path=kb_path)
        except Exception as e:
            result["errors"].append(f"oracle_export: {e}")

    # 2. Governance checks (global/local rules, trust score APIs)
    try:
        result["governance"] = run_governance_checks({"cycle_at": result["cycle_at"]})
    except Exception as e:
        result["errors"].append(f"governance: {e}")
        result["governance"] = {"passed": False, "error": str(e)}

    # 3. Sandbox: experiments in 60-day trial, generate report, queue for user approval
    if run_sandbox_review:
        try:
            from cognitive.autonomous_sandbox_lab import (
                get_sandbox_lab,
                ExperimentStatus,
                TRIAL_DAYS_GOVERNANCE,
                IMPROVEMENT_THRESHOLD_PROMOTION,
            )
            lab = get_sandbox_lab()
            # List experiments that completed trial and are awaiting approval
            awaiting = [
                e for e in lab.experiments.values()
                if e.status == ExperimentStatus.VALIDATED
            ]
            # List experiments in trial (live data phase)
            in_trial = [
                e for e in lab.experiments.values()
                if e.status == ExperimentStatus.TRIAL
            ]
            result["sandbox_review"] = {
                "trial_days": TRIAL_DAYS_GOVERNANCE,
                "improvement_threshold_percent": IMPROVEMENT_THRESHOLD_PROMOTION * 100,
                "awaiting_approval": len(awaiting),
                "in_trial": len(in_trial),
                "awaiting_ids": [e.experiment_id for e in awaiting],
                "message": "User-in-loop approval required for validated experiments; if +30% and approved, add to system.",
            }
        except Exception as e:
            result["errors"].append(f"sandbox_review: {e}")
            result["sandbox_review"] = {"error": str(e)}

    result["duration_sec"] = (datetime.utcnow() - start).total_seconds()
    return result


def get_governance_report(experiment_id: Optional[str] = None) -> Dict[str, Any]:
    """Generate 60-day right report for governance approval (single experiment or summary)."""
    try:
        from cognitive.autonomous_sandbox_lab import get_sandbox_lab, ExperimentStatus
        lab = get_sandbox_lab()
        if experiment_id:
            exp = lab.experiments.get(experiment_id)
            if not exp:
                return {"error": "experiment_not_found", "experiment_id": experiment_id}
            if exp.status != ExperimentStatus.VALIDATED:
                return {
                    "experiment_id": experiment_id,
                    "status": exp.status.value,
                    "message": "Report only for validated experiments (trial complete).",
                }
            return {
                "experiment_id": exp.experiment_id,
                "name": exp.name,
                "trial_days": exp.trial_duration_days,
                "trial_complete": exp.is_trial_complete(),
                "success_rate": exp.get_success_rate(),
                "improvement_percent": exp.improvement_percentage,
                "trust_score": exp.current_trust_score,
                "meets_30_percent": (exp.improvement_percentage or 0) >= (IMPROVEMENT_THRESHOLD * 100),
                "ready_for_approval": exp.can_promote_to_production(),
            }
        # Summary report
        validated = [e for e in lab.experiments.values() if e.status == ExperimentStatus.VALIDATED]
        in_trial = [e for e in lab.experiments.values() if e.status == ExperimentStatus.TRIAL]
        return {
            "validated_count": len(validated),
            "in_trial_count": len(in_trial),
            "validated_ids": [e.experiment_id for e in validated],
            "trial_days": TRIAL_DAYS,
            "improvement_threshold_percent": IMPROVEMENT_THRESHOLD * 100,
        }
    except Exception as e:
        return {"error": str(e)}
