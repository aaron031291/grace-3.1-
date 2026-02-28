"""v1/files — Folders, librarian, file CRUD"""
from fastapi import APIRouter, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/v1/files", tags=["v1 Files"])

BASE = "http://localhost:8000"


class DirCreate(BaseModel):
    path: str

class FileWrite(BaseModel):
    path: str
    content: str

class FileRename(BaseModel):
    old_path: str
    new_path: str

class FileMove(BaseModel):
    source_path: str
    destination_dir: str


@router.get("/tree")
async def file_tree(max_depth: int = 50):
    import requests as req
    return req.get(f"{BASE}/api/librarian-fs/tree?max_depth={max_depth}", timeout=10).json()

@router.get("/browse")
async def browse(path: str = ""):
    import requests as req
    return req.get(f"{BASE}/api/librarian-fs/browse?path={path}", timeout=10).json()

@router.get("/content")
async def read_file(path: str):
    import requests as req
    return req.get(f"{BASE}/api/librarian-fs/file/content?path={path}", timeout=10).json()

@router.put("/content")
async def save_file(request: FileWrite):
    import requests as req
    return req.put(f"{BASE}/api/librarian-fs/file/content", json=request.model_dump(), timeout=10).json()

@router.post("")
async def create_file(request: FileWrite):
    import requests as req
    return req.post(f"{BASE}/api/librarian-fs/file/create", json=request.model_dump(), timeout=10).json()

@router.delete("")
async def delete_file(path: str):
    import requests as req
    return req.delete(f"{BASE}/api/librarian-fs/file?path={path}", timeout=10).json()

@router.post("/directory")
async def create_dir(request: DirCreate):
    import requests as req
    return req.post(f"{BASE}/api/librarian-fs/directory", json=request.model_dump(), timeout=10).json()

@router.delete("/directory")
async def delete_dir(path: str, force: bool = True):
    import requests as req
    return req.delete(f"{BASE}/api/librarian-fs/directory?path={path}&force={force}", timeout=10).json()

@router.post("/upload")
async def upload(file: UploadFile = File(...), directory: str = Form("")):
    import requests as req
    r = req.post(f"{BASE}/api/librarian-fs/file/upload",
                 files={"file": (file.filename, file.file, file.content_type)},
                 data={"directory": directory}, timeout=30)
    return r.json()

@router.post("/rename")
async def rename(request: FileRename):
    import requests as req
    return req.post(f"{BASE}/api/librarian-fs/file/rename", json=request.model_dump(), timeout=10).json()

@router.post("/move")
async def move(request: FileMove):
    import requests as req
    return req.post(f"{BASE}/api/librarian-fs/file/move", json=request.model_dump(), timeout=10).json()

@router.post("/analyze")
async def analyze(file_path: str, use_kimi: bool = False):
    import requests as req
    return req.post(f"{BASE}/api/librarian-fs/analyze", json={"file_path": file_path, "use_kimi": use_kimi}, timeout=30).json()

@router.get("/stats")
async def stats():
    import requests as req
    return req.get(f"{BASE}/api/librarian-fs/stats", timeout=10).json()


# ── Chunked upload proxies ────────────────────────────────────────────

@router.post("/upload/initiate")
async def chunked_initiate(request: dict):
    import requests as req
    return req.post(f"{BASE}/api/upload/initiate", json=request, timeout=10).json()

@router.post("/upload/chunk")
async def chunked_chunk(
    upload_id: str = Form(...),
    chunk_index: int = Form(...),
    chunk_hash: Optional[str] = Form(None),
    chunk: UploadFile = File(...),
):
    import requests as req
    r = req.post(
        f"{BASE}/api/upload/chunk",
        files={"chunk": (chunk.filename, chunk.file, chunk.content_type)},
        data={"upload_id": upload_id, "chunk_index": str(chunk_index), "chunk_hash": chunk_hash or ""},
        timeout=60,
    )
    return r.json()

@router.get("/upload/status")
async def chunked_status(upload_id: str):
    import requests as req
    return req.get(f"{BASE}/api/upload/status?upload_id={upload_id}", timeout=10).json()

@router.post("/upload/complete")
async def chunked_complete(request: dict):
    import requests as req
    return req.post(f"{BASE}/api/upload/complete", json=request, timeout=120).json()

@router.delete("/upload/cancel")
async def chunked_cancel(upload_id: str):
    import requests as req
    return req.delete(f"{BASE}/api/upload/cancel?upload_id={upload_id}", timeout=10).json()

@router.get("/upload/active")
async def chunked_active():
    import requests as req
    return req.get(f"{BASE}/api/upload/active", timeout=10).json()
