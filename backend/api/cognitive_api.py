from fastapi import APIRouter
from typing import Dict, Any

router = APIRouter(prefix="/cognitive", tags=["Cognitive"])

@router.get("/stats/summary")
async def get_cognitive_stats_summary():
    return {"status": "ok", "stats": {}}

@router.get("/decisions/recent")
async def get_recent_decisions():
    return {"decisions": []}
