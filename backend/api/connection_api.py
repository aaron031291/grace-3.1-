"""
Connection Validation API
==========================
Exposes comprehensive connection validation via REST endpoints.

Endpoints:
- GET  /api/connections/status       - Quick status of all connections
- GET  /api/connections/validate     - Full validation with action checks
- GET  /api/connections/validate/{name} - Validate a single connection
- GET  /api/connections/summary      - Category-level summary
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/connections", tags=["Connection Validation"])


@router.get("/status")
async def connection_status():
    """
    Quick status check of all connections.
    Returns connection name, category, status, and connected boolean.
    Lightweight — no deep action validation.
    """
    from connection_validator import (
        validate_database,
        validate_qdrant,
        validate_llm_provider,
        validate_embedding_model,
        validate_serpapi,
        validate_kimi,
        validate_opus,
        validate_diagnostic_engine,
        validate_autonomous_loop,
        validate_websocket_manager,
        validate_genesis_tracking,
    )

    validators = [
        validate_database,
        validate_qdrant,
        validate_llm_provider,
        validate_embedding_model,
        validate_serpapi,
        validate_kimi,
        validate_opus,
        validate_diagnostic_engine,
        validate_autonomous_loop,
        validate_websocket_manager,
        validate_genesis_tracking,
    ]

    results = []
    for validator in validators:
        try:
            report = validator()
            results.append({
                "name": report.name,
                "category": report.category.value,
                "status": report.status.value,
                "connected": report.connected,
                "latency_ms": report.latency_ms,
                "message": report.message,
            })
        except Exception as e:
            results.append({
                "name": validator.__name__.replace("validate_", ""),
                "category": "unknown",
                "status": "error",
                "connected": False,
                "message": str(e),
            })

    connected = sum(1 for r in results if r["connected"])
    total = len(results)

    return {
        "status": "all_connected" if connected == total else "partial",
        "connected": connected,
        "total": total,
        "connections": results,
    }


@router.get("/validate")
async def validate_connections(
    include_layer1: bool = Query(True, description="Include Layer 1 connector validation"),
    include_background: bool = Query(True, description="Include background service validation"),
    include_external: bool = Query(True, description="Include external API validation"),
):
    """
    Full validation of ALL system connections.

    Checks every connection, validates each action it should perform,
    and returns a comprehensive report showing what's connected,
    what's not, and whether each action is doing its job.
    """
    from connection_validator import validate_all_connections

    report = validate_all_connections(
        include_layer1=include_layer1,
        include_background=include_background,
        include_external=include_external,
    )

    return report.to_dict()


@router.get("/validate/{connection_name}")
async def validate_single_connection(connection_name: str):
    """
    Validate a single connection by name.

    Supported names: database, qdrant, llm_provider, embedding_model,
    serpapi, kimi, opus, diagnostic_engine, autonomous_loop,
    continuous_learning, file_watcher, ml_intelligence,
    genesis_tracking, websocket_manager
    """
    from connection_validator import (
        validate_database,
        validate_qdrant,
        validate_llm_provider,
        validate_embedding_model,
        validate_serpapi,
        validate_kimi,
        validate_opus,
        validate_diagnostic_engine,
        validate_autonomous_loop,
        validate_continuous_learning,
        validate_file_watcher,
        validate_ml_intelligence,
        validate_genesis_tracking,
        validate_websocket_manager,
    )

    validator_map = {
        "database": validate_database,
        "qdrant": validate_qdrant,
        "llm_provider": validate_llm_provider,
        "embedding_model": validate_embedding_model,
        "serpapi": validate_serpapi,
        "kimi": validate_kimi,
        "opus": validate_opus,
        "diagnostic_engine": validate_diagnostic_engine,
        "autonomous_loop": validate_autonomous_loop,
        "continuous_learning": validate_continuous_learning,
        "file_watcher": validate_file_watcher,
        "ml_intelligence": validate_ml_intelligence,
        "genesis_tracking": validate_genesis_tracking,
        "websocket_manager": validate_websocket_manager,
    }

    if connection_name not in validator_map:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown connection: '{connection_name}'. "
                   f"Available: {', '.join(sorted(validator_map.keys()))}"
        )

    report = validator_map[connection_name]()
    return report.to_dict()


@router.get("/summary")
async def connection_summary():
    """
    High-level summary of connection status by category.

    Returns counts of connected/disconnected/degraded per category,
    plus total action validation pass/fail counts.
    """
    from connection_validator import validate_all_connections

    report = validate_all_connections()
    full = report.to_dict()

    return {
        "status": full["status"],
        "timestamp": full["timestamp"],
        "totals": {
            "connections": full["total_connections"],
            "connected": full["connected_count"],
            "disconnected": full["disconnected_count"],
            "degraded": full["degraded_count"],
        },
        "actions": {
            "validated": full["total_actions_validated"],
            "passing": full["total_actions_passing"],
            "failing": full["total_actions_failing"],
        },
        "categories": full["categories"],
    }


@router.get("/map")
async def connection_map():
    """
    Visual connection map showing all system connections,
    their relationships, and data flow paths.
    """
    from connection_validator import validate_all_connections

    report = validate_all_connections()

    data_flows = [
        {"from": "user_input", "to": "llm_provider", "label": "Chat queries"},
        {"from": "user_input", "to": "rag", "label": "Knowledge retrieval"},
        {"from": "ingestion", "to": "qdrant", "label": "Vector embeddings"},
        {"from": "ingestion", "to": "genesis_keys", "label": "Auto-create tracking keys"},
        {"from": "rag", "to": "qdrant", "label": "Vector search"},
        {"from": "rag", "to": "memory_mesh", "label": "Procedural context"},
        {"from": "rag", "to": "llm_orchestration", "label": "Answer generation"},
        {"from": "genesis_keys", "to": "memory_mesh", "label": "Learning linkage"},
        {"from": "memory_mesh", "to": "llm_orchestration", "label": "Skill registration"},
        {"from": "memory_mesh", "to": "autonomous_learning", "label": "Pattern detection"},
        {"from": "file_watcher", "to": "version_control", "label": "File change tracking"},
        {"from": "version_control", "to": "genesis_keys", "label": "Commit linkage"},
        {"from": "diagnostic_engine", "to": "websocket_manager", "label": "Health events"},
        {"from": "diagnostic_engine", "to": "autonomous_loop", "label": "Self-healing"},
        {"from": "continuous_learning", "to": "memory_mesh", "label": "Learning ingestion"},
        {"from": "llm_provider", "to": "database", "label": "Chat persistence"},
        {"from": "embedding_model", "to": "qdrant", "label": "Vector generation"},
    ]

    connection_statuses = {}
    for conn in report.connections:
        connection_statuses[conn.name] = {
            "status": conn.status.value,
            "connected": conn.connected,
            "actions_passing": conn.actions_passing,
            "actions_total": conn.actions_total,
        }

    return {
        "status": report.status,
        "connection_statuses": connection_statuses,
        "data_flows": data_flows,
        "total_connections": report.total_connections,
        "connected": report.connected_count,
    }
