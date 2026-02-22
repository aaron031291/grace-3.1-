"""
Grace Adaptive File Processor

Learns optimal processing strategies from experience.
Continuously improves file processing quality.

Classes:
- `ProcessingStrategy`
- `ProcessingOutcome`
- `StrategyLearner`
- `PerformanceTracker`
- `AdaptiveFileProcessor`

Key Methods:
- `get_optimal_strategy()`
- `learn_from_outcome()`
- `record_outcome()`
- `get_performance_summary()`
- `get_processing_strategy()`
- `record_processing_outcome()`
- `get_adaptive_file_processor()`
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ProcessingStrategy:
    """Processing strategy for a file type."""

    file_type: str
    chunk_size: int
    overlap: int
    use_semantic_chunking: bool
    embedding_batch_size: int
    quality_threshold: float
    additional_params: Dict[str, Any]

    # Performance metrics
    success_rate: float = 0.5
    avg_quality_score: float = 0.5
    avg_processing_time: float = 0.0
    times_used: int = 0
    last_used: Optional[datetime] = None


@dataclass
class ProcessingOutcome:
    """Outcome of a file processing operation."""

    file_id: int
    file_path: str
    file_type: str
    strategy_used: ProcessingStrategy
    success: bool
    quality_score: float
    processing_time: float
    num_chunks: int
    num_embeddings: int
    errors: List[str]
    timestamp: datetime


class StrategyLearner:
    """
    Learns optimal processing strategies from historical outcomes.

    Grace Principle: Recursive Learning
    - Tracks performance of different strategies
    - Adapts recommendations based on outcomes
    - Continuously improves processing quality
    """

    def __init__(self, session=None, genesis_tracker=None):
        """
        Initialize Strategy Learner.

        Args:
            session: Database session
            genesis_tracker: GenesisFileTracker for tracking
        """
        self.session = session
        self.genesis_tracker = genesis_tracker
        self.strategy_cache: Dict[str, ProcessingStrategy] = {}

        logger.info("[STRATEGY-LEARNER] Initialized")

    def get_optimal_strategy(
        self,
        file_type: str,
        file_size: int,
        complexity_level: str = "intermediate"
    ) -> ProcessingStrategy:
        """
        Get optimal processing strategy for a file type.

        Args:
            file_type: File extension (.pdf, .py, etc.)
            file_size: Size of file in bytes
            complexity_level: Complexity assessment

        Returns:
            Optimal ProcessingStrategy
        """
        # Check cache first
        cache_key = f"{file_type}_{complexity_level}"
        if cache_key in self.strategy_cache:
            logger.debug(f"[STRATEGY-LEARNER] Using cached strategy for {cache_key}")
            return self.strategy_cache[cache_key]

        # Query database for learned strategies
        if self.session:
            strategy = self._get_learned_strategy(file_type, complexity_level)
            if strategy:
                self.strategy_cache[cache_key] = strategy
                return strategy

        # Fall back to default strategy
        strategy = self._get_default_strategy(file_type, file_size, complexity_level)
        logger.info(
            f"[STRATEGY-LEARNER] Using default strategy for {file_type}: "
            f"chunk_size={strategy.chunk_size}"
        )

        return strategy

    def _get_learned_strategy(
        self,
        file_type: str,
        complexity_level: str
    ) -> Optional[ProcessingStrategy]:
        """
        Retrieve learned strategy from database.

        Args:
            file_type: File extension
            complexity_level: Complexity level

        Returns:
            ProcessingStrategy if found, None otherwise
        """
        try:
            from sqlalchemy import text

            # Query for best performing strategy
            query = text("""
                SELECT
                    file_type,
                    strategy,
                    success_rate,
                    avg_quality_score,
                    times_used,
                    last_used
                FROM processing_strategies
                WHERE file_type = :file_type
                ORDER BY (success_rate * 0.6 + avg_quality_score * 0.4) DESC
                LIMIT 1
            """)

            result = self.session.execute(
                query,
                {'file_type': file_type}
            ).fetchone()

            if result:
                import json
                strategy_data = json.loads(result[1])

                strategy = ProcessingStrategy(
                    file_type=result[0],
                    chunk_size=strategy_data.get('chunk_size', 1024),
                    overlap=strategy_data.get('overlap', 100),
                    use_semantic_chunking=strategy_data.get('use_semantic', False),
                    embedding_batch_size=strategy_data.get('batch_size', 32),
                    quality_threshold=strategy_data.get('quality_threshold', 0.5),
                    additional_params=strategy_data.get('additional', {}),
                    success_rate=result[2],
                    avg_quality_score=result[3],
                    times_used=result[4],
                    last_used=result[5]
                )

                logger.info(
                    f"[STRATEGY-LEARNER] Loaded learned strategy for {file_type}: "
                    f"success_rate={strategy.success_rate:.2f}, "
                    f"quality={strategy.avg_quality_score:.2f}, "
                    f"used={strategy.times_used} times"
                )

                return strategy

        except Exception as e:
            logger.error(f"[STRATEGY-LEARNER] Error loading learned strategy: {e}")

        return None

    def _get_default_strategy(
        self,
        file_type: str,
        file_size: int,
        complexity_level: str
    ) -> ProcessingStrategy:
        """
        Get default processing strategy.

        Args:
            file_type: File extension
            file_size: File size in bytes
            complexity_level: Complexity level

        Returns:
            Default ProcessingStrategy
        """
        # Base defaults
        chunk_size = 1024
        overlap = 100
        use_semantic = False
        batch_size = 32
        quality_threshold = 0.5

        # Adjust based on file type
        if file_type in ['.pdf', '.docx', '.txt']:
            chunk_size = 1024
            use_semantic = True
        elif file_type in ['.py', '.js', '.java', '.cpp']:
            chunk_size = 512
            use_semantic = True
            overlap = 50
        elif file_type in ['.md', '.rst']:
            chunk_size = 800
            use_semantic = True

        # Adjust based on complexity
        if complexity_level == 'beginner':
            chunk_size = int(chunk_size * 0.8)
            quality_threshold = 0.4
        elif complexity_level == 'advanced':
            chunk_size = int(chunk_size * 1.2)
            quality_threshold = 0.6

        # Adjust based on file size
        if file_size > 1_000_000:  # > 1MB
            chunk_size = int(chunk_size * 1.5)
            batch_size = 16
        elif file_size < 10_000:  # < 10KB
            chunk_size = int(chunk_size * 0.5)
            batch_size = 64

        return ProcessingStrategy(
            file_type=file_type,
            chunk_size=chunk_size,
            overlap=overlap,
            use_semantic_chunking=use_semantic,
            embedding_batch_size=batch_size,
            quality_threshold=quality_threshold,
            additional_params={}
        )

    def learn_from_outcome(self, outcome: ProcessingOutcome) -> None:
        """
        Learn from a processing outcome and update strategies.

        Args:
            outcome: ProcessingOutcome to learn from
        """
        if not self.session:
            logger.debug("[STRATEGY-LEARNER] No session, cannot learn")
            return

        try:
            from sqlalchemy import text
            import json

            # Serialize strategy
            strategy_json = json.dumps({
                'chunk_size': outcome.strategy_used.chunk_size,
                'overlap': outcome.strategy_used.overlap,
                'use_semantic': outcome.strategy_used.use_semantic_chunking,
                'batch_size': outcome.strategy_used.embedding_batch_size,
                'quality_threshold': outcome.strategy_used.quality_threshold,
                'additional': outcome.strategy_used.additional_params
            })

            # Check if strategy exists
            check_query = text("""
                SELECT id, success_rate, avg_quality_score, times_used
                FROM processing_strategies
                WHERE file_type = :file_type AND strategy = :strategy
            """)

            existing = self.session.execute(
                check_query,
                {'file_type': outcome.file_type, 'strategy': strategy_json}
            ).fetchone()

            if existing:
                # Update existing strategy
                strategy_id, old_success_rate, old_quality, old_times = existing

                # Calculate new metrics (weighted average)
                new_times = old_times + 1
                new_success_rate = (
                    (old_success_rate * old_times + (1.0 if outcome.success else 0.0))
                    / new_times
                )
                new_quality = (
                    (old_quality * old_times + outcome.quality_score)
                    / new_times
                )

                update_query = text("""
                    UPDATE processing_strategies
                    SET success_rate = :success_rate,
                        avg_quality_score = :quality,
                        times_used = :times_used,
                        last_used = :last_used,
                        updated_at = :updated_at
                    WHERE id = :id
                """)

                self.session.execute(
                    update_query,
                    {
                        'success_rate': new_success_rate,
                        'quality': new_quality,
                        'times_used': new_times,
                        'last_used': outcome.timestamp,
                        'updated_at': datetime.now(),
                        'id': strategy_id
                    }
                )

                logger.info(
                    f"[STRATEGY-LEARNER] Updated strategy for {outcome.file_type}: "
                    f"success_rate={new_success_rate:.2f}, quality={new_quality:.2f}"
                )

            else:
                # Insert new strategy
                insert_query = text("""
                    INSERT INTO processing_strategies
                    (file_type, strategy, success_rate, avg_quality_score,
                     times_used, last_used, created_at, updated_at)
                    VALUES
                    (:file_type, :strategy, :success_rate, :quality,
                     1, :last_used, :created_at, :updated_at)
                """)

                self.session.execute(
                    insert_query,
                    {
                        'file_type': outcome.file_type,
                        'strategy': strategy_json,
                        'success_rate': 1.0 if outcome.success else 0.0,
                        'quality': outcome.quality_score,
                        'last_used': outcome.timestamp,
                        'created_at': datetime.now(),
                        'updated_at': datetime.now()
                    }
                )

                logger.info(
                    f"[STRATEGY-LEARNER] Created new strategy for {outcome.file_type}"
                )

            self.session.commit()

            # Clear cache for this file type
            cache_keys_to_clear = [
                k for k in self.strategy_cache.keys()
                if k.startswith(outcome.file_type)
            ]
            for key in cache_keys_to_clear:
                del self.strategy_cache[key]

            # Track with Genesis Key
            if self.genesis_tracker:
                self.genesis_tracker.track_adaptive_learning(
                    file_type=outcome.file_type,
                    strategy=outcome.strategy_used.__dict__,
                    outcome={
                        'success': outcome.success,
                        'quality_score': outcome.quality_score,
                        'duration': outcome.processing_time
                    }
                )

        except Exception as e:
            logger.error(f"[STRATEGY-LEARNER] Error learning from outcome: {e}")
            self.session.rollback()


class PerformanceTracker:
    """
    Tracks file processing performance metrics.

    Grace Principle: Self-Awareness
    - Records all processing outcomes
    - Identifies performance trends
    - Detects degradation early
    """

    def __init__(self, session=None):
        """
        Initialize Performance Tracker.

        Args:
            session: Database session
        """
        self.session = session
        logger.info("[PERFORMANCE-TRACKER] Initialized")

    def record_outcome(self, outcome: ProcessingOutcome) -> None:
        """
        Record a processing outcome.

        Args:
            outcome: ProcessingOutcome to record
        """
        logger.info(
            f"[PERFORMANCE-TRACKER] Recording outcome: "
            f"file={Path(outcome.file_path).name}, "
            f"success={outcome.success}, "
            f"quality={outcome.quality_score:.2f}, "
            f"time={outcome.processing_time:.2f}s"
        )

        # In a full implementation, this would store outcomes
        # in a separate tracking table for trend analysis

    def get_performance_summary(
        self,
        file_type: Optional[str] = None,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Get performance summary for recent processing.

        Args:
            file_type: Filter by file type (optional)
            days: Number of days to analyze

        Returns:
            Performance summary dict
        """
        # Placeholder - would query historical data
        return {
            'total_processed': 0,
            'success_rate': 0.0,
            'avg_quality': 0.0,
            'avg_time': 0.0
        }


class AdaptiveFileProcessor:
    """
    Processes files using learned optimal strategies.

    Grace Principle: Autonomy + Recursive Learning
    - Uses best-known strategies automatically
    - Learns from every processing outcome
    - Continuously improves without human intervention
    """

    def __init__(
        self,
        session=None,
        intelligence_agent=None,
        genesis_tracker=None
    ):
        """
        Initialize Adaptive File Processor.

        Args:
            session: Database session
            intelligence_agent: FileIntelligenceAgent instance
            genesis_tracker: GenesisFileTracker instance
        """
        self.session = session
        self.intelligence_agent = intelligence_agent
        self.genesis_tracker = genesis_tracker

        self.strategy_learner = StrategyLearner(
            session=session,
            genesis_tracker=genesis_tracker
        )
        self.performance_tracker = PerformanceTracker(session=session)

        logger.info("[ADAPTIVE-PROCESSOR] Initialized")

    def get_processing_strategy(
        self,
        file_path: str,
        file_intelligence: Optional[Any] = None
    ) -> ProcessingStrategy:
        """
        Get optimal processing strategy for a file.

        Args:
            file_path: Path to file
            file_intelligence: FileIntelligence if already analyzed

        Returns:
            Optimal ProcessingStrategy
        """
        path = Path(file_path)
        file_type = path.suffix.lower()

        # Get file stats
        if path.exists():
            file_size = path.stat().st_size
        else:
            file_size = 0

        # Determine complexity
        complexity = "intermediate"
        if file_intelligence:
            complexity = file_intelligence.complexity_level

        # Get optimal strategy
        strategy = self.strategy_learner.get_optimal_strategy(
            file_type=file_type,
            file_size=file_size,
            complexity_level=complexity
        )

        logger.info(
            f"[ADAPTIVE-PROCESSOR] Strategy for {path.name}: "
            f"chunk_size={strategy.chunk_size}, "
            f"semantic={strategy.use_semantic_chunking}"
        )

        return strategy

    def record_processing_outcome(
        self,
        file_id: int,
        file_path: str,
        strategy: ProcessingStrategy,
        success: bool,
        quality_score: float,
        processing_time: float,
        num_chunks: int = 0,
        num_embeddings: int = 0,
        errors: Optional[List[str]] = None
    ) -> None:
        """
        Record processing outcome and learn from it.

        Args:
            file_id: Document ID
            file_path: Path to file
            strategy: Strategy that was used
            success: Whether processing succeeded
            quality_score: Quality score achieved
            processing_time: Time taken in seconds
            num_chunks: Number of chunks created
            num_embeddings: Number of embeddings generated
            errors: List of errors if any
        """
        outcome = ProcessingOutcome(
            file_id=file_id,
            file_path=file_path,
            file_type=Path(file_path).suffix.lower(),
            strategy_used=strategy,
            success=success,
            quality_score=quality_score,
            processing_time=processing_time,
            num_chunks=num_chunks,
            num_embeddings=num_embeddings,
            errors=errors or [],
            timestamp=datetime.now()
        )

        # Record outcome
        self.performance_tracker.record_outcome(outcome)

        # Learn from outcome
        self.strategy_learner.learn_from_outcome(outcome)

        logger.info(
            f"[ADAPTIVE-PROCESSOR] Recorded outcome and learned from it: "
            f"file_id={file_id}, success={success}"
        )


# Singleton instance
_adaptive_processor = None


def get_adaptive_file_processor(
    session=None,
    intelligence_agent=None,
    genesis_tracker=None
) -> AdaptiveFileProcessor:
    """
    Get or create AdaptiveFileProcessor singleton.

    Args:
        session: Database session
        intelligence_agent: FileIntelligenceAgent instance
        genesis_tracker: GenesisFileTracker instance

    Returns:
        AdaptiveFileProcessor instance
    """
    global _adaptive_processor

    if _adaptive_processor is None:
        _adaptive_processor = AdaptiveFileProcessor(
            session=session,
            intelligence_agent=intelligence_agent,
            genesis_tracker=genesis_tracker
        )

    return _adaptive_processor
