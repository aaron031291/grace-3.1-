"""
Unified Vector Store - Single point of access for ALL vector operations.

Connects to Qdrant Cloud (persistent, shared) or falls back to local file.

Every component that touches vectors goes through THIS module:
  - GraceKnowledgeEngine
  - KNN sub-agent
  - Knowledge Daemon
  - KimiKnowledgeFeedback
  - Code Pattern Miner
  - RAG retrieval

Configuration (via environment or settings):
  QDRANT_CLOUD_URL  = https://your-cluster.cloud.qdrant.io:6333
  QDRANT_CLOUD_API_KEY = your-api-key

Falls back to local file at /workspace/qdrant_unified if no cloud config.
"""

import os
import logging
import hashlib
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

COLLECTION_NAME = "knowledge"
VECTOR_DIM = 384
LOCAL_PATH = "/workspace/qdrant_unified"

_client = None
_is_cloud = False


def _get_cloud_config():
    """Get Qdrant Cloud config from environment or settings."""
    url = os.environ.get("QDRANT_CLOUD_URL", "")
    api_key = os.environ.get("QDRANT_CLOUD_API_KEY", "")

    if not url or not api_key:
        try:
            from settings import settings
            url = getattr(settings, "QDRANT_CLOUD_URL", "") or ""
            api_key = getattr(settings, "QDRANT_CLOUD_API_KEY", "") or ""
        except Exception:
            pass

    return url.strip(), api_key.strip()


def get_client():
    """Get the Qdrant client - cloud if configured, local fallback."""
    global _client, _is_cloud
    from qdrant_client import QdrantClient

    if _client is not None:
        return _client

    url, api_key = _get_cloud_config()

    if url and api_key:
        try:
            _client = QdrantClient(url=url, api_key=api_key, timeout=60)
            _client.get_collections()
            _is_cloud = True
            logger.info(f"[VECTOR-STORE] Connected to Qdrant Cloud: {url[:40]}...")
            return _client
        except Exception as e:
            logger.warning(f"[VECTOR-STORE] Cloud connection failed: {e}, falling back to local")
            _client = None

    lock_path = os.path.join(LOCAL_PATH, ".lock")
    if os.path.exists(lock_path):
        os.remove(lock_path)

    _client = QdrantClient(path=LOCAL_PATH)
    _is_cloud = False
    logger.info(f"[VECTOR-STORE] Using local Qdrant at {LOCAL_PATH}")
    return _client


def reset_client():
    """Reset client (e.g., after config change)."""
    global _client, _is_cloud
    if _client:
        try:
            _client.close()
        except Exception:
            pass
    _client = None
    _is_cloud = False


def is_cloud() -> bool:
    """Check if we're connected to cloud."""
    return _is_cloud


def ensure_collection(collection: str = COLLECTION_NAME, dim: int = VECTOR_DIM):
    """Create collection if it doesn't exist."""
    from qdrant_client.models import VectorParams, Distance

    client = get_client()
    existing = [c.name for c in client.get_collections().collections]

    if collection not in existing:
        client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )
        logger.info(f"[VECTOR-STORE] Created collection '{collection}' (dim={dim})")
        return {"created": True, "collection": collection}

    info = client.get_collection(collection)
    return {"created": False, "collection": collection, "points": info.points_count}


def upsert(texts: List[str], payloads: List[Dict], collection: str = COLLECTION_NAME, batch_size: int = 256) -> int:
    """Embed texts and upsert to vector store. Returns count upserted."""
    from embedding.fast_embedder import embed_texts
    from qdrant_client.models import PointStruct

    client = get_client()
    total = 0

    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i + batch_size]
        batch_payloads = payloads[i:i + batch_size]

        embeddings = embed_texts(batch_texts, batch_size=batch_size)

        points = []
        for j in range(len(batch_texts)):
            vid = hashlib.md5(batch_texts[j][:200].encode()).hexdigest()
            payload = dict(batch_payloads[j])
            payload["text"] = batch_texts[j][:1000]
            points.append(PointStruct(id=vid, vector=embeddings[j], payload=payload))

        client.upsert(collection_name=collection, points=points)
        total += len(points)

    return total


def search(query: str, limit: int = 10, threshold: float = 0.3, collection: str = COLLECTION_NAME) -> List[Dict]:
    """Search vectors by text query. Returns list of results with scores."""
    from embedding.fast_embedder import embed_single

    client = get_client()
    embedding = embed_single(query)

    results = client.query_points(
        collection_name=collection,
        query=embedding,
        limit=limit,
    )

    hits = []
    if results and hasattr(results, "points"):
        for point in results.points:
            if point.score >= threshold:
                payload = point.payload or {}
                hits.append({
                    "text": payload.get("text", "")[:500],
                    "subject": payload.get("subject", ""),
                    "domain": payload.get("domain", ""),
                    "confidence": payload.get("confidence", 0),
                    "score": round(point.score, 4),
                    "source": payload.get("source", ""),
                    "type": payload.get("type", ""),
                })

    return hits


def count(collection: str = COLLECTION_NAME) -> int:
    """Get vector count in collection."""
    try:
        client = get_client()
        info = client.get_collection(collection)
        return info.points_count
    except Exception:
        return 0


def get_info() -> Dict[str, Any]:
    """Get vector store info."""
    client = get_client()
    collections = []

    for c in client.get_collections().collections:
        try:
            info = client.get_collection(c.name)
            collections.append({
                "name": c.name,
                "points": info.points_count,
                "vectors_size": info.config.params.vectors.size if hasattr(info.config.params.vectors, 'size') else None,
            })
        except Exception:
            collections.append({"name": c.name, "error": True})

    return {
        "cloud": _is_cloud,
        "url": _get_cloud_config()[0][:40] + "..." if _is_cloud else LOCAL_PATH,
        "collections": collections,
    }
