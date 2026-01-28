"""
Grace File Health Monitor

Continuously monitors file system health.
Detects and heals issues autonomously.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from settings import settings

logger = logging.getLogger(__name__)


@dataclass
class HealthReport:
    """File system health check report."""

    health_status: str  # healthy, degraded, warning, critical
    anomalies: List[Dict[str, Any]]
    healing_actions: List[str]
    recommendations: List[str]
    timestamp: datetime


class FileHealthMonitor:
    """
    Continuously monitors file system health.
    Detects and heals issues autonomously.

    Grace Principle: Self-Healing
    - Proactive health monitoring
    - Autonomous issue detection
    - Trust-based healing execution
    - Learning from outcomes
    """

    def __init__(
        self,
        session=None,
        knowledge_base_path: str = "knowledge_base",
        trust_level: int = 5,
        genesis_tracker=None,
        dry_run: bool = True
    ):
        """
        Initialize File Health Monitor.

        Args:
            session: Database session
            knowledge_base_path: Path to knowledge base
            trust_level: Trust level for autonomous healing (0-9)
            genesis_tracker: GenesisFileTracker for tracking
            dry_run: If True, only report planned actions without mutating state
        """
        self.session = session
        self.knowledge_base_path = Path(knowledge_base_path)
        self.trust_level = trust_level
        self.genesis_tracker = genesis_tracker
        self.dry_run = dry_run

        self._embedding_model = None
        self._qdrant_client = None

        logger.info(
            f"[FILE-HEALTH] Monitor initialized: "
            f"trust_level={trust_level}, kb={knowledge_base_path}"
        )

    def _get_embedding_model(self):
        """Lazily load the embedding model singleton."""
        if self._embedding_model is not None:
            return self._embedding_model

        try:
            from embedding import get_embedding_model

            self._embedding_model = get_embedding_model(
                model_path=settings.EMBEDDING_MODEL_PATH,
                device=settings.EMBEDDING_DEVICE,
            )
            return self._embedding_model
        except Exception as e:
            logger.error(f"[FILE-HEALTH] Failed to load embedding model: {e}")
            return None

    def _get_qdrant_client(self):
        """Get or create the Qdrant client if available."""
        if self._qdrant_client is not None:
            return self._qdrant_client

        try:
            from vector_db.client import get_qdrant_client

            client = get_qdrant_client(
                host=settings.QDRANT_HOST,
                port=settings.QDRANT_PORT,
                api_key=settings.QDRANT_API_KEY or None,
            )

            if not client.is_connected():
                logger.error("[FILE-HEALTH] Qdrant client is not connected")
                return None

            self._qdrant_client = client
            return client
        except Exception as e:
            logger.error(f"[FILE-HEALTH] Failed to get Qdrant client: {e}")
            return None

    def _build_chunker(self):
        """Build a chunker configured with project settings."""
        from ingestion.service import TextChunker

        return TextChunker(
            chunk_size=settings.INGESTION_CHUNK_SIZE,
            chunk_overlap=settings.INGESTION_CHUNK_OVERLAP,
            embedding_model=self._get_embedding_model(),
            use_semantic_chunking=False,
            similarity_threshold=0.5,
        )

    def run_health_check_cycle(self) -> HealthReport:
        """
        Comprehensive file system health assessment.

        Returns:
            HealthReport with findings and actions
        """
        logger.info("[FILE-HEALTH] Starting health check cycle...")

        anomalies = []
        healing_actions = []

        # 1. Check for orphaned documents
        orphaned = self._detect_orphaned_documents()
        if orphaned:
            anomalies.append({
                'type': 'orphaned_documents',
                'severity': 'high',
                'count': len(orphaned),
                'files': [str(f) for f in orphaned[:10]]  # First 10
            })

            if self.trust_level >= 5:  # MEDIUM_RISK_AUTO
                if self.dry_run:
                    healing_actions.append(
                        f'planned_remove_{len(orphaned)}_orphaned_records'
                    )
                else:
                    healed_count = self._heal_orphaned_documents(orphaned)
                    healing_actions.append(
                        f'removed_{healed_count}_orphaned_records'
                    )

        # 2. Check for missing embeddings
        missing_embeddings = self._detect_missing_embeddings()
        if missing_embeddings:
            anomalies.append({
                'type': 'missing_embeddings',
                'severity': 'medium',
                'count': len(missing_embeddings)
            })

            if self.trust_level >= 3:  # LOW_RISK_AUTO
                if self.dry_run:
                    healing_actions.append(
                        f'planned_regenerate_{len(missing_embeddings)}_embeddings'
                    )
                else:
                    healed_count = self._heal_missing_embeddings(missing_embeddings)
                    healing_actions.append(
                        f'regenerated_{healed_count}_embeddings'
                    )

        # 3. Check for metadata corruption
        corrupt_metadata = self._detect_corrupt_metadata()
        if corrupt_metadata:
            anomalies.append({
                'type': 'corrupt_metadata',
                'severity': 'medium',
                'files': corrupt_metadata[:10]
            })

            if self.trust_level >= 5:
                if self.dry_run:
                    healing_actions.append(
                        f'planned_rebuild_{len(corrupt_metadata)}_metadata_files'
                    )
                else:
                    healed_count = self._heal_corrupt_metadata(corrupt_metadata)
                    healing_actions.append(
                        f'rebuilt_{healed_count}_metadata_files'
                    )

        # 4. Check for duplicates
        duplicates = self._detect_duplicates()
        if duplicates:
            anomalies.append({
                'type': 'duplicate_files',
                'severity': 'low',
                'groups': len(duplicates),
                'total_duplicates': sum(len(group) for group in duplicates)
            })

            if self.trust_level >= 7:  # HIGH_RISK_AUTO
                if self.dry_run:
                    healing_actions.append(
                        f'planned_merge_{len(duplicates)}_duplicate_groups'
                    )
                else:
                    merged_count = self._heal_duplicates(duplicates)
                    healing_actions.append(
                        f'merged_{merged_count}_duplicate_groups'
                    )

        # 5. Vector DB consistency check
        inconsistent = self._check_vector_db_consistency()
        if inconsistent:
            anomalies.append({
                'type': 'vector_db_inconsistency',
                'severity': 'high',
                'count': len(inconsistent)
            })

            if self.trust_level >= 5:
                if self.dry_run:
                    healing_actions.append(
                        f'planned_sync_{len(inconsistent)}_vector_records'
                    )
                else:
                    healed_count = self._heal_vector_inconsistencies(inconsistent)
                    healing_actions.append(
                        f'synced_{healed_count}_vector_records'
                    )

        # Calculate health status
        health_status = self._calculate_health_status(anomalies)

        # Generate recommendations
        recommendations = self._generate_recommendations(anomalies)

        # Create health report
        report = HealthReport(
            health_status=health_status,
            anomalies=anomalies,
            healing_actions=healing_actions,
            recommendations=recommendations,
            timestamp=datetime.utcnow()
        )

        # Track with Genesis Key
        if self.genesis_tracker:
            self.genesis_tracker.track_health_check({
                'health_status': health_status,
                'anomalies': anomalies,
                'healing_actions': healing_actions
            })

        logger.info(
            f"[FILE-HEALTH] Health check complete: status={health_status}, "
            f"anomalies={len(anomalies)}, actions={len(healing_actions)}"
        )

        return report

    def _detect_orphaned_documents(self) -> List[int]:
        """
        Detect documents in DB with missing files.

        Returns:
            List of orphaned document IDs
        """
        if not self.session:
            return []

        try:
            from models.database_models import Document

            orphaned = []
            documents = self.session.query(Document).all()

            for doc in documents:
                if doc.file_path:
                    file_path = Path(doc.file_path)
                    if not file_path.exists():
                        orphaned.append(doc.id)

            logger.debug(f"[FILE-HEALTH] Found {len(orphaned)} orphaned documents")
            return orphaned

        except Exception as e:
            logger.error(f"[FILE-HEALTH] Error detecting orphaned docs: {e}")
            return []

    def _heal_orphaned_documents(self, orphaned_ids: List[int]) -> int:
        """
        Heal orphaned documents by removing from DB.

        Returns:
            Number of documents healed
        """
        if not self.session:
            return 0

        try:
            from models.database_models import Document

            healed_count = 0
            for doc_id in orphaned_ids:
                doc = self.session.query(Document).filter(
                    Document.id == doc_id
                ).first()

                if doc:
                    self.session.delete(doc)
                    healed_count += 1

            self.session.commit()

            logger.info(f"[FILE-HEALTH] Healed {healed_count} orphaned documents")
            return healed_count

        except Exception as e:
            logger.error(f"[FILE-HEALTH] Error healing orphaned docs: {e}")
            self.session.rollback()
            return 0

    def _detect_missing_embeddings(self) -> List[int]:
        """
        Detect documents with missing vector embeddings.

        Returns:
            List of document IDs with missing embeddings
        """
        if not self.session:
            return []

        try:
            from models.database_models import Document, DocumentChunk

            missing = []
            documents = self.session.query(Document).filter(
                Document.status == 'completed'
            ).all()

            for doc in documents:
                # Check if chunks exist
                chunk_count = self.session.query(DocumentChunk).filter(
                    DocumentChunk.document_id == doc.id
                ).count()

                if chunk_count == 0:
                    missing.append(doc.id)

            logger.debug(f"[FILE-HEALTH] Found {len(missing)} docs with missing embeddings")
            return missing

        except Exception as e:
            logger.error(f"[FILE-HEALTH] Error detecting missing embeddings: {e}")
            return []

    def _heal_missing_embeddings(self, missing_ids: List[int]) -> int:
        """
        Heal missing embeddings by re-processing files.

        Returns:
            Number healed
        """
        if not self.session or not missing_ids:
            return 0

        healed_count = 0
        chunker = self._build_chunker()
        embedder = self._get_embedding_model()
        qdrant = self._get_qdrant_client()

        if embedder is None or qdrant is None:
            logger.error("[FILE-HEALTH] Cannot heal missing embeddings without embedder and Qdrant")
            return 0

        try:
            from models.database_models import Document, DocumentChunk

            for doc_id in missing_ids:
                doc = self.session.query(Document).filter(Document.id == doc_id).first()
                if not doc or not doc.file_path:
                    logger.warning(f"[FILE-HEALTH] Skipping doc {doc_id}: no file path")
                    continue

                file_path = Path(doc.file_path)
                if not file_path.exists():
                    logger.warning(f"[FILE-HEALTH] Skipping doc {doc_id}: file missing at {file_path}")
                    continue

                try:
                    text_content = file_path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    text_content = file_path.read_text(errors="ignore")
                except Exception as e:
                    logger.error(f"[FILE-HEALTH] Failed reading {file_path}: {e}")
                    continue

                if not text_content.strip():
                    logger.warning(f"[FILE-HEALTH] Skipping doc {doc_id}: empty file")
                    continue

                # Remove any existing chunks for a clean rebuild
                self.session.query(DocumentChunk).filter(
                    DocumentChunk.document_id == doc_id
                ).delete()

                chunks = chunker.chunk_text(text_content)
                vectors = []
                created_at = doc.created_at.isoformat() if doc.created_at else datetime.utcnow().isoformat()
                vector_base = int(f"{doc_id}000")

                for chunk_index, chunk in enumerate(chunks):
                    embedding = embedder.embed_text([chunk["text"]])[0]
                    vector_id = vector_base + chunk_index

                    chunk_metadata = {
                        "document_id": doc_id,
                        "chunk_index": chunk_index,
                        "filename": doc.filename,
                        "source": doc.source,
                        "created_at": created_at,
                    }

                    vectors.append((vector_id, embedding, chunk_metadata))

                    chunk_record = DocumentChunk(
                        document_id=doc_id,
                        chunk_index=chunk_index,
                        text_content=chunk["text"],
                        token_count=len(chunk["text"].split()),
                        embedding_vector_id=str(vector_id),
                        embedding_model=settings.EMBEDDING_DEFAULT,
                        char_start=chunk.get("char_start"),
                        char_end=chunk.get("char_end"),
                        chunk_metadata=json.dumps(chunk_metadata),
                        confidence_score=doc.confidence_score,
                    )
                    self.session.add(chunk_record)

                if vectors:
                    success = qdrant.upsert_vectors(
                        collection_name=settings.QDRANT_COLLECTION_NAME,
                        vectors=vectors,
                    )

                    if not success:
                        logger.error(f"[FILE-HEALTH] Failed upserting vectors for doc {doc_id}")
                        self.session.rollback()
                        continue

                doc.total_chunks = len(chunks)
                doc.status = "completed"
                self.session.commit()
                healed_count += 1

            return healed_count

        except Exception as e:
            logger.error(f"[FILE-HEALTH] Error healing missing embeddings: {e}")
            self.session.rollback()
            return healed_count

    def _detect_corrupt_metadata(self) -> List[str]:
        """
        Detect corrupted .metadata.json files.

        Returns:
            List of paths with corrupt metadata
        """
        corrupt = []

        if not self.knowledge_base_path.exists():
            return corrupt

        try:
            import json

            # Check main metadata file
            metadata_file = self.knowledge_base_path / ".metadata.json"
            if metadata_file.exists():
                try:
                    json.loads(metadata_file.read_text())
                except json.JSONDecodeError:
                    corrupt.append(str(metadata_file))

            logger.debug(f"[FILE-HEALTH] Found {len(corrupt)} corrupt metadata files")
            return corrupt

        except Exception as e:
            logger.error(f"[FILE-HEALTH] Error detecting corrupt metadata: {e}")
            return []

    def _heal_corrupt_metadata(self, corrupt_files: List[str]) -> int:
        """
        Heal corrupt metadata by rebuilding from DB.

        Returns:
            Number healed
        """
        if not corrupt_files:
            return 0

        try:
            from file_manager.knowledge_base_manager import KnowledgeBaseManager
            from models.database_models import Document

            kb_manager = KnowledgeBaseManager(base_path=str(self.knowledge_base_path))

            # Build a simple metadata map from the filesystem
            metadata: Dict[str, Any] = {}

            doc_by_path: Dict[str, Document] = {}
            if self.session:
                try:
                    documents = self.session.query(Document).all()
                    doc_by_path = {str(Path(doc.file_path)): doc for doc in documents if doc.file_path}
                except Exception as e:
                    logger.warning(f"[FILE-HEALTH] Skipping DB metadata merge: {e}")

            for file_path in self.knowledge_base_path.rglob("*"):
                if not file_path.is_file() or file_path.name == ".metadata.json":
                    continue

                relative_path = str(file_path.relative_to(self.knowledge_base_path))
                stat = file_path.stat()
                entry: Dict[str, Any] = {
                    "filename": file_path.name,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                }

                doc_match = doc_by_path.get(str(file_path))
                if doc_match:
                    entry.update({
                        "document_id": doc_match.id,
                        "content_hash": doc_match.content_hash,
                        "source": doc_match.source,
                    })

                metadata[f"files:{relative_path}"] = entry

            kb_manager._save_metadata(metadata)
            logger.info(f"[FILE-HEALTH] Rebuilt metadata for {len(metadata)} files")

            return len(corrupt_files)

        except Exception as e:
            logger.error(f"[FILE-HEALTH] Error rebuilding metadata: {e}")
            return 0

    def _detect_duplicates(self) -> List[List[int]]:
        """
        Detect duplicate files by content hash.

        Returns:
            List of duplicate groups (each group is list of doc IDs)
        """
        if not self.session:
            return []

        try:
            from models.database_models import Document
            from sqlalchemy import func

            # Find hashes that appear more than once
            duplicates = []
            hash_groups = self.session.query(
                Document.content_hash,
                func.count(Document.id).label('count')
            ).group_by(Document.content_hash).having(
                func.count(Document.id) > 1
            ).all()

            for content_hash, count in hash_groups:
                doc_ids = [
                    doc.id for doc in self.session.query(Document).filter(
                        Document.content_hash == content_hash
                    ).all()
                ]
                duplicates.append(doc_ids)

            logger.debug(f"[FILE-HEALTH] Found {len(duplicates)} duplicate groups")
            return duplicates

        except Exception as e:
            logger.error(f"[FILE-HEALTH] Error detecting duplicates: {e}")
            return []

    def _heal_duplicates(self, duplicate_groups: List[List[int]]) -> int:
        """
        Heal duplicates by keeping newest, removing others.

        Returns:
            Number of groups healed
        """
        if not self.session:
            return 0

        healed = 0
        qdrant = self._get_qdrant_client()

        try:
            from models.database_models import Document, DocumentChunk

            for group in duplicate_groups:
                docs = self.session.query(Document).filter(
                    Document.id.in_(group)
                ).order_by(Document.created_at.desc()).all()

                if len(docs) <= 1:
                    continue

                keeper = docs[0]
                to_remove = docs[1:]

                for dup in to_remove:
                    chunks = self.session.query(DocumentChunk).filter(
                        DocumentChunk.document_id == dup.id
                    ).all()

                    vector_ids: List[int] = []
                    for chunk in chunks:
                        try:
                            if chunk.embedding_vector_id:
                                vector_ids.append(int(chunk.embedding_vector_id))
                        except ValueError:
                            logger.debug(f"[FILE-HEALTH] Skipping non-numeric vector id for chunk {chunk.id}")

                    if qdrant and vector_ids:
                        qdrant.delete_vectors(
                            collection_name=settings.QDRANT_COLLECTION_NAME,
                            vector_ids=vector_ids,
                        )

                    self.session.delete(dup)

                self.session.commit()
                healed += 1
                logger.info(
                    f"[FILE-HEALTH] Merged duplicate group of {len(docs)} docs, kept {keeper.id}"
                )

            return healed

        except Exception as e:
            logger.error(f"[FILE-HEALTH] Error merging duplicates: {e}")
            self.session.rollback()
            return healed

    def _check_vector_db_consistency(self) -> List[int]:
        """
        Check if vector DB is consistent with database.

        Returns:
            List of document IDs with inconsistencies
        """
        if not self.session:
            return []

        inconsistent: List[int] = []
        qdrant = self._get_qdrant_client()

        if qdrant is None or qdrant.client is None:
            logger.warning("[FILE-HEALTH] Skipping vector consistency: Qdrant unavailable")
            return inconsistent

        try:
            from models.database_models import Document, DocumentChunk

            documents = self.session.query(Document).filter(
                Document.status == 'completed'
            ).all()

            for doc in documents:
                chunk_ids = self.session.query(DocumentChunk.embedding_vector_id).filter(
                    DocumentChunk.document_id == doc.id,
                    DocumentChunk.embedding_vector_id.isnot(None)
                ).all()

                vector_ids = []
                for cid in chunk_ids:
                    try:
                        vector_ids.append(int(cid[0]))
                    except (TypeError, ValueError):
                        logger.debug(f"[FILE-HEALTH] Non-numeric vector id in doc {doc.id}: {cid}")

                if not vector_ids:
                    continue

                existing: Set[int] = set()
                for start in range(0, len(vector_ids), 200):
                    batch = vector_ids[start:start + 200]
                    try:
                        points = qdrant.client.retrieve(
                            collection_name=settings.QDRANT_COLLECTION_NAME,
                            ids=batch,
                            with_payload=False,
                            with_vectors=False,
                        )
                        existing.update(int(p.id) for p in points)
                    except Exception as e:
                        logger.error(f"[FILE-HEALTH] Qdrant retrieve failed for doc {doc.id}: {e}")
                        break

                missing = [vid for vid in vector_ids if vid not in existing]
                if missing:
                    inconsistent.append(doc.id)
                    logger.warning(
                        f"[FILE-HEALTH] Doc {doc.id} missing {len(missing)} vectors in Qdrant"
                    )

            return inconsistent

        except Exception as e:
            logger.error(f"[FILE-HEALTH] Error checking vector consistency: {e}")
            return inconsistent

    def _heal_vector_inconsistencies(self, inconsistent_ids: List[int]) -> int:
        """
        Heal vector DB inconsistencies.

        Returns:
            Number healed
        """
        if not self.session or not inconsistent_ids:
            return 0

        embedder = self._get_embedding_model()
        qdrant = self._get_qdrant_client()

        if embedder is None or qdrant is None:
            logger.error("[FILE-HEALTH] Cannot heal vector inconsistencies without embedder/Qdrant")
            return 0

        healed = 0

        try:
            from models.database_models import DocumentChunk

            for doc_id in inconsistent_ids:
                chunks = self.session.query(DocumentChunk).filter(
                    DocumentChunk.document_id == doc_id
                ).order_by(DocumentChunk.chunk_index).all()

                if not chunks:
                    continue

                vectors = []
                vector_base = int(f"{doc_id}000")

                for chunk in chunks:
                    vector_id = None
                    try:
                        vector_id = int(chunk.embedding_vector_id) if chunk.embedding_vector_id else None
                    except (TypeError, ValueError):
                        vector_id = None

                    if vector_id is None:
                        vector_id = vector_base + chunk.chunk_index
                        chunk.embedding_vector_id = str(vector_id)

                    metadata = {}
                    if chunk.chunk_metadata:
                        try:
                            metadata = json.loads(chunk.chunk_metadata)
                        except Exception:
                            metadata = {}

                    metadata.setdefault("document_id", doc_id)
                    metadata.setdefault("chunk_index", chunk.chunk_index)

                    embedding = embedder.embed_text([chunk.text_content])[0]
                    vectors.append((vector_id, embedding, metadata))

                if vectors:
                    success = qdrant.upsert_vectors(
                        collection_name=settings.QDRANT_COLLECTION_NAME,
                        vectors=vectors,
                    )

                    if not success:
                        logger.error(f"[FILE-HEALTH] Failed to sync vectors for doc {doc_id}")
                        self.session.rollback()
                        continue

                self.session.commit()
                healed += 1

            return healed

        except Exception as e:
            logger.error(f"[FILE-HEALTH] Error healing vector inconsistencies: {e}")
            self.session.rollback()
            return healed

    def _calculate_health_status(self, anomalies: List[Dict]) -> str:
        """
        Calculate overall health status.

        Returns:
            'healthy', 'degraded', 'warning', or 'critical'
        """
        if not anomalies:
            return 'healthy'

        # Count by severity
        critical_count = sum(1 for a in anomalies if a['severity'] == 'critical')
        high_count = sum(1 for a in anomalies if a['severity'] == 'high')
        medium_count = sum(1 for a in anomalies if a['severity'] == 'medium')

        if critical_count > 0:
            return 'critical'
        elif high_count > 2:
            return 'warning'
        elif high_count > 0 or medium_count > 3:
            return 'degraded'
        else:
            return 'healthy'

    def _generate_recommendations(self, anomalies: List[Dict]) -> List[str]:
        """
        Generate recommendations based on anomalies.

        Returns:
            List of recommendation strings
        """
        recommendations = []

        for anomaly in anomalies:
            if anomaly['type'] == 'orphaned_documents':
                recommendations.append(
                    f"Clean up {anomaly['count']} orphaned document records"
                )
            elif anomaly['type'] == 'missing_embeddings':
                recommendations.append(
                    f"Re-ingest {anomaly['count']} files with missing embeddings"
                )
            elif anomaly['type'] == 'duplicate_files':
                recommendations.append(
                    f"Review and merge {anomaly.get('total_duplicates', 0)} duplicate files"
                )

        return recommendations


# Singleton instance
_health_monitor = None


def get_file_health_monitor(
    session=None,
    knowledge_base_path: str = "knowledge_base",
    trust_level: int = 5,
    genesis_tracker=None
) -> FileHealthMonitor:
    """
    Get or create FileHealthMonitor singleton.

    Args:
        session: Database session
        knowledge_base_path: Path to knowledge base
        trust_level: Trust level for healing (0-9)
        genesis_tracker: Genesis tracker instance

    Returns:
        FileHealthMonitor instance
    """
    global _health_monitor

    if _health_monitor is None:
        _health_monitor = FileHealthMonitor(
            session=session,
            knowledge_base_path=knowledge_base_path,
            trust_level=trust_level,
            genesis_tracker=genesis_tracker
        )

    return _health_monitor
