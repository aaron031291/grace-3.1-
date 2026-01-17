"""
Enterprise Analytics API Endpoints

Provides unified API access to all enterprise analytics across all systems.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
from pathlib import Path
import logging

from database.session import get_session
from cognitive.memory_analytics import get_memory_analytics
from librarian.enterprise_librarian import get_enterprise_librarian
from retrieval.enterprise_rag import get_enterprise_rag
from world_model.enterprise_world_model import get_enterprise_world_model
from layer1.enterprise_message_bus import get_enterprise_message_bus
from layer1.enterprise_connectors import get_enterprise_layer1_connectors
from layer2.enterprise_cognitive_engine import get_enterprise_cognitive_engine
from layer2.enterprise_intelligence import get_enterprise_layer2_intelligence
from ml_intelligence.enterprise_neuro_symbolic import get_enterprise_neuro_symbolic

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/enterprise", tags=["enterprise"])

# Configuration
KNOWLEDGE_BASE_PATH = Path("backend/knowledge_base")
WORLD_MODEL_PATH = Path("backend/.genesis_world_model.json")


@router.get("/overview")
async def get_enterprise_overview(session: Session = Depends(get_session)):
    """Get overview of all enterprise systems."""
    try:
        return {
            "total_features": 51,
            "systems": 9,
            "systems_list": [
                "Memory System",
                "Librarian",
                "RAG",
                "World Model",
                "Layer 1 Message Bus",
                "Layer 1 Connectors",
                "Layer 2 Cognitive Engine",
                "Layer 2 Intelligence",
                "Neuro-Symbolic AI"
            ]
        }
    except Exception as e:
        logger.error(f"Error getting enterprise overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/analytics")
async def get_memory_analytics_endpoint(session: Session = Depends(get_session)):
    """Get memory system analytics."""
    try:
        analytics = get_memory_analytics(session, KNOWLEDGE_BASE_PATH)
        dashboard = analytics.get_comprehensive_dashboard()
        return dashboard
    except Exception as e:
        logger.error(f"Error getting memory analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/librarian/analytics")
async def get_librarian_analytics_endpoint(session: Session = Depends(get_session)):
    """Get librarian system analytics."""
    try:
        librarian = get_enterprise_librarian(session, KNOWLEDGE_BASE_PATH)
        analytics = librarian.get_librarian_analytics()
        return analytics
    except Exception as e:
        logger.warning(f"Error getting librarian analytics: {e}")
        # Return placeholder if not available
        return {
            "timestamp": None,
            "priorities": {"total_documents": 0},
            "clusters": {},
            "health": {"health_score": 0.0, "health_status": "unknown"},
            "top_tags": []
        }


@router.get("/rag/analytics")
async def get_rag_analytics_endpoint(session: Session = Depends(get_session)):
    """Get RAG system analytics."""
    try:
        # Note: This requires a retriever instance
        # For now, return placeholder
        return {
            "message": "RAG analytics endpoint - requires retriever instance",
            "status": "not_implemented"
        }
    except Exception as e:
        logger.error(f"Error getting RAG analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/world-model/analytics")
async def get_world_model_analytics_endpoint():
    """Get world model analytics."""
    try:
        world_model = get_enterprise_world_model(WORLD_MODEL_PATH)
        analytics = world_model.get_world_model_analytics()
        return analytics
    except Exception as e:
        logger.warning(f"Error getting world model analytics: {e}")
        # Return placeholder if not available
        return {
            "timestamp": None,
            "priorities": {"total_contexts": 0},
            "health": {"health_score": 0.0, "health_status": "unknown"},
            "contexts_by_type": {},
            "file_size_kb": 0
        }


@router.get("/layer1/analytics")
async def get_layer1_analytics_endpoint(session: Session = Depends(get_session)):
    """Get Layer 1 analytics."""
    try:
        # Note: This requires a message bus instance
        # For now, return placeholder
        return {
            "message": "Layer 1 analytics endpoint - requires message bus instance",
            "status": "not_implemented"
        }
    except Exception as e:
        logger.error(f"Error getting Layer 1 analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/layer2/analytics")
async def get_layer2_analytics_endpoint(session: Session = Depends(get_session)):
    """Get Layer 2 analytics."""
    try:
        # Note: This requires cognitive engine and intelligence instances
        # For now, return placeholder
        return {
            "message": "Layer 2 analytics endpoint - requires cognitive engine and intelligence instances",
            "status": "not_implemented"
        }
    except Exception as e:
        logger.error(f"Error getting Layer 2 analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/neuro-symbolic/analytics")
async def get_neuro_symbolic_analytics_endpoint(session: Session = Depends(get_session)):
    """Get neuro-symbolic AI analytics."""
    try:
        # Note: This requires a neuro-symbolic reasoner instance
        # For now, return placeholder
        return {
            "message": "Neuro-symbolic analytics endpoint - requires reasoner instance",
            "status": "not_implemented"
        }
    except Exception as e:
        logger.error(f"Error getting neuro-symbolic analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/unified-dashboard")
async def get_unified_dashboard(session: Session = Depends(get_session)):
    """Get unified dashboard with all systems."""
    try:
        dashboard = {
            "timestamp": None,
            "overview": {},
            "memory": None,
            "librarian": None,
            "rag": None,
            "world_model": None,
            "layer1": None,
            "layer2": None,
            "neuro_symbolic": None
        }

        # Get overview
        dashboard["overview"] = {
            "total_features": 51,
            "systems": 9
        }

        # Get memory analytics
        try:
            analytics = get_memory_analytics(session, KNOWLEDGE_BASE_PATH)
            dashboard["memory"] = analytics.get_comprehensive_dashboard()
        except Exception as e:
            logger.warning(f"Could not get memory analytics: {e}")

        # Get librarian analytics
        try:
            librarian = get_enterprise_librarian(session, KNOWLEDGE_BASE_PATH)
            dashboard["librarian"] = librarian.get_librarian_analytics()
        except Exception as e:
            logger.warning(f"Could not get librarian analytics: {e}")

        # Get world model analytics
        try:
            world_model = get_enterprise_world_model(WORLD_MODEL_PATH)
            dashboard["world_model"] = world_model.get_world_model_analytics()
        except Exception as e:
            logger.warning(f"Could not get world model analytics: {e}")

        return dashboard
    except Exception as e:
        logger.error(f"Error getting unified dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))
