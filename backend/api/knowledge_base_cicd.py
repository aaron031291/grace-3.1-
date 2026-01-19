"""
Knowledge Base CI/CD Integration
================================
Enables autonomous CI/CD triggers from the knowledge base.
Integrates with the Genesis Key CI/CD system.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
import json
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/knowledge-base/cicd", tags=["Knowledge Base - CI/CD"])

# Knowledge base path
KB_PATH = Path(__file__).parent.parent.parent / "knowledge_base" / "cicd_pipelines"


class AutonomousAction(BaseModel):
    """An autonomous action that can be triggered."""
    id: str
    name: str
    description: str
    endpoint: str
    method: str
    payload: Optional[Dict[str, Any]] = None
    requires_confirmation: bool = False


class TriggerActionRequest(BaseModel):
    """Request to trigger an autonomous action."""
    action_id: str
    parameters: Optional[Dict[str, Any]] = None
    confirmed: bool = False


class KnowledgeBaseEntry(BaseModel):
    """Knowledge base entry with CI/CD info."""
    id: str
    title: str
    description: str
    category: str
    tags: List[str]
    autonomous_actions: List[AutonomousAction]
    api_endpoints: List[Dict[str, str]]


def load_metadata() -> Optional[Dict[str, Any]]:
    """Load CI/CD metadata from knowledge base."""
    metadata_path = KB_PATH / "metadata.json"
    if metadata_path.exists():
        with open(metadata_path, "r") as f:
            return json.load(f)
    return None


@router.get("/")
async def get_cicd_knowledge_base():
    """
    Get CI/CD knowledge base entry.

    Returns the full CI/CD knowledge base entry including
    available autonomous actions.
    """
    metadata = load_metadata()

    if not metadata:
        raise HTTPException(status_code=404, detail="CI/CD knowledge base not found")

    # Load README content
    readme_path = KB_PATH / "README.md"
    readme_content = ""
    if readme_path.exists():
        with open(readme_path, "r") as f:
            readme_content = f.read()

    return {
        **metadata,
        "readme": readme_content,
        "files": [
            str(f.relative_to(KB_PATH))
            for f in KB_PATH.rglob("*")
            if f.is_file()
        ]
    }


@router.get("/actions")
async def list_autonomous_actions():
    """
    List available autonomous CI/CD actions.

    Returns actions that can be triggered from the knowledge base.
    """
    metadata = load_metadata()

    if not metadata or "autonomous_actions" not in metadata:
        return {"actions": []}

    actions = metadata["autonomous_actions"].get("actions", [])

    return {
        "enabled": metadata["autonomous_actions"].get("enabled", False),
        "actions": actions,
        "count": len(actions)
    }


@router.post("/trigger")
async def trigger_autonomous_action(
    request: TriggerActionRequest,
    background_tasks: BackgroundTasks
):
    """
    Trigger an autonomous CI/CD action.

    Executes the specified action from the knowledge base.
    Some actions require confirmation.
    """
    metadata = load_metadata()

    if not metadata or "autonomous_actions" not in metadata:
        raise HTTPException(status_code=404, detail="No autonomous actions configured")

    if not metadata["autonomous_actions"].get("enabled", False):
        raise HTTPException(status_code=403, detail="Autonomous actions are disabled")

    # Find the action
    actions = metadata["autonomous_actions"].get("actions", [])
    action = next((a for a in actions if a["id"] == request.action_id), None)

    if not action:
        raise HTTPException(status_code=404, detail=f"Action '{request.action_id}' not found")

    # Check confirmation requirement
    if action.get("requires_confirmation", False) and not request.confirmed:
        return {
            "status": "confirmation_required",
            "action_id": request.action_id,
            "action_name": action["name"],
            "message": f"Action '{action['name']}' requires confirmation. Set confirmed=true to proceed."
        }

    # Execute the action
    import httpx

    try:
        endpoint = action["endpoint"]
        method = action["method"].upper()
        payload = {**action.get("payload", {}), **(request.parameters or {})}

        # Make internal API call
        base_url = os.getenv("API_BASE_URL", "http://localhost:8000")

        async with httpx.AsyncClient() as client:
            if method == "GET":
                response = await client.get(f"{base_url}{endpoint}", params=payload)
            elif method == "POST":
                response = await client.post(f"{base_url}{endpoint}", json=payload)
            elif method == "PUT":
                response = await client.put(f"{base_url}{endpoint}", json=payload)
            elif method == "DELETE":
                response = await client.delete(f"{base_url}{endpoint}")
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported method: {method}")

            result = response.json() if response.headers.get("content-type", "").startswith("application/json") else {"text": response.text}

            logger.info(f"[KB-CICD] Triggered action '{request.action_id}': {response.status_code}")

            return {
                "status": "triggered",
                "action_id": request.action_id,
                "action_name": action["name"],
                "response_status": response.status_code,
                "result": result,
                "triggered_at": datetime.utcnow().isoformat()
            }

    except httpx.RequestError as e:
        logger.error(f"[KB-CICD] Failed to trigger action: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger action: {str(e)}")


@router.get("/pipelines")
async def get_pipeline_files():
    """
    Get pipeline definition files from knowledge base.

    Returns YAML pipeline configurations.
    """
    pipelines_dir = Path(__file__).parent.parent.parent / "pipelines"

    if not pipelines_dir.exists():
        return {"pipelines": []}

    pipeline_files = []
    for f in pipelines_dir.glob("*.yaml"):
        with open(f, "r") as file:
            content = file.read()
            pipeline_files.append({
                "name": f.stem,
                "filename": f.name,
                "content": content,
                "size": f.stat().st_size,
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
            })

    return {
        "count": len(pipeline_files),
        "pipelines": pipeline_files
    }


@router.get("/status")
async def get_cicd_kb_status():
    """
    Get CI/CD knowledge base status.

    Returns status of the CI/CD knowledge base integration.
    """
    metadata = load_metadata()

    kb_exists = KB_PATH.exists()
    metadata_exists = (KB_PATH / "metadata.json").exists() if kb_exists else False
    readme_exists = (KB_PATH / "README.md").exists() if kb_exists else False

    pipelines_dir = Path(__file__).parent.parent.parent / "pipelines"
    pipeline_count = len(list(pipelines_dir.glob("*.yaml"))) if pipelines_dir.exists() else 0

    return {
        "knowledge_base": {
            "exists": kb_exists,
            "path": str(KB_PATH),
            "has_metadata": metadata_exists,
            "has_readme": readme_exists
        },
        "autonomous_actions": {
            "enabled": metadata.get("autonomous_actions", {}).get("enabled", False) if metadata else False,
            "count": len(metadata.get("autonomous_actions", {}).get("actions", [])) if metadata else 0
        },
        "pipelines": {
            "directory": str(pipelines_dir),
            "count": pipeline_count
        },
        "api_endpoints": len(metadata.get("api_endpoints", [])) if metadata else 0
    }


@router.post("/refresh")
async def refresh_cicd_knowledge():
    """
    Refresh CI/CD knowledge base.

    Reloads pipeline configurations and updates metadata.
    """
    # Ensure directory exists
    KB_PATH.mkdir(parents=True, exist_ok=True)

    # Get current pipeline list from CI/CD system
    from genesis.cicd import get_cicd

    cicd = get_cicd()
    pipelines = cicd.list_pipelines()

    # Update metadata with current pipelines
    metadata = load_metadata() or {
        "id": "cicd_pipelines",
        "title": "CI/CD Pipelines",
        "description": "Genesis Key-powered CI/CD pipeline system",
        "category": "infrastructure",
        "tags": ["cicd", "pipelines", "automation"],
        "created_at": datetime.utcnow().isoformat(),
        "autonomous_actions": {"enabled": True, "actions": []}
    }

    # Auto-generate actions from pipelines
    actions = [
        {
            "id": f"trigger_{p.id}",
            "name": f"Run {p.name}",
            "description": p.description or f"Trigger {p.name} pipeline",
            "endpoint": "/api/cicd/trigger",
            "method": "POST",
            "payload": {"pipeline_id": p.id, "branch": "main"},
            "requires_confirmation": "deploy" in p.id.lower()
        }
        for p in pipelines
    ]

    # Add standard actions
    actions.extend([
        {
            "id": "view_runs",
            "name": "View Pipeline Runs",
            "description": "List recent pipeline executions",
            "endpoint": "/api/cicd/runs",
            "method": "GET"
        },
        {
            "id": "view_status",
            "name": "CI/CD Status",
            "description": "Get CI/CD system status",
            "endpoint": "/api/cicd/status",
            "method": "GET"
        }
    ])

    metadata["autonomous_actions"]["actions"] = actions
    metadata["updated_at"] = datetime.utcnow().isoformat()

    # Save metadata
    with open(KB_PATH / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    return {
        "status": "refreshed",
        "pipelines_found": len(pipelines),
        "actions_generated": len(actions),
        "updated_at": metadata["updated_at"]
    }
