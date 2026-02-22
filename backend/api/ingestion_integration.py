"""
Ingestion Integration API - Complete Autonomous Cycle

Unified API that connects:
- File ingestion
- Genesis Key tracking
- Autonomous learning
- Self-healing
- Mirror self-modeling

Every file ingested triggers the complete autonomous cycle.

Classes:
- `IngestFileRequest`
- `IngestDirectoryRequest`
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from pathlib import Path

from cognitive.ingestion_self_healing_integration import get_ingestion_integration
from cognitive.learning_subagent_system import LearningOrchestrator
from database.session import initialize_session_factory
from settings import KNOWLEDGE_BASE_PATH

router = APIRouter(prefix="/ingestion-integration", tags=["ingestion-integration"])


# ======================================================================
# Request/Response Models
# ======================================================================

class IngestFileRequest(BaseModel):
    """Request to ingest a file with complete tracking."""
    file_path: str
    user_id: str = "system"
    metadata: Optional[Dict] = None


class IngestDirectoryRequest(BaseModel):
    """Request to ingest directory with complete tracking."""
    directory_path: str
    user_id: str = "system"
    recursive: bool = True


# ======================================================================
# ENDPOINTS
# ======================================================================

@router.post("/ingest-file")
async def ingest_file_with_tracking(request: IngestFileRequest) -> Dict[str, Any]:
    """
    **Ingest File with Complete Autonomous Cycle**

    This single endpoint triggers the complete flow:
    1. File ingested → Genesis Key created (what/where/when/who/how/why)
    2. Autonomous learning triggered (study the content)
    3. Health monitoring (detect issues)
    4. Self-healing if needed (fix problems)
    5. Mirror observation (learn patterns)
    6. Continuous improvement

    **Example:**
    ```bash
    curl -X POST http://localhost:8000/ingestion-integration/ingest-file \\
      -H "Content-Type: application/json" \\
      -d '{
        "file_path": "knowledge_base/my_file.txt",
        "user_id": "user-123"
      }'
    ```

    **Response:**
    ```json
    {
      "ingestion_key_id": "GK-abc123",
      "file_path": "knowledge_base/my_file.txt",
      "status": "success",
      "steps": [
        {"step": "ingestion", "status": "success"},
        {"step": "autonomous_learning", "status": "triggered", "task_id": "..."},
        {"step": "health_check", "status": "healthy"},
        {"step": "mirror_observation", "status": "analyzed"}
      ]
    }
    ```
    """
    try:
        session_factory = initialize_session_factory()
        session = session_factory()

        # Get integration system
        integration = get_ingestion_integration(
            session=session,
            knowledge_base_path=Path(KNOWLEDGE_BASE_PATH),
            learning_orchestrator=None,  # Will create if needed
            enable_healing=True,
            enable_mirror=True
        )

        # Ingest with complete tracking
        result = integration.ingest_file_with_tracking(
            file_path=Path(request.file_path),
            user_id=request.user_id,
            metadata=request.metadata
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.post("/ingest-directory")
async def ingest_directory_with_tracking(request: IngestDirectoryRequest) -> Dict[str, Any]:
    """
    **Ingest Entire Directory with Complete Tracking**

    Ingests all files in a directory, each with complete autonomous cycle:
    - Each file gets its own Genesis Key
    - Each triggers autonomous learning
    - Health monitored throughout
    - Self-healing applied if issues occur
    - Mirror observes patterns across all files

    **Example:**
    ```bash
    curl -X POST http://localhost:8000/ingestion-integration/ingest-directory \\
      -H "Content-Type: application/json" \\
      -d '{
        "directory_path": "knowledge_base/new_docs",
        "recursive": true
      }'
    ```

    **Response:**
    ```json
    {
      "directory": "knowledge_base/new_docs",
      "total_files": 25,
      "successful": 24,
      "failed": 1,
      "file_results": [...]
    }
    ```
    """
    try:
        session_factory = initialize_session_factory()
        session = session_factory()

        integration = get_ingestion_integration(
            session=session,
            knowledge_base_path=Path(KNOWLEDGE_BASE_PATH),
            enable_healing=True,
            enable_mirror=True
        )

        result = integration.ingest_directory_with_tracking(
            directory_path=Path(request.directory_path),
            user_id=request.user_id,
            recursive=request.recursive
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Directory ingestion failed: {str(e)}")


@router.post("/improvement-cycle")
async def run_improvement_cycle() -> Dict[str, Any]:
    """
    **Run Complete Improvement Cycle**

    This is the "iterate in sandbox" endpoint:
    1. Observe recent Genesis Keys
    2. Detect patterns (failures, successes)
    3. Generate improvements
    4. Apply improvements (learning/healing)
    5. Measure results

    **Run this periodically to continuously improve!**

    **Example:**
    ```bash
    curl -X POST http://localhost:8000/ingestion-integration/improvement-cycle
    ```

    **Response:**
    ```json
    {
      "timestamp": "2026-01-11T20:00:00",
      "observations": {
        "mirror": {
          "patterns": 5,
          "self_awareness": 0.73,
          "suggestions": 3
        },
        "health": {
          "status": "healthy",
          "anomalies": 0
        },
        "learning": {
          "total_subagents": 8,
          "completed": 156
        }
      },
      "improvements": [
        {"type": "learning", "task_id": "..."},
        {"type": "healing", "actions": 1}
      ]
    }
    ```
    """
    try:
        session_factory = initialize_session_factory()
        session = session_factory()

        integration = get_ingestion_integration(
            session=session,
            knowledge_base_path=Path(KNOWLEDGE_BASE_PATH),
            enable_healing=True,
            enable_mirror=True
        )

        result = integration.run_improvement_cycle()

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Improvement cycle failed: {str(e)}")


@router.get("/status")
async def get_integration_status() -> Dict[str, Any]:
    """
    **Get Complete Integration Status**

    Returns status of all integrated systems:
    - Ingestion statistics
    - Learning orchestrator status
    - Healing system health
    - Mirror self-awareness
    - Trigger pipeline activity

    **Example:**
    ```bash
    curl http://localhost:8000/ingestion-integration/status
    ```
    """
    try:
        session_factory = initialize_session_factory()
        session = session_factory()

        integration = get_ingestion_integration(
            session=session,
            knowledge_base_path=Path(KNOWLEDGE_BASE_PATH),
            enable_healing=True,
            enable_mirror=True
        )

        status = integration.get_complete_status()

        return status

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


@router.get("/genesis-keys/recent")
async def get_recent_genesis_keys(limit: int = 50) -> Dict[str, Any]:
    """
    **Get Recent Genesis Keys**

    Shows what/where/when/who/how/why for recent operations.
    This is your complete audit trail!

    **Example:**
    ```bash
    curl "http://localhost:8000/ingestion-integration/genesis-keys/recent?limit=20"
    ```
    """
    try:
        session_factory = initialize_session_factory()
        session = session_factory()

        from models.genesis_key_models import GenesisKey

        # Query recent Genesis Keys
        recent_keys = session.query(GenesisKey).order_by(
            GenesisKey.created_at.desc()
        ).limit(limit).all()

        keys_data = []
        for key in recent_keys:
            keys_data.append({
                "key_id": key.key_id,
                "type": key.key_type.value,
                "what": key.what_description,
                "who": key.who_actor,
                "where": key.where_location,
                "when": key.created_at.isoformat(),
                "why": key.why_reason,
                "how": key.how_method,
                "is_error": key.is_error
            })

        return {
            "total": len(keys_data),
            "genesis_keys": keys_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Genesis Keys: {str(e)}")
