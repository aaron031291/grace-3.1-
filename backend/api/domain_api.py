"""
Domain API — Per-folder context, chat, and governance rules.

Each folder is a domain environment with:
1. Its own chat (LLM has full context of that folder + system)
2. Its own governance rules (different rules per domain)
3. Full file context injected into every LLM call for that domain
"""

from fastapi import APIRouter, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/domain", tags=["Domain"])

DOMAIN_RULES_DIR = Path(__file__).parent.parent / "data" / "domain_rules"


class DomainChat(BaseModel):
    message: str
    folder_path: str
    provider: str = "auto"  # auto, ollama, kimi, opus


class DomainRuleSave(BaseModel):
    content: str


def _get_kb():
    from settings import settings
    return Path(settings.KNOWLEDGE_BASE_PATH)


def _get_folder_context(folder_path: str) -> str:
    """Read all files in a folder to build full context."""
    kb = _get_kb()
    folder = kb / folder_path
    if not folder.exists():
        return ""

    context_parts = []
    for f in sorted(folder.rglob("*")):
        if f.is_file() and not f.name.startswith('.') and f.suffix in ('.py', '.js', '.ts', '.jsx', '.tsx', '.md', '.txt', '.json', '.yaml', '.yml', '.html', '.css'):
            if '__pycache__' not in str(f) and 'node_modules' not in str(f):
                try:
                    content = f.read_text(errors="ignore")[:3000]
                    rel = str(f.relative_to(kb))
                    context_parts.append(f"--- {rel} ---\n{content}")
                except Exception:
                    pass
    return "\n\n".join(context_parts[:30])


def _get_domain_rules(folder_path: str) -> str:
    """Get governance rules specific to this domain folder."""
    rules_dir = DOMAIN_RULES_DIR / folder_path.replace("/", "_")
    if not rules_dir.exists():
        return ""

    parts = []
    for f in sorted(rules_dir.iterdir()):
        if f.is_file() and not f.name.startswith('.') and not f.name.endswith('.meta.json'):
            try:
                parts.append(f"[DOMAIN RULE: {f.name}]\n{f.read_text(errors='ignore')[:3000]}")
            except Exception:
                pass

    if not parts:
        return ""
    return "\n\nDOMAIN-SPECIFIC RULES (for folder: " + folder_path + "):\n" + "\n\n---\n\n".join(parts) + "\n\n"


# ── Domain Chat ───────────────────────────────────────────────────────

@router.post("/chat")
async def domain_chat(request: DomainChat):
    """Chat with full context of a specific domain folder."""
    from settings import settings

    # Build folder context
    folder_context = _get_folder_context(request.folder_path)
    domain_rules = _get_domain_rules(request.folder_path)

    system_prompt = (
        f"You are Grace, working within the domain folder: {request.folder_path}\n"
        f"You have full context of all files in this folder.\n"
        f"Answer questions and write code specific to this domain.\n"
    )
    if domain_rules:
        system_prompt += domain_rules
    if folder_context:
        system_prompt += f"\n\nDOMAIN FILES:\n{folder_context[:20000]}"

    # Select provider
    provider = request.provider
    if provider == "auto":
        if settings.OPUS_API_KEY:
            provider = "opus"
        elif settings.KIMI_API_KEY:
            provider = "kimi"
        else:
            provider = settings.LLM_PROVIDER

    try:
        from llm_orchestrator.factory import get_llm_client
        client = get_llm_client(provider=provider)
        response = client.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.message},
            ],
            temperature=0.5,
        )

        from api._genesis_tracker import track
        track(key_type="ai_response", what=f"Domain chat [{request.folder_path}]: {request.message[:80]}",
              where=request.folder_path, tags=["domain_chat", provider])

        return {
            "response": response,
            "folder_path": request.folder_path,
            "provider": provider,
            "files_in_context": folder_context.count("---"),
            "domain_rules_applied": bool(domain_rules),
        }
    except Exception as e:
        return {"error": str(e), "folder_path": request.folder_path}


# ── Domain-Specific Governance Rules ───────────────────────────────────

@router.get("/{folder_path:path}/rules")
async def list_domain_rules(folder_path: str):
    """List governance rules for a specific domain folder."""
    rules_dir = DOMAIN_RULES_DIR / folder_path.replace("/", "_")
    if not rules_dir.exists():
        return {"folder": folder_path, "rules": [], "total": 0}

    rules = []
    for f in sorted(rules_dir.iterdir()):
        if f.is_file() and not f.name.startswith('.') and not f.name.endswith('.meta.json'):
            rules.append({
                "filename": f.name,
                "size": f.stat().st_size,
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            })
    return {"folder": folder_path, "rules": rules, "total": len(rules)}


@router.post("/{folder_path:path}/rules/upload")
async def upload_domain_rule(folder_path: str, file: UploadFile = File(...), description: str = Form("")):
    """Upload a governance rule specific to this domain folder."""
    rules_dir = DOMAIN_RULES_DIR / folder_path.replace("/", "_")
    rules_dir.mkdir(parents=True, exist_ok=True)

    fp = rules_dir / file.filename
    content = await file.read()
    fp.write_bytes(content)

    from api._genesis_tracker import track
    track(key_type="upload", what=f"Domain rule uploaded: {file.filename} for {folder_path}",
          where=folder_path, tags=["domain_rules", folder_path])

    return {"uploaded": True, "folder": folder_path, "filename": file.filename, "size": len(content)}


@router.get("/{folder_path:path}/rules/{filename}/content")
async def read_domain_rule(folder_path: str, filename: str):
    """Read a domain rule's content."""
    fp = DOMAIN_RULES_DIR / folder_path.replace("/", "_") / filename
    if not fp.exists():
        return {"error": "Rule not found"}
    return {"filename": filename, "folder": folder_path, "content": fp.read_text(errors="ignore")}


@router.put("/{folder_path:path}/rules/{filename}/content")
async def save_domain_rule(folder_path: str, filename: str, request: DomainRuleSave):
    """Edit and save a domain-specific rule."""
    fp = DOMAIN_RULES_DIR / folder_path.replace("/", "_") / filename
    if not fp.exists():
        return {"error": "Rule not found"}
    fp.write_text(request.content, encoding="utf-8")

    from api._genesis_tracker import track
    track(key_type="file_op", what=f"Domain rule edited: {filename} for {folder_path}",
          tags=["domain_rules", "edit"])

    return {"saved": True, "filename": filename}


@router.delete("/{folder_path:path}/rules/{filename}")
async def delete_domain_rule(folder_path: str, filename: str):
    """Delete a domain-specific rule."""
    fp = DOMAIN_RULES_DIR / folder_path.replace("/", "_") / filename
    if fp.exists():
        fp.unlink()
    return {"deleted": True}


# ── Domain Info ────────────────────────────────────────────────────────

@router.get("/{folder_path:path}/info")
async def domain_info(folder_path: str):
    """Get info about a domain folder — files, rules, context size."""
    kb = _get_kb()
    folder = kb / folder_path
    if not folder.exists():
        return {"exists": False, "folder": folder_path}

    file_count = 0
    total_size = 0
    for f in folder.rglob("*"):
        if f.is_file():
            file_count += 1
            total_size += f.stat().st_size

    rules_count = 0
    rules_dir = DOMAIN_RULES_DIR / folder_path.replace("/", "_")
    if rules_dir.exists():
        rules_count = sum(1 for f in rules_dir.iterdir() if f.is_file() and not f.name.startswith('.'))

    return {
        "folder": folder_path,
        "exists": True,
        "file_count": file_count,
        "total_size_kb": round(total_size / 1024, 1),
        "domain_rules_count": rules_count,
        "has_custom_rules": rules_count > 0,
    }


# ── Available Models ───────────────────────────────────────────────────

@router.get("/models")
async def available_models():
    """List available LLM models for domain chat."""
    from settings import settings
    models = [{"id": "ollama", "name": "Local (Ollama)", "available": True}]

    if settings.KIMI_API_KEY:
        models.append({"id": "kimi", "name": "Kimi 2.5 Cloud", "available": True})
    else:
        models.append({"id": "kimi", "name": "Kimi 2.5 Cloud", "available": False})

    if getattr(settings, 'OPUS_API_KEY', ''):
        models.append({"id": "opus", "name": "Opus 4.6 (Claude)", "available": True})
    else:
        models.append({"id": "opus", "name": "Opus 4.6 (Claude)", "available": False})

    if settings.LLM_API_KEY and settings.LLM_PROVIDER == "openai":
        models.append({"id": "openai", "name": "OpenAI", "available": True})

    return {"models": models}
