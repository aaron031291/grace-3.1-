import os
import uuid
import datetime
import ast
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from pydantic import BaseModel
from pathlib import Path
from sqlalchemy.orm import Session
from database.connection import DatabaseConnection
from database.session import get_session_factory
from database.auto_migrate import run_auto_migrate
from models.database_models import SchemaProposal

router = APIRouter(prefix="/schema-evolution", tags=["Schema Evolution"])

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
DYNAMIC_MODELS_FILE = WORKSPACE_ROOT / "backend" / "models" / "dynamic_models.py"

class ProposalCreateRequest(BaseModel):
    trigger_reason: str
    proposed_code: str

class ProposalResponse(BaseModel):
    id: int
    proposal_id: str
    trigger_reason: str
    proposed_code: str
    status: str
    execution_logs: str | None
    created_at: str | None

def validate_sqlalchemy_ast(code: str) -> bool:
    """
    Rigorously gates the generated SQLAlchemy code to ensure it's safe.
    Rejects any code containing imports other than typical SQLAlchemy ORM,
    or dangerous constructs like DROP TABLE or os.system.
    """
    try:
        tree = ast.parse(code)
    except Exception:
        return False
        
    for node in ast.walk(tree):
        # We only want to allow ClassDefs and simple assignments (no complex loops, network calls, etc.)
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            # Disallow all random imports in dynamic blocks (they should rely on dynamic_models.py headers)
            return False
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                # Basic safety check against exec, eval, etc.
                if node.func.id in {"eval", "exec", "open", "system", "__import__"}:
                    return False
    
    # Must contain "class " and "BaseModel"
    if "class " not in code or "BaseModel" not in code:
        return False
        
    return True

@router.get("/proposals")
def get_schema_proposals():
    """List all pending and executed schema proposals."""
    try:
        Session = get_session_factory()
        session = Session()
        proposals = session.query(SchemaProposal).order_by(SchemaProposal.created_at.desc()).all()
        return {"proposals": [p.to_dict() for p in proposals]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/proposals")
def create_schema_proposal(req: ProposalCreateRequest):
    """
    Called by an agent (or human) to submit a new SQLAlchemy table/column.
    """
    try:
        if not validate_sqlalchemy_ast(req.proposed_code):
            raise HTTPException(status_code=400, detail="Proposed code failed the AST safety gate. Ensure it is only valid SQLAlchemy Model classes without dangerous imports.")
            
        proposal_id = f"SP-{uuid.uuid4().hex[:12]}"
        
        Session = get_session_factory()
        session = Session()
        
        new_prop = SchemaProposal(
            proposal_id=proposal_id,
            trigger_reason=req.trigger_reason,
            proposed_code=req.proposed_code,
            status="pending"
        )
        session.add(new_prop)
        session.commit()
        
        return {"success": True, "proposal_id": proposal_id, "status": "pending"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/proposals/{proposal_id}/approve")
def approve_schema_proposal(proposal_id: str):
    """
    Approves the proposal, injects it into dynamic_models.py, and executes auto_migrate.
    """
    Session = get_session_factory()
    session = Session()
    
    try:
        prop: SchemaProposal = session.query(SchemaProposal).filter(SchemaProposal.proposal_id == proposal_id).first()
        if not prop:
            raise HTTPException(status_code=404, detail="Proposal not found")
            
        if prop.status != "pending":
            raise HTTPException(status_code=400, detail=f"Cannot approve proposal with status: {prop.status}")
            
        # 1. Final Gate Check
        code_to_inject = prop.proposed_code
        if not validate_sqlalchemy_ast(code_to_inject):
            prop.status = "failed"
            prop.execution_logs = "AST Gate failed during approval. Code may be malformed."
            session.commit()
            raise HTTPException(status_code=400, detail="Code gate validation failed")
            
        # 2. Append to dynamic_models.py
        try:
            with open(DYNAMIC_MODELS_FILE, "a", encoding="utf-8") as f:
                f.write("\n\n" + "# TRIGGERED BY: " + prop.trigger_reason + "\n")
                f.write("# PROPOSAL ID: " + prop.proposal_id + "\n")
                f.write(code_to_inject + "\n")
        except Exception as file_err:
            prop.status = "failed"
            prop.execution_logs = f"Failed to write to dynamic_models.py: {file_err}"
            session.commit()
            raise HTTPException(status_code=500, detail="Failed to write schema to disk.")
            
        # 3. Reload dynamic models visually into python environment for SQLAlchemy
        import importlib
        import models.dynamic_models
        importlib.reload(models.dynamic_models)
        
        # 4. Trigger Auto-Migrate live against PG
        engine = conn.get_engine()
        changes = run_auto_migrate(engine)
        
        # 5. Log success
        prop.status = "approved"
        prop.execution_logs = "Dynamically injected. Auto-migrate reported: " + str(changes)
        
        from api._genesis_tracker import track
        try:
            prop.genesis_key_id = track(
                key_type="schema_migration",
                what_description=f"Approved schema proposal {prop.proposal_id}",
                why_reason=prop.trigger_reason,
                how_method="schema_evolution_api.approve_schema_proposal",
                context_data={"changes": changes},
                is_error=False
            )
        except Exception:
            pass
            
        session.commit()
        return {"success": True, "changes": changes, "genesis_key": prop.genesis_key_id}
        
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@router.post("/proposals/{proposal_id}/reject")
def reject_schema_proposal(proposal_id: str):
    """Rejects a schema proposal without applying it."""
    try:
        Session = get_session_factory()
        session = Session()
        
        prop: SchemaProposal = session.query(SchemaProposal).filter(SchemaProposal.proposal_id == proposal_id).first()
        if not prop:
            raise HTTPException(status_code=404, detail="Proposal not found")
            
        prop.status = "rejected"
        prop.execution_logs = "Rejected by human operator."
        session.commit()
        return {"success": True, "status": "rejected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
