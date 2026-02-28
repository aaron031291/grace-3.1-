"""v1/sources — Whitelist API + web sources"""
from fastapi import APIRouter, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, List, Dict

router = APIRouter(prefix="/api/v1/sources", tags=["v1 Sources"])
BASE = "http://localhost:8000"


class APISource(BaseModel):
    name: str
    url: str
    api_key: Optional[str] = None
    description: str = ""

class WebSource(BaseModel):
    name: str
    url: str
    source_type: str = "website"
    description: str = ""

class RunSource(BaseModel):
    query: Optional[str] = None
    use_kimi: bool = True


@router.get("/api")
async def list_api_sources():
    import requests as req
    return req.get(f"{BASE}/api/whitelist-hub/api-sources", timeout=10).json()

@router.post("/api")
async def add_api_source(request: APISource):
    import requests as req
    return req.post(f"{BASE}/api/whitelist-hub/api-sources", json=request.model_dump(), timeout=10).json()

@router.delete("/api/{source_id}")
async def delete_api_source(source_id: str):
    import requests as req
    return req.delete(f"{BASE}/api/whitelist-hub/api-sources/{source_id}", timeout=10).json()

@router.post("/api/{source_id}/run")
async def run_api_source(source_id: str, request: RunSource):
    import requests as req
    return req.post(f"{BASE}/api/whitelist-hub/api-sources/{source_id}/run", json={"source_id": source_id, **request.model_dump()}, timeout=30).json()

@router.get("/web")
async def list_web_sources():
    import requests as req
    return req.get(f"{BASE}/api/whitelist-hub/web-sources", timeout=10).json()

@router.post("/web")
async def add_web_source(request: WebSource):
    import requests as req
    return req.post(f"{BASE}/api/whitelist-hub/web-sources", json=request.model_dump(), timeout=10).json()

@router.delete("/web/{source_id}")
async def delete_web_source(source_id: str):
    import requests as req
    return req.delete(f"{BASE}/api/whitelist-hub/web-sources/{source_id}", timeout=10).json()

@router.post("/web/{source_id}/run")
async def run_web_source(source_id: str, request: RunSource):
    import requests as req
    return req.post(f"{BASE}/api/whitelist-hub/web-sources/{source_id}/run", json={"source_id": source_id, **request.model_dump()}, timeout=30).json()

@router.post("/{source_id}/upload")
async def upload_doc(source_id: str, file: UploadFile = File(...)):
    import requests as req
    r = req.post(f"{BASE}/api/whitelist-hub/sources/{source_id}/upload",
                 files={"file": (file.filename, file.file, file.content_type)}, timeout=30)
    return r.json()

@router.get("/{source_id}/documents")
async def source_docs(source_id: str):
    import requests as req
    return req.get(f"{BASE}/api/whitelist-hub/sources/{source_id}/documents", timeout=10).json()

@router.get("/stats")
async def stats():
    import requests as req
    return req.get(f"{BASE}/api/whitelist-hub/stats", timeout=10).json()
