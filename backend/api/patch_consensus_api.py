"""
Patch Consensus API — Trustless Code Change Pipeline

Endpoints for the full consensus-based patch flow:
- Generate patch instructions (Opus + Kimi structured JSON)
- Create proposals with SHA-256 hashing
- Run consensus verification
- Apply verified patches with librarian routing
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/patch-consensus", tags=["Patch Consensus"])


class PatchRequest(BaseModel):
    task: str
    context: str = ""
    models: Optional[List[str]] = None
    codebase_root: str = ""
    auto_apply: bool = False
    threshold: float = 0.67


class ApplyProposalRequest(BaseModel):
    proposal_id: str
    codebase_root: str = ""


@router.post("/run")
async def run_patch_pipeline(req: PatchRequest):
    """
    Full end-to-end patch consensus pipeline.

    1. Opus + Kimi produce structured JSON instructions
    2. Deepsea validates deterministically
    3. Nodes verify (hash, signature, clean apply)
    4. If 2/3+ approve → auto-merge + librarian routing
    """
    from cognitive.patch_consensus import run_patch_consensus

    try:
        result = run_patch_consensus(
            task=req.task,
            context=req.context,
            models=req.models,
            codebase_root=req.codebase_root,
            auto_apply=req.auto_apply,
            threshold=req.threshold,
        )
        return result
    except Exception as e:
        logger.error(f"Patch consensus failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/apply")
async def apply_proposal(req: ApplyProposalRequest):
    """Apply a previously verified proposal."""
    from cognitive.patch_consensus import (
        get_proposal, PatchProposal, PatchInstruction,
        apply_verified_proposal,
    )

    data = get_proposal(req.proposal_id)
    if not data:
        raise HTTPException(status_code=404, detail="Proposal not found")
    if data["status"] != "verified":
        raise HTTPException(
            status_code=400,
            detail=f"Proposal status is '{data['status']}', must be 'verified'"
        )

    instructions = [
        PatchInstruction(**inst) for inst in data["instructions"]
    ]
    proposal = PatchProposal(
        proposal_id=data["proposal_id"],
        instructions=instructions,
        source_models=data["source_models"],
        patch_hash=data["patch_hash"],
        timestamp=data["timestamp"],
        status=data["status"],
        verification_votes=data.get("verification_votes", []),
        threshold=data.get("threshold", 0.67),
    )

    proposal = apply_verified_proposal(proposal, req.codebase_root)
    return {
        "proposal_id": proposal.proposal_id,
        "status": proposal.status,
        "execution_result": proposal.execution_result,
        "error": proposal.error,
    }


@router.get("/proposals")
async def list_proposals(status: Optional[str] = None, limit: int = 50):
    """List patch proposals, optionally filtered by status."""
    from cognitive.patch_consensus import list_proposals as _list
    proposals = _list(status=status, limit=limit)
    return {"proposals": proposals, "total": len(proposals)}


@router.get("/proposals/{proposal_id}")
async def get_proposal(proposal_id: str):
    """Get a specific patch proposal."""
    from cognitive.patch_consensus import get_proposal as _get
    data = _get(proposal_id)
    if not data:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return data
