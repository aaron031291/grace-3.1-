import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from datetime import datetime
from pathlib import Path
from database.session import get_session

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/grace-os", tags=["grace-os"])


class ActionRequest(BaseModel):
    """Request for executing an action."""
    action_type: str = Field(..., description="Type of action to execute")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    source: str = Field(default="api")


class TaskRequest(BaseModel):
    """Request for scheduling a task."""
    task_type: str = Field(..., description="Type of task")
    description: str = Field(..., description="Task description")
    priority: str = Field(default="normal")
    parameters: Dict[str, Any] = Field(default_factory=dict)


class VoiceCommandRequest(BaseModel):
    """Voice command request."""
    transcript: str = Field(..., description="Voice transcript")
    confidence: float = Field(default=1.0)


class NaturalLanguageRequest(BaseModel):
    """Natural language input request."""
    text: str = Field(..., description="Natural language text")


class SelfUpdateRequest(BaseModel):
    """Self-update request."""
    update_type: str = Field(default="patch")
    description: str = Field(..., description="Update description")
    target_files: list = Field(default_factory=list)


class LearningFeedbackRequest(BaseModel):
    """Learning feedback request."""
    feedback: str = Field(..., description="Feedback text")
    example: Optional[str] = Field(default=None)


# =============================================================================
# Core Endpoints
# =============================================================================

@router.get("/status")
async def get_status(session=Depends(get_session)):
    """Get Grace OS status and all connected systems."""
    try:
        from genesis_ide.core_integration import GenesisIDECore
        core = GenesisIDECore(session=session)
        await core.initialize()
        return core.get_status()
    except Exception as e:
        logger.error(f"[GRACE-OS-API] Status error: {e}")
        return {"error": str(e), "status": "degraded"}


@router.get("/metrics")
async def get_metrics(session=Depends(get_session)):
    """Get comprehensive Grace OS metrics."""
    try:
        from genesis_ide.core_integration import GenesisIDECore
        core = GenesisIDECore(session=session)
        await core.initialize()
        return core.get_metrics()
    except Exception as e:
        return {"error": str(e)}


# =============================================================================
# Session Management
# =============================================================================

@router.post("/session/start")
async def start_session(
    user_id: Optional[str] = None,
    session=Depends(get_session)
):
    """Start a new IDE session with full tracking."""
    try:
        from genesis_ide.core_integration import GenesisIDECore
        core = GenesisIDECore(session=session)
        await core.initialize()
        ide_session = await core.start_session(user_id=user_id)
        return ide_session.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/end")
async def end_session(session=Depends(get_session)):
    """End the current IDE session."""
    try:
        from genesis_ide.core_integration import GenesisIDECore
        core = GenesisIDECore(session=session)
        await core.initialize()
        return await core.end_session()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Action Execution
# =============================================================================

@router.post("/action")
async def execute_action(
    request: ActionRequest,
    session=Depends(get_session)
):
    """Execute any action through the unified interface."""
    try:
        from genesis_ide.core_integration import GenesisIDECore
        core = GenesisIDECore(session=session)
        await core.initialize()
        return await core.execute_action(
            action_type=request.action_type,
            parameters=request.parameters,
            source=request.source
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Autonomous Tasks
# =============================================================================

@router.post("/task/schedule")
async def schedule_task(
    request: TaskRequest,
    background_tasks: BackgroundTasks,
    session=Depends(get_session)
):
    """Schedule an autonomous task."""
    try:
        from grace_os.autonomous_scheduler import AutonomousTaskScheduler, TaskType, TaskPriority

        scheduler = AutonomousTaskScheduler(session=session)
        await scheduler.start()

        # Map string to enum
        task_type_map = {
            "code_generation": TaskType.CODE_GENERATION,
            "healing": TaskType.HEALING,
            "refactor": TaskType.REFACTOR,
            "test": TaskType.TEST,
            "build": TaskType.BUILD,
            "research": TaskType.RESEARCH,
            "learning": TaskType.LEARNING
        }
        priority_map = {
            "critical": TaskPriority.CRITICAL,
            "high": TaskPriority.HIGH,
            "normal": TaskPriority.NORMAL,
            "low": TaskPriority.LOW
        }

        task_type = task_type_map.get(request.task_type, TaskType.CUSTOM)
        priority = priority_map.get(request.priority, TaskPriority.NORMAL)

        task = scheduler.schedule_task(
            task_type=task_type,
            description=request.description,
            parameters=request.parameters,
            priority=priority
        )

        return task.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/task/{task_id}")
async def get_task(task_id: str, session=Depends(get_session)):
    """Get task status."""
    try:
        from grace_os.autonomous_scheduler import AutonomousTaskScheduler
        scheduler = AutonomousTaskScheduler(session=session)
        task = scheduler.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return task.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks")
async def get_all_tasks(session=Depends(get_session)):
    """Get all tasks."""
    try:
        from grace_os.autonomous_scheduler import AutonomousTaskScheduler
        scheduler = AutonomousTaskScheduler(session=session)
        return scheduler.get_all_tasks()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Voice/NLP
# =============================================================================

@router.post("/voice/command")
async def process_voice_command(
    request: VoiceCommandRequest,
    session=Depends(get_session)
):
    """Process a voice command."""
    try:
        from grace_os.autonomous_scheduler import AutonomousTaskScheduler
        scheduler = AutonomousTaskScheduler(session=session)
        await scheduler.start()
        return await scheduler.process_voice_command(request.transcript)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/nl/process")
async def process_natural_language(
    request: NaturalLanguageRequest,
    session=Depends(get_session)
):
    """Process natural language input."""
    try:
        from grace_os.nocode_panels import NoCodePanelSystem
        panels = NoCodePanelSystem(session=session)
        return await panels.process_natural_language(request.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# No-Code Panels
# =============================================================================

@router.get("/panels")
async def get_panels(session=Depends(get_session)):
    """Get all available panels."""
    try:
        from grace_os.nocode_panels import NoCodePanelSystem
        panels = NoCodePanelSystem(session=session)
        return panels.get_all_panels()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard")
async def get_dashboard(session=Depends(get_session)):
    """Get complete dashboard layout."""
    try:
        from grace_os.nocode_panels import NoCodePanelSystem
        panels = NoCodePanelSystem(session=session)
        return panels.get_dashboard_layout()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dashboard/refresh")
async def refresh_dashboard(session=Depends(get_session)):
    """Refresh dashboard data."""
    try:
        from grace_os.nocode_panels import NoCodePanelSystem
        panels = NoCodePanelSystem(session=session)
        return await panels.refresh_dashboard_data()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Coding Agent Integration (IDE)
# =============================================================================

@router.post("/coding/generate")
async def ide_generate_code(
    request: Dict[str, Any],
    session=Depends(get_session)
):
    """
    IDE endpoint: Generate code with LLM reasoning and coding assistance.
    
    Allows IDE to request code generation with full reasoning support.
    """
    try:
        from cognitive.enterprise_coding_agent import get_enterprise_coding_agent, CodingTaskType
        from cognitive.autonomous_healing_system import TrustLevel
        from pathlib import Path
        
        coding_agent = get_enterprise_coding_agent(
            session=session,
            repo_path=Path.cwd(),
            enable_learning=True,
            enable_sandbox=True
        )
        
        # Create task
        task_type = CodingTaskType(request.get("task_type", "code_generation"))
        task = coding_agent.create_task(
            task_type=task_type,
            description=request.get("description", ""),
            target_files=request.get("target_files", []),
            requirements=request.get("requirements", {}),
            context=request.get("context", {}),
            priority=request.get("priority", "medium"),
            trust_level_required=TrustLevel(request.get("trust_level", 3))
        )
        
        # Execute with reasoning
        result = coding_agent.execute_task(task.task_id)
        
        return {
            "success": result.get("success", False),
            "task_id": task.task_id,
            "result": result,
            "reasoning": result.get("decision", {}),
            "knowledge_used": result.get("knowledge_used", {})
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Code generation error: {str(e)}")


@router.post("/coding/reason")
async def ide_reason_about_code(
    request: Dict[str, Any],
    session=Depends(get_session)
):
    """
    IDE endpoint: LLM reasoning about code.
    
    Allows IDE to get reasoning/explanation about code.
    """
    try:
        from llm_orchestrator.llm_orchestrator import get_llm_orchestrator, TaskType
        from pathlib import Path
        
        llm_orchestrator = get_llm_orchestrator(
            session=session,
            knowledge_base_path=Path("knowledge_base")
        )
        
        # Execute reasoning task
        reasoning_result = llm_orchestrator.execute_task(
            prompt=request.get("prompt", ""),
            task_type=TaskType.REASONING,
            user_id=request.get("user_id"),
            require_verification=True,
            require_grounding=True,
            context_documents=request.get("context_files", [])
        )
        
        return {
            "success": True,
            "reasoning": reasoning_result.content,
            "confidence": reasoning_result.confidence_score,
            "trust_score": reasoning_result.trust_score,
            "sources": reasoning_result.sources
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reasoning error: {str(e)}")


@router.post("/coding/assist")
async def ide_coding_assistance(
    request: Dict[str, Any],
    session=Depends(get_session)
):
    """
    IDE endpoint: Comprehensive coding assistance with LLM reasoning.
    
    Combines:
    - Code generation
    - Reasoning about code
    - Code analysis
    - Suggestions
    """
    try:
        from cognitive.enterprise_coding_agent import get_enterprise_coding_agent, CodingTaskType
        from llm_orchestrator.llm_orchestrator import get_llm_orchestrator, TaskType
        from pathlib import Path
        
        coding_agent = get_enterprise_coding_agent(
            session=session,
            repo_path=Path.cwd(),
            enable_learning=True,
            enable_sandbox=True
        )
        
        llm_orchestrator = get_llm_orchestrator(
            session=session,
            knowledge_base_path=Path("knowledge_base")
        )
        
        user_query = request.get("query", "")
        file_path = request.get("file_path", "")
        code_context = request.get("code_context", "")
        
        # Step 1: Reasoning about the request
        reasoning_prompt = f"""
        User wants: {user_query}
        File: {file_path}
        Current code context:
        ```python
        {code_context[:1000]}
        ```
        
        Analyze and reason about:
        1. What the user is trying to accomplish
        2. What code changes are needed
        3. Best approach to implement
        4. Potential issues to consider
        """
        
        reasoning_result = llm_orchestrator.execute_task(
            prompt=reasoning_prompt,
            task_type=TaskType.REASONING,
            require_verification=True
        )
        
        # Step 2: Generate code based on reasoning
        code_generation_prompt = f"""
        Based on this reasoning:
        {reasoning_result.content}
        
        Generate the code to implement: {user_query}
        """
        
        # Determine task type
        task_type_str = request.get("task_type", "code_generation")
        task_type = CodingTaskType(task_type_str)
        
        task = coding_agent.create_task(
            task_type=task_type,
            description=user_query,
            target_files=[file_path] if file_path else [],
            requirements={
                "reasoning": reasoning_result.content,
                "approach": reasoning_result.content
            },
            context={
                "code_context": code_context,
                "reasoning": reasoning_result.content
            }
        )
        
        code_result = coding_agent.execute_task(task.task_id)
        
        return {
            "success": code_result.get("success", False),
            "reasoning": {
                "analysis": reasoning_result.content,
                "confidence": reasoning_result.confidence_score,
                "trust_score": reasoning_result.trust_score
            },
            "code_generation": {
                "task_id": task.task_id,
                "result": code_result,
                "code": code_result.get("generation", {}).get("code_after", "") if code_result.get("generation") else ""
            },
            "suggestions": code_result.get("review_result", {}).get("analysis", {})
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Coding assistance error: {str(e)}")


@router.post("/coding/fix")
async def ide_fix_code(
    request: Dict[str, Any],
    session=Depends(get_session)
):
    """
    IDE endpoint: Fix code with reasoning.
    
    Uses coding agent to fix code issues with LLM reasoning.
    """
    try:
        from cognitive.enterprise_coding_agent import get_enterprise_coding_agent, CodingTaskType
        from pathlib import Path
        
        coding_agent = get_enterprise_coding_agent(
            session=session,
            repo_path=Path.cwd(),
            enable_learning=True,
            enable_sandbox=True
        )
        
        file_path = request.get("file_path", "")
        issue_description = request.get("issue_description", "")
        error_message = request.get("error_message", "")
        
        # Create fix task
        task = coding_agent.create_task(
            task_type=CodingTaskType.CODE_FIX,
            description=f"Fix: {issue_description}",
            target_files=[file_path] if file_path else [],
            requirements={
                "error_message": error_message,
                "issue_description": issue_description
            },
            context={
                "error": error_message,
                "issue": issue_description
            },
            priority="high"
        )
        
        result = coding_agent.execute_task(task.task_id)
        
        return {
            "success": result.get("success", False),
            "task_id": task.task_id,
            "result": result,
            "fixed_code": result.get("generation", {}).get("code_after", "") if result.get("generation") else ""
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Code fix error: {str(e)}")


@router.post("/coding/explain")
async def ide_explain_code(
    request: Dict[str, Any],
    session=Depends(get_session)
):
    """
    IDE endpoint: Explain code with LLM reasoning.
    
    Provides reasoning and explanation about code.
    """
    try:
        from llm_orchestrator.llm_orchestrator import get_llm_orchestrator, TaskType
        from pathlib import Path
        
        llm_orchestrator = get_llm_orchestrator(
            session=session,
            knowledge_base_path=Path("knowledge_base")
        )
        
        code = request.get("code", "")
        file_path = request.get("file_path", "")
        question = request.get("question", "Explain this code")
        
        prompt = f"""
        {question}
        
        Code from {file_path}:
        ```python
        {code}
        ```
        
        Provide:
        1. What this code does
        2. How it works
        3. Key concepts
        4. Potential improvements
        """
        
        result = llm_orchestrator.execute_task(
            prompt=prompt,
            task_type=TaskType.CODE_EXPLANATION,
            require_verification=True
        )
        
        return {
            "success": True,
            "explanation": result.content,
            "confidence": result.confidence_score,
            "trust_score": result.trust_score
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Code explanation error: {str(e)}")


@router.get("/coding/agent/status")
async def ide_coding_agent_status(session=Depends(get_session)):
    """Get coding agent status for IDE."""
    try:
        from cognitive.enterprise_coding_agent import get_enterprise_coding_agent
        from pathlib import Path
        
        coding_agent = get_enterprise_coding_agent(
            session=session,
            repo_path=Path.cwd(),
            enable_learning=True,
            enable_sandbox=True
        )
        
        health = coding_agent.get_health_status()
        metrics = coding_agent.get_metrics()
        learning = coding_agent.get_learning_connections()
        
        return {
            "health": health,
            "metrics": {
                "total_tasks": metrics.total_tasks,
                "tasks_completed": metrics.tasks_completed,
                "code_generated": metrics.code_generated,
                "learning_cycles": metrics.learning_cycles
            },
            "learning": learning
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status error: {str(e)}")


# =============================================================================
# Coding Agent Integration (IDE)
# =============================================================================

@router.post("/coding/generate")
async def ide_generate_code(
    request: Dict[str, Any],
    session=Depends(get_session)
):
    """
    IDE endpoint: Generate code with LLM reasoning and coding assistance.
    
    Allows IDE to request code generation with full reasoning support.
    """
    try:
        from cognitive.enterprise_coding_agent import get_enterprise_coding_agent, CodingTaskType
        from cognitive.autonomous_healing_system import TrustLevel
        from pathlib import Path
        
        coding_agent = get_enterprise_coding_agent(
            session=session,
            repo_path=Path.cwd(),
            enable_learning=True,
            enable_sandbox=True
        )
        
        # Create task
        task_type = CodingTaskType(request.get("task_type", "code_generation"))
        task = coding_agent.create_task(
            task_type=task_type,
            description=request.get("description", ""),
            target_files=request.get("target_files", []),
            requirements=request.get("requirements", {}),
            context=request.get("context", {}),
            priority=request.get("priority", "medium"),
            trust_level_required=TrustLevel(request.get("trust_level", 3))
        )
        
        # Execute with reasoning
        result = coding_agent.execute_task(task.task_id)
        
        return {
            "success": result.get("success", False),
            "task_id": task.task_id,
            "result": result,
            "reasoning": result.get("decision", {}),
            "knowledge_used": result.get("knowledge_used", {})
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Code generation error: {str(e)}")


@router.post("/coding/reason")
async def ide_reason_about_code(
    request: Dict[str, Any],
    session=Depends(get_session)
):
    """
    IDE endpoint: LLM reasoning about code.
    
    Allows IDE to get reasoning/explanation about code.
    """
    try:
        from llm_orchestrator.llm_orchestrator import get_llm_orchestrator, TaskType
        from pathlib import Path
        
        llm_orchestrator = get_llm_orchestrator(
            session=session,
            knowledge_base_path=Path("knowledge_base")
        )
        
        # Execute reasoning task
        reasoning_result = llm_orchestrator.execute_task(
            prompt=request.get("prompt", ""),
            task_type=TaskType.REASONING,
            user_id=request.get("user_id"),
            require_verification=True,
            require_grounding=True,
            context_documents=request.get("context_files", [])
        )
        
        return {
            "success": True,
            "reasoning": reasoning_result.content,
            "confidence": reasoning_result.confidence_score,
            "trust_score": reasoning_result.trust_score,
            "sources": reasoning_result.sources
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reasoning error: {str(e)}")


@router.post("/coding/assist")
async def ide_coding_assistance(
    request: Dict[str, Any],
    session=Depends(get_session)
):
    """
    IDE endpoint: Comprehensive coding assistance with LLM reasoning.
    
    Combines:
    - Code generation
    - Reasoning about code
    - Code analysis
    - Suggestions
    """
    try:
        from cognitive.enterprise_coding_agent import get_enterprise_coding_agent, CodingTaskType
        from llm_orchestrator.llm_orchestrator import get_llm_orchestrator, TaskType
        from pathlib import Path
        
        coding_agent = get_enterprise_coding_agent(
            session=session,
            repo_path=Path.cwd(),
            enable_learning=True,
            enable_sandbox=True
        )
        
        llm_orchestrator = get_llm_orchestrator(
            session=session,
            knowledge_base_path=Path("knowledge_base")
        )
        
        user_query = request.get("query", "")
        file_path = request.get("file_path", "")
        code_context = request.get("code_context", "")
        
        # Step 1: Reasoning about the request
        reasoning_prompt = f"""
        User wants: {user_query}
        File: {file_path}
        Current code context:
        ```python
        {code_context[:1000]}
        ```
        
        Analyze and reason about:
        1. What the user is trying to accomplish
        2. What code changes are needed
        3. Best approach to implement
        4. Potential issues to consider
        """
        
        reasoning_result = llm_orchestrator.execute_task(
            prompt=reasoning_prompt,
            task_type=TaskType.REASONING,
            require_verification=True
        )
        
        # Step 2: Generate code based on reasoning
        # Determine task type
        task_type_str = request.get("task_type", "code_generation")
        task_type = CodingTaskType(task_type_str)
        
        task = coding_agent.create_task(
            task_type=task_type,
            description=user_query,
            target_files=[file_path] if file_path else [],
            requirements={
                "reasoning": reasoning_result.content,
                "approach": reasoning_result.content
            },
            context={
                "code_context": code_context,
                "reasoning": reasoning_result.content
            }
        )
        
        code_result = coding_agent.execute_task(task.task_id)
        
        return {
            "success": code_result.get("success", False),
            "reasoning": {
                "analysis": reasoning_result.content,
                "confidence": reasoning_result.confidence_score,
                "trust_score": reasoning_result.trust_score
            },
            "code_generation": {
                "task_id": task.task_id,
                "result": code_result,
                "code": code_result.get("generation", {}).get("code_after", "") if code_result.get("generation") else ""
            },
            "suggestions": code_result.get("review_result", {}).get("analysis", {})
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Coding assistance error: {str(e)}")


@router.post("/coding/fix")
async def ide_fix_code(
    request: Dict[str, Any],
    session=Depends(get_session)
):
    """
    IDE endpoint: Fix code with reasoning.
    
    Uses coding agent to fix code issues with LLM reasoning.
    """
    try:
        from cognitive.enterprise_coding_agent import get_enterprise_coding_agent, CodingTaskType
        from pathlib import Path
        
        coding_agent = get_enterprise_coding_agent(
            session=session,
            repo_path=Path.cwd(),
            enable_learning=True,
            enable_sandbox=True
        )
        
        file_path = request.get("file_path", "")
        issue_description = request.get("issue_description", "")
        error_message = request.get("error_message", "")
        
        # Create fix task
        task = coding_agent.create_task(
            task_type=CodingTaskType.CODE_FIX,
            description=f"Fix: {issue_description}",
            target_files=[file_path] if file_path else [],
            requirements={
                "error_message": error_message,
                "issue_description": issue_description
            },
            context={
                "error": error_message,
                "issue": issue_description
            },
            priority="high"
        )
        
        result = coding_agent.execute_task(task.task_id)
        
        return {
            "success": result.get("success", False),
            "task_id": task.task_id,
            "result": result,
            "fixed_code": result.get("generation", {}).get("code_after", "") if result.get("generation") else ""
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Code fix error: {str(e)}")


@router.post("/coding/explain")
async def ide_explain_code(
    request: Dict[str, Any],
    session=Depends(get_session)
):
    """
    IDE endpoint: Explain code with LLM reasoning.
    
    Provides reasoning and explanation about code.
    """
    try:
        from llm_orchestrator.llm_orchestrator import get_llm_orchestrator, TaskType
        from pathlib import Path
        
        llm_orchestrator = get_llm_orchestrator(
            session=session,
            knowledge_base_path=Path("knowledge_base")
        )
        
        code = request.get("code", "")
        file_path = request.get("file_path", "")
        question = request.get("question", "Explain this code")
        
        prompt = f"""
        {question}
        
        Code from {file_path}:
        ```python
        {code}
        ```
        
        Provide:
        1. What this code does
        2. How it works
        3. Key concepts
        4. Potential improvements
        """
        
        result = llm_orchestrator.execute_task(
            prompt=prompt,
            task_type=TaskType.CODE_EXPLANATION,
            require_verification=True
        )
        
        return {
            "success": True,
            "explanation": result.content,
            "confidence": result.confidence_score,
            "trust_score": result.trust_score
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Code explanation error: {str(e)}")


@router.get("/coding/agent/status")
async def ide_coding_agent_status(session=Depends(get_session)):
    """Get coding agent status for IDE."""
    try:
        from cognitive.enterprise_coding_agent import get_enterprise_coding_agent
        from pathlib import Path
        
        coding_agent = get_enterprise_coding_agent(
            session=session,
            repo_path=Path.cwd(),
            enable_learning=True,
            enable_sandbox=True
        )
        
        health = coding_agent.get_health_status()
        metrics = coding_agent.get_metrics()
        learning = coding_agent.get_learning_connections()
        
        return {
            "health": health,
            "metrics": {
                "total_tasks": metrics.total_tasks,
                "tasks_completed": metrics.tasks_completed,
                "code_generated": metrics.code_generated,
                "learning_cycles": metrics.learning_cycles
            },
            "learning": learning
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status error: {str(e)}")


# =============================================================================
# Healing
# =============================================================================

@router.post("/healing/check")
async def check_health(session=Depends(get_session)):
    """Check system health."""
    try:
        from cognitive.autonomous_healing_system import AutonomousHealingSystem
        healer = AutonomousHealingSystem(session=session)
        return healer.assess_system_health()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/healing/file")
async def heal_file(
    file_path: str,
    session=Depends(get_session)
):
    """Heal a specific file."""
    try:
        from grace_os.ide_bridge import IDEBridge, IDEBridgeConfig
        config = IDEBridgeConfig(workspace_path=Path.cwd())
        bridge = IDEBridge(config, session=session)
        await bridge.initialize()
        return await bridge.request_healing(file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Ghost Ledger
# =============================================================================

@router.get("/ghost-ledger/history/{file_path:path}")
async def get_ghost_history(file_path: str, session=Depends(get_session)):
    """Get ghost ledger history for a file."""
    try:
        from grace_os.ghost_ledger import GhostLedger
        ledger = GhostLedger(session=session)
        return ledger.get_file_history(file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ghost-ledger/recent")
async def get_recent_changes(limit: int = 100, session=Depends(get_session)):
    """Get recent ghost ledger changes."""
    try:
        from grace_os.ghost_ledger import GhostLedger
        ledger = GhostLedger(session=session)
        return ledger.get_recent_changes(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ghost-ledger/stats")
async def get_ghost_stats(session=Depends(get_session)):
    """Get ghost ledger statistics."""
    try:
        from grace_os.ghost_ledger import GhostLedger
        ledger = GhostLedger(session=session)
        return ledger.get_statistics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Reasoning
# =============================================================================

@router.post("/reasoning/analyze")
async def analyze_with_reasoning(
    query: str,
    target_path: Optional[str] = None,
    session=Depends(get_session)
):
    """Analyze using multi-plane reasoning."""
    try:
        from grace_os.reasoning_planes import MultiPlaneReasoner
        reasoner = MultiPlaneReasoner(session=session)
        await reasoner.initialize()
        return await reasoner.reason(query=query, target_path=target_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reasoning/explain")
async def explain_code(
    query: str,
    target: Optional[str] = None,
    session=Depends(get_session)
):
    """Explain code using reasoning."""
    try:
        from grace_os.reasoning_planes import MultiPlaneReasoner
        reasoner = MultiPlaneReasoner(session=session)
        await reasoner.initialize()
        return await reasoner.explain(target=target, query=query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Cognitive Framework
# =============================================================================

@router.post("/cognitive/analyze")
async def cognitive_analyze(
    problem: str,
    session=Depends(get_session)
):
    """Analyze a problem using cognitive framework."""
    try:
        from genesis_ide.cognitive_ide import CognitiveIDEFramework
        cognitive = CognitiveIDEFramework(session=session)
        return await cognitive.analyze(problem)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cognitive/roadmap")
async def create_roadmap(
    goal: str,
    session=Depends(get_session)
):
    """Create a roadmap for a goal."""
    try:
        from genesis_ide.cognitive_ide import CognitiveIDEFramework
        cognitive = CognitiveIDEFramework(session=session)
        return cognitive.create_roadmap(goal)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Learning
# =============================================================================

@router.post("/learning/feedback")
async def submit_feedback(
    request: LearningFeedbackRequest,
    session=Depends(get_session)
):
    """Submit learning feedback."""
    try:
        from genesis_ide.failure_learning import FailureLearningSystem
        learning = FailureLearningSystem(session=session)
        return await learning.store_learning(
            feedback=request.feedback,
            example=request.example
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/learning/status")
async def get_learning_status(session=Depends(get_session)):
    """Get learning system status."""
    try:
        from genesis_ide.failure_learning import FailureLearningSystem
        learning = FailureLearningSystem(session=session)
        return learning.get_learning_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/learning/failures")
async def get_recent_failures(limit: int = 10, session=Depends(get_session)):
    """Get recent failures."""
    try:
        from genesis_ide.failure_learning import FailureLearningSystem
        learning = FailureLearningSystem(session=session)
        return learning.get_recent_failures(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Self-Update
# =============================================================================

@router.post("/self-update")
async def perform_self_update(
    request: SelfUpdateRequest,
    session=Depends(get_session)
):
    """Perform a self-update."""
    try:
        from genesis_ide.self_updater import SelfUpdater
        updater = SelfUpdater(session=session)
        return await updater.perform_update(
            update_type=request.update_type,
            description=request.description,
            target_files=request.target_files
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/self-update/analyze")
async def analyze_codebase(session=Depends(get_session)):
    """Analyze codebase for self-update opportunities."""
    try:
        from genesis_ide.self_updater import SelfUpdater
        updater = SelfUpdater(session=session)
        return await updater.analyze_codebase()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/self-update/suggest")
async def suggest_update(session=Depends(get_session)):
    """Get suggested self-update."""
    try:
        from genesis_ide.self_updater import SelfUpdater
        updater = SelfUpdater(session=session)
        return await updater.suggest_update()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/self-update/history")
async def get_update_history(limit: int = 20, session=Depends(get_session)):
    """Get self-update history."""
    try:
        from genesis_ide.self_updater import SelfUpdater
        updater = SelfUpdater(session=session)
        return updater.get_update_history(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Mutations
# =============================================================================

@router.get("/mutations/file/{file_path:path}")
async def get_file_mutations(file_path: str, session=Depends(get_session)):
    """Get mutation history for a file."""
    try:
        from genesis_ide.mutation_tracker import MutationTracker
        tracker = MutationTracker(session=session)
        return tracker.get_file_history(file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mutations/recent")
async def get_recent_mutations(limit: int = 20, session=Depends(get_session)):
    """Get recent mutations."""
    try:
        from genesis_ide.mutation_tracker import MutationTracker
        tracker = MutationTracker(session=session)
        return tracker.get_recent_mutations(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mutations/revert/{mutation_id}")
async def revert_mutation(mutation_id: str, session=Depends(get_session)):
    """Revert a mutation."""
    try:
        from genesis_ide.mutation_tracker import MutationTracker
        tracker = MutationTracker(session=session)
        return await tracker.revert_mutation(mutation_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Clarity Framework
# =============================================================================

@router.get("/clarity/report")
async def get_clarity_report(session=Depends(get_session)):
    """Get clarity report."""
    try:
        from genesis_ide.clarity_framework import ClarityFramework
        clarity = ClarityFramework(session=session)
        return clarity.generate_clarity_report()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clarity/contexts")
async def get_active_contexts(session=Depends(get_session)):
    """Get active clarity contexts."""
    try:
        from genesis_ide.clarity_framework import ClarityFramework
        clarity = ClarityFramework(session=session)
        return clarity.get_active_contexts()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
