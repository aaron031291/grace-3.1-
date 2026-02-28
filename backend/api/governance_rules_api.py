"""
Governance Rules & Persona API

Law documents become immutable rules that Grace and Kimi must follow:
- Upload industry standards (GDPR, ISO, anti-bribery, code parameters)
- Documents become law — editable, saveable, versioned
- Grace reasons with Kimi about document meaning
- Persona context windows control how Grace interacts

Two persona boxes:
1. Personal — how Grace interacts with YOU (tone, style, preferences)
2. Professional — how Grace shows up externally (emails, documents, meetings)
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path
import json
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/governance-rules", tags=["Governance Rules & Persona"])

RULES_DIR = Path(__file__).parent.parent / "data" / "governance_rules"
PERSONA_FILE = Path(__file__).parent.parent / "data" / "persona_config.json"


def _ensure_dirs():
    RULES_DIR.mkdir(parents=True, exist_ok=True)
    PERSONA_FILE.parent.mkdir(parents=True, exist_ok=True)


class PersonaUpdate(BaseModel):
    personal: Optional[str] = None
    professional: Optional[str] = None


class RuleDocSave(BaseModel):
    content: str


class RuleReasonRequest(BaseModel):
    document_id: str
    question: str
    use_kimi: bool = True


# ---------------------------------------------------------------------------
# Persona context windows
# ---------------------------------------------------------------------------

def _load_persona() -> Dict[str, str]:
    _ensure_dirs()
    if PERSONA_FILE.exists():
        try:
            return json.loads(PERSONA_FILE.read_text())
        except Exception:
            pass
    return {
        "personal": "",
        "professional": "",
    }


def _save_persona(data: Dict[str, str]):
    _ensure_dirs()
    PERSONA_FILE.write_text(json.dumps(data, indent=2))


@router.get("/persona")
async def get_persona():
    """Get the current persona configuration (personal + professional context)."""
    return _load_persona()


@router.put("/persona")
async def update_persona(request: PersonaUpdate):
    """Update persona context windows."""
    current = _load_persona()
    if request.personal is not None:
        current["personal"] = request.personal
    if request.professional is not None:
        current["professional"] = request.professional
    current["updated_at"] = datetime.utcnow().isoformat()
    _save_persona(current)

    from api._genesis_tracker import track
    track(key_type="system", what="Persona configuration updated",
          how="PUT /api/governance-rules/persona", tags=["persona", "governance"])

    return {"saved": True, **current}


def get_active_persona() -> Dict[str, str]:
    """Called by other systems to get the active persona for prompt injection."""
    return _load_persona()


# ---------------------------------------------------------------------------
# Rule documents — law uploads
# ---------------------------------------------------------------------------

def _list_rule_files() -> List[Dict[str, Any]]:
    _ensure_dirs()
    docs = []
    for category in sorted(RULES_DIR.iterdir()):
        if category.is_dir():
            for f in sorted(category.iterdir()):
                if f.is_file() and not f.name.startswith('.'):
                    stat = f.stat()
                    meta_path = f.with_suffix(f.suffix + '.meta.json')
                    meta = {}
                    if meta_path.exists():
                        try:
                            meta = json.loads(meta_path.read_text())
                        except Exception:
                            pass
                    docs.append({
                        "id": f"{category.name}/{f.name}",
                        "filename": f.name,
                        "category": category.name,
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "description": meta.get("description", ""),
                        "enforced": meta.get("enforced", True),
                        "tags": meta.get("tags", []),
                    })
    # also files in root
    for f in sorted(RULES_DIR.iterdir()):
        if f.is_file() and not f.name.startswith('.') and not f.name.endswith('.meta.json'):
            stat = f.stat()
            docs.append({
                "id": f.name,
                "filename": f.name,
                "category": "general",
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "description": "",
                "enforced": True,
                "tags": [],
            })
    return docs


@router.get("/documents")
async def list_rule_documents():
    """List all uploaded governance rule documents."""
    docs = _list_rule_files()
    categories = {}
    for d in docs:
        cat = d["category"]
        if cat not in categories:
            categories[cat] = {"name": cat, "count": 0, "documents": []}
        categories[cat]["count"] += 1
        categories[cat]["documents"].append(d)

    return {
        "total": len(docs),
        "categories": list(categories.values()),
        "documents": docs,
    }


@router.post("/documents/upload")
async def upload_rule_document(
    file: UploadFile = File(...),
    category: str = Form("general"),
    description: str = Form(""),
    tags: str = Form(""),
):
    """
    Upload a governance rule document. It becomes law.
    Categories: gdpr, iso, anti_bribery, code_standards, user_rules, general
    """
    _ensure_dirs()
    cat_dir = RULES_DIR / category.strip().lower().replace(" ", "_")
    cat_dir.mkdir(parents=True, exist_ok=True)

    file_path = cat_dir / file.filename
    try:
        content = await file.read()
        file_path.write_bytes(content)

        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
        meta = {
            "description": description,
            "enforced": True,
            "tags": tag_list,
            "uploaded_at": datetime.utcnow().isoformat(),
            "category": category,
        }
        meta_path = file_path.with_suffix(file_path.suffix + '.meta.json')
        meta_path.write_text(json.dumps(meta, indent=2))

        from api._genesis_tracker import track
        track(key_type="upload", what=f"Governance rule uploaded: {file.filename} [{category}]",
              where=str(file_path), how="POST /api/governance-rules/documents/upload",
              file_path=str(file_path), tags=["governance", "rule", category])

        return {
            "uploaded": True,
            "id": f"{category}/{file.filename}",
            "filename": file.filename,
            "category": category,
            "size": len(content),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/{doc_id:path}/content")
async def get_rule_document_content(doc_id: str):
    """Read a rule document's content for editing."""
    _ensure_dirs()
    file_path = RULES_DIR / doc_id
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        content = file_path.read_text(errors="ignore")
    except Exception:
        content = file_path.read_bytes().decode("utf-8", errors="replace")

    meta_path = file_path.with_suffix(file_path.suffix + '.meta.json')
    meta = {}
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text())
        except Exception:
            pass

    return {
        "id": doc_id,
        "filename": file_path.name,
        "content": content,
        "size": file_path.stat().st_size,
        "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
        "meta": meta,
    }


@router.put("/documents/{doc_id:path}/content")
async def save_rule_document(doc_id: str, request: RuleDocSave):
    """Save (edit) a rule document in place."""
    _ensure_dirs()
    file_path = RULES_DIR / doc_id
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        file_path.write_text(request.content, encoding="utf-8")

        from api._genesis_tracker import track
        track(key_type="file_op", what=f"Governance rule edited: {doc_id}",
              where=str(file_path), how="PUT /api/governance-rules/documents/content",
              file_path=str(file_path), tags=["governance", "rule", "edit"])

        stat = file_path.stat()
        return {
            "saved": True,
            "id": doc_id,
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{doc_id:path}")
async def delete_rule_document(doc_id: str):
    """Delete a governance rule document."""
    file_path = RULES_DIR / doc_id
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Document not found")
    file_path.unlink()
    meta_path = file_path.with_suffix(file_path.suffix + '.meta.json')
    if meta_path.exists():
        meta_path.unlink()

    from api._genesis_tracker import track
    track(key_type="file_op", what=f"Governance rule deleted: {doc_id}",
          how="DELETE /api/governance-rules/documents", tags=["governance", "rule", "delete"])

    return {"deleted": True, "id": doc_id}


# ---------------------------------------------------------------------------
# Reason with Kimi about a rule document
# ---------------------------------------------------------------------------

@router.post("/documents/reason")
async def reason_about_rule(request: RuleReasonRequest):
    """
    Grace reasons with Kimi about the meaning of a governance document.
    Interprets the rules and explains how they apply.
    """
    _ensure_dirs()
    file_path = RULES_DIR / request.document_id
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Document not found")

    content = file_path.read_text(errors="ignore")[:15000]

    system_prompt = (
        "You are Grace's governance intelligence. You have been given a governance rule "
        "document that is LAW — Grace must follow it. Analyse the document carefully and "
        "answer questions about its meaning, implications, and how Grace should comply. "
        "Be precise about specific rules, obligations, and prohibitions."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Governance document: {request.document_id}\n\n"
                                     f"---\n{content}\n---\n\n"
                                     f"Question: {request.question}"},
    ]

    try:
        if request.use_kimi:
            from llm_orchestrator.factory import get_kimi_client
            client = get_kimi_client()
            provider = "kimi"
        else:
            from llm_orchestrator.factory import get_llm_client
            client = get_llm_client()
            provider = "local"

        response = client.chat(messages=messages, temperature=0.3)

        from api._genesis_tracker import track
        track(key_type="ai_response", what=f"Governance reasoning: {request.question[:60]}",
              how="POST /api/governance-rules/documents/reason",
              input_data={"document": request.document_id, "question": request.question},
              tags=["governance", "reasoning", provider])

        return {"response": response, "document_id": request.document_id, "provider": provider}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Get all active rules as system prompt context
# ---------------------------------------------------------------------------

@router.get("/active-rules-context")
async def get_active_rules_context():
    """
    Returns all enforced rule documents concatenated as a system prompt context.
    Used by chat and world model to inject governance rules into LLM prompts.
    """
    docs = _list_rule_files()
    context_parts = []
    for d in docs:
        if not d.get("enforced", True):
            continue
        file_path = RULES_DIR / d["id"]
        if file_path.exists():
            try:
                text = file_path.read_text(errors="ignore")[:5000]
                context_parts.append(f"[RULE: {d['filename']} ({d['category']})]\n{text}")
            except Exception:
                pass

    persona = _load_persona()

    return {
        "rules_count": len(context_parts),
        "rules_context": "\n\n---\n\n".join(context_parts) if context_parts else "",
        "persona_personal": persona.get("personal", ""),
        "persona_professional": persona.get("professional", ""),
    }
