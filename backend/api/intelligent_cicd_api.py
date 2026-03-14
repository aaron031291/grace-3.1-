"""
Intelligent CICD API — webhook and decision endpoints for the Intelligent CICD Orchestrator.

Allows external systems (GitHub, GitLab, etc.) to push webhook events and trigger
ML-assisted pipeline decisions (test selection, failure prediction, closed-loop feedback).
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cicd/intelligent", tags=["Intelligent CICD"])


class WebhookRequest(BaseModel):
    """Webhook payload and source."""
    payload: Dict[str, Any] = Field(..., description="Webhook JSON payload (e.g. GitHub push/PR)")
    source: str = Field(default="webhook", description="Source identifier: github, gitlab, jenkins, etc.")


class DecisionRequest(BaseModel):
    """Request a pipeline decision from the orchestrator."""
    trigger_source: str = Field(
        ...,
        description="One of: git_push, git_pull_request, webhook, scheduled, anomaly_detected, health_degradation, user_request"
    )
    context: Dict[str, Any] = Field(default_factory=dict, description="Optional context: changed_files, max_tests, time_budget, etc.")


@router.post("/webhook")
async def post_webhook(request: WebhookRequest) -> Dict[str, Any]:
    """Accept a webhook event (e.g. from GitHub/GitLab) and process it."""
    try:
        from genesis.intelligent_cicd_orchestrator import get_intelligent_cicd_orchestrator, TriggerSource

        orch = get_intelligent_cicd_orchestrator()
        event = orch.webhook_processor.parse_webhook_event(request.payload, source=request.source)
        result = await orch.webhook_processor.process_event(event)
        return {"ok": True, "event_id": event.id, "result": result}
    except Exception as e:
        logger.warning("[IntelligentCICD-API] Webhook processing failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/decision")
async def request_decision(req: DecisionRequest) -> Dict[str, Any]:
    """Request an intelligent pipeline decision (test selection, sandbox, trigger)."""
    try:
        from genesis.intelligent_cicd_orchestrator import (
            get_intelligent_cicd_orchestrator,
            TriggerSource,
        )

        orch = get_intelligent_cicd_orchestrator()
        try:
            trigger = TriggerSource(req.trigger_source)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid trigger_source. Use one of: {[t.value for t in TriggerSource]}"
            )
        decision = await orch.make_pipeline_decision(trigger, req.context)
        return {
            "ok": True,
            "decision_id": decision.decision_id,
            "decision": decision.decision.value,
            "confidence": decision.confidence,
            "reasoning": decision.reasoning,
            "tests_selected": decision.tests_selected[:50],
            "genesis_key": decision.genesis_key,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("[IntelligentCICD-API] Decision failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_status() -> Dict[str, Any]:
    """Return orchestrator status and stats."""
    try:
        from genesis.intelligent_cicd_orchestrator import get_intelligent_cicd_orchestrator

        orch = get_intelligent_cicd_orchestrator()
        return {
            "intelligence_mode": orch.intelligence_mode.value,
            "auto_trigger_enabled": getattr(orch, "auto_trigger_enabled", True),
            "decisions_count": len(orch.decisions),
            "webhook_processed": orch.webhook_processor.processed_count,
        }
    except Exception as e:
        logger.warning("[IntelligentCICD-API] Status failed: %s", e)
        return {"error": str(e)}
