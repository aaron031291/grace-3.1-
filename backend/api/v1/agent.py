"""v1/agent — Unified coding agent with feedback loop"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/v1/agent", tags=["v1 Agent"])
BASE = "http://localhost:8000"


class AgentPrompt(BaseModel):
    prompt: str
    project_folder: str
    current_file: Optional[str] = None
    use_kimi: bool = False

class AgentApply(BaseModel):
    path: str
    content: str
    project_folder: str

class AgentFeedback(BaseModel):
    genesis_key: str
    prompt: str
    output: str
    outcome: str  # positive, negative, failure
    correction: Optional[str] = None


@router.post("/generate")
async def generate(request: AgentPrompt):
    import requests as req
    return req.post(f"{BASE}/api/coding-agent/generate", json={
        **request.model_dump(),
        "include_codenet": True, "include_memory": True,
        "include_rag": True, "include_cognitive": True, "verify_output": True,
    }, timeout=120).json()

@router.post("/apply")
async def apply(request: AgentApply):
    import requests as req
    return req.post(f"{BASE}/api/coding-agent/apply", json=request.model_dump(), timeout=10).json()

@router.post("/feedback")
async def feedback(request: AgentFeedback):
    """Record outcome of a generation — closes the learning loop."""
    from cognitive.pipeline import FeedbackLoop
    FeedbackLoop.record_outcome(
        genesis_key=request.genesis_key,
        prompt=request.prompt,
        output=request.output,
        outcome=request.outcome,
        correction=request.correction,
    )
    return {"recorded": True, "outcome": request.outcome}

@router.get("/capabilities")
async def capabilities():
    import requests as req
    return req.get(f"{BASE}/api/coding-agent/capabilities", timeout=10).json()
