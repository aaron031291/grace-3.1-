"""v1/governance — Approvals, scores, rules, persona, genesis keys, healing"""
from fastapi import APIRouter, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/v1/governance", tags=["v1 Governance"])
BASE = "http://localhost:8000"


class ApprovalAction(BaseModel):
    decision: str
    reason: Optional[str] = None

class PersonaUpdate(BaseModel):
    personal: Optional[str] = None
    professional: Optional[str] = None

class RuleSave(BaseModel):
    content: str

class ReasonRequest(BaseModel):
    document_id: str
    question: str
    use_kimi: bool = True

class HealTrigger(BaseModel):
    action: str

class LearnTrigger(BaseModel):
    method: str
    query: Optional[str] = None
    topic: Optional[str] = None


@router.get("/dashboard")
async def dashboard():
    import requests as req
    return req.get(f"{BASE}/api/governance-hub/dashboard", timeout=10).json()

@router.get("/approvals")
async def approvals():
    import requests as req
    return req.get(f"{BASE}/api/governance-hub/approvals", timeout=10).json()

@router.get("/approvals/history")
async def approval_history():
    import requests as req
    return req.get(f"{BASE}/api/governance-hub/approvals/history", timeout=10).json()

@router.post("/approvals/{decision_id}")
async def action_approval(decision_id: int, request: ApprovalAction):
    import requests as req
    return req.post(f"{BASE}/api/governance-hub/approvals/{decision_id}", json=request.model_dump(), timeout=10).json()

@router.get("/scores")
async def scores():
    import requests as req
    return req.get(f"{BASE}/api/governance-hub/scores", timeout=10).json()

@router.get("/performance")
async def performance():
    import requests as req
    return req.get(f"{BASE}/api/governance-hub/performance", timeout=10).json()

@router.post("/healing")
async def heal(request: HealTrigger):
    import requests as req
    return req.post(f"{BASE}/api/governance-hub/healing/trigger", json=request.model_dump(), timeout=10).json()

@router.get("/healing/actions")
async def healing_actions():
    import requests as req
    return req.get(f"{BASE}/api/governance-hub/healing/actions", timeout=10).json()

@router.post("/learning")
async def learn(request: LearnTrigger):
    import requests as req
    return req.post(f"{BASE}/api/governance-hub/learning/trigger", json=request.model_dump(), timeout=30).json()

# Rules & Persona
@router.get("/persona")
async def get_persona():
    import requests as req
    return req.get(f"{BASE}/api/governance-rules/persona", timeout=10).json()

@router.put("/persona")
async def set_persona(request: PersonaUpdate):
    import requests as req
    return req.put(f"{BASE}/api/governance-rules/persona", json=request.model_dump(), timeout=10).json()

@router.get("/rules")
async def list_rules():
    import requests as req
    return req.get(f"{BASE}/api/governance-rules/documents", timeout=10).json()

@router.post("/rules/upload")
async def upload_rule(file: UploadFile = File(...), category: str = Form("general"), description: str = Form("")):
    import requests as req
    r = req.post(f"{BASE}/api/governance-rules/documents/upload",
                 files={"file": (file.filename, file.file, file.content_type)},
                 data={"category": category, "description": description}, timeout=30)
    return r.json()

@router.get("/rules/{doc_id:path}/content")
async def rule_content(doc_id: str):
    import requests as req
    return req.get(f"{BASE}/api/governance-rules/documents/{doc_id}/content", timeout=10).json()

@router.put("/rules/{doc_id:path}/content")
async def save_rule(doc_id: str, request: RuleSave):
    import requests as req
    return req.put(f"{BASE}/api/governance-rules/documents/{doc_id}/content", json=request.model_dump(), timeout=10).json()

@router.post("/rules/reason")
async def reason_rule(request: ReasonRequest):
    import requests as req
    return req.post(f"{BASE}/api/governance-rules/documents/reason", json=request.model_dump(), timeout=60).json()

# Genesis Keys
@router.get("/genesis/folders")
async def genesis_folders(days: int = 30):
    import requests as req
    return req.get(f"{BASE}/api/genesis-daily/folders?days={days}", timeout=10).json()

@router.get("/genesis/folder/{date}")
async def genesis_folder(date: str):
    import requests as req
    return req.get(f"{BASE}/api/genesis-daily/folder/{date}", timeout=10).json()

@router.get("/genesis/key/{key_id}")
async def genesis_key(key_id: str):
    import requests as req
    return req.get(f"{BASE}/api/genesis-daily/key/{key_id}", timeout=10).json()

@router.get("/genesis/stats")
async def genesis_stats():
    import requests as req
    return req.get(f"{BASE}/api/genesis-daily/stats", timeout=10).json()
