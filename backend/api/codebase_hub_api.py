import os
import json
import uuid
import datetime
from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from pathlib import Path

router = APIRouter(prefix="/codebase-hub", tags=["Codebase Hub"])

# The workspace root is the parent of the backend directory
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
GENESIS_TRACKING_FILE = WORKSPACE_ROOT / "backend" / ".genesis_file_versions.json"
GENESIS_SNAPSHOTS_DIR = WORKSPACE_ROOT / "backend" / ".genesis_snapshots"
os.makedirs(GENESIS_SNAPSHOTS_DIR, exist_ok=True)

EXCLUDED_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".pytest_cache"}

class FileSaveRequest(BaseModel):
    path: str
    content: str

class FileCreateRequest(BaseModel):
    project_name: str
    type: str # 'file' or 'directory'
    name: str
    path: str

def get_next_version(versions: List[Dict]) -> str:
    """Calculate linear version v1.X -> v1.(X+1)"""
    if not versions:
        return "v1.0"
    latest_version = versions[-1].get("linear_version", "v1.0")
    try:
        if latest_version.startswith("v"):
            parts = latest_version[1:].split(".")
            v_minor = int(parts[1]) if len(parts) > 1 else 0
            return f"v1.{v_minor + 1}"
    except Exception:
        pass
    return f"v1.{len(versions)}"

def record_genesis_block(file_path: str, content: str, trigger: str = "Manual Edit"):
    """Creates an immutable linear version block linked to a Genesis Key"""
    if not GENESIS_TRACKING_FILE.exists():
        genesis_data = {"version": "1.0", "files": {}}
    else:
        try:
            with open(GENESIS_TRACKING_FILE, "r", encoding="utf-8") as f:
                genesis_data = json.load(f)
        except Exception:
            genesis_data = {"version": "1.0", "files": {}}
            
    abs_path = str(WORKSPACE_ROOT / file_path)
    file_id = f"FILE-{uuid.uuid4().hex[:12]}"
    
    # Check if file is already tracked
    target_fid = None
    for fid, record in genesis_data.get("files", {}).items():
        if record.get("absolute_path") == abs_path or record.get("file_path") == abs_path:
            target_fid = fid
            break
            
    if not target_fid:
        target_fid = file_id
        genesis_data["files"][target_fid] = {
            "file_genesis_key": target_fid,
            "absolute_path": abs_path,
            "file_path": abs_path,
            "versions": []
        }
        
    file_record = genesis_data["files"][target_fid]
    versions = file_record.get("versions", [])
    
    linear_ver = get_next_version(versions)
    genesis_key = f"GK-{uuid.uuid4().hex}"
    
    new_version = {
        "linear_version": linear_ver,
        "genesis_key": genesis_key,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "trigger": trigger,
        "file_size": len(content),
        "status": "active"
    }
    
    # Store snapshot file physically
    snapshot_path = GENESIS_SNAPSHOTS_DIR / f"{genesis_key}.txt"
    try:
        with open(snapshot_path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        print(f"Failed to write snapshot {genesis_key}: {e}")
        
    # Mark old versions as superseded
    for v in versions:
        v["status"] = "superseded"
        
    versions.append(new_version)
    file_record["versions"] = versions
    file_record["last_updated"] = new_version["timestamp"]
    
    with open(GENESIS_TRACKING_FILE, "w", encoding="utf-8") as f:
        json.dump(genesis_data, f, indent=2)

@router.get("/projects")
async def get_projects():
    """List root directories as projects"""
    projects = ["root"]
    try:
        for item in os.listdir(WORKSPACE_ROOT):
            item_path = WORKSPACE_ROOT / item
            if item_path.is_dir() and item not in EXCLUDED_DIRS:
                projects.append(item)
    except Exception as e:
        pass
    return projects

def build_tree(dir_path: Path, rel_base: Path):
    tree = []
    try:
        items = sorted(os.listdir(dir_path))
        for item in items:
            if item in EXCLUDED_DIRS:
                continue
            item_path = dir_path / item
            rel_path = item_path.relative_to(rel_base).as_posix()
            
            node = {
                "name": item,
                "path": rel_path,
                "type": "directory" if item_path.is_dir() else "file"
            }
            if item_path.is_dir():
                node["children"] = build_tree(item_path, rel_base)
            tree.append(node)
    except Exception:
        pass
    return tree

@router.get("/tree/{project_name}")
async def get_tree(project_name: str):
    """Get project file tree"""
    if project_name == "root":
        project_path = WORKSPACE_ROOT
    else:
        project_path = WORKSPACE_ROOT / project_name
        
    if not project_path.exists() or not project_path.is_dir():
        raise HTTPException(status_code=404, detail="Project not found")
        
    return {
        "name": project_name,
        "path": project_name if project_name != "root" else "",
        "type": "directory",
        "children": build_tree(project_path, WORKSPACE_ROOT)
    }

@router.get("/file")
async def get_file(path: str = Query(...)):
    """Read file content and return its Genesis lineage"""
    file_path = WORKSPACE_ROOT / path
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
        
    try:
        # Load content
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Get Lineage
        genesis_history = []
        if GENESIS_TRACKING_FILE.exists():
            with open(GENESIS_TRACKING_FILE, "r", encoding="utf-8") as f:
                tracker = json.load(f)
                abs_path = str(file_path.resolve())
                
                # Match by path
                abs_path_lower = abs_path.lower()
                for fid, record in tracker.get("files", {}).items():
                    if record.get("absolute_path", "").lower() == abs_path_lower or record.get("file_path", "").lower() == abs_path_lower:
                        # Convert to UI friendly format
                        for v in reversed(record.get("versions", [])):
                            genesis_history.append({
                                "version": v.get("linear_version"),
                                "genesis_key": v.get("genesis_key"),
                                "timestamp": v.get("timestamp"),
                                "author": v.get("trigger", "Manual Edit").split(" ")[0] if " " in v.get("trigger", "") else "User",
                                "message": v.get("trigger", "Manual Edit"),
                                "status": v.get("status")
                            })
                        break
                        
        return {"path": path, "content": content, "genesis_history": genesis_history}
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Cannot read binary files")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/file/version")
async def get_file_version(genesis_key: str = Query(...)):
    """Read a specific historical snapshot of a file by genesis key"""
    snapshot_path = GENESIS_SNAPSHOTS_DIR / f"{genesis_key}.txt"
    if not snapshot_path.exists():
        raise HTTPException(status_code=404, detail=f"Snapshot {genesis_key} not found")
        
    try:
        with open(snapshot_path, "r", encoding="utf-8") as f:
            return {"genesis_key": genesis_key, "content": f.read()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/file")
async def save_file(req: FileSaveRequest):
    """Save file content and hook into Genesis Linear Versioning"""
    file_path = WORKSPACE_ROOT / req.path
    if not file_path.parent.exists():
        raise HTTPException(status_code=400, detail="Directory does not exist")
        
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(req.content)
            
        # Hook into Genesis keys (Replacing Git)
        record_genesis_block(req.path, req.content, trigger=f"Manual edit of {req.path}")
            
        return {"success": True, "path": req.path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/file/create")
async def create_file(req: FileCreateRequest):
    """Create a new file or directory"""
    target_path = WORKSPACE_ROOT / req.path
    if target_path.exists():
        raise HTTPException(status_code=400, detail="Target already exists")
        
    try:
        if req.type == "directory":
            target_path.mkdir(parents=True, exist_ok=True)
        else:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with open(target_path, "w", encoding="utf-8") as f:
                f.write("")
            record_genesis_block(req.path, "", trigger=f"Created {req.path}")
                
        return {"success": True, "path": req.path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/file")
async def delete_file(path: str = Query(...)):
    """Delete a file or directory"""
    target_path = WORKSPACE_ROOT / path
    if not target_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
        
    try:
        import shutil
        if target_path.is_dir():
            shutil.rmtree(target_path)
        else:
            target_path.unlink()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class RenameRequest(BaseModel):
    old_path: str
    new_name: str

@router.post("/rename")
async def rename_file(req: RenameRequest):
    old_path = WORKSPACE_ROOT / req.old_path
    if not old_path.exists():
        raise HTTPException(status_code=404, detail="Path not found")
    new_path = old_path.parent / req.new_name
    if new_path.exists():
        raise HTTPException(status_code=400, detail="New name already exists")
    try:
        old_path.rename(new_path)
        return {"success": True, "new_path": new_path.relative_to(WORKSPACE_ROOT).as_posix()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class MoveRequest(BaseModel):
    source_path: str
    dest_path: str

@router.post("/move")
async def move_file(req: MoveRequest):
    src = WORKSPACE_ROOT / req.source_path
    dest = WORKSPACE_ROOT / req.dest_path
    if not src.exists():
        raise HTTPException(status_code=404, detail="Source not found")
    if not dest.is_dir():
        dest = dest.parent
    dest_file = dest / src.name
    if dest_file.exists():
        raise HTTPException(status_code=400, detail="Destination already exists")
    try:
        import shutil
        shutil.move(str(src), str(dest_file))
        return {"success": True, "new_path": dest_file.relative_to(WORKSPACE_ROOT).as_posix()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class AnalyzeRequest(BaseModel):
    path: str
    model: str = "kimi"

@router.post("/analyze")
async def analyze_file(req: AnalyzeRequest):
    target = WORKSPACE_ROOT / req.path
    if not target.exists():
        raise HTTPException(status_code=404, detail="Path not found")
    # Mock analysis
    import asyncio
    await asyncio.sleep(2)
    return {
        "success": True,
        "analysis": f"Analysis complete for {req.path} using {req.model}.\nFile seems well structured and contains {target.stat().st_size} bytes."
    }

from fastapi import UploadFile, File

@router.post("/upload")
async def upload_file(directory: str = Query(""), file: UploadFile = File(...)):
    target_dir = WORKSPACE_ROOT / directory
    if not target_dir.exists():
        target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / file.filename
    try:
        content = await file.read()
        with open(target_file, "wb") as f:
            f.write(content)
        return {"success": True, "path": target_file.relative_to(WORKSPACE_ROOT).as_posix()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

