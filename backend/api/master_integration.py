"""
Master Integration API

Single unified API for Grace's complete autonomous system.
ALL systems integrated and accessible through one endpoint.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from pathlib import Path

from cognitive.autonomous_master_integration import get_master_integration
from database.session import initialize_session_factory
from settings import KNOWLEDGE_BASE_PATH

router = APIRouter(prefix="/grace", tags=["master-integration"])


# ======================================================================
# Request/Response Models
# ======================================================================

class UnifiedInputRequest(BaseModel):
    """Unified input request - handles ALL types of input."""
    input_data: Any
    input_type: str  # user_input, file_upload, learning_memory, etc.
    user_id: Optional[str] = None
    metadata: Optional[Dict] = None


class FileInputRequest(BaseModel):
    """File upload request."""
    content: bytes
    name: str
    type: str
    user_id: Optional[str] = None


class UserQueryRequest(BaseModel):
    """User query request."""
    query: str
    user_id: Optional[str] = None
    request_verification: bool = False  # Request multi-LLM verification


# ======================================================================
# MASTER ENDPOINTS
# ======================================================================

@router.post("/start")
async def start_grace() -> Dict[str, Any]:
    """
    **Start Grace's Complete Autonomous System**

    Initializes and connects ALL systems:
    - Layer 1 (Trust & Truth Foundation)
    - Genesis Keys (Audit Trail)
    - Autonomous Triggers
    - Learning Subagents (8 processes)
    - Memory Mesh (Pattern Analysis)
    - Multi-LLM Orchestration

    **Returns:**
    Complete system status with all components.

    **Example:**
    ```bash
    curl -X POST http://localhost:8000/grace/start
    ```
    """
    try:
        session_factory = initialize_session_factory()
        session = session_factory()

        master = get_master_integration(
            session=session,
            knowledge_base_path=Path(KNOWLEDGE_BASE_PATH),
            enable_learning=True,
            enable_multi_llm=True,
            auto_initialize=True
        )

        status = master.get_complete_system_status()

        return {
            "status": "running",
            "message": "Grace's complete autonomous system is operational",
            "systems": status
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start Grace: {str(e)}")


@router.get("/status")
async def get_grace_status() -> Dict[str, Any]:
    """
    **Get Complete System Status**

    Returns status of ALL integrated systems:
    - Master integration statistics
    - Layer 1 input processing
    - Genesis Key tracking
    - Autonomous trigger activity
    - Learning orchestrator (8 processes)
    - Memory mesh analysis
    - Multi-LLM verification

    **Example:**
    ```bash
    curl http://localhost:8000/grace/status
    ```
    """
    try:
        session_factory = initialize_session_factory()
        session = session_factory()

        master = get_master_integration(session=session, auto_initialize=False)

        if not master.layer1:
            return {
                "status": "not_initialized",
                "message": "Grace not started. Call POST /grace/start first"
            }

        status = master.get_complete_system_status()

        return {
            "status": "operational",
            "systems": status
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


@router.post("/input")
async def process_unified_input(request: UnifiedInputRequest) -> Dict[str, Any]:
    """
    **Unified Input Processor - ALL inputs flow through here**

    Single endpoint for ALL types of input:
    - user_input (questions, commands)
    - file_upload (documents, code)
    - learning_memory (training data)
    - external_api (third-party data)
    - system_event (internal events)

    **Flow:**
    1. Input → Layer 1
    2. Genesis Key created
    3. Autonomous triggers evaluated
    4. Learning tasks spawned (if applicable)
    5. Multi-LLM verification (if low confidence)
    6. Results returned

    **Example:**
    ```bash
    curl -X POST http://localhost:8000/grace/input \\
      -H "Content-Type: application/json" \\
      -d '{
        "input_data": "What is the best database for high writes?",
        "input_type": "user_input",
        "user_id": "user-123"
      }'
    ```
    """
    try:
        session_factory = initialize_session_factory()
        session = session_factory()

        master = get_master_integration(session=session)

        result = master.process_input(
            input_data=request.input_data,
            input_type=request.input_type,
            user_id=request.user_id,
            metadata=request.metadata
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process input: {str(e)}")


@router.post("/query")
async def ask_grace(request: UserQueryRequest) -> Dict[str, Any]:
    """
    **Ask Grace a Question**

    Convenience endpoint for user queries.
    Automatically routes through complete autonomous system.

    **Features:**
    - Automatic Genesis Key creation
    - Autonomous trigger evaluation
    - Multi-LLM verification (if requested or low confidence)
    - Memory mesh pattern matching
    - Complete audit trail

    **Example:**
    ```bash
    curl -X POST http://localhost:8000/grace/query \\
      -H "Content-Type: application/json" \\
      -d '{
        "query": "Explain quantum entanglement",
        "request_verification": true
      }'
    ```
    """
    try:
        session_factory = initialize_session_factory()
        session = session_factory()

        master = get_master_integration(session=session)

        # Add verification flag to metadata
        metadata = {
            "request_verification": request.request_verification
        }

        result = master.process_input(
            input_data=request.query,
            input_type="user_input",
            user_id=request.user_id,
            metadata=metadata
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process query: {str(e)}")


@router.post("/proactive-cycle")
async def run_proactive_cycle() -> Dict[str, Any]:
    """
    **Run Proactive Monitoring Cycle**

    Triggers proactive autonomous operations:
    - Check memory mesh for learning gaps
    - Review recursive self-improvement loops
    - Monitor learning task queues
    - Identify contradictions
    - Suggest high-value learning topics

    **This should be called periodically (e.g., every minute) for fully autonomous operation.**

    **Example:**
    ```bash
    curl -X POST http://localhost:8000/grace/proactive-cycle
    ```
    """
    try:
        session_factory = initialize_session_factory()
        session = session_factory()

        master = get_master_integration(session=session)

        result = master.run_proactive_cycle()

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run proactive cycle: {str(e)}")


@router.get("/health")
async def grace_health_check() -> Dict[str, Any]:
    """
    **Grace Health Check**

    Quick health check of all integrated systems.

    **Returns:**
    - Overall health status
    - Component health
    - Error flags
    """
    try:
        session_factory = initialize_session_factory()
        session = session_factory()

        master = get_master_integration(session=session, auto_initialize=False)

        health = {
            "overall": "healthy",
            "components": {
                "layer1": master.layer1 is not None,
                "trigger_pipeline": master.trigger_pipeline is not None,
                "learning_orchestrator": master.learning_orchestrator is not None,
                "memory_learner": master.memory_learner is not None
            }
        }

        # Check if any component is missing
        if not all(health['components'].values()):
            health['overall'] = "degraded"
            health['message'] = "Some components not initialized. Call POST /grace/start"

        return health

    except Exception as e:
        return {
            "overall": "unhealthy",
            "error": str(e)
        }


@router.post("/shutdown")
async def shutdown_grace() -> Dict[str, Any]:
    """
    **Gracefully Shutdown Grace**

    Stops all autonomous processes:
    - Learning subagents (8 processes)
    - Proactive file watching
    - Background tasks

    **Example:**
    ```bash
    curl -X POST http://localhost:8000/grace/shutdown
    ```
    """
    try:
        session_factory = initialize_session_factory()
        session = session_factory()

        master = get_master_integration(session=session, auto_initialize=False)

        if master.layer1:
            master.shutdown()
            return {
                "status": "shutdown",
                "message": "Grace stopped gracefully"
            }
        else:
            return {
                "status": "not_running",
                "message": "Grace was not running"
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to shutdown: {str(e)}")


# ======================================================================
# CONVENIENCE ENDPOINTS
# ======================================================================

@router.get("/learning-suggestions")
async def get_learning_suggestions() -> Dict[str, Any]:
    """
    **Get Proactive Learning Suggestions from Memory Mesh**

    Returns what Grace should learn next based on:
    - Knowledge gaps (high theory, low practice)
    - Failure patterns (needs re-study)
    - High-value topics (worth reinforcing)
    - Related clusters (should learn together)

    **Example:**
    ```bash
    curl http://localhost:8000/grace/learning-suggestions
    ```
    """
    try:
        session_factory = initialize_session_factory()
        session = session_factory()

        master = get_master_integration(session=session)

        if not master.memory_learner:
            raise HTTPException(status_code=400, detail="Memory learner not initialized")

        suggestions = master.memory_learner.get_learning_suggestions()

        return suggestions

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get suggestions: {str(e)}")


@router.get("/triggers/stats")
async def get_trigger_stats() -> Dict[str, Any]:
    """
    **Get Autonomous Trigger Statistics**

    Returns statistics about autonomous actions triggered:
    - Total triggers fired
    - Recursive loops active
    - Recent actions

    **Example:**
    ```bash
    curl http://localhost:8000/grace/triggers/stats
    ```
    """
    try:
        session_factory = initialize_session_factory()
        session = session_factory()

        master = get_master_integration(session=session)

        if not master.trigger_pipeline:
            raise HTTPException(status_code=400, detail="Trigger pipeline not initialized")

        stats = master.trigger_pipeline.get_status()

        return stats

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get trigger stats: {str(e)}")
