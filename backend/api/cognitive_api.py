from fastapi import APIRouter
from typing import Dict, Any
from api.tab_schemas import CognitiveStatsResponse, CognitiveDecisionsResponse

router = APIRouter(prefix="/cognitive", tags=["Cognitive"])

@router.get("/stats/summary", response_model=CognitiveStatsResponse)
async def get_cognitive_stats_summary():
    return {"status": "ok", "stats": {}}

@router.get("/decisions/recent", response_model=CognitiveDecisionsResponse)
async def get_recent_decisions():
    return {"decisions": []}
