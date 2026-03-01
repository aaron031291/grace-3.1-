"""
Feedback API — User says "worked" or "didn't work", feeds ALL systems.

Data flow:
  User verdict → ML Trainer + Ghost Memory + Playbook + Unified Memory
  If "didn't work" → consensus suggests next steps
"""

from fastapi import APIRouter, Form
from typing import Optional
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/feedback", tags=["Feedback Loop"])


@router.post("/code")
async def code_feedback(
    verdict: str = Form(...),  # worked, didnt_work
    task: str = Form(""),
    code_preview: str = Form(""),
    detail: str = Form(""),
    session_id: str = Form(""),
):
    """
    User feedback on generated code. Feeds ALL learning systems.
    """
    is_positive = verdict == "worked"
    result = {"verdict": verdict, "recorded": True, "fed_to": []}

    # 1. ML Trainer
    try:
        from cognitive.ml_trainer import get_ml_trainer
        get_ml_trainer().observe("blueprint_build", {
            "user_verdict": 1.0 if is_positive else 0.0,
            "code_length": len(code_preview),
        }, "success" if is_positive else "failure")
        result["fed_to"].append("ml_trainer")
    except Exception:
        pass

    # 2. Ghost Memory
    try:
        from cognitive.ghost_memory import get_ghost_memory
        ghost = get_ghost_memory()
        ghost.append("user_feedback", f"{'WORKED' if is_positive else 'DIDNT WORK'}: {detail}")
        if is_positive and ghost.is_task_done():
            ghost.complete_task(user_approved=True)
        result["fed_to"].append("ghost_memory")
    except Exception:
        pass

    # 3. Unified Memory
    try:
        from cognitive.unified_memory import get_unified_memory
        mem = get_unified_memory()
        if is_positive:
            mem.store_learning(
                input_ctx=f"User approved: {task[:200]}",
                expected=code_preview[:2000],
                trust=0.9,
                source="user_feedback_positive",
                example_type="user_approved_code",
            )
        else:
            mem.store_episode(
                problem=f"User rejected code: {task[:200]}",
                action=f"Code: {code_preview[:500]}",
                outcome=f"REJECTED: {detail}",
                trust=0.3,
                source="user_feedback_negative",
            )
        result["fed_to"].append("unified_memory")
    except Exception:
        pass

    # 4. Intelligence Layer
    try:
        from cognitive.intelligence_layer import get_intelligence_layer
        il = get_intelligence_layer()
        il.observe_loop("user_feedback", {
            "positive": 1.0 if is_positive else 0.0,
        }, "success" if is_positive else "failure")
        result["fed_to"].append("intelligence_layer")
    except Exception:
        pass

    # 5. Genesis Key
    try:
        from api._genesis_tracker import track
        track(
            key_type="system",
            what=f"User feedback: {verdict} — {task[:60]}",
            who="user",
            output_data={"verdict": verdict, "detail": detail[:200]},
            tags=["feedback", verdict, "user"],
        )
        result["fed_to"].append("genesis")
    except Exception:
        pass

    # 6. If didn't work — suggest next steps via consensus
    if not is_positive:
        try:
            from cognitive.consensus_engine import run_consensus
            suggestions = run_consensus(
                prompt=f"Code didn't work. Task: {task}\nDetail: {detail}\nCode: {code_preview[:500]}\n\nSuggest 3 next steps to fix it.",
                models=["kimi", "opus"],
                source="user",
            )
            result["next_steps"] = suggestions.final_output[:1000]
        except Exception:
            result["next_steps"] = "Consensus unavailable — try describing the issue in more detail."

    return result
