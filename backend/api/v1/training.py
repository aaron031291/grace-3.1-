"""v1/training — Oracle, learning memory, skills, audit"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/v1/training", tags=["v1 Training"])
BASE = "http://localhost:8000"


class AuditRequest(BaseModel):
    focus: Optional[str] = None
    use_kimi: bool = True

class FillGap(BaseModel):
    topic: str
    method: str = "kimi"


@router.get("/dashboard")
async def dashboard():
    import requests as req
    return req.get(f"{BASE}/api/oracle/dashboard", timeout=10).json()

@router.get("/data")
async def training_data(sort: str = "newest", limit: int = 100, example_type: str = ""):
    import requests as req
    params = f"?sort={sort}&limit={limit}"
    if example_type: params += f"&example_type={example_type}"
    return req.get(f"{BASE}/api/oracle/training-data{params}", timeout=10).json()

@router.get("/data/{example_id}")
async def training_example(example_id: int):
    import requests as req
    return req.get(f"{BASE}/api/oracle/training-data/{example_id}", timeout=10).json()

@router.get("/patterns")
async def patterns():
    import requests as req
    return req.get(f"{BASE}/api/oracle/patterns", timeout=10).json()

@router.get("/skills")
async def skills():
    import requests as req
    return req.get(f"{BASE}/api/oracle/procedures", timeout=10).json()

@router.get("/episodes")
async def episodes():
    import requests as req
    return req.get(f"{BASE}/api/oracle/episodes", timeout=10).json()

@router.get("/trust-distribution")
async def trust_dist():
    import requests as req
    return req.get(f"{BASE}/api/oracle/trust-distribution", timeout=10).json()

@router.post("/audit")
async def audit(request: AuditRequest):
    import requests as req
    return req.post(f"{BASE}/api/oracle/audit", json=request.model_dump(), timeout=60).json()

@router.post("/fill-gap")
async def fill_gap(request: FillGap):
    import requests as req
    return req.post(f"{BASE}/api/oracle/fill-gap", json=request.model_dump(), timeout=60).json()
