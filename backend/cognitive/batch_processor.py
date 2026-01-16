"""
Batch Processor - Performance Optimization for Layer 1 Operations

This module provides batch processing capabilities for:
- Trust score calculations
- Consistency checks
- Causal relationship analysis
- Performance optimization

Maintains 100% determinism while providing significant performance improvements.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from sqlalchemy.orm import Session
from cognitive.learning_memory import LearningExample
from cognitive.enhanced_trust_scorer import TrustScoreResult, get_adaptive_trust_scorer
from cognitive.enhanced_consistency_checker import ConsistencyResult, get_consistency_checker
from cognitive.enhanced_causal_reasoner import CausalAnalysis, get_causal_reasoner

logger = logging.getLogger(__name__)


@dataclass
class BatchProcessingStats:
    """Statistics for batch processing operations."""
    total_items: int
    processed_items: int
    failed_items: int
    processing_time_seconds: float
    items_per_second: float
    cache_hits: int
    cache_misses: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'total_items': self.total_items,
            'processed_items': self.processed_items,
            'failed_items': self.failed_items,
            'processing_time_seconds': self.processing_time_seconds,
            'items_per_second': self.items_per_second,
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'success_rate': self.processed_items / self.total_items if self.total_items > 0 else 0.0
        }


class BatchTrustCalculator:
    """
    Batch processing for trust score calculations.
    
    Provides significant performance improvements by:
    - Loading all examples in one query
    - Pre-loading related data
    - Using caching
    - Parallel processing where possible
    """
    
    def __init__(self, session: Session, use_cache: bool = True):
        """
        Initialize batch trust calculator.
        
        Args:
            session: Database session
            use_cache: If True, use trust score cache
        """
        self.session = session
        self.use_cache = use_cache
        self.trust_scorer = get_adaptive_trust_scorer()
        
        if use_cache:
            from cognitive.enhanced_trust_scorer import get_trust_score_cache
            self.cache = get_trust_score_cache()
        else:
            self.cache = None
    
    def calculate_batch_trust_scores(
        self,
        learning_example_ids: List[int],
        context: Optional[Dict[str, Any]] = None,
        use_parallel: bool = False,
        max_workers: int = 4
    ) -> Tuple[Dict[int, TrustScoreResult], BatchProcessingStats]:
        """
        Calculate trust scores for multiple examples in batch.
        
        Args:
            learning_example_ids: List of learning example IDs
            context: Optional context for adaptive weighting
            use_parallel: If True, use parallel processing
            max_workers: Maximum worker threads for parallel processing
            
        Returns:
            Tuple of (results_dict, stats)
        """
        import time
        start_time = time.time()
        
        # Load all examples in one query
        examples = self.session.query(LearningExample).filter(
            LearningExample.id.in_(learning_example_ids)
        ).all()
        
        if not examples:
            stats = BatchProcessingStats(
                total_items=len(learning_example_ids),
                processed_items=0,
                failed_items=0,
                processing_time_seconds=time.time() - start_time,
                items_per_second=0.0,
                cache_hits=0,
                cache_misses=0
            )
            return {}, stats
        
        # Pre-load related data
        validation_counts = self._load_validation_counts([ex.id for ex in examples])
        related_examples_map = self._load_related_examples(examples)
        
        results = {}
        cache_hits = 0
        cache_misses = 0
        failed_items = 0
        
        # Process in batch
        if use_parallel and len(examples) > 10:
            # Parallel processing for large batches
            results = self._calculate_parallel(
                examples,
                validation_counts,
                related_examples_map,
                context or {},
                max_workers
            )
        else:
            # Sequential processing
            for example in examples:
                try:
                    # Check cache first
                    cached_result = None
                    if self.cache:
                        cached_result = self.cache.get_trust_score(example.id)
                    
                    if cached_result:
                        results[example.id] = cached_result
                        cache_hits += 1
                    else:
                        # Calculate trust score
                        validation_history = validation_counts.get(
                            example.id,
                            {'validated': 0, 'invalidated': 0}
                        )
                        
                        age_days = (datetime.utcnow() - example.created_at).days if hasattr(example, 'created_at') else 0
                        
                        trust_result = self.trust_scorer.calculate_trust_score(
                            source=example.source if hasattr(example, 'source') else 'unknown',
                            outcome_quality=example.outcome_quality if hasattr(example, 'outcome_quality') else 0.5,
                            consistency_score=example.consistency_score if hasattr(example, 'consistency_score') else 0.5,
                            validation_history=validation_history,
                            age_days=age_days,
                            operational_confidence=getattr(example, 'operational_confidence', None),
                            context=context or {}
                        )
                        
                        results[example.id] = trust_result
                        cache_misses += 1
                        
                        # Cache result
                        if self.cache:
                            self.cache.set_trust_score(example.id, trust_result)
                
                except Exception as e:
                    logger.error(f"Error calculating trust score for example {example.id}: {e}")
                    failed_items += 1
        
        processing_time = time.time() - start_time
        
        stats = BatchProcessingStats(
            total_items=len(learning_example_ids),
            processed_items=len(results),
            failed_items=failed_items,
            processing_time_seconds=processing_time,
            items_per_second=len(results) / processing_time if processing_time > 0 else 0.0,
            cache_hits=cache_hits,
            cache_misses=cache_misses
        )
        
        return results, stats
    
    def _calculate_parallel(
        self,
        examples: List[LearningExample],
        validation_counts: Dict[int, Dict[str, int]],
        related_examples_map: Dict[int, List[LearningExample]],
        context: Dict[str, Any],
        max_workers: int
    ) -> Dict[int, TrustScoreResult]:
        """Calculate trust scores in parallel."""
        results = {}
        
        def calculate_single(example: LearningExample) -> Tuple[int, Optional[TrustScoreResult]]:
            """Calculate trust score for a single example."""
            try:
                # Check cache
                if self.cache:
                    cached = self.cache.get_trust_score(example.id)
                    if cached:
                        return example.id, cached
                
                # Calculate
                validation_history = validation_counts.get(
                    example.id,
                    {'validated': 0, 'invalidated': 0}
                )
                
                age_days = (datetime.utcnow() - example.created_at).days if hasattr(example, 'created_at') else 0
                
                trust_result = self.trust_scorer.calculate_trust_score(
                    source=example.source if hasattr(example, 'source') else 'unknown',
                    outcome_quality=example.outcome_quality if hasattr(example, 'outcome_quality') else 0.5,
                    consistency_score=example.consistency_score if hasattr(example, 'consistency_score') else 0.5,
                    validation_history=validation_history,
                    age_days=age_days,
                    operational_confidence=getattr(example, 'operational_confidence', None),
                    context=context
                )
                
                # Cache
                if self.cache:
                    self.cache.set_trust_score(example.id, trust_result)
                
                return example.id, trust_result
            except Exception as e:
                logger.error(f"Error in parallel calculation for {example.id}: {e}")
                return example.id, None
        
        # Process in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(calculate_single, ex): ex for ex in examples}
            
            for future in as_completed(futures):
                example_id, result = future.result()
                if result:
                    results[example_id] = result
        
        return results
    
    def _load_validation_counts(
        self,
        example_ids: List[int]
    ) -> Dict[int, Dict[str, int]]:
        """Load validation counts for examples."""
        counts = {}
        
        for example_id in example_ids:
            example = self.session.query(LearningExample).filter(
                LearningExample.id == example_id
            ).first()
            
            if example:
                counts[example_id] = {
                    'validated': example.times_validated if hasattr(example, 'times_validated') else 0,
                    'invalidated': example.times_invalidated if hasattr(example, 'times_invalidated') else 0
                }
            else:
                counts[example_id] = {'validated': 0, 'invalidated': 0}
        
        return counts
    
    def _load_related_examples(
        self,
        examples: List[LearningExample]
    ) -> Dict[int, List[LearningExample]]:
        """Load related examples for consistency checking."""
        # Extract topics
        topics = set()
        for example in examples:
            topic = self._extract_topic(example)
            if topic:
                topics.add(topic)
        
        # Load related examples (simplified - could be optimized)
        related_map = defaultdict(list)
        
        if topics:
            related_examples = self.session.query(LearningExample).filter(
                LearningExample.input_context.contains({'topic': list(topics)[0]})  # Simplified
            ).limit(100).all()
            
            for example in examples:
                topic = self._extract_topic(example)
                related_map[example.id] = [
                    ex for ex in related_examples
                    if self._extract_topic(ex) == topic and ex.id != example.id
                ]
        
        return dict(related_map)
    
    def _extract_topic(self, example: LearningExample) -> str:
        """Extract topic from example."""
        if hasattr(example, 'input_context'):
            if isinstance(example.input_context, dict):
                return example.input_context.get('topic', '')
            return str(example.input_context)
        return ''


class BatchConsistencyChecker:
    """
    Batch processing for consistency checks.
    """
    
    def __init__(self, session: Session):
        """Initialize batch consistency checker."""
        self.session = session
        self.consistency_checker = get_consistency_checker(use_semantic_detection=True)
    
    def check_batch_consistency(
        self,
        learning_example_ids: List[int],
        use_parallel: bool = False,
        max_workers: int = 4
    ) -> Tuple[Dict[int, ConsistencyResult], BatchProcessingStats]:
        """
        Check consistency for multiple examples in batch.
        
        Args:
            learning_example_ids: List of learning example IDs
            use_parallel: If True, use parallel processing
            max_workers: Maximum worker threads
            
        Returns:
            Tuple of (results_dict, stats)
        """
        import time
        start_time = time.time()
        
        # Load all examples
        examples = self.session.query(LearningExample).filter(
            LearningExample.id.in_(learning_example_ids)
        ).all()
        
        if not examples:
            stats = BatchProcessingStats(
                total_items=len(learning_example_ids),
                processed_items=0,
                failed_items=0,
                processing_time_seconds=time.time() - start_time,
                items_per_second=0.0,
                cache_hits=0,
                cache_misses=0
            )
            return {}, stats
        
        # Load all existing examples for comparison
        all_examples = self.session.query(LearningExample).filter(
            LearningExample.id.notin_(learning_example_ids)
        ).limit(1000).all()
        
        results = {}
        failed_items = 0
        
        if use_parallel and len(examples) > 5:
            # Parallel processing
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(
                        self._check_single_consistency,
                        example,
                        all_examples
                    ): example.id
                    for example in examples
                }
                
                for future in as_completed(futures):
                    example_id = futures[future]
                    try:
                        result = future.result()
                        results[example_id] = result
                    except Exception as e:
                        logger.error(f"Error checking consistency for {example_id}: {e}")
                        failed_items += 1
        else:
            # Sequential processing
            for example in examples:
                try:
                    result = self._check_single_consistency(example, all_examples)
                    results[example.id] = result
                except Exception as e:
                    logger.error(f"Error checking consistency for {example.id}: {e}")
                    failed_items += 1
        
        processing_time = time.time() - start_time
        
        stats = BatchProcessingStats(
            total_items=len(learning_example_ids),
            processed_items=len(results),
            failed_items=failed_items,
            processing_time_seconds=processing_time,
            items_per_second=len(results) / processing_time if processing_time > 0 else 0.0,
            cache_hits=0,  # Consistency checks not cached yet
            cache_misses=len(results)
        )
        
        return results, stats
    
    def _check_single_consistency(
        self,
        example: LearningExample,
        existing_examples: List[LearningExample]
    ) -> ConsistencyResult:
        """Check consistency for a single example."""
        return self.consistency_checker.check_consistency(
            new_example=example,
            existing_examples=existing_examples
        )


class BatchCausalAnalyzer:
    """
    Batch processing for causal relationship analysis.
    """
    
    def __init__(self, session: Session):
        """Initialize batch causal analyzer."""
        self.session = session
        self.causal_reasoner = get_causal_reasoner(session=session)
    
    def analyze_batch_causal_relationships(
        self,
        topics: List[str],
        min_strength: float = 0.5
    ) -> Tuple[Dict[str, CausalAnalysis], BatchProcessingStats]:
        """
        Analyze causal relationships for multiple topics in batch.
        
        Args:
            topics: List of topics to analyze
            min_strength: Minimum relationship strength
            
        Returns:
            Tuple of (results_dict, stats)
        """
        import time
        start_time = time.time()
        
        results = {}
        failed_items = 0
        
        for topic in topics:
            try:
                analysis = self.causal_reasoner.analyze_causal_relationships(
                    topic=topic,
                    min_strength=min_strength
                )
                results[topic] = analysis
            except Exception as e:
                logger.error(f"Error analyzing causal relationships for {topic}: {e}")
                failed_items += 1
        
        processing_time = time.time() - start_time
        
        stats = BatchProcessingStats(
            total_items=len(topics),
            processed_items=len(results),
            failed_items=failed_items,
            processing_time_seconds=processing_time,
            items_per_second=len(results) / processing_time if processing_time > 0 else 0.0,
            cache_hits=0,
            cache_misses=len(results)
        )
        
        return results, stats
