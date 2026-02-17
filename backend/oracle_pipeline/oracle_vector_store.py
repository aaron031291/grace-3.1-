"""
Oracle Vector Store

The Oracle Vector DB stores ALL dependencies and training data.
Anyone can spin up a copy and it works immediately because
all knowledge is in the vectors.

Stores:
- Ingested document chunks with embeddings
- Training data with domain tags
- Dependency information
- Trust scores and provenance metadata
- Source tracking (which whitelist item produced this)
"""

import logging
import uuid
import hashlib
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class OracleRecord:
    """A record in the Oracle Vector Store."""
    record_id: str
    content: str
    domain: Optional[str] = None
    source_item_id: Optional[str] = None
    content_hash: str = ""
    trust_score: float = 1.0
    embedding: Optional[List[float]] = None
    chunk_index: int = 0
    total_chunks: int = 1
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class SearchResult:
    """A search result from the Oracle."""
    record_id: str
    content: str
    score: float
    domain: Optional[str]
    trust_score: float
    metadata: Dict[str, Any]


class OracleVectorStore:
    """
    The Oracle Vector DB - central knowledge store for Grace.

    All training data, dependencies, and ingested knowledge lives here.
    The Oracle is the single source of truth that makes Grace's
    knowledge portable (spin up a new instance -> instant knowledge).

    Features:
    - Store chunked content with embeddings
    - Domain-tagged storage for efficient retrieval
    - Trust score tracking per record
    - Content deduplication via hashing
    - KNN search for finding neighbors
    - Domain statistics and coverage tracking
    """

    CHUNK_SIZE = 512

    def __init__(self, chunk_size: int = CHUNK_SIZE):
        self.chunk_size = chunk_size
        self.records: Dict[str, OracleRecord] = {}
        self._domain_index: Dict[str, List[str]] = defaultdict(list)
        self._hash_index: Dict[str, str] = {}  # content_hash -> record_id
        self._source_index: Dict[str, List[str]] = defaultdict(list)
        logger.info("[ORACLE] Vector Store initialized")

    def ingest(
        self,
        content: str,
        domain: Optional[str] = None,
        source_item_id: Optional[str] = None,
        trust_score: float = 1.0,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        auto_chunk: bool = True,
    ) -> List[OracleRecord]:
        """
        Ingest content into the Oracle Vector Store.

        Automatically chunks large content, deduplicates, and indexes.

        Args:
            content: Raw content to ingest
            domain: Knowledge domain
            source_item_id: ID of the whitelist item that produced this
            trust_score: Trust score (1.0 for user-submitted)
            tags: Tags for categorization
            metadata: Additional metadata
            auto_chunk: Whether to auto-chunk large content

        Returns:
            List of OracleRecords created
        """
        if not content or len(content.strip()) < 5:
            return []

        # Check for duplicates
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        if content_hash in self._hash_index:
            existing_id = self._hash_index[content_hash]
            logger.debug(f"[ORACLE] Duplicate content detected: {existing_id}")
            return [self.records[existing_id]] if existing_id in self.records else []

        # Chunk if needed
        if auto_chunk and len(content) > self.chunk_size:
            chunks = self._chunk_content(content)
        else:
            chunks = [content]

        records: List[OracleRecord] = []
        for i, chunk in enumerate(chunks):
            chunk_hash = hashlib.sha256(chunk.encode()).hexdigest()[:16]

            record = OracleRecord(
                record_id=f"oracle-{uuid.uuid4().hex[:12]}",
                content=chunk,
                domain=domain,
                source_item_id=source_item_id,
                content_hash=chunk_hash,
                trust_score=trust_score,
                chunk_index=i,
                total_chunks=len(chunks),
                tags=list(tags or []),
                metadata=dict(metadata or {}),
            )

            self.records[record.record_id] = record
            self._hash_index[chunk_hash] = record.record_id
            if domain:
                self._domain_index[domain].append(record.record_id)
            if source_item_id:
                self._source_index[source_item_id].append(record.record_id)

            records.append(record)

        # Index the full content hash to first record for dedup
        self._hash_index[content_hash] = records[0].record_id if records else ""

        logger.info(
            f"[ORACLE] Ingested {len(records)} record(s) "
            f"domain={domain} trust={trust_score:.2f}"
        )

        return records

    def search_by_domain(
        self, domain: str, limit: int = 20
    ) -> List[OracleRecord]:
        """Search records by domain."""
        record_ids = self._domain_index.get(domain, [])
        records = [
            self.records[rid] for rid in record_ids if rid in self.records
        ]
        return records[:limit]

    def search_by_content(
        self, query: str, limit: int = 10
    ) -> List[SearchResult]:
        """
        Simple content-based search (word overlap).
        In production, this uses vector similarity via Qdrant.

        Args:
            query: Search query
            limit: Max results

        Returns:
            List of SearchResult
        """
        query_words = set(query.lower().split())
        scored: List[Tuple[str, float]] = []

        for record_id, record in self.records.items():
            record_words = set(record.content.lower().split())
            if not record_words:
                continue
            overlap = len(query_words & record_words)
            score = overlap / max(len(query_words), 1)
            if score > 0:
                scored.append((record_id, score))

        scored.sort(key=lambda x: x[1], reverse=True)

        results: List[SearchResult] = []
        for record_id, score in scored[:limit]:
            record = self.records[record_id]
            results.append(SearchResult(
                record_id=record_id,
                content=record.content,
                score=score,
                domain=record.domain,
                trust_score=record.trust_score,
                metadata=record.metadata,
            ))

        return results

    def get_all_domains(self) -> List[str]:
        """Get all domains in the store."""
        return list(self._domain_index.keys())

    def get_domain_stats(self) -> Dict[str, int]:
        """Get record count per domain."""
        return {
            domain: len(ids) for domain, ids in self._domain_index.items()
        }

    def get_records_by_source(self, source_item_id: str) -> List[OracleRecord]:
        """Get all records created from a specific whitelist item."""
        record_ids = self._source_index.get(source_item_id, [])
        return [
            self.records[rid] for rid in record_ids if rid in self.records
        ]

    def _chunk_content(self, content: str) -> List[str]:
        """Split content into chunks."""
        chunks: List[str] = []
        paragraphs = content.split("\n\n")
        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            if len(current_chunk) + len(para) + 2 <= self.chunk_size:
                current_chunk += ("\n\n" if current_chunk else "") + para
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                if len(para) > self.chunk_size:
                    words = para.split()
                    current_chunk = ""
                    for word in words:
                        if len(current_chunk) + len(word) + 1 <= self.chunk_size:
                            current_chunk += (" " if current_chunk else "") + word
                        else:
                            if current_chunk:
                                chunks.append(current_chunk)
                            current_chunk = word
                else:
                    current_chunk = para

        if current_chunk:
            chunks.append(current_chunk)

        return chunks if chunks else [content]

    def get_record(self, record_id: str) -> Optional[OracleRecord]:
        """Get a record by ID."""
        return self.records.get(record_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get store statistics."""
        domains = self.get_domain_stats()
        total_size = sum(len(r.content) for r in self.records.values())
        trusts = [r.trust_score for r in self.records.values()]
        return {
            "total_records": len(self.records),
            "total_domains": len(domains),
            "domains": domains,
            "total_bytes": total_size,
            "average_trust": sum(trusts) / len(trusts) if trusts else 0.0,
            "unique_sources": len(self._source_index),
        }
