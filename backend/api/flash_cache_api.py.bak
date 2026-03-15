from fastapi import APIRouter
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/flash-cache", tags=["Flash Cache"])


@router.get("/status")
async def get_flash_cache_status() -> Dict[str, Any]:
    """Return flash cache status."""
    try:
        from cognitive.flash_cache import get_flash_cache
        fc = get_flash_cache()
        return fc.get_stats()
    except Exception as e:
        return {"total_entries": 0, "error": str(e)[:100]}
