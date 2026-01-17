"""
Self-Healing Training API

API endpoints for continuous self-healing training system.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime

from cognitive.self_healing_training_system import (
    get_self_healing_training_system,
    TrainingCycle,
    AlertSource,
    ProblemPerspective,
    TrainingCycleState
)

router = APIRouter(prefix="/self-healing-training", tags=["self-healing-training"])


# ==================== Request/Response Models ====================

class StartTrainingRequest(BaseModel):
    """Request to start training cycle."""
    folder_path: str = Field(..., description="Path to folder with broken code")
    problem_perspective: Optional[str] = Field(None, description="Problem perspective (syntax_errors, logic_errors, etc.)")
    max_cycles: Optional[int] = Field(None, description="Maximum cycles to run (None = infinite)")


class RegisterAlertRequest(BaseModel):
    """Request to register alert."""
    source: str = Field(..., description="Alert source: diagnostic_engine, llm_analyzer, code_analyzer, user_need")
    severity: str = Field(..., description="Severity: low, medium, high, critical")
    description: str = Field(..., description="Alert description")
    affected_files: List[str] = Field(default_factory=list, description="List of affected files")


class TrainingCycleResponse(BaseModel):
    """Response with training cycle details."""
    cycle_id: str
    state: str
    folder_path: str
    problem_perspective: str
    difficulty_level: float
    cycle_number: int
    files_collected: int
    files_fixed: int
    files_failed: int
    alerts_received: int
    knowledge_gained_count: int
    metrics: Dict[str, Any]


class TrainingStatusResponse(BaseModel):
    """Response with training system status."""
    active_cycle: Optional[Dict[str, Any]]
    cycles_completed: int
    total_files_fixed: int
    total_alerts_responded: int
    current_difficulty: float
    folders_trained: List[str]
    config: Dict[str, Any]


# ==================== API Endpoints ====================

@router.get("/status", response_model=TrainingStatusResponse)
async def get_training_status():
    """Get current training system status."""
    try:
        from database.session import get_session
        from pathlib import Path
        
        session = next(get_session())
        kb_path = Path("knowledge_base")
        
        # Import systems
        from cognitive.autonomous_sandbox_lab import get_sandbox_lab
        from cognitive.autonomous_healing_system import get_autonomous_healing, TrustLevel
        from diagnostic_machine.diagnostic_engine import get_diagnostic_engine
        from llm_orchestrator.llm_orchestrator import get_llm_orchestrator
        
        sandbox_lab = get_sandbox_lab()
        healing_system = get_autonomous_healing(session=session, trust_level=TrustLevel.MEDIUM_RISK_AUTO)
        diagnostic_engine = get_diagnostic_engine()
        llm_orchestrator = get_llm_orchestrator(session=session, knowledge_base_path=kb_path)
        
        training_system = get_self_healing_training_system(
            session=session,
            knowledge_base_path=kb_path,
            sandbox_lab=sandbox_lab,
            healing_system=healing_system,
            diagnostic_engine=diagnostic_engine,
            llm_orchestrator=llm_orchestrator
        )
        
        active_cycle = None
        if training_system.current_cycle:
            cycle = training_system.current_cycle
            active_cycle = {
                "cycle_id": cycle.cycle_id,
                "state": cycle.state.value,
                "folder_path": cycle.folder_path,
                "problem_perspective": cycle.problem_perspective.value,
                "difficulty_level": cycle.difficulty_level,
                "cycle_number": cycle.cycle_number,
                "files_collected": len(cycle.files_collected),
                "files_fixed": len(cycle.files_fixed),
                "files_failed": len(cycle.files_failed)
            }
        
        return TrainingStatusResponse(
            active_cycle=active_cycle,
            cycles_completed=training_system.stats["total_cycles"],
            total_files_fixed=training_system.stats["total_files_fixed"],
            total_alerts_responded=training_system.stats["total_alerts_responded"],
            current_difficulty=training_system.stats["current_difficulty"],
            folders_trained=list(training_system.stats["folders_trained"]),
            config=training_system.config
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting training status: {str(e)}")


@router.post("/start", response_model=TrainingCycleResponse)
async def start_training_cycle(request: StartTrainingRequest):
    """Start a new training cycle."""
    try:
        from database.session import get_session
        from pathlib import Path
        
        session = next(get_session())
        kb_path = Path("knowledge_base")
        
        # Import systems
        from cognitive.autonomous_sandbox_lab import get_sandbox_lab
        from cognitive.autonomous_healing_system import get_autonomous_healing, TrustLevel
        from diagnostic_machine.diagnostic_engine import get_diagnostic_engine
        from llm_orchestrator.llm_orchestrator import get_llm_orchestrator
        
        sandbox_lab = get_sandbox_lab()
        healing_system = get_autonomous_healing(session=session, trust_level=TrustLevel.MEDIUM_RISK_AUTO)
        diagnostic_engine = get_diagnostic_engine()
        llm_orchestrator = get_llm_orchestrator(session=session, knowledge_base_path=kb_path)
        
        training_system = get_self_healing_training_system(
            session=session,
            knowledge_base_path=kb_path,
            sandbox_lab=sandbox_lab,
            healing_system=healing_system,
            diagnostic_engine=diagnostic_engine,
            llm_orchestrator=llm_orchestrator
        )
        
        # Determine perspective
        perspective = None
        if request.problem_perspective:
            perspective = ProblemPerspective(request.problem_perspective)
        
        # Start cycle
        cycle = training_system.start_training_cycle(
            folder_path=request.folder_path,
            problem_perspective=perspective
        )
        
        return TrainingCycleResponse(
            cycle_id=cycle.cycle_id,
            state=cycle.state.value,
            folder_path=cycle.folder_path,
            problem_perspective=cycle.problem_perspective.value,
            difficulty_level=cycle.difficulty_level,
            cycle_number=cycle.cycle_number,
            files_collected=len(cycle.files_collected),
            files_fixed=len(cycle.files_fixed),
            files_failed=len(cycle.files_failed),
            alerts_received=len(cycle.alerts_received),
            knowledge_gained_count=len(cycle.knowledge_gained),
            metrics=cycle.metrics
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting training cycle: {str(e)}")


@router.post("/alert")
async def register_alert(request: RegisterAlertRequest):
    """Register an alert that brings Grace out of sandbox."""
    try:
        from database.session import get_session
        from pathlib import Path
        
        session = next(get_session())
        kb_path = Path("knowledge_base")
        
        # Import systems
        from cognitive.autonomous_sandbox_lab import get_sandbox_lab
        from cognitive.autonomous_healing_system import get_autonomous_healing, TrustLevel
        from diagnostic_machine.diagnostic_engine import get_diagnostic_engine
        from llm_orchestrator.llm_orchestrator import get_llm_orchestrator
        
        sandbox_lab = get_sandbox_lab()
        healing_system = get_autonomous_healing(session=session, trust_level=TrustLevel.MEDIUM_RISK_AUTO)
        diagnostic_engine = get_diagnostic_engine()
        llm_orchestrator = get_llm_orchestrator(session=session, knowledge_base_path=kb_path)
        
        training_system = get_self_healing_training_system(
            session=session,
            knowledge_base_path=kb_path,
            sandbox_lab=sandbox_lab,
            healing_system=healing_system,
            diagnostic_engine=diagnostic_engine,
            llm_orchestrator=llm_orchestrator
        )
        
        # Register alert
        alert = training_system.register_alert(
            source=AlertSource(request.source),
            severity=request.severity,
            description=request.description,
            affected_files=request.affected_files
        )
        
        # If alert received, respond to it
        if training_system.current_cycle and training_system.current_cycle.state == TrainingCycleState.ALERTED:
            response = training_system.respond_to_alert(alert)
            return {
                "success": True,
                "alert_id": alert.alert_id,
                "response": response,
                "message": "Alert registered and Grace exited sandbox to fix real system"
            }
        
        return {
            "success": True,
            "alert_id": alert.alert_id,
            "message": "Alert registered, Grace will respond when in sandbox"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error registering alert: {str(e)}")


@router.get("/cycles")
async def get_training_cycles():
    """Get all completed training cycles."""
    try:
        from database.session import get_session
        from pathlib import Path
        
        session = next(get_session())
        kb_path = Path("knowledge_base")
        
        # Import systems
        from cognitive.autonomous_sandbox_lab import get_sandbox_lab
        from cognitive.autonomous_healing_system import get_autonomous_healing, TrustLevel
        from diagnostic_machine.diagnostic_engine import get_diagnostic_engine
        from llm_orchestrator.llm_orchestrator import get_llm_orchestrator
        
        sandbox_lab = get_sandbox_lab()
        healing_system = get_autonomous_healing(session=session, trust_level=TrustLevel.MEDIUM_RISK_AUTO)
        diagnostic_engine = get_diagnostic_engine()
        llm_orchestrator = get_llm_orchestrator(session=session, knowledge_base_path=kb_path)
        
        training_system = get_self_healing_training_system(
            session=session,
            knowledge_base_path=kb_path,
            sandbox_lab=sandbox_lab,
            healing_system=healing_system,
            diagnostic_engine=diagnostic_engine,
            llm_orchestrator=llm_orchestrator
        )
        
        cycles = []
        for cycle in training_system.cycles_completed:
            cycles.append({
                "cycle_id": cycle.cycle_id,
                "state": cycle.state.value,
                "folder_path": cycle.folder_path,
                "problem_perspective": cycle.problem_perspective.value,
                "difficulty_level": cycle.difficulty_level,
                "cycle_number": cycle.cycle_number,
                "files_collected": len(cycle.files_collected),
                "files_fixed": len(cycle.files_fixed),
                "files_failed": len(cycle.files_failed),
                "success_rate": len(cycle.files_fixed) / len(cycle.files_collected) if cycle.files_collected else 0,
                "started_at": cycle.started_at.isoformat(),
                "completed_at": cycle.completed_at.isoformat() if cycle.completed_at else None,
                "metrics": cycle.metrics
            })
        
        return {
            "cycles": cycles,
            "total": len(cycles)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting cycles: {str(e)}")


@router.post("/continuous")
async def start_continuous_training(request: StartTrainingRequest):
    """Start continuous training cycles."""
    try:
        import threading
        
        from database.session import get_session
        from pathlib import Path
        
        session = next(get_session())
        kb_path = Path("knowledge_base")
        
        # Import systems
        from cognitive.autonomous_sandbox_lab import get_sandbox_lab
        from cognitive.autonomous_healing_system import get_autonomous_healing, TrustLevel
        from diagnostic_machine.diagnostic_engine import get_diagnostic_engine
        from llm_orchestrator.llm_orchestrator import get_llm_orchestrator
        
        sandbox_lab = get_sandbox_lab()
        healing_system = get_autonomous_healing(session=session, trust_level=TrustLevel.MEDIUM_RISK_AUTO)
        diagnostic_engine = get_diagnostic_engine()
        llm_orchestrator = get_llm_orchestrator(session=session, knowledge_base_path=kb_path)
        
        training_system = get_self_healing_training_system(
            session=session,
            knowledge_base_path=kb_path,
            sandbox_lab=sandbox_lab,
            healing_system=healing_system,
            diagnostic_engine=diagnostic_engine,
            llm_orchestrator=llm_orchestrator
        )
        
        # Start continuous training in background thread
        def run_continuous():
            training_system.run_continuous_training(
                folder_path=request.folder_path,
                max_cycles=request.max_cycles
            )
        
        thread = threading.Thread(target=run_continuous, daemon=True)
        thread.start()
        
        return {
            "success": True,
            "message": "Continuous training started in background",
            "folder_path": request.folder_path,
            "max_cycles": request.max_cycles
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting continuous training: {str(e)}")
