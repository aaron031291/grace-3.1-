"""
Thin Genesis Key tracking helper used by all CRUD APIs.

Every new output — uploads, directories, subdirectories, files,
document registrations, edits, and intelligence operations — gets
a Genesis Key so the full provenance chain is preserved.
"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def track(
    key_type: str,
    what: str,
    who: str = "system",
    where: str = "",
    why: str = "",
    how: str = "",
    file_path: str = "",
    input_data: Optional[Dict[str, Any]] = None,
    output_data: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
    tags: Optional[list] = None,
    parent_key_id: Optional[str] = None,
) -> Optional[str]:
    """
    Create a Genesis Key for any system output.
    Returns the genesis key id (GK-...) or None if tracking fails.

    This is fire-and-forget — tracking failures never break the caller.
    """
    try:
        from genesis.genesis_key_service import get_genesis_service
        from models.genesis_key_models import GenesisKeyType

        type_map = {
            "upload": GenesisKeyType.USER_UPLOAD,
            "file_op": GenesisKeyType.FILE_OPERATION,
            "file_ingestion": GenesisKeyType.FILE_INGESTION,
            "librarian": GenesisKeyType.LIBRARIAN_ACTION,
            "ai_response": GenesisKeyType.AI_RESPONSE,
            "api_request": GenesisKeyType.API_REQUEST,
            "system": GenesisKeyType.SYSTEM_EVENT,
            "db_change": GenesisKeyType.DATABASE_CHANGE,
        }
        gk_type = type_map.get(key_type, GenesisKeyType.SYSTEM_EVENT)

        service = get_genesis_service()
        key = service.create_key(
            key_type=gk_type,
            what_description=what,
            who_actor=who,
            where_location=where,
            why_reason=why,
            how_method=how,
            file_path=file_path or None,
            input_data=input_data,
            output_data=output_data,
            context_data=context,
            tags=tags,
            parent_key_id=parent_key_id,
        )
        gk_id = getattr(key, "key_id", None) or getattr(key, "id", None)
        return str(gk_id) if gk_id else None
    except Exception as e:
        logger.debug(f"Genesis tracking skipped: {e}")
        return None
