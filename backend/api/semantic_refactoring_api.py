"""
Semantic Refactoring API - REST endpoints for multi-file refactoring.

Provides endpoints for:
- Symbol renaming across repository
- Module moves with import updates
- Refactoring plan management
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/refactoring", tags=["Semantic Refactoring"])


class RenameSymbolRequest(BaseModel):
    """Request to rename a symbol across the codebase."""
    old_name: str = Field(..., description="Current symbol name")
    new_name: str = Field(..., description="New symbol name")
    symbol_type: Optional[str] = Field(None, description="Type: function, class, method, variable")
    scope_file: Optional[str] = Field(None, description="Limit to specific file")
    dry_run: bool = Field(False, description="Simulate without applying changes")


class MoveModuleRequest(BaseModel):
    """Request to move a module to a new location."""
    source_module: str = Field(..., description="Current module path (e.g., 'cognitive.old_module')")
    target_module: str = Field(..., description="Target module path (e.g., 'cognitive.new_module')")
    dry_run: bool = Field(False, description="Simulate without applying changes")


class FindReferencesRequest(BaseModel):
    """Request to find all references to a symbol."""
    symbol_name: str = Field(..., description="Symbol name to find")
    symbol_type: Optional[str] = Field(None, description="Type filter")
    scope_file: Optional[str] = Field(None, description="Limit to specific file")


class RefactoringResponse(BaseModel):
    """Response from a refactoring operation."""
    success: bool
    plan_id: str
    files_modified: int = 0
    references_updated: int = 0
    affected_files: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []
    execution_time_ms: float = 0.0
    rollback_available: bool = True


class SymbolReferenceResponse(BaseModel):
    """A reference to a symbol."""
    file_path: str
    line_number: int
    column: int
    symbol_name: str
    symbol_type: str
    context: str
    is_definition: bool
    is_import: bool


class FindReferencesResponse(BaseModel):
    """Response from find references."""
    symbol_name: str
    total_references: int
    references: List[SymbolReferenceResponse]
    files_with_references: List[str]


class PlanStatusResponse(BaseModel):
    """Status of a refactoring plan."""
    plan_id: str
    refactoring_type: str
    source_symbol: str
    target_symbol: Optional[str]
    status: str
    affected_files_count: int
    references_count: int
    confidence: float
    risk_level: str


def _get_engine():
    """Get the semantic refactoring engine."""
    from cognitive.semantic_refactoring_engine import get_refactoring_engine
    return get_refactoring_engine()


def _get_symbol_type(type_str: Optional[str]):
    """Convert string to SymbolType enum."""
    if not type_str:
        return None
    from cognitive.semantic_refactoring_engine import SymbolType
    type_map = {
        "function": SymbolType.FUNCTION,
        "class": SymbolType.CLASS,
        "method": SymbolType.METHOD,
        "variable": SymbolType.VARIABLE,
        "constant": SymbolType.CONSTANT,
        "module": SymbolType.MODULE,
        "parameter": SymbolType.PARAMETER,
    }
    return type_map.get(type_str.lower())


@router.post("/rename", response_model=RefactoringResponse)
async def rename_symbol(request: RenameSymbolRequest):
    """
    Rename a symbol across the entire codebase.
    
    Finds all references to the symbol and renames them atomically.
    Validates changes and rolls back on failure.
    """
    try:
        engine = _get_engine()
        symbol_type = _get_symbol_type(request.symbol_type)
        
        # Create plan
        plan = engine.plan_rename_symbol(
            old_name=request.old_name,
            new_name=request.new_name,
            symbol_type=symbol_type,
            scope_file=request.scope_file,
        )
        
        # Execute plan
        result = engine.execute_plan(plan.plan_id, dry_run=request.dry_run)
        
        return RefactoringResponse(
            success=result.success,
            plan_id=plan.plan_id,
            files_modified=result.files_modified,
            references_updated=result.references_updated,
            affected_files=plan.affected_files,
            errors=result.errors,
            warnings=result.warnings,
            execution_time_ms=result.execution_time_ms,
            rollback_available=result.rollback_available,
        )
        
    except Exception as e:
        logger.error(f"[REFACTORING-API] Rename failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/move-module", response_model=RefactoringResponse)
async def move_module(request: MoveModuleRequest):
    """
    Move a module to a new location and update all imports.
    
    Updates all import statements across the codebase to reflect
    the new module location.
    """
    try:
        engine = _get_engine()
        
        # Create plan
        plan = engine.plan_move_module(
            source_module=request.source_module,
            target_module=request.target_module,
        )
        
        # Execute plan
        result = engine.execute_plan(plan.plan_id, dry_run=request.dry_run)
        
        return RefactoringResponse(
            success=result.success,
            plan_id=plan.plan_id,
            files_modified=result.files_modified,
            references_updated=result.references_updated,
            affected_files=plan.affected_files,
            errors=result.errors,
            warnings=result.warnings,
            execution_time_ms=result.execution_time_ms,
            rollback_available=result.rollback_available,
        )
        
    except Exception as e:
        logger.error(f"[REFACTORING-API] Move module failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/find-references", response_model=FindReferencesResponse)
async def find_references(request: FindReferencesRequest):
    """
    Find all references to a symbol across the codebase.
    
    Returns locations of all definitions, usages, and imports
    of the specified symbol.
    """
    try:
        engine = _get_engine()
        symbol_type = _get_symbol_type(request.symbol_type)
        
        refs = engine.find_symbol_references(
            symbol_name=request.symbol_name,
            symbol_type=symbol_type,
            scope_file=request.scope_file,
        )
        
        # Convert to response format
        ref_responses = [
            SymbolReferenceResponse(
                file_path=r.file_path,
                line_number=r.line_number,
                column=r.column,
                symbol_name=r.symbol_name,
                symbol_type=r.symbol_type.value,
                context=r.context,
                is_definition=r.is_definition,
                is_import=r.is_import,
            )
            for r in refs
        ]
        
        files_with_refs = list(set(r.file_path for r in refs))
        
        return FindReferencesResponse(
            symbol_name=request.symbol_name,
            total_references=len(refs),
            references=ref_responses,
            files_with_references=files_with_refs,
        )
        
    except Exception as e:
        logger.error(f"[REFACTORING-API] Find references failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plans", response_model=List[PlanStatusResponse])
async def list_plans():
    """List all refactoring plans."""
    try:
        engine = _get_engine()
        plans = engine.list_plans()
        
        return [
            PlanStatusResponse(
                plan_id=p["plan_id"],
                refactoring_type=p["refactoring_type"],
                source_symbol=p["source_symbol"],
                target_symbol=p.get("target_symbol"),
                status=p["status"],
                affected_files_count=p["affected_files_count"],
                references_count=p["references_count"],
                confidence=p["confidence"],
                risk_level=p["risk_level"],
            )
            for p in plans
        ]
        
    except Exception as e:
        logger.error(f"[REFACTORING-API] List plans failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plans/{plan_id}", response_model=PlanStatusResponse)
async def get_plan_status(plan_id: str):
    """Get status of a specific refactoring plan."""
    try:
        engine = _get_engine()
        plan = engine.get_plan_status(plan_id)
        
        if not plan:
            raise HTTPException(status_code=404, detail=f"Plan not found: {plan_id}")
        
        return PlanStatusResponse(
            plan_id=plan["plan_id"],
            refactoring_type=plan["refactoring_type"],
            source_symbol=plan["source_symbol"],
            target_symbol=plan.get("target_symbol"),
            status=plan["status"],
            affected_files_count=plan["affected_files_count"],
            references_count=plan["references_count"],
            confidence=plan["confidence"],
            risk_level=plan["risk_level"],
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[REFACTORING-API] Get plan status failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plans/{plan_id}/rollback")
async def rollback_plan(plan_id: str):
    """Rollback a previously executed refactoring plan."""
    try:
        engine = _get_engine()
        success = engine.rollback_plan(plan_id)
        
        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot rollback plan {plan_id}. Check plan status."
            )
        
        return {"success": True, "message": f"Plan {plan_id} rolled back successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[REFACTORING-API] Rollback failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plans/{plan_id}/execute")
async def execute_plan(
    plan_id: str,
    dry_run: bool = Query(False, description="Simulate without applying"),
    skip_validation: bool = Query(False, description="Skip validation gates"),
):
    """Execute a previously created refactoring plan."""
    try:
        engine = _get_engine()
        result = engine.execute_plan(
            plan_id=plan_id,
            dry_run=dry_run,
            skip_validation=skip_validation,
        )
        
        return RefactoringResponse(
            success=result.success,
            plan_id=plan_id,
            files_modified=result.files_modified,
            references_updated=result.references_updated,
            affected_files=result.plan.affected_files,
            errors=result.errors,
            warnings=result.warnings,
            execution_time_ms=result.execution_time_ms,
            rollback_available=result.rollback_available,
        )
        
    except Exception as e:
        logger.error(f"[REFACTORING-API] Execute plan failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
