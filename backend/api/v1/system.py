"""v1/system — Health, BI, APIs, manifest"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any

router = APIRouter(prefix="/api/v1/system", tags=["v1 System"])
BASE = "http://localhost:8000"


class ExplorerCall(BaseModel):
    method: str
    path: str
    body: Optional[Dict[str, Any]] = None

class DiagnoseRequest(BaseModel):
    api_path: str
    error_info: Optional[str] = None


@router.get("/health")
async def health():
    import requests as req
    return req.get(f"{BASE}/api/system-health/dashboard", timeout=10).json()

@router.get("/health/processes")
async def processes():
    import requests as req
    return req.get(f"{BASE}/api/system-health/processes", timeout=10).json()

@router.get("/bi")
async def bi_dashboard():
    import requests as req
    return req.get(f"{BASE}/api/bi/dashboard", timeout=10).json()

@router.get("/bi/trends")
async def bi_trends():
    import requests as req
    return req.get(f"{BASE}/api/bi/trends", timeout=10).json()

@router.get("/apis")
async def api_catalogue():
    import requests as req
    return req.get(f"{BASE}/api/registry/all", timeout=10).json()

@router.get("/apis/health")
async def api_health():
    import requests as req
    return req.get(f"{BASE}/api/registry/health-check", timeout=15).json()

@router.post("/apis/diagnose")
async def diagnose(request: DiagnoseRequest):
    import requests as req
    return req.post(f"{BASE}/api/registry/diagnose", json=request.model_dump(), timeout=60).json()

@router.post("/apis/call")
async def explorer_call(request: ExplorerCall):
    import requests as req
    return req.post(f"{BASE}/api/explorer/call", json=request.model_dump(), timeout=30).json()

@router.get("/apis/routes")
async def all_routes():
    import requests as req
    return req.get(f"{BASE}/api/explorer/routes", timeout=10).json()

@router.get("/manifest")
async def manifest():
    import requests as req
    return req.get(f"{BASE}/api/manifest/full", timeout=10).json()

@router.get("/manifest/summary")
async def manifest_summary():
    import requests as req
    return req.get(f"{BASE}/api/manifest/summary", timeout=10).json()

@router.get("/learn-heal")
async def learn_heal():
    import requests as req
    return req.get(f"{BASE}/api/learn-heal/dashboard", timeout=10).json()

@router.post("/learn")
async def learn(topic: str, method: str = "kimi"):
    import requests as req
    return req.post(f"{BASE}/api/learn-heal/learn", json={"topic": topic, "method": method}, timeout=60).json()

@router.post("/heal")
async def heal(action: str):
    import requests as req
    return req.post(f"{BASE}/api/learn-heal/heal", json={"action": action}, timeout=10).json()

@router.get("/skills")
async def skills():
    import requests as req
    return req.get(f"{BASE}/api/learn-heal/skills", timeout=10).json()
