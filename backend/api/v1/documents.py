"""v1/documents — Docs library, ingestion, retrieval, intelligence"""
from fastapi import APIRouter, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/v1/documents", tags=["v1 Documents"])
BASE = "http://localhost:8000"


class SearchQuery(BaseModel):
    query: str
    limit: int = 10
    threshold: float = 0.3


@router.get("")
async def list_docs(search: str = "", sort: str = "newest", limit: int = 200):
    import requests as req
    params = f"?sort={sort}&limit={limit}"
    if search: params += f"&search={search}"
    return req.get(f"{BASE}/api/docs/all{params}", timeout=10).json()

@router.get("/by-folder")
async def by_folder():
    import requests as req
    return req.get(f"{BASE}/api/docs/by-folder", timeout=10).json()

@router.get("/{doc_id}")
async def get_doc(doc_id: int):
    import requests as req
    return req.get(f"{BASE}/api/docs/document/{doc_id}", timeout=10).json()

@router.delete("/{doc_id}")
async def delete_doc(doc_id: int):
    import requests as req
    return req.delete(f"{BASE}/api/docs/document/{doc_id}", timeout=10).json()

@router.post("/upload")
async def upload(file: UploadFile = File(...), folder: str = Form(""), description: str = Form("")):
    import requests as req
    r = req.post(f"{BASE}/api/docs/upload",
                 files={"file": (file.filename, file.file, file.content_type)},
                 data={"folder": folder, "description": description}, timeout=30)
    return r.json()

@router.post("/search")
async def search(request: SearchQuery):
    import requests as req
    return req.post(f"{BASE}/retrieve/search", json=request.model_dump(), timeout=15).json()

@router.get("/{doc_id}/tags")
async def doc_tags(doc_id: int):
    import requests as req
    return req.get(f"{BASE}/api/intelligence/document/{doc_id}/tags", timeout=10).json()

@router.get("/{doc_id}/related")
async def doc_related(doc_id: int):
    import requests as req
    return req.get(f"{BASE}/api/intelligence/document/{doc_id}/related", timeout=10).json()

@router.post("/{doc_id}/reprocess")
async def reprocess(doc_id: int):
    import requests as req
    return req.post(f"{BASE}/api/intelligence/document/{doc_id}/reprocess", timeout=10).json()

@router.get("/stats/summary")
async def doc_stats():
    import requests as req
    return req.get(f"{BASE}/api/docs/stats", timeout=10).json()

@router.get("/tags/all")
async def all_tags():
    import requests as req
    return req.get(f"{BASE}/api/intelligence/tags", timeout=10).json()
