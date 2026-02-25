"""v1/projects — Codebase, coding agent, project management"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/v1/projects", tags=["v1 Projects"])
BASE = "http://localhost:8000"


class ProjectCreate(BaseModel):
    name: str
    domain_folder: str
    project_type: str = "general"
    description: str = ""

class FileWrite(BaseModel):
    path: str
    content: str


@router.get("")
async def list_projects():
    import requests as req
    return req.get(f"{BASE}/api/codebase-hub/projects", timeout=10).json()

@router.post("")
async def create_project(request: ProjectCreate):
    import requests as req
    return req.post(f"{BASE}/api/codebase-hub/projects", json=request.model_dump(), timeout=10).json()

@router.delete("/{project_id}")
async def delete_project(project_id: str):
    import requests as req
    return req.delete(f"{BASE}/api/codebase-hub/projects/{project_id}", timeout=10).json()

@router.get("/tree/{folder:path}")
async def project_tree(folder: str):
    import requests as req
    return req.get(f"{BASE}/api/codebase-hub/tree/{folder}", timeout=10).json()

@router.get("/file")
async def read_file(path: str):
    import requests as req
    return req.get(f"{BASE}/api/codebase-hub/file?path={path}", timeout=10).json()

@router.put("/file")
async def write_file(request: FileWrite):
    import requests as req
    return req.put(f"{BASE}/api/codebase-hub/file", json=request.model_dump(), timeout=10).json()

@router.post("/file")
async def create_file(request: FileWrite):
    import requests as req
    return req.post(f"{BASE}/api/codebase-hub/file/create", json=request.model_dump(), timeout=10).json()

@router.delete("/file")
async def delete_file(path: str):
    import requests as req
    return req.delete(f"{BASE}/api/codebase-hub/file?path={path}", timeout=10).json()
