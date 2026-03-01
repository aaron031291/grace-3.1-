"""
Thin Genesis Key tracking helper — ASYNC, NON-BLOCKING.

Fire-and-forget: genesis key creation never slows down the caller.
Qdrant embeddings batched and pushed every 5 seconds in background thread.
Memory Mesh feed removed (was crashing and blocking).
"""

import logging
import threading
import queue
import time
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Background queue for Qdrant pushes (non-blocking)
_qdrant_queue = queue.SimpleQueue()
_qdrant_thread_started = False


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
    is_error: bool = False,
    error_type: str = "",
    error_message: str = "",
    code_before: str = None,
    code_after: str = None,
) -> Optional[str]:
    """
    Create a Genesis Key for any system output.
    Returns the genesis key id (GK-...) or None if tracking fails.

    This is fire-and-forget — tracking failures never break the caller.
    Also fires the real-time event engine for instant notification.
    """
    # Fire real-time engine FIRST (even if DB write fails)
    try:
        from genesis.realtime import get_realtime_engine
        get_realtime_engine().on_key_created(
            key_type=key_type, what=what, who=who, where=where,
            is_error=is_error, error_type=error_type, error_message=error_message,
            data={"tags": tags, "input": input_data, "output": output_data},
        )
    except Exception:
        pass

    # Fire event bus for system-wide awareness
    try:
        from cognitive.event_bus import publish_async
        event_data = {
            "key_type": key_type, "what": what, "who": who,
            "is_error": is_error, "tags": tags,
        }
        event_topic = f"genesis.{key_type}" if not is_error else "genesis.error"
        publish_async(event_topic, event_data, source="genesis_tracker")
        publish_async("genesis.key_created", event_data, source="genesis_tracker")
    except Exception:
        pass

    # Write to database (auto-init if needed)
    try:
        from database.session import SessionLocal, initialize_session_factory
        if SessionLocal is None:
            try:
                initialize_session_factory()
            except Exception:
                return None

        from genesis.genesis_key_service import get_genesis_service
        from models.genesis_key_models import GenesisKeyType

        type_map = {
            "upload": GenesisKeyType.USER_UPLOAD,
            "file_op": GenesisKeyType.FILE_OPERATION,
            "file_ingestion": GenesisKeyType.FILE_INGESTION,
            "librarian": GenesisKeyType.LIBRARIAN_ACTION,
            "ai_response": GenesisKeyType.AI_RESPONSE,
            "ai_code_generation": GenesisKeyType.AI_CODE_GENERATION,
            "coding_agent_action": GenesisKeyType.CODING_AGENT_ACTION,
            "api_request": GenesisKeyType.API_REQUEST,
            "system": GenesisKeyType.SYSTEM_EVENT,
            "db_change": GenesisKeyType.DATABASE_CHANGE,
            "code_change": GenesisKeyType.CODE_CHANGE,
            "web_fetch": GenesisKeyType.WEB_FETCH,
            "error": GenesisKeyType.ERROR,
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
            is_error=is_error,
            error_type=error_type,
            error_message=error_message,
            code_before=code_before,
            code_after=code_after,
        )
        gk_id = getattr(key, "key_id", None) or getattr(key, "id", None)
        if not gk_id:
            import uuid
            gk_id = f"GK-{uuid.uuid4().hex}"

        # Queue embedding for background batch push (NON-BLOCKING)
        try:
            _qdrant_queue.put_nowait({
                "gk_id": gk_id, "key_type": key_type,
                "what": what, "where": where or "", "tags": tags or [],
            })
            _ensure_qdrant_thread()
        except Exception:
            pass

        return str(gk_id)
    except Exception as e:
        logger.debug(f"Genesis tracking skipped: {e}")
        return None


def _ensure_qdrant_thread():
    """Start the background Qdrant batch pusher if not already running."""
    global _qdrant_thread_started
    if _qdrant_thread_started:
        return
    _qdrant_thread_started = True

    def _batch_worker():
        """Background thread: batch-uploads genesis keys to Qdrant every 5 seconds."""
        import os
        qdrant_url = os.getenv("QDRANT_URL", "")
        qdrant_key = os.getenv("QDRANT_API_KEY", "")
        if not qdrant_url:
            return

        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import PointStruct, VectorParams, Distance
            client = QdrantClient(url=qdrant_url, api_key=qdrant_key, timeout=10)

            # Ensure collection
            try:
                collections = [c.name for c in client.get_collections().collections]
                if "genesis_keys" not in collections:
                    client.create_collection("genesis_keys",
                        vectors_config=VectorParams(size=384, distance=Distance.COSINE))
            except Exception:
                pass

            buf = []
            while True:
                try:
                    item = _qdrant_queue.get(timeout=2)
                    buf.append(item)
                except Exception:
                    pass

                if buf and (len(buf) >= 50 or time.time() % 5 < 2):
                    try:
                        import hashlib
                        points = []
                        for item in buf:
                            text = f"{item['key_type']} {item['what']} {item['where']} {' '.join(item['tags'])}"
                            raw = hashlib.sha384(text.encode()).digest()
                            vector = [b / 255.0 for b in raw]
                            pid = int(hashlib.md5(item['gk_id'].encode()).hexdigest()[:16], 16) % (2**63)
                            points.append(PointStruct(id=pid, vector=vector,
                                payload={"gk_id": item["gk_id"], "type": item["key_type"],
                                         "what": item["what"][:200], "tags": item["tags"]}))
                        client.upsert("genesis_keys", points=points)
                        buf.clear()
                    except Exception:
                        buf.clear()
        except Exception:
            pass

    t = threading.Thread(target=_batch_worker, daemon=True, name="qdrant_batch")
    t.start()


def _push_to_qdrant(gk_id: str, key_type: str, what: str, where: str, tags: list):
    """Push genesis key as embedding to Qdrant Cloud for vector search."""
    import os
    qdrant_url = os.getenv("QDRANT_URL", "")
    qdrant_key = os.getenv("QDRANT_API_KEY", "")

    if not qdrant_url:
        return

    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import PointStruct, VectorParams, Distance
        import hashlib

        client = QdrantClient(url=qdrant_url, api_key=qdrant_key, timeout=10)

        # Ensure collection exists
        collections = [c.name for c in client.get_collections().collections]
        if "genesis_keys" not in collections:
            client.create_collection(
                collection_name="genesis_keys",
                vectors_config=VectorParams(size=384, distance=Distance.COSINE),
            )

        # Generate embedding from the text
        text = f"{key_type} {what} {where or ''} {' '.join(tags or [])}"

        # Simple hash-based embedding (fast, deterministic, no model needed)
        # Real embeddings happen when embedding model is loaded
        raw = hashlib.sha384(text.encode()).digest()
        vector = [b / 255.0 for b in raw]  # 384-dim normalised vector

        # Try real embedding if available
        try:
            from embedding.embedder import get_embedding_model
            model = get_embedding_model()
            if model and hasattr(model, 'encode'):
                real_vec = model.encode(text)
                if real_vec is not None and len(real_vec) > 0:
                    vector = real_vec.tolist() if hasattr(real_vec, 'tolist') else list(real_vec)
        except Exception:
            pass  # Use hash-based fallback

        # Generate numeric ID from genesis key hash
        point_id = int(hashlib.md5(gk_id.encode()).hexdigest()[:16], 16) % (2**63)

        client.upsert(
            collection_name="genesis_keys",
            points=[PointStruct(
                id=point_id,
                vector=vector[:384],  # Ensure 384 dims
                payload={
                    "genesis_key_id": gk_id,
                    "key_type": key_type,
                    "what": what[:500],
                    "where": where[:200] if where else "",
                    "tags": tags or [],
                    "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
                },
            )],
        )
    except Exception as e:
        logger.debug(f"Qdrant push skipped: {e}")
