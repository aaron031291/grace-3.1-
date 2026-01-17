"""
Enterprise Genesis Key Storage API

API endpoints for enterprise Genesis Key storage with:
- Smart querying and indexing
- Bulk operations
- Lifecycle management
- Statistics and analytics
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel
from pathlib import Path

from backend.database.session import get_session
from backend.genesis.enterprise_genesis_storage import (
    get_enterprise_genesis_storage,
    EnterpriseGenesisStorage
)
from backend.models.genesis_key_models import GenesisKeyType, GenesisKeyStatus

router = APIRouter(prefix="/api/enterprise/genesis", tags=["enterprise-genesis"])


class GenesisKeyQuery(BaseModel):
    """Query parameters for Genesis Key search."""
    query_text: Optional[str] = None
    key_type: Optional[str] = None
    file_path: Optional[str] = None
    user_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = 1000
    offset: int = 0


class GenesisKeyResponse(BaseModel):
    """Response model for Genesis Key."""
    key_id: str
    key_type: str
    status: str
    what_description: str
    where_location: Optional[str]
    when_timestamp: datetime
    who_actor: str
    file_path: Optional[str]
    user_id: Optional[str]


class GenesisKeySearchResponse(BaseModel):
    """Response model for Genesis Key search."""
    keys: List[GenesisKeyResponse]
    total_count: int
    limit: int
    offset: int


class LifecycleManagementResponse(BaseModel):
    """Response model for lifecycle management."""
    compressed: int
    archived: int
    errors: List[str]


class StorageStatisticsResponse(BaseModel):
    """Response model for storage statistics."""
    total_keys: int
    active_keys: int
    compressed_keys: int
    archived_keys: int
    cached_keys: int
    cache_hit_rate: float
    storage_estimates: Dict[str, float]
    performance: Dict[str, float]


class HealthMetricsResponse(BaseModel):
    """Response model for health metrics."""
    health_score: float
    health_status: str
    cache_efficiency: float
    storage_efficiency: float
    recommendations: List[str]


def get_genesis_storage(session: Session = Depends(get_session)) -> EnterpriseGenesisStorage:
    """Get enterprise Genesis Key storage instance."""
    return get_enterprise_genesis_storage(session, cache_size=1000)


@router.get("/key/{key_id}", response_model=GenesisKeyResponse)
async def get_genesis_key(
    key_id: str,
    storage: EnterpriseGenesisStorage = Depends(get_genesis_storage)
):
    """Get a single Genesis Key by ID."""
    key = storage.get_key_smart(key_id)
    if not key:
        raise HTTPException(status_code=404, detail=f"Genesis Key {key_id} not found")
    
    return GenesisKeyResponse(
        key_id=key.key_id,
        key_type=key.key_type.value if hasattr(key.key_type, 'value') else str(key.key_type),
        status=key.status.value if hasattr(key.status, 'value') else str(key.status),
        what_description=key.what_description,
        where_location=key.where_location,
        when_timestamp=key.when_timestamp,
        who_actor=key.who_actor,
        file_path=key.file_path,
        user_id=key.user_id
    )


@router.post("/search", response_model=GenesisKeySearchResponse)
async def search_genesis_keys(
    query: GenesisKeyQuery,
    storage: EnterpriseGenesisStorage = Depends(get_genesis_storage)
):
    """Search Genesis Keys with multiple filters."""
    # Convert string key_type to enum if provided
    key_type_enum = None
    if query.key_type:
        try:
            key_type_enum = GenesisKeyType(query.key_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid key_type: {query.key_type}")
    
    keys, total_count = storage.search_keys(
        query_text=query.query_text,
        key_type=key_type_enum,
        file_path=query.file_path,
        user_id=query.user_id,
        start_date=query.start_date,
        end_date=query.end_date,
        limit=query.limit,
        offset=query.offset
    )
    
    key_responses = [
        GenesisKeyResponse(
            key_id=key.key_id,
            key_type=key.key_type.value if hasattr(key.key_type, 'value') else str(key.key_type),
            status=key.status.value if hasattr(key.status, 'value') else str(key.status),
            what_description=key.what_description,
            where_location=key.where_location,
            when_timestamp=key.when_timestamp,
            who_actor=key.who_actor,
            file_path=key.file_path,
            user_id=key.user_id
        )
        for key in keys
    ]
    
    return GenesisKeySearchResponse(
        keys=key_responses,
        total_count=total_count,
        limit=query.limit,
        offset=query.offset
    )


@router.get("/by-type/{key_type}", response_model=List[GenesisKeyResponse])
async def get_keys_by_type(
    key_type: str,
    limit: int = Query(1000, ge=1, le=10000),
    offset: int = Query(0, ge=0),
    active_only: bool = Query(True),
    storage: EnterpriseGenesisStorage = Depends(get_genesis_storage)
):
    """Get Genesis Keys by type."""
    try:
        key_type_enum = GenesisKeyType(key_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid key_type: {key_type}")
    
    keys = storage.get_keys_by_type(key_type_enum, limit=limit, offset=offset, active_only=active_only)
    
    return [
        GenesisKeyResponse(
            key_id=key.key_id,
            key_type=key.key_type.value if hasattr(key.key_type, 'value') else str(key.key_type),
            status=key.status.value if hasattr(key.status, 'value') else str(key.status),
            what_description=key.what_description,
            where_location=key.where_location,
            when_timestamp=key.when_timestamp,
            who_actor=key.who_actor,
            file_path=key.file_path,
            user_id=key.user_id
        )
        for key in keys
    ]


@router.get("/by-file/{file_path:path}", response_model=List[GenesisKeyResponse])
async def get_keys_by_file(
    file_path: str,
    limit: int = Query(1000, ge=1, le=10000),
    storage: EnterpriseGenesisStorage = Depends(get_genesis_storage)
):
    """Get Genesis Keys by file path."""
    keys = storage.get_keys_by_file_path(file_path, limit=limit)
    
    return [
        GenesisKeyResponse(
            key_id=key.key_id,
            key_type=key.key_type.value if hasattr(key.key_type, 'value') else str(key.key_type),
            status=key.status.value if hasattr(key.status, 'value') else str(key.status),
            what_description=key.what_description,
            where_location=key.where_location,
            when_timestamp=key.when_timestamp,
            who_actor=key.who_actor,
            file_path=key.file_path,
            user_id=key.user_id
        )
        for key in keys
    ]


@router.post("/lifecycle/manage", response_model=LifecycleManagementResponse)
async def manage_lifecycle(
    force: bool = Query(False),
    storage: EnterpriseGenesisStorage = Depends(get_genesis_storage)
):
    """Manage Genesis Key lifecycle (compress and archive old keys)."""
    results = storage.manage_lifecycle(force=force)
    
    return LifecycleManagementResponse(
        compressed=results["compressed"],
        archived=results["archived"],
        errors=results["errors"]
    )


@router.get("/statistics", response_model=StorageStatisticsResponse)
async def get_statistics(
    storage: EnterpriseGenesisStorage = Depends(get_genesis_storage)
):
    """Get storage statistics."""
    stats = storage.get_statistics()
    
    return StorageStatisticsResponse(
        total_keys=stats["total_keys"],
        active_keys=stats["active_keys"],
        compressed_keys=stats["compressed_keys"],
        archived_keys=stats["archived_keys"],
        cached_keys=stats["cached_keys"],
        cache_hit_rate=stats["cache_hit_rate"],
        storage_estimates=stats["storage_estimates"],
        performance=stats["performance"]
    )


@router.get("/health", response_model=HealthMetricsResponse)
async def get_health_metrics(
    storage: EnterpriseGenesisStorage = Depends(get_genesis_storage)
):
    """Get storage health metrics."""
    metrics = storage.get_health_metrics()
    
    return HealthMetricsResponse(
        health_score=metrics["health_score"],
        health_status=metrics["health_status"],
        cache_efficiency=metrics["cache_efficiency"],
        storage_efficiency=metrics["storage_efficiency"],
        recommendations=metrics["recommendations"]
    )


@router.post("/cache/clear")
async def clear_cache(
    storage: EnterpriseGenesisStorage = Depends(get_genesis_storage)
):
    """Clear the cache."""
    storage.clear_cache()
    return {"message": "Cache cleared"}


@router.get("/count")
async def get_key_count(
    key_type: Optional[str] = None,
    active_only: bool = Query(True),
    storage: EnterpriseGenesisStorage = Depends(get_genesis_storage)
):
    """Get count of Genesis Keys."""
    if key_type:
        try:
            key_type_enum = GenesisKeyType(key_type)
            keys = storage.get_keys_by_type(key_type_enum, limit=100000, active_only=active_only)
            return {"count": len(keys), "key_type": key_type, "active_only": active_only}
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid key_type: {key_type}")
    else:
        stats = storage.get_statistics()
        return {
            "total_keys": stats["total_keys"],
            "active_keys": stats["active_keys"],
            "compressed_keys": stats["compressed_keys"],
            "archived_keys": stats["archived_keys"]
        }
