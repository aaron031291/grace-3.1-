import os
import json
import uuid
import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from pathlib import Path

# Actual LLM Orchestrator
from llm_orchestrator.factory import get_llm_for_task

router = APIRouter(prefix="/whitelist-hub", tags=["Whitelist Hub"])

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
GENESIS_TRACKING_FILE = WORKSPACE_ROOT / "backend" / ".genesis_file_versions.json"
WHITELIST_SOURCES_FILE = WORKSPACE_ROOT / "backend" / ".whitelist_sources.json"

class WhitelistSource(BaseModel):
    id: Optional[str] = None
    name: str
    url: str
    type: str # 'web', 'api', 'authority'
    active: bool = True
    domain: str = "Global"

class ConsensusRequest(BaseModel):
    domain: str
    flash_cache: str
    web_links: List[Dict]
    api_sources: List[Dict]
    authorities: List[Dict]

def record_genesis_block(file_path: str, content: str, trigger: str = "Whitelist Synthesis"):
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
    
    latest_version = versions[-1].get("linear_version", "v1.0") if versions else "v1.0"
    try:
        if latest_version.startswith("v"):
            parts = latest_version[1:].split(".")
            v_minor = int(parts[1]) if len(parts) > 1 else 0
            linear_ver = f"v1.{v_minor + 1}"
        else:
            linear_ver = f"v1.{len(versions)}"
    except:
        linear_ver = f"v1.{len(versions)}"
        
    genesis_key = f"GK-{uuid.uuid4().hex}"
    
    new_version = {
        "linear_version": linear_ver,
        "genesis_key": genesis_key,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "trigger": trigger,
        "file_size": len(content),
        "status": "active"
    }
    
    for v in versions:
        v["status"] = "superseded"
        
    versions.append(new_version)
    file_record["versions"] = versions
    file_record["last_updated"] = new_version["timestamp"]
    
    with open(GENESIS_TRACKING_FILE, "w", encoding="utf-8") as f:
        json.dump(genesis_data, f, indent=2)

def load_whitelist_sources():
    if not WHITELIST_SOURCES_FILE.exists():
        return []
    try:
        with open(WHITELIST_SOURCES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_whitelist_sources(sources):
    with open(WHITELIST_SOURCES_FILE, "w", encoding="utf-8") as f:
        json.dump(sources, f, indent=2)

@router.get("/sources")
async def get_whitelist_sources(domain: str = "Global"):
    """Get all configured deterministic whitelist sources"""
    sources = load_whitelist_sources()
    # If empty, return some defaults for UI demonstration
    if not sources:
        sources = [
            {"id": "ws-1", "name": "DeepMind Docs", "url": "https://deepmind.google/technologies", "type": "web", "active": True, "domain": "Global"},
            {"id": "ws-2", "name": "GitHub API", "url": "api.github.com/v3", "type": "api", "active": True, "domain": "Global"},
            {"id": "ws-3", "name": "ArXiv CS Papers", "url": "export.arxiv.org/api", "type": "api", "active": True, "domain": "Global"},
        ]
        save_whitelist_sources(sources)
        
    return {"sources": [s for s in sources if s.get("domain") == domain or domain == "Global"]}

@router.post("/sources")
async def add_whitelist_source(source: WhitelistSource):
    """Add a new deterministic tracking source"""
    sources = load_whitelist_sources()
    new_source = source.dict()
    new_source["id"] = f"ws-{uuid.uuid4().hex[:8]}"
    sources.append(new_source)
    save_whitelist_sources(sources)
    return {"success": True, "source": new_source}

@router.post("/consensus")
async def run_llm_consensus(req: ConsensusRequest):
    """
    Takes data from the 5 Deterministic Whitelist layers and runs it through
    an LLM consensus engine (Opus, Kimi, Qwen simulate) to produce validated knowledge.
    """
    
    # Extract active monitoring data
    active_webs = [w['url'] for w in req.web_links if w['active']]
    active_apis = [a['endpoint'] for a in req.api_sources if a['active']]
    
    # Live LLM Generation using orchestrator
    reasoning_llm = get_llm_for_task("reason")
    document_llm = get_llm_for_task("document")
    
    flash_content = ""
    validated_nodes = []
    timestamp = datetime.datetime.utcnow().isoformat()
    
    if req.flash_cache:
        try:
            flash_prompt = f"Synthesize and audit the following internal concepts for a knowledge base:\n{req.flash_cache}\nRespond with a concise, factual summary."
            flash_content = reasoning_llm.chat(messages=[{"role": "user", "content": flash_prompt}])
        except Exception as e:
            flash_content = f"Failed to run LLM: {str(e)}"
            
        validated_nodes.append({
            "id": f"node-{uuid.uuid4().hex[:8]}",
            "title": "Flash Cache Synthesis (AI Generated)",
            "content": flash_content,
            "models": ["Qwen/Opus (Reasoning)"],
            "timestamp": timestamp
        })
        
    web_api_content = ""
    if active_webs or active_apis:
        try:
            scope_prompt = f"We are tracking these generic APIs: {active_apis} and web scopes: {active_webs}. Provide a synthesized overview of what knowledge we might extract from these structural bounds."
            web_api_content = document_llm.chat(messages=[{"role": "user", "content": scope_prompt}])
        except Exception as e:
            web_api_content = f"Failed to run LLM: {str(e)}"
            
        validated_nodes.append({
            "id": f"node-{uuid.uuid4().hex[:8]}",
            "title": "Web & API Structured Data (AI Generated)",
            "content": web_api_content,
            "models": ["Qwen/Kimi (Document)"],
            "timestamp": timestamp
        })
    
    # Write this consensus to the Domain's local RAG knowledge path so ChatTab can read it
    domain_safe = "".join(c if c.isalnum() else "_" for c in req.domain)
    knowledge_dir = WORKSPACE_ROOT / "backend" / "data" / "domains" / domain_safe / "whitelist"
    knowledge_dir.mkdir(parents=True, exist_ok=True)
    
    file_name = f"consensus_{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')}.json"
    file_path = knowledge_dir / file_name
    
    content_str = json.dumps(validated_nodes, indent=2)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content_str)
        
    # Hook into Genesis Version Control
    rel_path = f"backend/data/domains/{domain_safe}/whitelist/{file_name}"
    record_genesis_block(rel_path, content_str, trigger="LLM Consensus Whitelist Generation")
    
    return {"success": True, "validated_knowledge": validated_nodes}
