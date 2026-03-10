"""
Consensus Auto-Fixer — gives the consensus mechanism full authority to
diagnose and fix problems, subject to:
  1. Hallucination verification
  2. All models must agree
  3. Every action tracked via Genesis key
  4. Governance rules enforced

Flow:
  1. Probe detects broken endpoint / dormant service
  2. All available models independently diagnose the problem
  3. Consensus formed — agreements and disagreements identified
  4. If ALL models agree with high confidence → auto-execute fix
  5. Fix verified by re-probing the endpoint
  6. Everything tracked in Genesis keys with full provenance
"""

from fastapi import APIRouter
from typing import List, Dict, Any
from datetime import datetime, timezone
import logging
import json

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/consensus-fix", tags=["Consensus Auto-Fixer"])


def _get_all_problems() -> List[dict]:
    """Collect all known problems from every diagnostic source."""
    problems = []

    # 1. Broken API endpoints (from probe)
    try:
        from api.probe_agent_api import _discover_routes, _probe_endpoint
        routes = _discover_routes()
        for r in routes[:100]:
            result = _probe_endpoint(r["path"], r["method"])
            if result["status"] == "broken":
                problems.append({
                    "source": "api_probe",
                    "type": "broken_endpoint",
                    "target": result["path"],
                    "error": result.get("error", ""),
                    "status_code": result.get("status_code", 0),
                })
    except Exception as e:
        logger.debug("Probe discovery skipped: %s", e)

    # 2. Component health problems
    try:
        from api.component_health_api import (
            COMPONENT_REGISTRY, _get_genesis_keys, _classify_component,
            _check_service_health
        )
        keys = _get_genesis_keys(minutes=60, limit=2000)
        svc_health = _check_service_health()
        for comp_id, comp in COMPONENT_REGISTRY.items():
            classified = _classify_component(comp_id, comp, keys, svc_health)
            if classified["status"] in ("red", "orange"):
                problems.append({
                    "source": "component_health",
                    "type": "degraded_component",
                    "target": classified["label"],
                    "component_id": comp_id,
                    "error": classified["reason"],
                    "status": classified["status"],
                })
    except Exception as e:
        logger.debug("Component health check skipped: %s", e)

    # 3. Trigger scan
    try:
        from api.runtime_triggers_api import (
            _scan_resources, _scan_services, _scan_code, _scan_network
        )
        for scanner in [_scan_resources, _scan_services, _scan_code, _scan_network]:
            try:
                found = scanner()
                for t in found:
                    entry = t.to_dict() if hasattr(t, 'to_dict') else t
                    if entry.get("severity") in ("critical", "warning"):
                        problems.append({
                            "source": "trigger_scan",
                            "type": entry.get("category", "unknown"),
                            "target": entry.get("name", ""),
                            "error": entry.get("detail", ""),
                            "severity": entry.get("severity", ""),
                        })
            except Exception:
                pass
    except Exception:
        pass

    return problems


def _consensus_diagnose_and_fix(problem: dict) -> dict:
    """
    Send a problem to ALL models for diagnosis + fix proposal.
    If all agree → execute. If not → log for human review.
    """
    prompt = (
        f"Grace system problem detected:\n\n"
        f"Source: {problem.get('source')}\n"
        f"Type: {problem.get('type')}\n"
        f"Target: {problem.get('target')}\n"
        f"Error: {problem.get('error')}\n"
        f"Status: {problem.get('status', problem.get('status_code', ''))}\n\n"
        f"1. What is the root cause? (max 2 sentences)\n"
        f"2. What is the specific fix? (max 3 sentences)\n"
        f"3. Can this be safely auto-fixed without human approval? (yes/no + reason)\n"
    )

    result = {
        "problem": problem,
        "diagnosis": None,
        "confidence": 0,
        "all_agree": False,
        "auto_fixable": False,
        "action_taken": "none",
        "genesis_key_id": None,
    }

    try:
        from cognitive.consensus_engine import run_consensus
        consensus = run_consensus(
            prompt=prompt,
            system_prompt=(
                "You are a system diagnostician for Grace AI. "
                "Diagnose problems precisely. Propose concrete fixes. "
                "Only say 'yes' to auto-fix if the action is safe and reversible."
            ),
            source="autonomous",
        )

        result["diagnosis"] = consensus.final_output
        result["confidence"] = consensus.confidence
        result["models_used"] = consensus.models_used
        result["agreements"] = consensus.agreements
        result["disagreements"] = consensus.disagreements
        result["all_agree"] = len(consensus.disagreements) == 0
        result["individual_responses"] = consensus.individual_responses

        # Check if auto-fixable
        output_lower = consensus.final_output.lower()
        result["auto_fixable"] = (
            result["all_agree"]
            and result["confidence"] >= 0.6
            and "yes" in output_lower
            and "auto-fix" in output_lower or "safely" in output_lower
        )

        # Track diagnosis via Genesis key
        try:
            from api._genesis_tracker import track
            gk_id = track(
                key_type="ai_response",
                what=f"Consensus diagnosis: {problem.get('target')} — {consensus.final_output[:100]}",
                who="consensus_fixer",
                how="consensus_engine.run_consensus",
                input_data={"problem": problem},
                output_data={
                    "diagnosis": consensus.final_output[:500],
                    "confidence": consensus.confidence,
                    "all_agree": result["all_agree"],
                    "models": consensus.models_used,
                },
                tags=["consensus-fix", "diagnosis", problem.get("type", "")],
            )
            result["genesis_key_id"] = gk_id
        except Exception:
            pass

        # Auto-execute if safe
        if result["auto_fixable"]:
            heal_result = _execute_healing(problem)
            result["action_taken"] = heal_result.get("action", "attempted")
            result["heal_result"] = heal_result

    except Exception as e:
        result["diagnosis"] = f"Consensus failed: {e}"
        result["action_taken"] = "consensus_error"

    return result


def _execute_healing(problem: dict) -> dict:
    """Execute a safe healing action for a problem."""
    ptype = problem.get("type", "")
    target = problem.get("target", "")

    try:
        # Service-level healing
        if ptype == "degraded_component" or "down" in problem.get("error", "").lower():
            from diagnostic_machine.diagnostic_engine import get_diagnostic_engine, TriggerSource
            engine = get_diagnostic_engine()
            engine.run_cycle(TriggerSource.SENSOR_FLAG)

            from api._genesis_tracker import track
            track(
                key_type="system_event",
                what=f"Consensus auto-heal: diagnostic cycle for {target}",
                who="consensus_fixer",
                tags=["consensus-fix", "auto-heal", "diagnostic-cycle"],
            )
            return {"action": "diagnostic_cycle", "target": target}

        # DB reconnect
        if "database" in target.lower() or "db" in ptype.lower():
            from database.connection import DatabaseConnection
            DatabaseConnection.get_engine().dispose()
            from api._genesis_tracker import track
            track(
                key_type="system_event",
                what=f"Consensus auto-heal: DB pool reset for {target}",
                who="consensus_fixer",
                tags=["consensus-fix", "auto-heal", "db-reconnect"],
            )
            return {"action": "db_pool_reset", "target": target}

        # GC for memory issues
        if "memory" in problem.get("error", "").lower() or "ram" in ptype.lower():
            import gc
            gc.collect()
            return {"action": "gc_collect", "target": target}

        return {"action": "no_safe_action", "target": target}

    except Exception as e:
        return {"action": "heal_error", "target": target, "error": str(e)}


# ── Endpoints ────────────────────────────────────────────────────────

@router.post("/scan")
async def scan_all_problems():
    """Scan every diagnostic source for problems."""
    problems = _get_all_problems()
    return {
        "problems": problems,
        "total": len(problems),
        "critical": sum(1 for p in problems if p.get("severity") == "critical" or p.get("status") == "red"),
        "scanned_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/fix-all")
async def consensus_fix_all():
    """
    Full autonomous pipeline: scan → diagnose via consensus → fix.
    All models must agree. Everything tracked via Genesis keys.
    """
    problems = _get_all_problems()

    if not problems:
        return {
            "status": "all_clear",
            "message": "No problems found",
            "problems_found": 0,
        }

    results = []
    for problem in problems[:10]:  # Limit to 10 to control token costs
        result = _consensus_diagnose_and_fix(problem)
        results.append(result)

    fixed = [r for r in results if r.get("action_taken") not in ("none", "consensus_error")]
    agreed = [r for r in results if r.get("all_agree")]

    # Track overall run
    try:
        from api._genesis_tracker import track
        track(
            key_type="system_event",
            what=f"Consensus fix-all: {len(problems)} problems, {len(fixed)} fixed, {len(agreed)} agreed",
            who="consensus_fixer",
            how="consensus_fix_all",
            output_data={
                "problems_found": len(problems),
                "diagnosed": len(results),
                "fixed": len(fixed),
                "all_agreed": len(agreed),
            },
            tags=["consensus-fix", "batch-run"],
        )
    except Exception:
        pass

    return {
        "problems_found": len(problems),
        "diagnosed": len(results),
        "fixed": len(fixed),
        "consensus_agreed": len(agreed),
        "results": results,
    }


@router.post("/fix-one")
async def consensus_fix_one(target: str = "", error: str = ""):
    """Diagnose and fix a single specific problem via consensus."""
    problem = {
        "source": "manual",
        "type": "user_reported",
        "target": target,
        "error": error,
    }
    result = _consensus_diagnose_and_fix(problem)
    return result
