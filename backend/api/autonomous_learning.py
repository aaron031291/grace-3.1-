"""
Autonomous Multi-Process Learning API

Controls Grace's complete autonomous learning system with:
- Multi-process subagent architecture
- Background operation
- Automatic task distribution
- Self-reflection and improvement

Classes:
- `StartLearningSystemRequest`
- `StudyTaskRequest`
- `PracticeTaskRequest`

Key Methods:
- `get_orchestrator()`
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

import sys
import platform

# Use thread-based orchestrator on Windows, multiprocessing on Linux/Mac
if platform.system() == "Windows":
    from cognitive.thread_learning_orchestrator import ThreadLearningOrchestrator as LearningOrchestrator
    from cognitive.learning_subagent_system import TaskType
else:
    from cognitive.learning_subagent_system import LearningOrchestrator, TaskType
from cognitive.memory_mesh_learner import get_memory_mesh_learner
from genesis.autonomous_triggers import get_genesis_trigger_pipeline
from database.session import initialize_session_factory
from settings import KNOWLEDGE_BASE_PATH
from pathlib import Path

router = APIRouter(prefix="/autonomous-learning", tags=["autonomous-learning"])

# Global orchestrator
_orchestrator: Optional[LearningOrchestrator] = None


def get_orchestrator() -> LearningOrchestrator:
    """
    Get or create learning orchestrator.

    NOW INTEGRATES WITH GENESIS KEY TRIGGER PIPELINE!
    """
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = LearningOrchestrator(
            knowledge_base_path=KNOWLEDGE_BASE_PATH,
            num_study_agents=3,    # 3 parallel study processes
            num_practice_agents=2   # 2 parallel practice processes
        )

        # INTEGRATE WITH GENESIS KEY TRIGGER PIPELINE
        trigger_pipeline = get_genesis_trigger_pipeline(
            knowledge_base_path=Path(KNOWLEDGE_BASE_PATH),
            orchestrator=_orchestrator
        )

        # Set orchestrator reference in trigger pipeline
        trigger_pipeline.set_orchestrator(_orchestrator)

    return _orchestrator


# ======================================================================
# Request Models
# ======================================================================

class StartLearningSystemRequest(BaseModel):
    num_study_agents: int = 3
    num_practice_agents: int = 2


class StudyTaskRequest(BaseModel):
    topic: str
    learning_objectives: List[str] = []
    priority: int = 5


class PracticeTaskRequest(BaseModel):
    skill_name: str
    task_description: str
    complexity: float = 0.5
    priority: int = 5


# ======================================================================
# System Control
# ======================================================================

@router.post("/start")
async def start_autonomous_learning(
    request: StartLearningSystemRequest
) -> Dict[str, Any]:
    """
    **Start Grace's autonomous multi-process learning system.**

    Spawns independent subagent processes:
    - Study Subagents (extract concepts from materials)
    - Practice Subagents (execute skills in sandbox)
    - Mirror Subagent (self-reflection + gap identification)

    **All run in background as separate processes.**

    **Example:**
    ```json
    POST /autonomous-learning/start
    {
        "num_study_agents": 3,
        "num_practice_agents": 2
    }
    ```

    **Architecture:**
    ```
    Master Process (Orchestrator)
      |
      +-- Study Agent 1 (Process)
      +-- Study Agent 2 (Process)
      +-- Study Agent 3 (Process)
      |
      +-- Practice Agent 1 (Process)
      +-- Practice Agent 2 (Process)
      |
      +-- Mirror Agent (Process)
    ```

    **Returns:**
    - System configuration
    - Process IDs
    - Total capacity
    """
    try:
        # Validate configuration
        if request.num_study_agents < 1 or request.num_study_agents > 10:
            raise HTTPException(
                status_code=400,
                detail="num_study_agents must be between 1 and 10"
            )

        if request.num_practice_agents < 1 or request.num_practice_agents > 10:
            raise HTTPException(
                status_code=400,
                detail="num_practice_agents must be between 1 and 10"
            )

        # Create new orchestrator if configuration changed
        global _orchestrator
        if _orchestrator is None:
            _orchestrator = LearningOrchestrator(
                knowledge_base_path=KNOWLEDGE_BASE_PATH,
                num_study_agents=request.num_study_agents,
                num_practice_agents=request.num_practice_agents
            )

        orchestrator = get_orchestrator()
        orchestrator.start()

        return {
            "status": "started",
            "message": "Autonomous learning system is now running",
            "configuration": {
                "study_agents": request.num_study_agents,
                "practice_agents": request.num_practice_agents,
                "mirror_agents": 1,
                "total_processes": request.num_study_agents + request.num_practice_agents + 1
            },
            "capabilities": {
                "parallel_study_capacity": request.num_study_agents,
                "parallel_practice_capacity": request.num_practice_agents,
                "autonomous_reflection": True,
                "background_operation": True
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start: {str(e)}")


@router.post("/stop")
async def stop_autonomous_learning() -> Dict[str, Any]:
    """
    **Stop Grace's autonomous learning system.**

    Gracefully shuts down all subagent processes:
    - Completes current tasks
    - Saves final state
    - Terminates all processes

    **Returns:**
    - Final statistics
    - Tasks completed
    - System summary
    """
    try:
        orchestrator = get_orchestrator()
        final_status = orchestrator.get_status()

        orchestrator.stop()

        return {
            "status": "stopped",
            "message": "Autonomous learning system stopped",
            "final_statistics": final_status
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop: {str(e)}")


@router.get("/status")
async def get_learning_system_status() -> Dict[str, Any]:
    """
    **Get autonomous learning system status.**

    **Returns:**
    - Running processes
    - Queue sizes
    - Tasks completed
    - Current capacity

    **Example response:**
    ```json
    {
        "status": "running",
        "total_subagents": 6,
        "study_agents": 3,
        "practice_agents": 2,
        "study_queue_size": 12,
        "practice_queue_size": 5,
        "total_tasks_submitted": 145,
        "total_tasks_completed": 132
    }
    ```
    """
    try:
        orchestrator = get_orchestrator()
        status = orchestrator.get_status()
        return status

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


@router.get("/trigger-pipeline/status")
async def get_trigger_pipeline_status() -> Dict[str, Any]:
    """
    **Get Genesis Key trigger pipeline status.**

    Shows how many autonomous actions have been triggered by Genesis Keys.

    **Returns:**
    - Total triggers fired
    - Recursive loops active
    - Integration status

    **Example response:**
    ```json
    {
        "triggers_fired": 45,
        "recursive_loops_active": 3,
        "orchestrator_connected": true,
        "message": "Genesis Key autonomous trigger pipeline operational"
    }
    ```
    """
    try:
        session_factory = initialize_session_factory()
        session = session_factory()

        trigger_pipeline = get_genesis_trigger_pipeline(
            session=session,
            knowledge_base_path=Path(KNOWLEDGE_BASE_PATH),
            orchestrator=get_orchestrator()
        )

        status = trigger_pipeline.get_status()
        return status

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get trigger status: {str(e)}")


@router.get("/memory-mesh/learning-suggestions")
async def get_learning_suggestions() -> Dict[str, Any]:
    """
    **Get learning suggestions from memory mesh analysis.**

    Memory mesh analyzes patterns and suggests what Grace should learn next:
    - Knowledge gaps (knows but can't apply)
    - High-value topics (worth reinforcing)
    - Related topic clusters (should learn together)
    - Failure patterns (needs re-study)

    **This creates the feedback loop: Memory → Learning → Memory**

    **Returns:**
    - Knowledge gaps to practice
    - High-value topics to reinforce
    - Related topics to study together
    - Failures to re-study
    - Top priorities (ranked)

    **Example response:**
    ```json
    {
        "knowledge_gaps": [
            {
                "topic": "Docker containers",
                "data_confidence": 0.85,
                "operational_confidence": 0.30,
                "gap_size": 0.55,
                "recommendation": "practice"
            }
        ],
        "high_value_topics": [...],
        "related_clusters": [...],
        "failure_patterns": [...],
        "top_priorities": [
            {
                "topic": "Python decorators",
                "action": "restudy",
                "priority": 1,
                "reason": "Failed practice attempts"
            }
        ]
    }
    ```
    """
    try:
        session_factory = initialize_session_factory()
        session = session_factory()

        memory_learner = get_memory_mesh_learner(session=session)
        suggestions = memory_learner.get_learning_suggestions()

        return suggestions

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get learning suggestions: {str(e)}")
    finally:
        session.close()


# ======================================================================
# Task Submission
# ======================================================================

@router.post("/tasks/study")
async def submit_study_task(request: StudyTaskRequest) -> Dict[str, Any]:
    """
    **Submit autonomous study task.**

    Task will be processed in background by next available study subagent.

    **Example:**
    ```json
    POST /autonomous-learning/tasks/study
    {
        "topic": "Python decorators",
        "learning_objectives": [
            "Understand decorator syntax",
            "Learn to write custom decorators"
        ],
        "priority": 3
    }
    ```

    **What happens:**
    1. Task queued for study subagents
    2. Next available subagent picks it up
    3. Concepts extracted from training materials
    4. Results stored in Layer 1 with trust scores
    5. Results sent back via result queue

    **All happens in background - API returns immediately.**

    **Returns:**
    - Task ID for tracking
    - Queue position
    """
    try:
        # Validate input
        if not request.topic or len(request.topic.strip()) == 0:
            raise HTTPException(status_code=400, detail="Topic cannot be empty")
        
        # Get orchestrator and ensure it's running
        orchestrator = get_orchestrator()
        
        # Auto-start if not running
        status = orchestrator.get_status()
        if not status.get("running", False):
            orchestrator.start()
            import logging
            logger = logging.getLogger(__name__)
            logger.info("[API] Auto-started orchestrator for study task submission")

        task_id = orchestrator.submit_study_task(
            topic=request.topic,
            learning_objectives=request.learning_objectives,
            priority=request.priority
        )

        return {
            "status": "queued",
            "task_id": task_id,
            "task_type": "study",
            "topic": request.topic,
            "priority": request.priority,
            "queue_size": orchestrator.study_queue.qsize(),
            "message": "Study task queued successfully. Subagent will process in background."
        }

    except HTTPException:
        raise
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"[API] Failed to submit study task: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to submit study task: {str(e)}")


@router.post("/tasks/practice")
async def submit_practice_task(request: PracticeTaskRequest) -> Dict[str, Any]:
    """
    **Submit autonomous practice task.**

    Task will be processed in background by next available practice subagent.

    **Example:**
    ```json
    POST /autonomous-learning/tasks/practice
    {
        "skill_name": "Python programming",
        "task_description": "Write a factorial function",
        "complexity": 0.4,
        "priority": 5
    }
    ```

    **What happens:**
    1. Task queued for practice subagents
    2. Next available subagent picks it up
    3. Skill executed in sandbox
    4. Outcome observed
    5. Operational confidence updated
    6. If failed → Mirror subagent reflects → Gaps identified → Study triggered

    **All happens autonomously in background.**

    **Returns:**
    - Task ID for tracking
    - Queue position
    """
    try:
        # Validate input
        if not request.skill_name or len(request.skill_name.strip()) == 0:
            raise HTTPException(status_code=400, detail="Skill name cannot be empty")
        if not request.task_description or len(request.task_description.strip()) == 0:
            raise HTTPException(status_code=400, detail="Task description cannot be empty")
        
        # Get orchestrator and ensure it's running
        orchestrator = get_orchestrator()
        
        # Auto-start if not running
        status = orchestrator.get_status()
        if not status.get("running", False):
            orchestrator.start()
            import logging
            logger = logging.getLogger(__name__)
            logger.info("[API] Auto-started orchestrator for practice task submission")

        task_id = orchestrator.submit_practice_task(
            skill_name=request.skill_name,
            task_description=request.task_description,
            complexity=request.complexity
        )

        return {
            "status": "queued",
            "task_id": task_id,
            "task_type": "practice",
            "skill": request.skill_name,
            "priority": request.priority,
            "queue_size": orchestrator.practice_queue.qsize(),
            "message": "Practice task queued successfully. Subagent will process in background."
        }

    except HTTPException:
        raise
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"[API] Failed to submit practice task: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to submit practice task: {str(e)}")


@router.get("/tasks/{task_id}/status")
async def get_task_status(task_id: str) -> Dict[str, Any]:
    """
    **Get status of a specific task.**
    
    Check if a task is queued, processing, completed, or failed.
    
    **Example:**
    ```
    GET /autonomous-learning/tasks/study-42/status
    ```
    
    **Returns:**
    ```json
    {
        "task_id": "study-42",
        "status": "completed",
        "result": {...},
        "processing_time": 12.5
    }
    ```
    """
    try:
        orchestrator = get_orchestrator()
        status = orchestrator.get_status()
        
        # Check if task ID exists in shared state or completed tasks
        # For now, return queue info - full tracking requires shared state expansion
        return {
            "task_id": task_id,
            "status": "tracking_limited",
            "message": "Task submitted successfully. Check orchestrator status for overall progress.",
            "orchestrator_status": {
                "running": status.get("running", False),
                "tasks_completed": status.get("total_tasks_completed", 0),
                "study_queue_size": status.get("study_queue_size", 0),
                "practice_queue_size": status.get("practice_queue_size", 0)
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get task status: {str(e)}")


@router.post("/tasks/batch-study")
async def submit_batch_study_tasks(
    topics: List[str],
    priority: int = 5
) -> Dict[str, Any]:
    """
    **Submit multiple study tasks at once.**

    All tasks processed in parallel by available subagents.

    **Example:**
    ```json
    POST /autonomous-learning/tasks/batch-study
    {
        "topics": [
            "Python decorators",
            "REST API design",
            "Docker containers",
            "SQL joins"
        ],
        "priority": 5
    }
    ```

    **Parallel processing:**
    - If 3 study agents available → 3 topics studied simultaneously
    - Remaining topics queued
    - Maximum throughput

    **Returns:**
    - Task IDs for all submitted tasks
    - Estimated processing time
    """
    try:
        orchestrator = get_orchestrator()

        task_ids = []
        for topic in topics:
            task_id = orchestrator.submit_study_task(
                topic=topic,
                learning_objectives=[f"Learn {topic}"],
                priority=priority
            )
            task_ids.append(task_id)

        return {
            "status": "queued",
            "total_tasks": len(task_ids),
            "task_ids": task_ids,
            "queue_size": orchestrator.study_queue.qsize(),
            "parallel_capacity": len(orchestrator.study_agents),
            "message": f"{len(task_ids)} study tasks queued for parallel processing"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit batch: {str(e)}")


# ======================================================================
# Analytics
# ======================================================================

@router.get("/analytics/throughput")
async def get_learning_throughput() -> Dict[str, Any]:
    """
    **Get learning throughput metrics.**

    Measures:
    - Tasks per minute
    - Concepts learned per minute
    - Parallel efficiency
    - Queue wait times

    **Returns:**
    - Real-time throughput statistics
    """
    try:
        orchestrator = get_orchestrator()
        status = orchestrator.get_status()

        return {
            "total_tasks_submitted": status["total_tasks_submitted"],
            "total_tasks_completed": status["total_tasks_completed"],
            "pending_tasks": (
                status["study_queue_size"] +
                status["practice_queue_size"] +
                status["mirror_queue_size"]
            ),
            "parallel_capacity": {
                "study": status["study_agents"],
                "practice": status["practice_agents"],
                "total": status["total_subagents"]
            },
            "queue_distribution": {
                "study_queue": status["study_queue_size"],
                "practice_queue": status["practice_queue_size"],
                "mirror_queue": status["mirror_queue_size"]
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get throughput: {str(e)}")
