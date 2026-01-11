"""
Grace File Health Monitor

Continuously monitors file system health.
Detects and heals issues autonomously.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

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
        genesis_tracker=None
    ):
        """
        Initialize File Health Monitor.

        Args:
            session: Database session
            knowledge_base_path: Path to knowledge base
            trust_level: Trust level for autonomous healing (0-9)
            genesis_tracker: GenesisFileTracker for tracking
        """
        self.session = session
        self.knowledge_base_path = Path(knowledge_base_path)
        self.trust_level = trust_level
        self.genesis_tracker = genesis_tracker

        logger.info(
            f"[FILE-HEALTH] Monitor initialized: "
            f"trust_level={trust_level}, kb={knowledge_base_path}"
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
        # This would trigger re-ingestion
        # For now, just log the need
        logger.info(
            f"[FILE-HEALTH] Would re-ingest {len(missing_ids)} files "
            f"(not implemented yet)"
        )
        return 0

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
        logger.info(
            f"[FILE-HEALTH] Would rebuild {len(corrupt_files)} metadata files "
            f"(not implemented yet)"
        )
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
        logger.info(
            f"[FILE-HEALTH] Would merge {len(duplicate_groups)} duplicate groups "
            f"(not implemented yet)"
        )
        return 0

    def _check_vector_db_consistency(self) -> List[int]:
        """
        Check if vector DB is consistent with database.

        Returns:
            List of document IDs with inconsistencies
        """
        # This would query Qdrant and compare with DB
        logger.debug("[FILE-HEALTH] Vector DB consistency check (placeholder)")
        return []

    def _heal_vector_inconsistencies(self, inconsistent_ids: List[int]) -> int:
        """
        Heal vector DB inconsistencies.

        Returns:
            Number healed
        """
        logger.info(
            f"[FILE-HEALTH] Would sync {len(inconsistent_ids)} vector records "
            f"(not implemented yet)"
        )
        return 0

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
