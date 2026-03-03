"""
Project Operations — export, import, rollback, cross-project file ops.

Handles: export project as ZIP, import from ZIP, per-project rollback,
move/copy files between projects, cross-project search.
"""

import json
import shutil
import logging
import zipfile
import io
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
PROJECTS_DIR = DATA_DIR / "projects"


def export_project(project_id: str) -> dict:
    """Export a project as a ZIP file."""
    project_dir = PROJECTS_DIR / project_id
    if not project_dir.exists():
        return {"error": "Project not found"}

    export_dir = DATA_DIR / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    zip_name = f"{project_id}_{timestamp}.zip"
    zip_path = export_dir / zip_name

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in project_dir.rglob("*"):
            if f.is_file() and "__pycache__" not in str(f):
                zf.write(f, f.relative_to(project_dir))

    size_mb = round(zip_path.stat().st_size / 1048576, 2)

    try:
        from core.tracing import light_track
        light_track("system_event", f"Project exported: {project_id} ({size_mb}MB)",
                     "project_ops", ["export", project_id])
    except Exception:
        pass

    return {"exported": True, "file": zip_name, "size_mb": size_mb, "path": str(zip_path)}


def import_project(project_id: str, zip_path: str) -> dict:
    """Import a project from a ZIP file."""
    zp = Path(zip_path)
    if not zp.exists():
        return {"error": "ZIP file not found"}

    project_dir = PROJECTS_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zp, "r") as zf:
        zf.extractall(project_dir)

    file_count = sum(1 for _ in project_dir.rglob("*") if _.is_file())
    return {"imported": True, "project_id": project_id, "files": file_count}


def copy_file_between_projects(source_project: str, source_path: str,
                                dest_project: str, dest_path: str = None) -> dict:
    """Copy a file from one project to another."""
    src = PROJECTS_DIR / source_project / source_path
    if not src.exists():
        return {"error": f"Source not found: {source_project}/{source_path}"}

    dst_path = dest_path or source_path
    dst = PROJECTS_DIR / dest_project / dst_path
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(src), str(dst))

    try:
        from core.librarian import ingest_document
        content = dst.read_text(errors="ignore")
        ingest_document(str(dst.relative_to(PROJECTS_DIR)), content, dest_project, "cross_project_copy")
    except Exception:
        pass

    return {"copied": True, "from": f"{source_project}/{source_path}",
            "to": f"{dest_project}/{dst_path}"}


def move_file_between_projects(source_project: str, source_path: str,
                                dest_project: str, dest_path: str = None) -> dict:
    """Move a file from one project to another."""
    result = copy_file_between_projects(source_project, source_path, dest_project, dest_path)
    if result.get("copied"):
        src = PROJECTS_DIR / source_project / source_path
        src.unlink(missing_ok=True)
        result["moved"] = True
        del result["copied"]
    return result


def project_rollback(project_id: str) -> dict:
    """Rollback a project to its last snapshot (per-project, doesn't affect others)."""
    try:
        from core.safety import list_snapshots, rollback_to
        snapshots = list_snapshots()
        # Find snapshots for this project
        project_snaps = [s for s in snapshots if project_id in s.get("label", "")]
        if project_snaps:
            return rollback_to(project_snaps[-1]["id"])
        return {"error": "No snapshots found for this project"}
    except Exception as e:
        return {"error": str(e)}


def list_exports() -> list:
    """List all exported project ZIPs."""
    export_dir = DATA_DIR / "exports"
    if not export_dir.exists():
        return []
    return [
        {"file": f.name, "size_mb": round(f.stat().st_size / 1048576, 2),
         "created": datetime.fromtimestamp(f.stat().st_mtime).isoformat()}
        for f in sorted(export_dir.glob("*.zip"), reverse=True)
    ]
