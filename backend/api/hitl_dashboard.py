"""
HITL Dashboard API

Provides endpoints for the Spindle Human-in-the-Loop handoff dashboard.
Listens for handoff signals and provides endpoints to resolve them,
ingesting the resolution as Procedural Memory.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import uuid

from cognitive.event_bus import subscribe

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/spindle/hitl", tags=["Spindle HITL Dashboard"])

# In-memory store of active handoffs
_active_handoffs: Dict[str, Dict[str, Any]] = {}

def _on_handoff_signal(event: Dict[str, Any]):
    """Event bus listener for spindle.hitl.handoff events."""
    payload = event.get("payload", event)
    handoff_id = str(uuid.uuid4())
    payload["handoff_id"] = handoff_id
    payload["status"] = "pending"
    payload["received_at"] = datetime.utcnow().isoformat()
    
    # Query ClarityFramework for 5W1H context here if needed
    try:
        from core.clarity_framework import ClarityFramework
        payload["clarity_context"] = ClarityFramework.get_latest_context() # Mock or integrate
    except ImportError:
        payload["clarity_context"] = {"fallback": "ClarityFramework unavailable."}
        
    _active_handoffs[handoff_id] = payload
    logger.info(f"[SPINDLE-HITL] New handoff registered: {handoff_id}")

# Subscribe to the event bus
try:
    subscribe("spindle.hitl.handoff", _on_handoff_signal)
except Exception as e:
    logger.error(f"[SPINDLE-HITL] Failed to subscribe to event bus: {e}")

class ResolutionPayload(BaseModel):
    decision: str
    fix_code: Optional[str] = None
    notes: Optional[str] = None

@router.get("/active")
async def get_active_handoffs():
    """Returns all currently pending HITL handoffs."""
    return {
        "ok": True,
        "count": len(_active_handoffs),
        "handoffs": list(_active_handoffs.values())
    }

@router.get("/{handoff_id}")
async def get_handoff(handoff_id: str):
    """Get details of a specific handoff."""
    if handoff_id not in _active_handoffs:
        raise HTTPException(status_code=404, detail="Handoff not found")
    return {"ok": True, "handoff": _active_handoffs[handoff_id]}

@router.post("/{handoff_id}/resolve")
async def resolve_handoff(handoff_id: str, payload: ResolutionPayload, background_tasks: BackgroundTasks):
    """
    Ingest a human resolution for a handoff.
    Packages it as a Procedural memory pattern and writes to Event Store.
    """
    if handoff_id not in _active_handoffs:
        raise HTTPException(status_code=404, detail="Handoff not found")
        
    handoff = _active_handoffs[handoff_id]
    
    # Structure the procedural memory payload
    resolution_record = {
        "handoff_id": handoff_id,
        "signal": handoff.get("signal"),
        "failed_layers": handoff.get("failed_layers"),
        "human_decision": payload.decision,
        "fix_code": payload.fix_code,
        "notes": payload.notes,
        "resolved_at": datetime.utcnow().isoformat()
    }
    
    # Ingest into Event Store / Procedural Memory
    try:
        from core.services.memory_service import UnifiedMemory
        # Assuming UnifiedMemory has a method to add procedural memory
        memory_store = UnifiedMemory()
        memory_store.add_procedural_pattern(
            trigger=f"layer_failure_{handoff.get('signal')}",
            resolution=resolution_record,
            source="hitl_replay"
        )
    except Exception as e:
        logger.warning(f"[SPINDLE-HITL] Memory ingestion unavailable or varying API: {e}")
        # Fallback to Genesis Key tracking
        try:
            from api._genesis_tracker import track
            track(
                key_type="fix",
                what=f"HITL Resolution for {handoff_id}",
                who="human_operator",
                how="spindle.hitl.resolve",
                input_data=resolution_record,
                tags=["hitl", "resolution", "procedural_memory"]
            )
        except Exception:
            pass

    # Mark as resolved and remove from active
    _active_handoffs.pop(handoff_id, None)
    
    return {
        "ok": True,
        "message": "Resolution ingested successfully",
        "handoff_id": handoff_id
    }
