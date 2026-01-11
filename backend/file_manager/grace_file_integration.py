"""
Grace File Management Integration

Integrates all Grace-aligned file management components:
- FileIntelligenceAgent (deep understanding)
- AdaptiveFileProcessor (learning-based optimization)
- FileHealthMonitor (autonomous health)
- GenesisFileTracker (complete tracking)
"""

import logging
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import time

logger = logging.getLogger(__name__)


class GraceFileManager:
    """
    Complete Grace-aligned file management system.

    Integrates:
    - Deep content understanding
    - Adaptive learning
    - Health monitoring
    - Complete tracking
    """

    def __init__(
        self,
        session=None,
        knowledge_base_path: str = "knowledge_base",
        trust_level: int = 5,
        genesis_service=None
    ):
        """
        Initialize Grace File Manager.

        Args:
            session: Database session
            knowledge_base_path: Path to knowledge base
            trust_level: Trust level for autonomous actions
            genesis_service: Genesis Key service
        """
        self.session = session
        self.knowledge_base_path = Path(knowledge_base_path)
        self.trust_level = trust_level

        # Initialize components
        from file_manager.file_intelligence_agent import get_file_intelligence_agent
        from file_manager.adaptive_file_processor import get_adaptive_file_processor
        from file_manager.file_health_monitor import get_file_health_monitor
        from file_manager.genesis_file_tracker import get_genesis_file_tracker

        self.genesis_tracker = get_genesis_file_tracker(genesis_service=genesis_service)

        self.intelligence_agent = get_file_intelligence_agent()

        self.adaptive_processor = get_adaptive_file_processor(
            session=session,
            intelligence_agent=self.intelligence_agent,
            genesis_tracker=self.genesis_tracker
        )

        self.health_monitor = get_file_health_monitor(
            session=session,
            knowledge_base_path=str(self.knowledge_base_path),
            trust_level=trust_level,
            genesis_tracker=self.genesis_tracker
        )

        logger.info(
            f"[GRACE-FILE-MANAGER] Initialized with trust_level={trust_level}, "
            f"kb={knowledge_base_path}"
        )

    def process_file_intelligently(
        self,
        file_path: str,
        user_id: str = "system",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a file with full Grace intelligence.

        This is the main entry point for file processing with:
        1. Deep content understanding
        2. Adaptive strategy selection
        3. Complete tracking
        4. Learning from outcomes

        Args:
            file_path: Path to file
            user_id: User who uploaded
            metadata: Additional metadata

        Returns:
            Processing result dict
        """
        start_time = time.time()
        path = Path(file_path)

        logger.info(
            f"[GRACE-FILE-MANAGER] Processing file intelligently: {path.name}"
        )

        try:
            # Step 1: Track file upload
            upload_key_id = self.genesis_tracker.track_file_upload(
                file_path=file_path,
                user_id=user_id,
                metadata=metadata
            )

            # Step 2: Deep content analysis
            logger.info("[GRACE-FILE-MANAGER] Analyzing file content...")
            intelligence = self.intelligence_agent.analyze_file_deeply(
                file_path=file_path
            )

            # Track intelligence extraction
            self.genesis_tracker.track_intelligence_extraction(
                file_path=file_path,
                intelligence={
                    'content_summary': intelligence.content_summary,
                    'quality_score': intelligence.quality_score,
                    'complexity_level': intelligence.complexity_level,
                    'detected_topics': intelligence.detected_topics,
                    'extracted_entities': intelligence.extracted_entities
                }
            )

            # Step 3: Get adaptive processing strategy
            logger.info("[GRACE-FILE-MANAGER] Determining optimal strategy...")
            strategy = self.adaptive_processor.get_processing_strategy(
                file_path=file_path,
                file_intelligence=intelligence
            )

            # Step 4: Return processing configuration
            processing_time = time.time() - start_time

            result = {
                'success': True,
                'file_path': file_path,
                'intelligence': {
                    'summary': intelligence.content_summary,
                    'quality_score': intelligence.quality_score,
                    'complexity_level': intelligence.complexity_level,
                    'topics': intelligence.detected_topics,
                    'entities': intelligence.extracted_entities,
                    'relationships': intelligence.relationships
                },
                'strategy': {
                    'chunk_size': strategy.chunk_size,
                    'overlap': strategy.overlap,
                    'use_semantic_chunking': strategy.use_semantic_chunking,
                    'embedding_batch_size': strategy.embedding_batch_size,
                    'quality_threshold': strategy.quality_threshold
                },
                'processing_time': processing_time,
                'upload_key_id': upload_key_id
            }

            logger.info(
                f"[GRACE-FILE-MANAGER] File processed intelligently: "
                f"quality={intelligence.quality_score:.2f}, "
                f"complexity={intelligence.complexity_level}, "
                f"chunk_size={strategy.chunk_size}"
            )

            return result

        except Exception as e:
            logger.error(f"[GRACE-FILE-MANAGER] Error processing file: {e}")
            return {
                'success': False,
                'file_path': file_path,
                'error': str(e),
                'processing_time': time.time() - start_time
            }

    def record_ingestion_outcome(
        self,
        file_id: int,
        file_path: str,
        processing_result: Dict[str, Any]
    ) -> None:
        """
        Record ingestion outcome and learn from it.

        Call this AFTER ingestion completes to enable learning.

        Args:
            file_id: Document ID
            file_path: Path to file
            processing_result: Result from ingestion
        """
        logger.info(
            f"[GRACE-FILE-MANAGER] Recording ingestion outcome for file_id={file_id}"
        )

        try:
            # Extract strategy from result
            from file_manager.adaptive_file_processor import ProcessingStrategy

            strategy_data = processing_result.get('strategy', {})
            strategy = ProcessingStrategy(
                file_type=Path(file_path).suffix.lower(),
                chunk_size=strategy_data.get('chunk_size', 1024),
                overlap=strategy_data.get('overlap', 100),
                use_semantic_chunking=strategy_data.get('use_semantic_chunking', False),
                embedding_batch_size=strategy_data.get('embedding_batch_size', 32),
                quality_threshold=strategy_data.get('quality_threshold', 0.5),
                additional_params={}
            )

            # Record outcome for learning
            self.adaptive_processor.record_processing_outcome(
                file_id=file_id,
                file_path=file_path,
                strategy=strategy,
                success=processing_result.get('success', True),
                quality_score=processing_result.get('intelligence', {}).get('quality_score', 0.5),
                processing_time=processing_result.get('processing_time', 0.0),
                num_chunks=processing_result.get('num_chunks', 0),
                num_embeddings=processing_result.get('num_embeddings', 0),
                errors=processing_result.get('errors', [])
            )

            # Track with Genesis Key
            self.genesis_tracker.track_file_processing(
                file_id=file_id,
                file_path=file_path,
                processing_result={
                    'success': processing_result.get('success', True),
                    'num_chunks': processing_result.get('num_chunks', 0),
                    'num_embeddings': processing_result.get('num_embeddings', 0),
                    'quality_score': processing_result.get('intelligence', {}).get('quality_score', 0.5),
                    'duration': processing_result.get('processing_time', 0.0),
                    'strategy': 'adaptive'
                }
            )

            logger.info(
                f"[GRACE-FILE-MANAGER] Ingestion outcome recorded and learned from"
            )

        except Exception as e:
            logger.error(f"[GRACE-FILE-MANAGER] Error recording outcome: {e}")

    def run_health_check(self) -> Dict[str, Any]:
        """
        Run file system health check.

        Returns:
            Health report dict
        """
        logger.info("[GRACE-FILE-MANAGER] Running health check...")

        try:
            report = self.health_monitor.run_health_check_cycle()

            result = {
                'health_status': report.health_status,
                'anomalies_count': len(report.anomalies),
                'anomalies': report.anomalies,
                'healing_actions_count': len(report.healing_actions),
                'healing_actions': report.healing_actions,
                'recommendations': report.recommendations,
                'timestamp': report.timestamp.isoformat()
            }

            logger.info(
                f"[GRACE-FILE-MANAGER] Health check complete: "
                f"status={report.health_status}, "
                f"anomalies={len(report.anomalies)}, "
                f"actions={len(report.healing_actions)}"
            )

            return result

        except Exception as e:
            logger.error(f"[GRACE-FILE-MANAGER] Health check failed: {e}")
            return {
                'health_status': 'error',
                'error': str(e)
            }

    def get_file_intelligence(self, file_id: int) -> Optional[Dict[str, Any]]:
        """
        Get intelligence data for a file.

        Args:
            file_id: Document ID

        Returns:
            Intelligence dict or None
        """
        if not self.session:
            return None

        try:
            from sqlalchemy import text
            import json

            query = text("""
                SELECT
                    content_summary,
                    extracted_entities,
                    detected_topics,
                    quality_score,
                    complexity_level,
                    recommended_strategy
                FROM file_intelligence
                WHERE document_id = :doc_id
            """)

            result = self.session.execute(
                query,
                {'doc_id': file_id}
            ).fetchone()

            if result:
                return {
                    'summary': result[0],
                    'entities': json.loads(result[1]) if result[1] else {},
                    'topics': json.loads(result[2]) if result[2] else [],
                    'quality_score': result[3],
                    'complexity_level': result[4],
                    'recommended_strategy': json.loads(result[5]) if result[5] else {}
                }

        except Exception as e:
            logger.error(f"[GRACE-FILE-MANAGER] Error getting intelligence: {e}")

        return None

    def get_file_relationships(self, file_id: int) -> List[Dict[str, Any]]:
        """
        Get relationships for a file.

        Args:
            file_id: Document ID

        Returns:
            List of relationship dicts
        """
        if not self.session:
            return []

        try:
            from sqlalchemy import text
            import json

            query = text("""
                SELECT
                    file_b_id,
                    relationship_type,
                    strength,
                    relationship_metadata
                FROM file_relationships
                WHERE file_a_id = :file_id
                ORDER BY strength DESC
            """)

            results = self.session.execute(
                query,
                {'file_id': file_id}
            ).fetchall()

            relationships = []
            for row in results:
                relationships.append({
                    'related_file_id': row[0],
                    'relationship_type': row[1],
                    'strength': row[2],
                    'metadata': json.loads(row[3]) if row[3] else {}
                })

            return relationships

        except Exception as e:
            logger.error(f"[GRACE-FILE-MANAGER] Error getting relationships: {e}")
            return []

    def get_performance_metrics(self, days: int = 7) -> Dict[str, Any]:
        """
        Get file processing performance metrics.

        Args:
            days: Number of days to analyze

        Returns:
            Performance metrics dict
        """
        # Use performance tracker
        summary = self.adaptive_processor.performance_tracker.get_performance_summary(
            days=days
        )

        return {
            'period_days': days,
            'total_processed': summary.get('total_processed', 0),
            'success_rate': summary.get('success_rate', 0.0),
            'avg_quality_score': summary.get('avg_quality', 0.0),
            'avg_processing_time': summary.get('avg_time', 0.0)
        }


# Singleton instance
_grace_file_manager = None


def get_grace_file_manager(
    session=None,
    knowledge_base_path: str = "knowledge_base",
    trust_level: int = 5,
    genesis_service=None
) -> GraceFileManager:
    """
    Get or create GraceFileManager singleton.

    Args:
        session: Database session
        knowledge_base_path: Path to knowledge base
        trust_level: Trust level for autonomous actions
        genesis_service: Genesis Key service

    Returns:
        GraceFileManager instance
    """
    global _grace_file_manager

    if _grace_file_manager is None:
        _grace_file_manager = GraceFileManager(
            session=session,
            knowledge_base_path=knowledge_base_path,
            trust_level=trust_level,
            genesis_service=genesis_service
        )

    return _grace_file_manager
