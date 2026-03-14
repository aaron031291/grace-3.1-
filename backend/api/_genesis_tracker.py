"""
Thin Genesis Key tracking helper — ASYNC, NON-BLOCKING.

Fire-and-forget: genesis key creation never slows down the caller.
Qdrant embeddings batched and pushed when batch size reached (default 5) or timeout.
Memory Mesh feed removed (was crashing and blocking).
"""

import logging
import os
import threading
import queue
import time
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Batch size: upload when this many new keys are queued (default 5)
BATCH_SIZE = int(os.getenv("GENESIS_BATCH_SIZE", "5"))
# Max wait (seconds) before flushing a partial batch
BATCH_TIMEOUT_SEC = int(os.getenv("GENESIS_BATCH_TIMEOUT", "30"))
# Genesis keys Qdrant collection vector size (must match Qdrant Cloud collection; default 384 for all-MiniLM-L6-v2)
GENESIS_VECTOR_SIZE = int(os.getenv("GENESIS_VECTOR_SIZE", "384"))

# Background queue for Qdrant pushes (non-blocking)
_qdrant_queue = queue.SimpleQueue()
_qdrant_thread_started = False
# Backoff: after a 400, skip upserts until this time (avoid log spam and repeated failures)
_qdrant_backoff_until = 0.0
_qdrant_backoff_logged = False
# Seconds to skip upserts after a 400 (configurable via env)
QDRANT_BACKOFF_SEC = int(os.getenv("GENESIS_QDRANT_BACKOFF_SEC", "300"))


def _get_collection_vector_size(info) -> Optional[int]:
    """Extract vector size from Qdrant collection info. Handles config.params.vectors.size (Qdrant Cloud) and legacy config.params.size."""
    try:
        config = getattr(info, "config", None)
        if not config or not getattr(config, "params", None):
            return None
        params = config.params
        # Qdrant Cloud: config.params.vectors.size
        vectors = getattr(params, "vectors", None)
        if vectors is not None:
            size = getattr(vectors, "size", None)
            if size is not None:
                return int(size)
            # Named vectors: dict of name -> VectorParams
            if isinstance(vectors, dict) and vectors:
                first = next(iter(vectors.values()))
                return getattr(first, "size", None)
        # Legacy: config.params.size
        return getattr(params, "size", None)
    except Exception:
        return None


def _get_genesis_vector_size() -> int:
    """Effective vector size: GENESIS_VECTOR_SIZE env if set, else embedder dimension, else 384."""
    env_val = os.getenv("GENESIS_VECTOR_SIZE", "").strip()
    if env_val and env_val.isdigit():
        return int(env_val)
    try:
        from embedding.embedder import get_embedding_model
        model = get_embedding_model()
        if model and hasattr(model, "get_embedding_dimension"):
            return model.get_embedding_dimension()
    except Exception:
        pass
    return 384


def _vector_to_fixed_size(vec, size: int):
    """Return a list of length `size`: slice if longer, pad with zeros if shorter."""
    if vec is None:
        return [0.0] * size
    lst = vec.tolist() if hasattr(vec, "tolist") else list(vec)
    if len(lst) >= size:
        return lst[:size]
    return lst + [0.0] * (size - len(lst))


def _qdrant_safe_payload(item: dict, gk_id: str, key_type: str, what: str, where: str, tags: list) -> dict:
    """Build a payload with only types Qdrant accepts (str, int, float, bool, list of str)."""
    from datetime import datetime, timezone
    safe_tags = [str(t) for t in (tags or []) if t is not None][:100]
    return {
        "gk_id": str(gk_id)[:64],
        "genesis_key_id": str(gk_id)[:64],
        "key_type": str(key_type)[:64],
        "type": str(key_type)[:64],
        "what": str(what or "")[:500],
        "where": str(where or "")[:200],
        "tags": safe_tags,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _is_valid_point(vector: list, vec_size: int, payload: dict) -> bool:
    """Return True if point is safe to send to Qdrant (vector length and payload types)."""
    if not isinstance(vector, (list, tuple)) or len(vector) != vec_size:
        return False
    try:
        for v in vector:
            if not isinstance(v, (int, float)):
                return False
    except (TypeError, ValueError):
        return False
    if not isinstance(payload, dict):
        return False
    for k, v in payload.items():
        if v is None:
            continue
        if isinstance(v, (str, int, float, bool)):
            continue
        if isinstance(v, list) and all(isinstance(x, str) for x in v):
            continue
        return False
    return True


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
    try:
        from ml_intelligence.kpi_tracker import get_kpi_tracker
        get_kpi_tracker().increment_kpi("genesis_tracker", "requests", 1.0)
    except Exception:
        pass

    # Tiered storage — hot tier + sampling gate
    try:
        from core.genesis_storage import get_genesis_storage
        storage = get_genesis_storage()

        # Always store in hot tier (in-memory, instant)
        storage.store_hot(key_type, what, who, is_error, tags)

        # Sampling gate — high-frequency identical calls sampled at 1%
        if not storage.should_store(key_type, what, who):
            return None  # Sampled out — skip DB write, keep hot tier
    except Exception:
        pass

    # Fire real-time engine
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
            # Deterministic fallback (no random, no model)
            import hashlib
            payload = f"{key_type}|{what}|{who}|{where or ''}"
            gk_id = "GK-" + hashlib.sha256(payload.encode()).hexdigest()[:32]

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
        """Background thread: batch-uploads genesis keys to Qdrant when batch size (default 5) or timeout.
        Never raises: all failures are caught and logged; backoff after 400 to avoid log spam."""
        global _qdrant_backoff_until, _qdrant_backoff_logged
        if os.getenv("DISABLE_GENESIS_QDRANT_PUSH", "").strip().lower() in ("1", "true", "yes"):
            return
        qdrant_url = os.getenv("QDRANT_URL", "")
        qdrant_key = os.getenv("QDRANT_API_KEY", "")
        if not qdrant_url:
            return

        client = None
        effective_size = 384
        _collection_vector_size = None
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import PointStruct, VectorParams, Distance
            client = QdrantClient(url=qdrant_url, api_key=qdrant_key, timeout=10)
            effective_size = _get_genesis_vector_size()
            try:
                collections = [c.name for c in client.get_collections().collections]
                if "genesis_keys" not in collections:
                    client.create_collection("genesis_keys",
                        vectors_config=VectorParams(size=effective_size, distance=Distance.COSINE))
                    _collection_vector_size = effective_size
                else:
                    info = client.get_collection("genesis_keys")
                    _collection_vector_size = _get_collection_vector_size(info)
                    if _collection_vector_size is not None and _collection_vector_size != effective_size:
                        logger.warning(
                            "[GENESIS] Qdrant 'genesis_keys' vector size is %s but backend is using %s. "
                            "Set GENESIS_VECTOR_SIZE=%s in backend/.env (or drop the collection in Qdrant Cloud to let backend recreate it).",
                            _collection_vector_size, effective_size, _collection_vector_size,
                        )
            except Exception:
                pass
        except Exception as e:
            logger.warning("[GENESIS] Qdrant batch worker could not init client: %s. Genesis keys will not be pushed to Qdrant.", e)
            return

        buf = []
        last_flush_at = time.time()
        while True:
            try:
                try:
                    item = _qdrant_queue.get(timeout=2)
                    buf.append(item)
                except Exception:
                    pass

                now = time.time()
                # Respect backoff: after a 400 we skip upserts for a while
                if now < _qdrant_backoff_until:
                    if buf and not _qdrant_backoff_logged:
                        _qdrant_backoff_logged = True
                        logger.info("[GENESIS] Genesis keys Qdrant push in backoff until %s (set GENESIS_VECTOR_SIZE or DISABLE_GENESIS_QDRANT_PUSH=1 to fix).", time.ctime(_qdrant_backoff_until))
                    if buf:
                        buf.clear()
                        last_flush_at = now
                    continue

                should_flush = (
                    buf
                    and (
                        len(buf) >= BATCH_SIZE
                        or (now - last_flush_at) >= BATCH_TIMEOUT_SEC
                    )
                )
                if not should_flush:
                    continue

                import hashlib
                points = []
                # Safe join: tags may contain non-strings
                texts = []
                for item in buf:
                    tags = item.get("tags") or []
                    tag_str = " ".join(str(t) for t in tags if t is not None)
                    texts.append(f"{item.get('key_type','')} {item.get('what','')} {item.get('where','')} {tag_str}".strip())
                vectors_raw = None
                try:
                    from embedding.embedder import get_embedding_model
                    model = get_embedding_model()
                    if model and hasattr(model, "embed_text"):
                        emb = model.embed_text(texts, convert_to_numpy=True)
                        if emb is not None and (emb.shape[0] if hasattr(emb, "shape") else len(emb)) == len(buf):
                            vectors_raw = [emb[i] for i in range(len(buf))]
                except Exception:
                    pass
                # Use existing collection size when available so we match Qdrant and avoid 400
                vec_size = _collection_vector_size if _collection_vector_size is not None else _get_genesis_vector_size()
                for i, item in enumerate(buf):
                    if vectors_raw and i < len(vectors_raw) and vectors_raw[i] is not None:
                        vector = _vector_to_fixed_size(vectors_raw[i], vec_size)
                    else:
                        raw = hashlib.sha384(texts[i].encode()).digest()
                        vec48 = [b / 255.0 for b in raw]
                        vector = (vec48 * (vec_size // len(vec48) + 1))[:vec_size]
                    vector = [float(x) for x in vector]
                    pid = int(hashlib.md5(item["gk_id"].encode()).hexdigest()[:16], 16) % (2**63)
                    payload = _qdrant_safe_payload(
                        item, item["gk_id"], item["key_type"], item["what"],
                        item.get("where") or "", item.get("tags") or [],
                    )
                    if _is_valid_point(vector, vec_size, payload):
                        points.append(PointStruct(id=pid, vector=vector, payload=payload))
                if not points:
                    buf.clear()
                    last_flush_at = now
                    continue
                # vec_size already matches _collection_vector_size when collection exists (see above)
                try:
                    client.upsert("genesis_keys", points=points)
                    _qdrant_backoff_logged = False  # success clears one-time backoff log
                except Exception as e:
                    err_msg = str(e)
                    if "400" in err_msg or "Bad Request" in err_msg:
                        _qdrant_backoff_until = time.time() + QDRANT_BACKOFF_SEC
                        _qdrant_backoff_logged = False
                        hint = ""
                        try:
                            info = client.get_collection("genesis_keys")
                            actual = _get_collection_vector_size(info)
                            if actual is not None:
                                hint = " Collection vector size is %s — set GENESIS_VECTOR_SIZE=%s in backend/.env. " % (actual, actual)
                        except Exception:
                            pass
                        logger.error(
                            "[GENESIS] Qdrant upsert (genesis_keys) returns 400.%s Backoff %ss. Set GENESIS_VECTOR_SIZE or DISABLE_GENESIS_QDRANT_PUSH=1. Error: %s",
                            hint, QDRANT_BACKOFF_SEC, err_msg[:300],
                        )
                    else:
                        logger.error("[GENESIS] Qdrant upsert genesis_keys FAILED: %s", e, exc_info=True)
                buf.clear()
                last_flush_at = time.time()
                if os.getenv("HOT_RELOAD_ON_DATA_BATCH", "").strip().lower() in ("1", "true", "yes"):
                    try:
                        from core.hot_reload import hot_reload_all_services
                        hot_reload_all_services()
                    except Exception:
                        pass
            except Exception as e:
                logger.debug("[GENESIS] Qdrant batch worker loop error (non-fatal): %s", e)
                try:
                    buf.clear()
                except Exception:
                    pass
                last_flush_at = time.time()

    try:
        t = threading.Thread(target=_batch_worker, daemon=True, name="qdrant_batch")
        t.start()
    except Exception as e:
        logger.debug("[GENESIS] Could not start Qdrant batch thread: %s", e)


def _push_to_qdrant(gk_id: str, key_type: str, what: str, where: str, tags: list):
    """Push genesis key as embedding to Qdrant Cloud for vector search."""
    if os.getenv("DISABLE_GENESIS_QDRANT_PUSH", "").strip().lower() in ("1", "true", "yes"):
        return
    qdrant_url = os.getenv("QDRANT_URL", "")
    qdrant_key = os.getenv("QDRANT_API_KEY", "")

    if not qdrant_url:
        return

    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import PointStruct, VectorParams, Distance
        import hashlib
        from datetime import datetime

        client = QdrantClient(url=qdrant_url, api_key=qdrant_key, timeout=10)

        effective_size = _get_genesis_vector_size()
        # Ensure collection exists with effective vector size
        collections = [c.name for c in client.get_collections().collections]
        if "genesis_keys" not in collections:
            client.create_collection(
                collection_name="genesis_keys",
                vectors_config=VectorParams(size=effective_size, distance=Distance.COSINE),
            )

        tag_str = " ".join(str(t) for t in (tags or []) if t is not None)
        text = f"{key_type or ''} {what or ''} {where or ''} {tag_str}".strip()

        # Try real embedding first, then slice/pad to effective size
        vector = None
        try:
            from embedding.embedder import get_embedding_model
            model = get_embedding_model()
            if model and hasattr(model, "embed_text"):
                emb = model.embed_text(text, convert_to_numpy=True)
                if emb is not None and (hasattr(emb, "shape") and emb.size > 0):
                    vec = emb[0] if emb.ndim > 1 else emb
                    vector = _vector_to_fixed_size(vec, effective_size)
        except Exception:
            pass

        # Hash-based fallback: sha384 gives 48 bytes -> pad to effective size
        if not vector or len(vector) != effective_size:
            raw = hashlib.sha384(text.encode()).digest()
            vec48 = [b / 255.0 for b in raw]
            vector = (vec48 * (effective_size // len(vec48) + 1))[:effective_size]

        point_id = int(hashlib.md5(gk_id.encode()).hexdigest()[:16], 16) % (2**63)
        payload = _qdrant_safe_payload(
            {"gk_id": gk_id, "key_type": key_type, "what": what, "where": where or "", "tags": tags or []},
            gk_id, key_type, what, where or "", tags or [],
        )

        client.upsert(
            collection_name="genesis_keys",
            points=[PointStruct(id=point_id, vector=vector, payload=payload)],
        )
    except Exception as e:
        err_msg = str(e)
        if "400" in err_msg or "Bad Request" in err_msg:
            hint = ""
            try:
                from qdrant_client import QdrantClient as _QC
                _client = _QC(url=qdrant_url, api_key=qdrant_key, timeout=5)
                info = _client.get_collection("genesis_keys")
                actual = _get_collection_vector_size(info)
                if actual is not None:
                    hint = " Collection size is %s — set GENESIS_VECTOR_SIZE=%s in backend/.env. " % (actual, actual)
            except Exception:
                pass
            logger.error(
                "[GENESIS] Qdrant push genesis_keys 400 - backend vector size: %s.%s Or set DISABLE_GENESIS_QDRANT_PUSH=1. %s",
                _get_genesis_vector_size(), hint, err_msg[:200],
            )
        else:
            logger.error("[GENESIS] Qdrant push genesis_keys FAILED: %s", e, exc_info=True)
