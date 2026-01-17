import logging
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime
class GenesisFileTracker:
    logger = logging.getLogger(__name__)
    """
    Creates Genesis Keys for ALL file operations.
    Complete provenance tracking for file management.

    Grace Principle: Complete Tracking
    - Every file operation creates a Genesis Key
    - Full context: what/where/when/who/how/why
    - Enables debugging, learning, and compliance
    """

    def __init__(self, genesis_service=None):
        """
        Initialize Genesis File Tracker.

        Args:
            genesis_service: Service for creating Genesis Keys
        """
        self.genesis_service = genesis_service
        logger.info("[GENESIS-FILE-TRACKER] Initialized")

    def track_file_upload(
        self,
        file_path: str,
        user_id: str = "system",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Track file upload with complete context.

        Args:
            file_path: Path to uploaded file
            user_id: User who uploaded
            metadata: Additional metadata

        Returns:
            Genesis Key ID
        """
        if not self.genesis_service:
            logger.debug("[GENESIS-FILE-TRACKER] No genesis service, skipping tracking")
            return None

        try:
            file_stats = Path(file_path).stat()
            metadata = metadata or {}

            context = {
                'operation': 'file_upload',
                'file_size': file_stats.st_size,
                'file_type': Path(file_path).suffix,
                'source': metadata.get('source', 'user'),
                **metadata
            }

            key_id = self.genesis_service.create_key(
                key_type='FILE_OPERATION',
                what=f"File uploaded: {Path(file_path).name}",
                where=str(file_path),
                when=datetime.utcnow(),
                who=user_id,
                why=metadata.get('reason', 'Knowledge base expansion'),
                how='file_upload_api',
                context=context
            )

            logger.info(
                f"[GENESIS-FILE-TRACKER] Tracked upload: {Path(file_path).name} "
                f"by {user_id} → Key: {key_id}"
            )

            return key_id

        except Exception as e:
            logger.error(f"[GENESIS-FILE-TRACKER] Failed to track upload: {e}")
            return None

    def track_file_processing(
        self,
        file_id: int,
        file_path: str,
        processing_result: Dict[str, Any]
    ) -> Optional[str]:
        """
        Track file processing outcome.

        Args:
            file_id: Document ID
            file_path: Path to file
            processing_result: Processing results

        Returns:
            Genesis Key ID
        """
        if not self.genesis_service:
            return None

        try:
            context = {
                'operation': 'file_processing',
                'document_id': file_id,
                'chunks_created': processing_result.get('num_chunks', 0),
                'embeddings_generated': processing_result.get('num_embeddings', 0),
                'processing_time': processing_result.get('duration', 0),
                'quality_score': processing_result.get('quality_score', 0.5),
                'strategy_used': processing_result.get('strategy', 'default'),
                'success': processing_result.get('success', True)
            }

            key_id = self.genesis_service.create_key(
                key_type='FILE_OPERATION',
                what=f"File processed: {Path(file_path).name}",
                where=f"document_id:{file_id}",
                when=datetime.utcnow(),
                who='ingestion_service',
                why='Convert file to searchable knowledge',
                how=processing_result.get('strategy', 'adaptive_processing'),
                context=context
            )

            logger.info(
                f"[GENESIS-FILE-TRACKER] Tracked processing: doc_id={file_id}, "
                f"chunks={context['chunks_created']} → Key: {key_id}"
            )

            return key_id

        except Exception as e:
            logger.error(f"[GENESIS-FILE-TRACKER] Failed to track processing: {e}")
            return None

    def track_health_check(
        self,
        health_result: Dict[str, Any]
    ) -> Optional[str]:
        """
        Track file system health check.

        Args:
            health_result: Health check results

        Returns:
            Genesis Key ID
        """
        if not self.genesis_service:
            return None

        try:
            context = {
                'operation': 'file_health_check',
                'health_status': health_result.get('health_status', 'unknown'),
                'anomalies_detected': len(health_result.get('anomalies', [])),
                'healing_actions_taken': len(health_result.get('healing_actions', [])),
                'anomalies': health_result.get('anomalies', []),
                'actions': health_result.get('healing_actions', [])
            }

            key_id = self.genesis_service.create_key(
                key_type='SYSTEM_HEALTH',
                what="File system health check",
                where='file_management_system',
                when=datetime.utcnow(),
                who='file_health_monitor',
                why='Ensure file system integrity',
                how='automated_health_scan',
                context=context
            )

            logger.info(
                f"[GENESIS-FILE-TRACKER] Tracked health check: "
                f"status={context['health_status']}, "
                f"anomalies={context['anomalies_detected']} → Key: {key_id}"
            )

            return key_id

        except Exception as e:
            logger.error(f"[GENESIS-FILE-TRACKER] Failed to track health check: {e}")
            return None

    def track_relationship_discovery(
        self,
        file_id: int,
        relationships: list
    ) -> Optional[str]:
        """
        Track file relationship detection.

        Args:
            file_id: Document ID
            relationships: Discovered relationships

        Returns:
            Genesis Key ID
        """
        if not self.genesis_service:
            return None

        try:
            relationship_types = list(set(r.get('type', 'unknown') for r in relationships))

            context = {
                'operation': 'relationship_discovery',
                'document_id': file_id,
                'relationships_found': len(relationships),
                'relationship_types': relationship_types,
                'relationships': relationships[:10]  # Store first 10
            }

            key_id = self.genesis_service.create_key(
                key_type='LEARNING_TASK',
                what=f"Discovered relationships for document {file_id}",
                where=f"document_id:{file_id}",
                when=datetime.utcnow(),
                who='relationship_engine',
                why='Build semantic knowledge graph',
                how='multi_method_relationship_detection',
                context=context
            )

            logger.info(
                f"[GENESIS-FILE-TRACKER] Tracked relationships: doc_id={file_id}, "
                f"count={len(relationships)} → Key: {key_id}"
            )

            return key_id

        except Exception as e:
            logger.error(f"[GENESIS-FILE-TRACKER] Failed to track relationships: {e}")
            return None

    def track_intelligence_extraction(
        self,
        file_path: str,
        intelligence: Dict[str, Any]
    ) -> Optional[str]:
        """
        Track file intelligence extraction.

        Args:
            file_path: Path to file
            intelligence: Extracted intelligence

        Returns:
            Genesis Key ID
        """
        if not self.genesis_service:
            return None

        try:
            context = {
                'operation': 'intelligence_extraction',
                'file_path': str(file_path),
                'quality_score': intelligence.get('quality_score', 0.5),
                'complexity_level': intelligence.get('complexity_level', 'unknown'),
                'topics_detected': len(intelligence.get('detected_topics', [])),
                'entities_extracted': sum(
                    len(v) for v in intelligence.get('extracted_entities', {}).values()
                ),
                'topics': intelligence.get('detected_topics', []),
                'summary': intelligence.get('content_summary', '')[:200]
            }

            key_id = self.genesis_service.create_key(
                key_type='FILE_OPERATION',
                what=f"Extracted intelligence: {Path(file_path).name}",
                where=str(file_path),
                when=datetime.utcnow(),
                who='file_intelligence_agent',
                why='Deep content understanding',
                how='ai_powered_analysis',
                context=context
            )

            logger.info(
                f"[GENESIS-FILE-TRACKER] Tracked intelligence: {Path(file_path).name}, "
                f"quality={context['quality_score']:.2f} → Key: {key_id}"
            )

            return key_id

        except Exception as e:
            logger.error(f"[GENESIS-FILE-TRACKER] Failed to track intelligence: {e}")
            return None

    def track_file_deletion(
        self,
        file_path: str,
        user_id: str = "system",
        reason: str = "user_request"
    ) -> Optional[str]:
        """
        Track file deletion.

        Args:
            file_path: Path to deleted file
            user_id: User who deleted
            reason: Reason for deletion

        Returns:
            Genesis Key ID
        """
        if not self.genesis_service:
            return None

        try:
            context = {
                'operation': 'file_deletion',
                'file_path': str(file_path),
                'file_name': Path(file_path).name,
                'reason': reason
            }

            key_id = self.genesis_service.create_key(
                key_type='FILE_OPERATION',
                what=f"File deleted: {Path(file_path).name}",
                where=str(file_path),
                when=datetime.utcnow(),
                who=user_id,
                why=reason,
                how='file_management_api',
                context=context
            )

            logger.info(
                f"[GENESIS-FILE-TRACKER] Tracked deletion: {Path(file_path).name} "
                f"by {user_id} → Key: {key_id}"
            )

            return key_id

        except Exception as e:
            logger.error(f"[GENESIS-FILE-TRACKER] Failed to track deletion: {e}")
            return None

    def track_adaptive_learning(
        self,
        file_type: str,
        strategy: Dict[str, Any],
        outcome: Dict[str, Any]
    ) -> Optional[str]:
        """
        Track adaptive learning from file processing.

        Args:
            file_type: Type of file
            strategy: Strategy used
            outcome: Processing outcome

        Returns:
            Genesis Key ID
        """
        if not self.genesis_service:
            return None

        try:
            context = {
                'operation': 'adaptive_learning',
                'file_type': file_type,
                'strategy_used': strategy,
                'success': outcome.get('success', False),
                'quality_score': outcome.get('quality_score', 0.5),
                'processing_time': outcome.get('duration', 0),
                'learned_from': 'processing_outcome'
            }

            # Calculate trust score based on outcome quality
            trust_score = outcome.get('quality_score', 0.5)
            if outcome.get('success', False) and trust_score >= 0.7:
                trust_score = 0.8  # High trust for successful learning
            elif not outcome.get('success', False):
                trust_score = 0.4  # Lower trust for failures
            
            key_id = self.genesis_service.create_key(
                key_type='LEARNING_TASK',
                what=f"Learned optimal strategy for {file_type}",
                where='adaptive_file_processor',
                when=datetime.utcnow(),
                who='strategy_learner',
                why='Continuous processing improvement',
                how='outcome_based_learning',
                context=context,
                metadata={
                    'outcome_type': 'file_processing_outcome',
                    'example_type': 'file_processing_outcome',
                    'trust_score': trust_score,
                    'success': outcome.get('success', False),
                    'file_type': file_type,
                    'quality_score': outcome.get('quality_score', 0.5)
                }
            )

            logger.info(
                f"[GENESIS-FILE-TRACKER] Tracked learning: {file_type}, "
                f"success={outcome.get('success')} → Key: {key_id}"
            )

            return key_id

        except Exception as e:
            logger.error(f"[GENESIS-FILE-TRACKER] Failed to track learning: {e}")
            return None


# Singleton instance
_genesis_tracker = None


def get_genesis_file_tracker(genesis_service=None) -> GenesisFileTracker:
    """
    Get or create GenesisFileTracker singleton.

    Args:
        genesis_service: Optional Genesis Key service

    Returns:
        GenesisFileTracker instance
    """
    global _genesis_tracker

    if _genesis_tracker is None:
        _genesis_tracker = GenesisFileTracker(genesis_service=genesis_service)

    return _genesis_tracker
