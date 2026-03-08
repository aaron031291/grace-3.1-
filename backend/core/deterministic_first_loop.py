"""
Deterministic-First Loop — push determinism right up to the front door of LLMs.

Full scope and full breadth:
  1. Search Genesis keys (recent errors) → find what broke
  2. Probe agent (testing) → find broken endpoints / models
  3. AST + deterministic bridge (parsing, syntax, imports, tests, DB health) → find bugs
  4. Deterministic coding agent (auto-fix) → fix what can be fixed without LLM
  5. Hand off to LLM only when we can't finish: reasoning, validation, generation

Used by the 9-phase coding pipeline: Phase 0 (this loop) then Layers 1–8.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def search_genesis_errors(limit: int = 50) -> List[Dict[str, Any]]:
    """Search Genesis keys for recent errors — deterministic, no LLM."""
    try:
        from core.genesis_storage import get_genesis_storage
        keys = get_genesis_storage().get_hot(limit)
        return [k for k in keys if k.get("is_error")]
    except Exception as e:
        logger.debug(f"Genesis error search failed: {e}")
        return []


def run_probe_sync() -> Dict[str, Any]:
    """Run probe agent (sweep endpoints + models) — deterministic testing."""
    async def _run():
        from api.probe_agent_api import probe_sweep, probe_models
        api_sweep = await probe_sweep()
        model_sweep = await probe_models()
        broken = api_sweep.get("broken_endpoints", [])
        broken_models = [m for m in model_sweep.get("models", []) if m.get("status") == "broken"]
        return {
            "api_sweep": api_sweep,
            "model_sweep": model_sweep,
            "broken_endpoints": broken,
            "broken_models": broken_models,
            "total_broken": len(broken) + len(broken_models),
        }
    try:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop is not None and loop.is_running():
            return {"error": "use run_probe_async from async context", "broken_endpoints": [], "broken_models": [], "total_broken": 0}
        return asyncio.run(_run())
    except Exception as e:
        logger.debug(f"Probe run failed: {e}")
        return {"error": str(e), "broken_endpoints": [], "broken_models": [], "total_broken": 0}


async def run_probe_async() -> Dict[str, Any]:
    """Async: run probe agent (sweep + models)."""
    try:
        from api.probe_agent_api import probe_sweep, probe_models
        api_sweep = await probe_sweep()
        model_sweep = await probe_models()
        broken = api_sweep.get("broken_endpoints", [])
        broken_models = [m for m in model_sweep.get("models", []) if m.get("status") == "broken"]
        return {
            "api_sweep": api_sweep,
            "model_sweep": model_sweep,
            "broken_endpoints": broken,
            "broken_models": broken_models,
            "total_broken": len(broken) + len(broken_models),
        }
    except Exception as e:
        logger.debug(f"Probe run failed: {e}")
        return {"error": str(e), "broken_endpoints": [], "broken_models": [], "total_broken": 0}


def run_deterministic_scan_and_fix(task: Optional[str] = None) -> Dict[str, Any]:
    """AST + deterministic bridge: scan then auto-fix. No LLM until handoff."""
    try:
        from core.deterministic_bridge import build_deterministic_report, DeterministicAutoFixer
        report = build_deterministic_report()
        problems = report.get("problems", [])
        fixer = DeterministicAutoFixer()
        auto_fixes = fixer.auto_fix(problems) if problems else []
        n_fixed = len(auto_fixes)
        remaining = problems[n_fixed:] if n_fixed < len(problems) else []
        return {
            "total_checks": report.get("total_checks", 0),
            "total_problems": len(problems),
            "auto_fixed": len(auto_fixes),
            "auto_fixes": auto_fixes,
            "remaining_for_llm": remaining,
            "remaining_count": len(remaining),
            "ready_for_llm_handoff": len(remaining) > 0,
        }
    except Exception as e:
        logger.debug(f"Deterministic scan/fix failed: {e}")
        return {"error": str(e), "remaining_for_llm": [], "remaining_count": 0, "ready_for_llm_handoff": True}


def run_deterministic_first_loop(
    task: Optional[str] = None,
    run_probe: bool = True,
    run_genesis_search: bool = True,
    run_deterministic_scan: bool = True,
) -> Dict[str, Any]:
    """
    Full deterministic-first loop:
      Genesis keys (errors) → Probe agent (testing) → Deterministic bridge (AST, fix) →
      hand off to LLM only when can't finish.

    Returns a single result with:
      - genesis_errors: recent error keys
      - probe_result: broken endpoints/models
      - deterministic_result: scan + auto-fix result, remaining_for_llm
      - handoff_to_llm: True if reasoning/validation/generation needed
    """
    result = {
        "started_at": datetime.utcnow().isoformat(),
        "genesis_errors": [],
        "probe_result": None,
        "deterministic_result": None,
        "handoff_to_llm": False,
        "handoff_reason": [],
    }

    if run_genesis_search:
        result["genesis_errors"] = search_genesis_errors(50)

    if run_probe:
        result["probe_result"] = run_probe_sync()
        total_broken = result["probe_result"].get("total_broken", 0)
        if total_broken > 0:
            result["handoff_to_llm"] = True
            result["handoff_reason"].append("probe_failures")

    if run_deterministic_scan:
        result["deterministic_result"] = run_deterministic_scan_and_fix(task)
        det = result["deterministic_result"]
        if det.get("ready_for_llm_handoff") and det.get("remaining_count", 0) > 0:
            result["handoff_to_llm"] = True
            result["handoff_reason"].append("deterministic_remaining")

    if result["genesis_errors"] and "genesis_errors" not in result["handoff_reason"]:
        result["handoff_reason"].append("recent_errors")

    try:
        from api._genesis_tracker import track
        track(
            key_type="system_event",
            what="Deterministic-first loop completed",
            who="deterministic_first_loop",
            how="genesis_search+probe+deterministic_scan_fix",
            output_data={
                "genesis_errors_count": len(result["genesis_errors"]),
                "probe_broken": result["probe_result"].get("total_broken", 0) if result["probe_result"] else 0,
                "remaining_for_llm": result["deterministic_result"].get("remaining_count", 0) if result["deterministic_result"] else 0,
                "handoff_to_llm": result["handoff_to_llm"],
            },
            tags=["deterministic_first_loop", "phase0", "probe", "ast", "genesis"],
        )
    except Exception:
        pass

    return result


def get_handoff_context(loop_result: Dict[str, Any]) -> Dict[str, Any]:
    """Build context for LLM handoff: what reasoning/validation/generation is needed."""
    ctx = {"reasoning": [], "validation": [], "generation": []}
    if not loop_result.get("handoff_to_llm"):
        return ctx
    reasons = loop_result.get("handoff_reason", [])
    if "probe_failures" in reasons:
        ctx["validation"].append("Re-validate endpoints and models after probe found failures.")
    if "deterministic_remaining" in reasons:
        det = loop_result.get("deterministic_result") or {}
        remaining = det.get("remaining_for_llm", [])
        ctx["reasoning"].append(f"Determine fix for {len(remaining)} remaining deterministic problems.")
        ctx["generation"].append("Generate code or config fixes for problems that auto-fix could not resolve.")
    if "recent_errors" in reasons:
        ctx["reasoning"].append("Review recent Genesis errors for recurring failure patterns.")
    return ctx
