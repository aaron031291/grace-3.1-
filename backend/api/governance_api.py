from fastapi import APIRouter
from typing import Dict, Any

router = APIRouter(prefix="/governance", tags=["Governance"])

@router.get("/stats")
async def get_stats(): return {"status": "ok"}

@router.get("/rules")
async def get_rules(): return {"rules": []}

@router.get("/rules/{rule_id}")
async def get_rule_by_id(rule_id: str): return {"rule": {"id": rule_id}}

@router.post("/rules/new")
async def create_rule(payload: Dict[str, Any]): return {"status": "ok"}

@router.put("/rules/{rule_id}")
async def update_rule(rule_id: str, payload: Dict[str, Any]): return {"status": "ok", "rule": {"id": rule_id}}

@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: str): return {"status": "ok"}

@router.get("/decisions/pending")
async def pending_decisions(): return {"decisions": []}

@router.get("/decisions/history")
async def decision_history(): return {"history": []}

@router.post("/decisions/{decision_id}/confirm")
async def confirm_decision(decision_id: str, payload: Dict[str, Any] = None): return {"status": "ok"}

@router.post("/decisions/{decision_id}/deny")
async def deny_decision(decision_id: str, payload: Dict[str, Any] = None): return {"status": "ok"}

@router.get("/pillars")
async def get_pillars(): return {"pillars": []}

@router.get("/pillars/{pillar_name}/status")
async def get_pillar_status(pillar_name: str): return {"status": "ok"}

@router.post("/documents/upload")
async def upload_document(payload: Dict[str, Any] = None): return {"status": "ok"}

@router.get("/documents")
async def get_documents(): return {"documents": []}

@router.get("/documents/{doc_id}")
async def get_document_by_id(doc_id: str): return {"document": {"id": doc_id}}
