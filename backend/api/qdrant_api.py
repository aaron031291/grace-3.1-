"""
Simple Qdrant API — connection status and health.
"""
import os
from fastapi import APIRouter

router = APIRouter(prefix="/api/qdrant", tags=["Qdrant"])


@router.get("/status")
async def qdrant_status():
    """
    Simple Qdrant connection status.
    Returns connected, url, and collection list.
    """
    try:
        from vector_db.client import get_qdrant_client
        client = get_qdrant_client()
        connected = client.is_connected()
        try:
            from settings import settings
            url = (
                settings.QDRANT_URL
                if settings.QDRANT_URL
                else f"{settings.QDRANT_HOST}:{settings.QDRANT_PORT}"
            )
        except Exception:
            url = os.getenv("QDRANT_URL", "") or f"{os.getenv('QDRANT_HOST', 'localhost')}:{os.getenv('QDRANT_PORT', '6333')}"
        collections = []
        if connected:
            try:
                collections = client.list_collections()
            except Exception:
                pass
        return {
            "connected": connected,
            "url": url,
            "collections": collections,
        }
    except Exception as e:
        return {
            "connected": False,
            "url": None,
            "collections": [],
            "error": str(e),
        }
