from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(tags=["Agents"])

class TriadRequest(BaseModel):
    prompt: str
    system_prompt: str = ""
    execution_allowed: bool = False
    conversation_history: Optional[List[dict]] = None
    project_folder: str = ""

@router.post("/triad")
async def trigger_triad_orchestrator(req: TriadRequest):
    """Trigger the 3-model parallel processing pipeline."""
    try:
        from cognitive.qwen_triad_orchestrator import get_triad_orchestrator
        orchestrator = get_triad_orchestrator()
        result = await orchestrator.process(
            prompt=req.prompt,
            system_prompt=req.system_prompt,
            execution_allowed=req.execution_allowed,
            conversation_history=req.conversation_history,
            project_folder=req.project_folder
        )
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

class BlueprintRequest(BaseModel):
    prompt: str

@router.post("/blueprint/create")
async def create_blueprint(req: BlueprintRequest):
    """Trigger autonomous code generation via the Blueprint Engine."""
    try:
        from cognitive.blueprint_engine import create_from_prompt
        # This function is synchronous in blueprint_engine.py
        result = create_from_prompt(req.prompt)
        return {"success": result.get("result") == "SUCCESS", "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/blueprint/stats")
async def get_blueprint_stats():
    """Get statistics on the coding playbook."""
    try:
        from cognitive.blueprint_engine import get_playbook_stats
        result = get_playbook_stats()
        return {"success": True, "stats": result}
    except Exception as e:
        return {"success": False, "error": str(e)}
