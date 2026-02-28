"""
Coding Agent Rules — Upload documents that enforce how the agent writes code.

Devs can upload:
- Coding standards (style guides, naming conventions)
- Architecture rules (design patterns, folder structure)
- Configuration schemas (API specs, database schemas)
- Compliance rules (security, accessibility)
- Custom instructions (any text the agent must follow)

These are injected into the coding agent's system prompt on every
generation, alongside governance rules. The agent MUST comply.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/agent/rules", tags=["Agent Rules"])

RULES_DIR = Path(__file__).parent.parent.parent / "data" / "agent_rules"


def _ensure():
    RULES_DIR.mkdir(parents=True, exist_ok=True)


class RuleSave(BaseModel):
    content: str


@router.get("")
async def list_rules():
    """List all coding agent rule documents."""
    _ensure()
    rules = []
    for f in sorted(RULES_DIR.rglob("*")):
        if f.is_file() and not f.name.startswith('.') and not f.name.endswith('.meta.json'):
            meta = _load_meta(f)
            rules.append({
                "id": str(f.relative_to(RULES_DIR)),
                "filename": f.name,
                "category": f.parent.name if f.parent != RULES_DIR else "general",
                "size": f.stat().st_size,
                "description": meta.get("description", ""),
                "enforced": meta.get("enforced", True),
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            })
    return {"total": len(rules), "rules": rules}


@router.post("/upload")
async def upload_rule(
    file: UploadFile = File(...),
    category: str = Form("general"),
    description: str = Form(""),
):
    """Upload a rule document for the coding agent to follow."""
    _ensure()
    cat_dir = RULES_DIR / category.strip().lower().replace(" ", "_")
    cat_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = cat_dir / file.filename
    content = await file.read()
    file_path.write_bytes(content)
    
    meta = {"description": description, "enforced": True, "category": category,
            "uploaded_at": datetime.utcnow().isoformat()}
    _save_meta(file_path, meta)

    from api._genesis_tracker import track
    track(key_type="upload", what=f"Agent rule uploaded: {file.filename} [{category}]",
          file_path=str(file_path), tags=["agent_rules", category])

    return {"uploaded": True, "filename": file.filename, "category": category, "size": len(content)}


@router.get("/{rule_id:path}/content")
async def get_rule_content(rule_id: str):
    """Read a rule document's content."""
    _ensure()
    fp = RULES_DIR / rule_id
    if not fp.exists():
        raise HTTPException(status_code=404, detail="Rule not found")
    return {
        "id": rule_id, "filename": fp.name,
        "content": fp.read_text(errors="ignore"),
        "size": fp.stat().st_size,
        "meta": _load_meta(fp),
    }


@router.put("/{rule_id:path}/content")
async def save_rule_content(rule_id: str, request: RuleSave):
    """Edit and save a rule document."""
    fp = RULES_DIR / rule_id
    if not fp.exists():
        raise HTTPException(status_code=404, detail="Rule not found")
    fp.write_text(request.content, encoding="utf-8")
    from api._genesis_tracker import track
    track(key_type="file_op", what=f"Agent rule edited: {rule_id}", tags=["agent_rules", "edit"])
    return {"saved": True, "size": fp.stat().st_size}


@router.delete("/{rule_id:path}")
async def delete_rule(rule_id: str):
    """Delete a rule document."""
    fp = RULES_DIR / rule_id
    if fp.exists():
        fp.unlink()
        meta_fp = fp.with_suffix(fp.suffix + '.meta.json')
        if meta_fp.exists():
            meta_fp.unlink()
    return {"deleted": True}


def get_agent_rules_context() -> str:
    """
    Called by the coding agent to get all enforced rules as a system prompt block.
    This is injected into every code generation call.
    """
    _ensure()
    parts = []
    for f in sorted(RULES_DIR.rglob("*")):
        if f.is_file() and not f.name.startswith('.') and not f.name.endswith('.meta.json'):
            meta = _load_meta(f)
            if not meta.get("enforced", True):
                continue
            try:
                text = f.read_text(errors="ignore")[:5000]
                category = f.parent.name if f.parent != RULES_DIR else "general"
                parts.append(f"[AGENT RULE: {f.name} ({category})]\n{text}")
            except Exception:
                pass
    if not parts:
        return ""
    return (
        "\n\nMANDATORY CODING AGENT RULES:\n"
        "You MUST follow these rules when writing code.\n\n"
        + "\n\n---\n\n".join(parts)
        + "\n\n---\n\n"
    )


def _load_meta(fp: Path) -> dict:
    meta_fp = fp.with_suffix(fp.suffix + '.meta.json')
    if meta_fp.exists():
        try:
            return json.loads(meta_fp.read_text())
        except Exception:
            pass
    return {}


def _save_meta(fp: Path, meta: dict):
    meta_fp = fp.with_suffix(fp.suffix + '.meta.json')
    meta_fp.write_text(json.dumps(meta, indent=2))
