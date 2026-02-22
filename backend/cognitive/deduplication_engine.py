"""
Deduplication Engine

Multi-layer deduplication to prevent duplicate data from entering
any part of the system:

Layer 1 — File-level: SHA256 hash of raw file content (ingestion service)
Layer 2 — Chunk-level: Hash of chunk text before embedding (ingestion)
Layer 3 — Semantic-level: Cosine similarity check against existing vectors
Layer 4 — Oracle-level: Unified intelligence record dedup
Layer 5 — Pipeline-level: Processed seeds set (neighbor expansion)

This engine adds Layer 3 (semantic) and Layer 4 (Oracle) which were missing.

Classes:
- `DeduplicationEngine`

Key Methods:
- `check_file_duplicate()`
- `check_semantic_duplicate()`
- `check_title_duplicate()`
- `check_oracle_record_duplicate()`
- `get_stats()`
- `get_dedup_engine()`

Database Tables:
None (no DB tables)

Connects To:
- `genesis.unified_intelligence`
- `retrieval.retriever`
"""

import logging
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class DeduplicationEngine:
    """
    Multi-layer deduplication for all data entering Grace.

    Prevents:
    - Same file ingested twice (SHA256 hash)
    - Same chunk embedded twice (chunk hash)
    - Semantically identical content (cosine similarity > 0.95)
    - Duplicate Oracle intelligence records
    - Duplicate pipeline seeds
    """

    def __init__(self):
        self._file_hashes: set = set()
        self._chunk_hashes: set = set()
        self._known_titles: set = set()

    def check_file_duplicate(self, file_path: str = None, content: bytes = None) -> Tuple[bool, str]:
        """
        Check if a file is a duplicate before ingestion.

        Returns (is_duplicate, hash).
        """
        if content:
            h = hashlib.sha256(content).hexdigest()
        elif file_path:
            try:
                with open(file_path, "rb") as f:
                    h = hashlib.sha256(f.read()).hexdigest()
            except Exception:
                return False, ""
        else:
            return False, ""

        if h in self._file_hashes:
            return True, h

        self._file_hashes.add(h)
        return False, h

    def check_semantic_duplicate(
        self, text: str, threshold: float = 0.95
    ) -> Tuple[bool, float]:
        """
        Check if text is semantically duplicate of existing content.

        Uses embedding similarity against existing vectors.
        Returns (is_duplicate, similarity_score).
        """
        try:
            from retrieval.retriever import DocumentRetriever
            from embedding import get_embedding_model
            model = get_embedding_model()
            retriever = DocumentRetriever(
                collection_name="documents", embedding_model=model
            )
            results = retriever.retrieve(
                query=text[:500], limit=1, score_threshold=threshold
            )
            if results and results[0].get("score", 0) >= threshold:
                return True, results[0]["score"]
        except Exception:
            pass
        return False, 0.0

    def check_title_duplicate(self, title: str) -> bool:
        """Check if a document with this title was already processed."""
        normalized = title.lower().strip()
        if normalized in self._known_titles:
            return True
        self._known_titles.add(normalized)
        return False

    def check_oracle_record_duplicate(
        self, source_system: str, signal_name: str, session=None
    ) -> bool:
        """Check if this exact Oracle record already exists recently."""
        if not session:
            return False
        try:
            from genesis.unified_intelligence import UnifiedIntelligenceRecord
            from datetime import timedelta
            cutoff = datetime.now() - timedelta(minutes=5)
            exists = session.query(UnifiedIntelligenceRecord).filter(
                UnifiedIntelligenceRecord.source_system == source_system,
                UnifiedIntelligenceRecord.signal_name == signal_name,
                UnifiedIntelligenceRecord.recorded_at >= cutoff
            ).first()
            return exists is not None
        except Exception:
            return False

    def get_stats(self) -> Dict[str, Any]:
        return {
            "file_hashes_tracked": len(self._file_hashes),
            "chunk_hashes_tracked": len(self._chunk_hashes),
            "titles_tracked": len(self._known_titles),
        }


_dedup: Optional[DeduplicationEngine] = None

def get_dedup_engine() -> DeduplicationEngine:
    global _dedup
    if _dedup is None:
        _dedup = DeduplicationEngine()
    return _dedup
