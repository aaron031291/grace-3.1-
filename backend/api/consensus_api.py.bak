from fastapi import APIRouter
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/consensus", tags=["Consensus"])


@router.get("/status")
async def get_consensus_status() -> Dict[str, Any]:
    """Return current consensus engine status."""
    return {
        "active": False,
        "participants": 0,
        "last_round": None,
    }
