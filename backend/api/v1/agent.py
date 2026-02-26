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

@router.post("/kimi/review")
async def kimi_review(request: AgentPrompt):
    """Kimi reviews code as second opinion before applying."""
    from llm_orchestrator.kimi_enhanced import get_kimi_enhanced
    kimi = get_kimi_enhanced()
    try:
        from api.agent_rules_api import get_agent_rules_context
        rules = get_agent_rules_context()
    except Exception:
        rules = ""
    return kimi.review_code(request.prompt, project_context=request.project_folder, rules=rules)

@router.post("/kimi/teach")
async def kimi_teach(topic: str, context: str = ""):
    """Kimi teaches Grace a topic — ingests into Magma + learning memory."""
    from llm_orchestrator.kimi_enhanced import get_kimi_enhanced
    return get_kimi_enhanced().teach_topic(topic, context)

@router.post("/kimi/analyse-project")
async def kimi_analyse_project(request: AgentPrompt):
    """Send entire project to Kimi for holistic analysis (128K context)."""
    from llm_orchestrator.kimi_enhanced import get_kimi_enhanced
    from pathlib import Path
    kimi = get_kimi_enhanced()
    try:
        from settings import settings
        kb = Path(settings.KNOWLEDGE_BASE_PATH) / request.project_folder
        files = {}
        if kb.exists():
            for f in kb.rglob("*"):
                if f.is_file() and f.suffix in ('.py', '.js', '.ts', '.jsx', '.tsx', '.md', '.json', '.yaml'):
                    if '__pycache__' not in str(f) and 'node_modules' not in str(f):
                        files[str(f.relative_to(kb))] = f.read_text(errors="ignore")[:3000]
        return kimi.analyse_project(files)
    except Exception as e:
        return {"error": str(e)}

@router.post("/kimi/enrich-magma")
async def kimi_enrich(query: str, context: str = ""):
    """Use Kimi to generate causal/semantic relationships for Magma memory."""
    from llm_orchestrator.kimi_enhanced import get_kimi_enhanced
    return get_kimi_enhanced().enrich_magma(query, context)

@router.post("/kimi/process-rules")
async def kimi_process_rules(doc_name: str, content: str):
    """Kimi pre-processes a rule document — extracts structured rules."""
    from llm_orchestrator.kimi_enhanced import get_kimi_enhanced
    return get_kimi_enhanced().process_rule_document(content, doc_name)
