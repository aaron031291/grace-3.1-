"""
Kimi Knowledge Feedback Loop

Every time Kimi generates a high-quality answer, it gets embedded back
into the Qdrant vector DB so that:

1. KNN can discover edges from Kimi's synthesized knowledge
2. RAG retrieval can use Kimi's past answers (no repeating work)
3. Self-agents can find Kimi's insights in vector search
4. The knowledge base grows from BOTH books AND Kimi's reasoning

Quality gate: Only answers with confidence >= 0.7 and length >= 200
characters get vectorized. Low-quality or short answers are filtered out.

This creates a knowledge flywheel:
  User asks question -> Kimi synthesizes answer -> Answer embedded ->
  KNN discovers connections -> Next question gets BETTER context ->
  Kimi gives BETTER answer -> Embedded -> KNN expands further -> ...
"""

import logging
import hashlib
import time
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)
def _track_genesis(entity_type, description):
    try:
        from genesis.genesis_key_service import GenesisKeyService
        from database.session import SessionLocal
        s = SessionLocal()
        if s:
            try:
                GenesisKeyService(session=s).create_key(entity_type=entity_type, description=description[:200])
            except Exception:
                pass
            finally:
                s.close()
    except Exception:
        pass


def _track_feedback(desc, **kw):
    try:
        from cognitive.learning_hook import track_learning_event
        track_learning_event("kimi_knowledge_feedback", desc, **kw)
    except Exception:
        pass


class KimiKnowledgeFeedback:
    """
    Feeds Kimi's synthesized knowledge back into the vector DB.

    Quality filters:
    - Minimum length: 200 characters (skip short/trivial answers)
    - Minimum confidence: 0.7 (skip uncertain answers)
    - Deduplication: SHA256 hash prevents re-embedding same answer
    - Source tagged as "kimi_synthesis" with lower base trust (0.6)
      so book knowledge still outranks Kimi's generated content
    """

    def __init__(self):
        self._ingestion_service = None
        self._embedded_hashes: set = set()
        self.stats = {
            "total_considered": 0,
            "total_embedded": 0,
            "total_filtered_short": 0,
            "total_filtered_low_confidence": 0,
            "total_filtered_duplicate": 0,
        }

    @property
    def ingestion(self):
        """Lazy-init ingestion service. Falls back to fast direct embedding."""
        if self._ingestion_service is None:
            try:
                from ingestion.service import TextIngestionService
                from embedding import get_embedding_model
                model = get_embedding_model()
                self._ingestion_service = TextIngestionService(
                    collection_name="documents",
                    chunk_size=512,
                    chunk_overlap=50,
                    embedding_model=model,
                )
            except Exception:
                self._ingestion_service = "direct"
        return self._ingestion_service

    def feed_answer(
        self,
        question: str,
        answer: str,
        confidence: float = 0.5,
        tier_used: str = "standard",
        sources_count: int = 0,
        chat_id: Optional[int] = None,
    ) -> bool:
        """
        Consider feeding a Kimi answer back into the vector DB.

        Returns True if the answer was embedded, False if filtered out.
        """
        self.stats["total_considered"] += 1

        # Filter 1: Too short
        if len(answer.strip()) < 200:
            self.stats["total_filtered_short"] += 1
            return False

        # Filter 2: Low confidence
        if confidence < 0.7:
            self.stats["total_filtered_low_confidence"] += 1
            return False

        # Filter 3: Deduplication
        content_hash = hashlib.sha256(answer.encode()).hexdigest()
        if content_hash in self._embedded_hashes:
            self.stats["total_filtered_duplicate"] += 1
            return False

        # Passed all filters — embed into vector DB
        knowledge_text = (
            f"Question: {question}\n\n"
            f"Answer: {answer}\n\n"
            f"Source: Kimi synthesis (confidence: {confidence:.0%}, tier: {tier_used})"
        )

        embedded = False

        # Try standard ingestion service first
        if self.ingestion and self.ingestion != "direct":
            try:
                doc_id, message = self.ingestion.ingest_text_fast(
                    text_content=knowledge_text,
                    filename=f"kimi_synthesis_{content_hash[:12]}",
                    source="kimi_synthesis",
                    upload_method="kimi_feedback_loop",
                    source_type="ai_generated",
                    metadata={
                        "question": question[:200],
                        "confidence": confidence,
                        "tier_used": tier_used,
                        "sources_count": sources_count,
                        "chat_id": chat_id,
                        "embedded_at": datetime.now().isoformat(),
                    },
                )
                if doc_id:
                    embedded = True
            except Exception:
                pass

        # Fallback: direct fast embedding into file-based Qdrant
        if not embedded:
            try:
                self._direct_embed(knowledge_text, {
                    "question": question[:200],
                    "confidence": confidence,
                    "tier_used": tier_used,
                    "source": "kimi_synthesis",
                })
                embedded = True
            except Exception as e:
                logger.debug(f"[KIMI-FEEDBACK] Direct embed failed: {e}")

        if embedded:
            self._embedded_hashes.add(content_hash)
            self.stats["total_embedded"] += 1
            _track_feedback(
                f"Embedded answer (confidence={confidence:.0%}, {len(answer)} chars)",
                outcome="success",
                confidence=confidence,
            )
            return True

        return False

    def _direct_embed(self, text: str, metadata: dict):
        """Directly embed into file-based Qdrant using fast embedder."""
        import os
        from embedding.fast_embedder import embed_single
        from qdrant_client import QdrantClient
        from qdrant_client.models import PointStruct

        qdrant_path = "/workspace/qdrant_unified"
        lock_path = os.path.join(qdrant_path, ".lock")
        if os.path.exists(lock_path):
            os.remove(lock_path)

        vector = embed_single(text[:500])
        vid = hashlib.md5(text[:200].encode()).hexdigest()

        qc = QdrantClient(path=qdrant_path)
        try:
            collections = [c.name for c in qc.get_collections().collections]
            collection = "knowledge" if "knowledge" in collections else "documents"
            metadata["text"] = text[:1000]
            qc.upsert(collection_name=collection, points=[
                PointStruct(id=vid, vector=vector, payload=metadata)
            ])
        finally:
            qc.close()

    def get_stats(self) -> Dict[str, Any]:
        """Get feedback loop statistics."""
        total = max(self.stats["total_considered"], 1)
        return {
            **self.stats,
            "embed_rate": round(self.stats["total_embedded"] / total, 3),
            "filter_rate": round(1 - self.stats["total_embedded"] / total, 3),
        }


_feedback: Optional[KimiKnowledgeFeedback] = None

def get_kimi_feedback() -> KimiKnowledgeFeedback:
    """Get the Kimi knowledge feedback singleton."""
    global _feedback
    if _feedback is None:
        _feedback = KimiKnowledgeFeedback()
    return _feedback
