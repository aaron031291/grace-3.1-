"""
Proactive Learning API

Endpoints for Grace's autonomous background learning system.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

from cognitive.proactive_learner import ProactiveLearningOrchestrator
from settings import KNOWLEDGE_BASE_PATH
from pathlib import Path

router = APIRouter(prefix="/proactive-learning", tags=["proactive-learning"])

# Global orchestrator instance
_orchestrator: Optional[ProactiveLearningOrchestrator] = None


def get_orchestrator() -> ProactiveLearningOrchestrator:
    """Get or create the proactive learning orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ProactiveLearningOrchestrator(
            knowledge_base_path=Path(KNOWLEDGE_BASE_PATH),
            num_subagents=3,  # 3 parallel learning agents
            max_concurrent_per_agent=2  # 2 tasks per agent = 6 total concurrent
        )
    return _orchestrator


# ======================================================================
# Request/Response Models
# ======================================================================

class StartProactiveLearningRequest(BaseModel):
    num_subagents: int = 3
    max_concurrent_per_agent: int = 2


class AddTaskRequest(BaseModel):
    task_type: str  # "study", "practice", "ingest_and_study"
    topic: Optional[str] = None
    learning_objectives: List[str] = []
    file_path: Optional[str] = None
    priority: int = 5


# ======================================================================
# Control Endpoints
# ======================================================================

@router.post("/start")
async def start_proactive_learning(
    request: StartProactiveLearningRequest
) -> Dict[str, Any]:
    """
    **Start Grace's proactive learning system.**

    Activates autonomous background learning:
    - Monitors knowledge base for new files
    - Automatically ingests and studies new content
    - Runs multiple parallel learning agents
    - Processes learning tasks continuously

    **Example:**
    ```json
    POST /proactive-learning/start
    {
        "num_subagents": 3,
        "max_concurrent_per_agent": 2
    }
    ```

    **What happens:**
    - File system monitoring activated
    - Learning subagents started
    - Grace begins autonomous learning
    - New files trigger automatic study sessions

    **Returns:**
    - System status
    - Number of active agents
    - Monitoring path
    """
    try:
        orchestrator = get_orchestrator()

        # Reconfigure if needed
        if request.num_subagents != orchestrator.num_subagents:
            raise HTTPException(
                status_code=400,
                detail="Cannot change num_subagents on running system. Stop first."
            )

        orchestrator.start()

        return {
            "status": "started",
            "message": "Proactive learning system is now active",
            "num_subagents": orchestrator.num_subagents,
            "max_concurrent_per_agent": orchestrator.max_concurrent_per_agent,
            "total_concurrent_capacity": (
                orchestrator.num_subagents * orchestrator.max_concurrent_per_agent
            ),
            "monitoring_path": str(orchestrator.knowledge_base_path)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start: {str(e)}")


@router.post("/stop")
async def stop_proactive_learning() -> Dict[str, Any]:
    """
    **Stop Grace's proactive learning system.**

    Gracefully shuts down:
    - File system monitoring
    - All learning subagents
    - Completes current tasks before stopping

    **Returns:**
    - Final statistics
    - Tasks completed
    - Concepts learned
    """
    try:
        orchestrator = get_orchestrator()

        # Get final stats before stopping
        final_stats = orchestrator.get_status()

        orchestrator.stop()

        return {
            "status": "stopped",
            "message": "Proactive learning system stopped",
            "final_statistics": final_stats
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop: {str(e)}")


@router.get("/status")
async def get_proactive_learning_status() -> Dict[str, Any]:
    """
    **Get proactive learning system status.**

    **Returns:**
    - Running status
    - Queue size (pending tasks)
    - Tasks completed/failed
    - Concepts learned
    - Learning velocity (concepts per hour)
    - Subagent status for each agent

    **Example response:**
    ```json
    {
        "status": "running",
        "num_subagents": 3,
        "queue_size": 5,
        "total_tasks_completed": 47,
        "total_concepts_learned": 1250,
        "learning_velocity_per_hour": 312.5,
        "subagents": [
            {
                "agent_id": "agent-1",
                "is_running": true,
                "current_tasks": 2,
                "tasks_completed": 18,
                "total_concepts_learned": 450
            }
        ]
    }
    ```
    """
    try:
        orchestrator = get_orchestrator()
        status = orchestrator.get_status()
        return status

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


# ======================================================================
# Task Management
# ======================================================================

@router.post("/tasks/add")
async def add_learning_task(request: AddTaskRequest) -> Dict[str, Any]:
    """
    **Manually add a learning task to the queue.**

    Grace will process it autonomously in the background.

    **Task types:**
    - `study` - Study a topic from training materials
    - `practice` - Practice a skill
    - `ingest_and_study` - Ingest new file + study its content

    **Priority:**
    - 1 = Highest priority (processed first)
    - 5 = Normal priority
    - 10 = Lowest priority

    **Example - Study Task:**
    ```json
    POST /proactive-learning/tasks/add
    {
        "task_type": "study",
        "topic": "Docker containers",
        "learning_objectives": [
            "Learn Docker basics",
            "Understand containerization"
        ],
        "priority": 3
    }
    ```

    **Example - Ingest Task:**
    ```json
    POST /proactive-learning/tasks/add
    {
        "task_type": "ingest_and_study",
        "file_path": "/path/to/new/docker-guide.pdf",
        "priority": 1
    }
    ```

    **Returns:**
    - Task ID for tracking
    - Queue position
    """
    try:
        orchestrator = get_orchestrator()

        task_id = orchestrator.add_learning_task(
            task_type=request.task_type,
            topic=request.topic,
            learning_objectives=request.learning_objectives,
            file_path=request.file_path,
            priority=request.priority
        )

        return {
            "status": "queued",
            "task_id": task_id,
            "task_type": request.task_type,
            "topic": request.topic,
            "priority": request.priority,
            "queue_size": orchestrator.learning_queue.qsize()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add task: {str(e)}")


@router.get("/tasks/queue")
async def get_task_queue() -> Dict[str, Any]:
    """
    **Get current learning task queue status.**

    Shows:
    - Number of pending tasks
    - Current processing tasks
    - Queue capacity
    - Estimated processing time

    **Returns:**
    - Queue statistics
    - Processing capacity
    """
    try:
        orchestrator = get_orchestrator()
        status = orchestrator.get_status()

        # Calculate processing capacity
        total_capacity = orchestrator.num_subagents * orchestrator.max_concurrent_per_agent

        # Count current processing tasks
        current_processing = sum(
            agent_status["current_tasks"]
            for agent_status in status["subagents"]
        )

        return {
            "queue_size": status["queue_size"],
            "currently_processing": current_processing,
            "total_capacity": total_capacity,
            "available_capacity": total_capacity - current_processing,
            "total_completed": status["total_tasks_completed"],
            "total_failed": status["total_tasks_failed"],
            "success_rate": (
                status["total_tasks_completed"] /
                (status["total_tasks_completed"] + status["total_tasks_failed"])
                if (status["total_tasks_completed"] + status["total_tasks_failed"]) > 0
                else 0
            )
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get queue: {str(e)}")


# ======================================================================
# Analytics
# ======================================================================

@router.get("/analytics/learning-velocity")
async def get_learning_velocity() -> Dict[str, Any]:
    """
    **Get Grace's learning velocity metrics.**

    Measures how fast Grace is learning:
    - Concepts learned per hour
    - Files processed per hour
    - Tasks completed per hour
    - Trend analysis

    **Returns:**
    - Current velocity
    - Historical trends
    - Performance metrics
    """
    try:
        orchestrator = get_orchestrator()
        status = orchestrator.get_status()

        uptime_hours = status["uptime_hours"]

        if uptime_hours > 0:
            velocity = {
                "concepts_per_hour": status["learning_velocity_per_hour"],
                "tasks_per_hour": status["total_tasks_completed"] / uptime_hours,
                "success_rate": (
                    status["total_tasks_completed"] /
                    (status["total_tasks_completed"] + status["total_tasks_failed"])
                    if (status["total_tasks_completed"] + status["total_tasks_failed"]) > 0
                    else 0
                ),
                "uptime_hours": uptime_hours,
                "total_concepts_learned": status["total_concepts_learned"]
            }
        else:
            velocity = {
                "concepts_per_hour": 0,
                "tasks_per_hour": 0,
                "success_rate": 0,
                "uptime_hours": 0,
                "total_concepts_learned": 0
            }

        return velocity

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get velocity: {str(e)}")


@router.get("/analytics/subagent-performance")
async def get_subagent_performance() -> Dict[str, Any]:
    """
    **Get performance metrics for each learning subagent.**

    Shows:
    - Tasks completed per agent
    - Success rate per agent
    - Concepts learned per agent
    - Current workload

    **Use this to:**
    - Monitor agent efficiency
    - Identify bottlenecks
    - Balance workload

    **Returns:**
    - Per-agent statistics
    - Comparative performance
    """
    try:
        orchestrator = get_orchestrator()
        status = orchestrator.get_status()

        # Add calculated metrics to each subagent
        for agent_status in status["subagents"]:
            total_tasks = (
                agent_status["tasks_completed"] + agent_status["tasks_failed"]
            )
            agent_status["total_tasks"] = total_tasks

            if total_tasks > 0:
                agent_status["average_concepts_per_task"] = (
                    agent_status["total_concepts_learned"] / agent_status["tasks_completed"]
                    if agent_status["tasks_completed"] > 0 else 0
                )
            else:
                agent_status["average_concepts_per_task"] = 0

        return {
            "num_subagents": status["num_subagents"],
            "subagents": status["subagents"],
            "total_concepts": status["total_concepts_learned"],
            "total_tasks": status["total_tasks_completed"] + status["total_tasks_failed"]
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get subagent performance: {str(e)}"
        )
