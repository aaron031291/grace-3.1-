"""
Knowledge Base Connectors API.

Endpoints for managing knowledge base connections, sources, and data flow.
These endpoints are not exposed to the frontend yet - internal use only.

Classes:
- `ConnectorType`
- `ConnectorStatus`
- `SyncFrequency`
- `ConnectorConfig`
- `ConnectorResponse`
- `SyncResultResponse`
- `KnowledgeSourceResponse`
- `SearchKnowledgeRequest`
- `SearchResultResponse`
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum
from sqlalchemy.orm import Session

from database.session import get_session

router = APIRouter(prefix="/knowledge-base", tags=["Knowledge Base Connectors"])


# ==================== Enums ====================

class ConnectorType(str, Enum):
    """Types of knowledge base connectors."""
    GITHUB = "github"
    GITLAB = "gitlab"
    CONFLUENCE = "confluence"
    NOTION = "notion"
    JIRA = "jira"
    SLACK = "slack"
    GOOGLE_DRIVE = "google_drive"
    SHAREPOINT = "sharepoint"
    DATABASE = "database"
    FILE_SYSTEM = "file_system"
    API = "api"
    RSS = "rss"
    WEB_SCRAPER = "web_scraper"


class ConnectorStatus(str, Enum):
    """Status of a connector."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    SYNCING = "syncing"
    PENDING = "pending"


class SyncFrequency(str, Enum):
    """Sync frequency options."""
    REALTIME = "realtime"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MANUAL = "manual"


# ==================== Pydantic Models ====================

class ConnectorConfig(BaseModel):
    """Configuration for a knowledge base connector."""
    connector_type: ConnectorType = Field(..., description="Type of connector")
    name: str = Field(..., description="Display name for the connector")
    description: Optional[str] = Field(None, description="Description of the connector")
    connection_params: Dict[str, Any] = Field(default_factory=dict, description="Connection parameters")
    sync_frequency: SyncFrequency = Field(SyncFrequency.DAILY, description="How often to sync")
    enabled: bool = Field(True, description="Whether connector is enabled")
    filters: Optional[Dict[str, Any]] = Field(None, description="Filters for what to sync")


class ConnectorResponse(BaseModel):
    """Response for a connector."""
    id: str = Field(..., description="Unique connector ID")
    connector_type: ConnectorType = Field(..., description="Type of connector")
    name: str = Field(..., description="Display name")
    description: Optional[str] = Field(None, description="Description")
    status: ConnectorStatus = Field(..., description="Current status")
    sync_frequency: SyncFrequency = Field(..., description="Sync frequency")
    enabled: bool = Field(..., description="Whether enabled")
    last_sync: Optional[str] = Field(None, description="Last sync timestamp")
    documents_synced: int = Field(0, description="Number of documents synced")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")


class SyncResultResponse(BaseModel):
    """Response for a sync operation."""
    connector_id: str = Field(..., description="Connector ID")
    status: str = Field(..., description="Sync status: success, partial, failed")
    documents_added: int = Field(0, description="New documents added")
    documents_updated: int = Field(0, description="Existing documents updated")
    documents_deleted: int = Field(0, description="Documents deleted")
    errors: List[str] = Field(default_factory=list, description="Any errors encountered")
    duration_seconds: float = Field(..., description="Sync duration")
    started_at: str = Field(..., description="Start timestamp")
    completed_at: str = Field(..., description="Completion timestamp")


class KnowledgeSourceResponse(BaseModel):
    """Response for a knowledge source."""
    id: str = Field(..., description="Source ID")
    connector_id: str = Field(..., description="Connector ID")
    source_type: str = Field(..., description="Type of source")
    name: str = Field(..., description="Source name")
    path: Optional[str] = Field(None, description="Path or URL")
    document_count: int = Field(0, description="Number of documents")
    last_indexed: Optional[str] = Field(None, description="Last indexed timestamp")
    status: str = Field(..., description="Source status")


class SearchKnowledgeRequest(BaseModel):
    """Request to search knowledge base."""
    query: str = Field(..., description="Search query")
    connector_ids: Optional[List[str]] = Field(None, description="Filter by connectors")
    source_types: Optional[List[str]] = Field(None, description="Filter by source types")
    limit: int = Field(10, ge=1, le=100, description="Maximum results")
    include_metadata: bool = Field(True, description="Include document metadata")


class SearchResultResponse(BaseModel):
    """Response for search results."""
    query: str = Field(..., description="Original query")
    total_results: int = Field(..., description="Total matching results")
    results: List[Dict[str, Any]] = Field(default_factory=list, description="Search results")
    search_time_ms: float = Field(..., description="Search duration in ms")


# ==================== In-Memory Storage (for demo) ====================
# In production, these would be stored in the database

_connectors: Dict[str, Dict[str, Any]] = {}
_sources: Dict[str, Dict[str, Any]] = {}
_sync_history: List[Dict[str, Any]] = []


def _generate_id() -> str:
    """Generate a unique ID."""
    import uuid
    return str(uuid.uuid4())[:8]


# ==================== Endpoints ====================

@router.get("/connectors", response_model=List[ConnectorResponse])
async def list_connectors(
    connector_type: Optional[ConnectorType] = None,
    status: Optional[ConnectorStatus] = None,
    session: Session = Depends(get_session)
):
    """
    List all knowledge base connectors.

    Optionally filter by type or status.
    """
    try:
        connectors = list(_connectors.values())

        if connector_type:
            connectors = [c for c in connectors if c["connector_type"] == connector_type]

        if status:
            connectors = [c for c in connectors if c["status"] == status]

        return [ConnectorResponse(**c) for c in connectors]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/connectors", response_model=ConnectorResponse)
async def create_connector(
    config: ConnectorConfig,
    session: Session = Depends(get_session)
):
    """
    Create a new knowledge base connector.

    Configure connection to external knowledge sources.
    """
    try:
        connector_id = _generate_id()
        now = datetime.now().isoformat()

        connector = {
            "id": connector_id,
            "connector_type": config.connector_type,
            "name": config.name,
            "description": config.description,
            "connection_params": config.connection_params,
            "sync_frequency": config.sync_frequency,
            "enabled": config.enabled,
            "filters": config.filters,
            "status": ConnectorStatus.PENDING,
            "last_sync": None,
            "documents_synced": 0,
            "created_at": now,
            "updated_at": now
        }

        _connectors[connector_id] = connector

        return ConnectorResponse(**connector)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/connectors/{connector_id}", response_model=ConnectorResponse)
async def get_connector(
    connector_id: str,
    session: Session = Depends(get_session)
):
    """
    Get a specific connector by ID.
    """
    try:
        if connector_id not in _connectors:
            raise HTTPException(status_code=404, detail=f"Connector '{connector_id}' not found")

        return ConnectorResponse(**_connectors[connector_id])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/connectors/{connector_id}", response_model=ConnectorResponse)
async def update_connector(
    connector_id: str,
    config: ConnectorConfig,
    session: Session = Depends(get_session)
):
    """
    Update an existing connector.
    """
    try:
        if connector_id not in _connectors:
            raise HTTPException(status_code=404, detail=f"Connector '{connector_id}' not found")

        connector = _connectors[connector_id]
        connector.update({
            "connector_type": config.connector_type,
            "name": config.name,
            "description": config.description,
            "connection_params": config.connection_params,
            "sync_frequency": config.sync_frequency,
            "enabled": config.enabled,
            "filters": config.filters,
            "updated_at": datetime.now().isoformat()
        })

        return ConnectorResponse(**connector)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/connectors/{connector_id}")
async def delete_connector(
    connector_id: str,
    session: Session = Depends(get_session)
):
    """
    Delete a connector.
    """
    try:
        if connector_id not in _connectors:
            raise HTTPException(status_code=404, detail=f"Connector '{connector_id}' not found")

        del _connectors[connector_id]

        # Also remove associated sources
        sources_to_delete = [sid for sid, s in _sources.items() if s["connector_id"] == connector_id]
        for sid in sources_to_delete:
            del _sources[sid]

        return {"status": "deleted", "connector_id": connector_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/connectors/{connector_id}/sync", response_model=SyncResultResponse)
async def sync_connector(
    connector_id: str,
    full_sync: bool = Query(False, description="Force full resync"),
    session: Session = Depends(get_session)
):
    """
    Trigger a sync for a connector.

    Fetches new and updated documents from the connected source.
    """
    try:
        if connector_id not in _connectors:
            raise HTTPException(status_code=404, detail=f"Connector '{connector_id}' not found")

        connector = _connectors[connector_id]
        started_at = datetime.now()

        # Update status to syncing
        connector["status"] = ConnectorStatus.SYNCING
        connector["updated_at"] = started_at.isoformat()

        # Simulate sync operation
        import random
        import time
        time.sleep(0.1)  # Simulate work

        docs_added = random.randint(0, 10)
        docs_updated = random.randint(0, 5)
        docs_deleted = random.randint(0, 2)

        completed_at = datetime.now()
        duration = (completed_at - started_at).total_seconds()

        # Update connector status
        connector["status"] = ConnectorStatus.ACTIVE
        connector["last_sync"] = completed_at.isoformat()
        connector["documents_synced"] = connector.get("documents_synced", 0) + docs_added
        connector["updated_at"] = completed_at.isoformat()

        result = SyncResultResponse(
            connector_id=connector_id,
            status="success",
            documents_added=docs_added,
            documents_updated=docs_updated,
            documents_deleted=docs_deleted,
            errors=[],
            duration_seconds=duration,
            started_at=started_at.isoformat(),
            completed_at=completed_at.isoformat()
        )

        _sync_history.append(result.dict())

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/connectors/{connector_id}/test")
async def test_connector(
    connector_id: str,
    session: Session = Depends(get_session)
):
    """
    Test connection to a connector's source.

    Verifies credentials and connectivity without syncing.
    """
    try:
        if connector_id not in _connectors:
            raise HTTPException(status_code=404, detail=f"Connector '{connector_id}' not found")

        connector = _connectors[connector_id]

        # Simulate connection test
        return {
            "connector_id": connector_id,
            "connector_type": connector["connector_type"],
            "connection_status": "success",
            "latency_ms": 45.2,
            "message": "Connection successful",
            "tested_at": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sources", response_model=List[KnowledgeSourceResponse])
async def list_sources(
    connector_id: Optional[str] = None,
    source_type: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """
    List all knowledge sources.

    Sources are individual data locations within connectors.
    """
    try:
        sources = list(_sources.values())

        if connector_id:
            sources = [s for s in sources if s["connector_id"] == connector_id]

        if source_type:
            sources = [s for s in sources if s["source_type"] == source_type]

        return [KnowledgeSourceResponse(**s) for s in sources]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sources")
async def add_source(
    connector_id: str = Body(..., embed=True),
    source_type: str = Body(..., embed=True),
    name: str = Body(..., embed=True),
    path: Optional[str] = Body(None, embed=True),
    session: Session = Depends(get_session)
):
    """
    Add a knowledge source to a connector.
    """
    try:
        if connector_id not in _connectors:
            raise HTTPException(status_code=404, detail=f"Connector '{connector_id}' not found")

        source_id = _generate_id()
        now = datetime.now().isoformat()

        source = {
            "id": source_id,
            "connector_id": connector_id,
            "source_type": source_type,
            "name": name,
            "path": path,
            "document_count": 0,
            "last_indexed": None,
            "status": "pending"
        }

        _sources[source_id] = source

        return KnowledgeSourceResponse(**source)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sources/{source_id}")
async def delete_source(
    source_id: str,
    session: Session = Depends(get_session)
):
    """
    Delete a knowledge source.
    """
    try:
        if source_id not in _sources:
            raise HTTPException(status_code=404, detail=f"Source '{source_id}' not found")

        del _sources[source_id]

        return {"status": "deleted", "source_id": source_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=SearchResultResponse)
async def search_knowledge_base(
    request: SearchKnowledgeRequest,
    session: Session = Depends(get_session)
):
    """
    Search across the knowledge base.

    Searches all connected sources or filtered subset.
    """
    try:
        import time
        start_time = time.time()

        # Simulate search results
        results = []
        for i in range(min(request.limit, 5)):
            results.append({
                "id": f"doc_{i}",
                "title": f"Document {i} matching '{request.query}'",
                "snippet": f"This is a snippet from document {i} that matches the query...",
                "score": 0.95 - (i * 0.1),
                "source_type": "file_system" if i % 2 == 0 else "github",
                "connector_id": list(_connectors.keys())[0] if _connectors else "default",
                "metadata": {
                    "path": f"/knowledge/doc_{i}.md",
                    "last_modified": datetime.now().isoformat()
                } if request.include_metadata else None
            })

        search_time = (time.time() - start_time) * 1000

        return SearchResultResponse(
            query=request.query,
            total_results=len(results),
            results=results,
            search_time_ms=search_time
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sync-history")
async def get_sync_history(
    connector_id: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session)
):
    """
    Get sync history.

    Returns recent sync operations and their results.
    """
    try:
        history = _sync_history

        if connector_id:
            history = [h for h in history if h["connector_id"] == connector_id]

        # Return most recent first
        return {
            "total": len(history),
            "history": history[-limit:][::-1]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_knowledge_base_stats(session: Session = Depends(get_session)):
    """
    Get knowledge base statistics.

    Returns overview of connectors, sources, and documents.
    """
    try:
        active_connectors = sum(1 for c in _connectors.values() if c["status"] == ConnectorStatus.ACTIVE)
        total_documents = sum(c.get("documents_synced", 0) for c in _connectors.values())
        total_sources = len(_sources)

        return {
            "connectors": {
                "total": len(_connectors),
                "active": active_connectors,
                "by_type": {}
            },
            "sources": {
                "total": total_sources,
                "by_type": {}
            },
            "documents": {
                "total": total_documents,
                "synced_today": 0,
                "pending": 0
            },
            "sync": {
                "last_sync": _sync_history[-1]["completed_at"] if _sync_history else None,
                "syncs_today": len(_sync_history),
                "total_syncs": len(_sync_history)
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def get_knowledge_base_health(session: Session = Depends(get_session)):
    """
    Get knowledge base health status.

    Checks connectivity and status of all connectors.
    """
    try:
        connector_health = []
        for cid, connector in _connectors.items():
            connector_health.append({
                "id": cid,
                "name": connector["name"],
                "type": connector["connector_type"],
                "status": connector["status"],
                "healthy": connector["status"] in [ConnectorStatus.ACTIVE, ConnectorStatus.SYNCING]
            })

        healthy_count = sum(1 for c in connector_health if c["healthy"])
        total_count = len(connector_health)

        if total_count == 0:
            status = "no_connectors"
        elif healthy_count == total_count:
            status = "healthy"
        elif healthy_count > 0:
            status = "degraded"
        else:
            status = "unhealthy"

        return {
            "status": status,
            "healthy_connectors": healthy_count,
            "total_connectors": total_count,
            "connectors": connector_health,
            "checked_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
