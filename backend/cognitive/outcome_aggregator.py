"""
Outcome Aggregator Service - Unified Outcome Aggregation

Collects outcomes from all systems (healing, testing, diagnostics, LLM, file_processing)
and stores them in a unified format. Detects cross-system patterns and triggers updates
to all relevant systems.

This addresses the critical gap identified in SYSTEM_GAPS_ANALYSIS.md:
"Unified Outcome Aggregation & Cross-System Learning"
"""
import logging
import threading
from typing import Dict, List, Optional, Any
from datetime import datetime
from uuid import uuid4
from collections import defaultdict
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Global aggregator instance and lock
_aggregator_instance: Optional['OutcomeAggregator'] = None
_aggregator_lock = threading.Lock()


class OutcomeAggregator:
    """
    Unified Outcome Aggregation Service.
    
    Collects outcomes from all systems:
    - Healing outcomes
    - Testing outcomes
    - Diagnostic outcomes
    - LLM outcomes
    - File processing outcomes
    
    Stores outcomes in unified format, detects cross-system patterns,
    and triggers updates to all relevant systems.
    
    Thread-safe with internal locking.
    """
    
    # Valid outcome sources
    VALID_SOURCES = {'healing', 'testing', 'diagnostics', 'llm', 'file_processing'}
    
    def __init__(self, session: Optional[Session] = None):
        """
        Initialize Outcome Aggregator.
        
        Args:
            session: Database session for creating LearningExamples
        """
        self.session = session
        self._lock = threading.Lock()
        
        # Store outcomes in memory (max 1000 total)
        self._outcomes: List[Dict[str, Any]] = []
        self._max_outcomes = 1000
        
        # Cross-system patterns detected
        self._patterns: List[Dict[str, Any]] = []
        self._max_patterns = 100
        
        # Statistics
        self._stats = {
            "total_outcomes_recorded": 0,
            "outcomes_by_source": defaultdict(int),
            "patterns_detected": 0,
            "cross_system_learnings_created": 0,
            "errors": 0,
            "started_at": datetime.utcnow().isoformat()
        }
        
        logger.info("[OUTCOME-AGGREGATOR] Initialized unified outcome aggregation service")
    
    def record_outcome(
        self,
        source: str,
        outcome: Dict[str, Any]
    ) -> str:
        """
        Record an outcome from any system.
        
        Automatically:
        - Stores in unified format
        - Detects cross-system patterns
        - Triggers updates to relevant systems
        
        Args:
            source: Source system ('healing', 'testing', 'diagnostics', 'llm', 'file_processing')
            outcome: Outcome dictionary containing at least 'success' and optionally 'trust_score'
            
        Returns:
            outcome_id: Unique identifier for the recorded outcome
        """
        outcome_id = str(uuid4())
        
        with self._lock:
            try:
                # Validate source
                if source not in self.VALID_SOURCES:
                    logger.warning(f"[OUTCOME-AGGREGATOR] Unknown source '{source}', allowing anyway")
                
                # Create unified outcome
                unified_outcome = {
                    'id': outcome_id,
                    'source': source,
                    'timestamp': datetime.utcnow(),
                    'outcome': outcome,
                    'trust_score': float(outcome.get('trust_score', 0.5)),
                    'success': bool(outcome.get('success', False)),
                    'context': outcome.get('context', {})
                }
                
                # Store outcome
                self._outcomes.append(unified_outcome)
                
                # Enforce max size limit
                if len(self._outcomes) > self._max_outcomes:
                    self._outcomes.pop(0)
                
                # Update statistics
                self._stats["total_outcomes_recorded"] += 1
                self._stats["outcomes_by_source"][source] += 1
                
                logger.debug(
                    f"[OUTCOME-AGGREGATOR] Recorded outcome {outcome_id[:8]} from {source}: "
                    f"success={unified_outcome['success']}, trust={unified_outcome['trust_score']:.2f}"
                )
                
                return outcome_id
                
            except Exception as e:
                self._stats["errors"] += 1
                logger.error(f"[OUTCOME-AGGREGATOR] Error recording outcome: {e}", exc_info=True)
                return outcome_id
    
    def get_outcomes(
        self,
        source: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recorded outcomes with optional filtering.
        
        Args:
            source: Filter by source (None for all sources)
            since: Filter by timestamp (outcomes after this time)
            
        Returns:
            List of unified outcome dictionaries
        """
        with self._lock:
            results = self._outcomes.copy()
        
        # Filter by source
        if source is not None:
            results = [o for o in results if o['source'] == source]
        
        # Filter by timestamp
        if since is not None:
            results = [o for o in results if o['timestamp'] >= since]
        
        return results
    
    def detect_patterns(self) -> List[Dict[str, Any]]:
        """
        Detect cross-system patterns from recorded outcomes.
        
        Analyzes correlations between:
        - Healing actions and diagnostic issues
        - Test failures and code patterns
        - LLM suggestions and successful outcomes
        
        Returns:
            List of detected cross-system patterns
        """
        detected = []
        
        with self._lock:
            outcomes = self._outcomes.copy()
        
        if len(outcomes) < 2:
            return detected
        
        try:
            # Group outcomes by source
            by_source: Dict[str, List[Dict]] = defaultdict(list)
            for outcome in outcomes:
                by_source[outcome['source']].append(outcome)
            
            # Correlate healing actions with diagnostic issues
            if by_source['healing'] and by_source['diagnostics']:
                healing_diagnostic_patterns = self._find_healing_diagnostic_patterns(
                    by_source['healing'],
                    by_source['diagnostics']
                )
                detected.extend(healing_diagnostic_patterns)
            
            # Correlate test failures with code patterns
            if by_source['testing'] and by_source['file_processing']:
                test_code_patterns = self._find_test_code_patterns(
                    by_source['testing'],
                    by_source['file_processing']
                )
                detected.extend(test_code_patterns)
            
            # Track which LLM suggestions lead to successful outcomes
            if by_source['llm'] and by_source['healing']:
                llm_healing_patterns = self._find_llm_healing_patterns(
                    by_source['llm'],
                    by_source['healing']
                )
                detected.extend(llm_healing_patterns)
            
            # Store detected patterns
            with self._lock:
                for pattern in detected:
                    self._patterns.append(pattern)
                    self._stats["patterns_detected"] += 1
                    
                    # Create cross-system learning for high-confidence patterns
                    if pattern.get('confidence', 0) >= 0.8:
                        related_outcomes = pattern.get('related_outcomes', [])
                        self._create_cross_system_learning(related_outcomes, pattern)
                
                # Enforce max patterns
                while len(self._patterns) > self._max_patterns:
                    self._patterns.pop(0)
            
            if detected:
                logger.info(f"[OUTCOME-AGGREGATOR] Detected {len(detected)} cross-system patterns")
            
            return detected
            
        except Exception as e:
            logger.error(f"[OUTCOME-AGGREGATOR] Error detecting patterns: {e}", exc_info=True)
            return detected
    
    def _find_healing_diagnostic_patterns(
        self,
        healing_outcomes: List[Dict],
        diagnostic_outcomes: List[Dict]
    ) -> List[Dict]:
        """Find patterns between healing actions and diagnostic issues."""
        patterns = []
        
        for healing in healing_outcomes:
            if not healing.get('success'):
                continue
                
            healing_time = healing['timestamp']
            healing_action = healing['outcome'].get('action', 'unknown')
            
            for diagnostic in diagnostic_outcomes:
                # Check time correlation (within 10 minutes)
                time_diff = abs((healing_time - diagnostic['timestamp']).total_seconds())
                if time_diff > 600:
                    continue
                
                correlation = self._correlate_outcomes(healing, diagnostic)
                if correlation >= 0.6:
                    issue_type = diagnostic['outcome'].get('issue_type', 'unknown')
                    patterns.append({
                        'pattern_type': 'healing_diagnostic_correlation',
                        'description': f"Healing action '{healing_action}' resolves diagnostic issue '{issue_type}'",
                        'sources': ['healing', 'diagnostics'],
                        'confidence': correlation,
                        'healing_action': healing_action,
                        'diagnostic_issue': issue_type,
                        'related_outcomes': [healing, diagnostic],
                        'timestamp': datetime.utcnow()
                    })
        
        return patterns
    
    def _find_test_code_patterns(
        self,
        test_outcomes: List[Dict],
        file_outcomes: List[Dict]
    ) -> List[Dict]:
        """Find patterns between test failures and code patterns."""
        patterns = []
        
        # Look for test failures and correlate with file processing
        failed_tests = [t for t in test_outcomes if not t.get('success')]
        
        for test in failed_tests:
            test_time = test['timestamp']
            test_name = test['outcome'].get('test_name', 'unknown')
            
            for file_outcome in file_outcomes:
                time_diff = abs((test_time - file_outcome['timestamp']).total_seconds())
                if time_diff > 300:
                    continue
                
                correlation = self._correlate_outcomes(test, file_outcome)
                if correlation >= 0.5:
                    file_path = file_outcome['outcome'].get('file_path', 'unknown')
                    patterns.append({
                        'pattern_type': 'test_code_correlation',
                        'description': f"Test '{test_name}' failure correlates with changes in '{file_path}'",
                        'sources': ['testing', 'file_processing'],
                        'confidence': correlation,
                        'test_name': test_name,
                        'file_path': file_path,
                        'related_outcomes': [test, file_outcome],
                        'timestamp': datetime.utcnow()
                    })
        
        return patterns
    
    def _find_llm_healing_patterns(
        self,
        llm_outcomes: List[Dict],
        healing_outcomes: List[Dict]
    ) -> List[Dict]:
        """Track which LLM suggestions lead to successful healing."""
        patterns = []
        
        successful_healings = [h for h in healing_outcomes if h.get('success')]
        
        for healing in successful_healings:
            healing_time = healing['timestamp']
            
            for llm in llm_outcomes:
                # LLM suggestion should come before healing
                time_diff = (healing_time - llm['timestamp']).total_seconds()
                if time_diff < 0 or time_diff > 600:
                    continue
                
                correlation = self._correlate_outcomes(llm, healing)
                if correlation >= 0.6:
                    suggestion = llm['outcome'].get('suggestion', llm['outcome'].get('response', 'unknown'))
                    healing_action = healing['outcome'].get('action', 'unknown')
                    patterns.append({
                        'pattern_type': 'llm_healing_success',
                        'description': f"LLM suggestion led to successful healing action '{healing_action}'",
                        'sources': ['llm', 'healing'],
                        'confidence': correlation,
                        'llm_suggestion': str(suggestion)[:200],
                        'healing_action': healing_action,
                        'related_outcomes': [llm, healing],
                        'timestamp': datetime.utcnow()
                    })
        
        return patterns
    
    def _correlate_outcomes(
        self,
        outcome1: Dict[str, Any],
        outcome2: Dict[str, Any]
    ) -> float:
        """
        Calculate correlation score between two outcomes.
        
        Args:
            outcome1: First outcome
            outcome2: Second outcome
            
        Returns:
            Correlation score (0.0 to 1.0)
        """
        try:
            score = 0.0
            
            # Time proximity (0-0.3)
            time_diff = abs((outcome1['timestamp'] - outcome2['timestamp']).total_seconds())
            if time_diff < 60:
                score += 0.3
            elif time_diff < 300:
                score += 0.2
            elif time_diff < 600:
                score += 0.1
            
            # Trust score alignment (0-0.3)
            trust_diff = abs(outcome1['trust_score'] - outcome2['trust_score'])
            if trust_diff < 0.1:
                score += 0.3
            elif trust_diff < 0.2:
                score += 0.2
            elif trust_diff < 0.3:
                score += 0.1
            
            # Success alignment (0-0.2)
            if outcome1['success'] == outcome2['success']:
                score += 0.2
            
            # Content correlation (0-0.2)
            content_score = self._check_content_similarity(
                outcome1['outcome'],
                outcome2['outcome']
            )
            score += content_score * 0.2
            
            return min(1.0, score)
            
        except Exception as e:
            logger.debug(f"[OUTCOME-AGGREGATOR] Error correlating outcomes: {e}")
            return 0.0
    
    def _check_content_similarity(
        self,
        content1: Dict[str, Any],
        content2: Dict[str, Any]
    ) -> float:
        """Check content similarity between two outcome dictionaries."""
        try:
            # Extract keywords from both
            keys_to_check = [
                'action', 'anomaly_type', 'test_name', 'issue_type',
                'error_type', 'file_path', 'function_name', 'component'
            ]
            
            matches = 0
            total = 0
            
            for key in keys_to_check:
                val1 = content1.get(key)
                val2 = content2.get(key)
                
                if val1 is not None or val2 is not None:
                    total += 1
                    if val1 and val2 and str(val1).lower() == str(val2).lower():
                        matches += 1
            
            return matches / max(total, 1)
            
        except Exception:
            return 0.0
    
    def _create_cross_system_learning(
        self,
        outcomes: List[Dict[str, Any]],
        pattern: Dict[str, Any]
    ) -> None:
        """
        Create a LearningExample from cross-system pattern detection.
        
        Args:
            outcomes: List of related outcomes
            pattern: The detected pattern
        """
        if not self.session:
            logger.debug("[OUTCOME-AGGREGATOR] No session available for creating learning example")
            return
        
        try:
            from cognitive.learning_memory import LearningExample
            
            # Create learning example from pattern
            example = LearningExample(
                example_type='cross_system_pattern',
                input_context={
                    'pattern_type': pattern.get('pattern_type'),
                    'sources': pattern.get('sources', []),
                    'description': pattern.get('description', ''),
                    'related_outcome_ids': [o.get('id') for o in outcomes if o.get('id')]
                },
                expected_output={
                    'confidence': pattern.get('confidence', 0.0),
                    'pattern_details': {
                        k: v for k, v in pattern.items()
                        if k not in ['related_outcomes', 'timestamp']
                    }
                },
                actual_output=None,
                trust_score=pattern.get('confidence', 0.5),
                source='outcome_aggregator',
                source_reliability=0.8,
                outcome_quality=pattern.get('confidence', 0.5),
                consistency_score=0.7
            )
            
            self.session.add(example)
            self.session.commit()
            
            self._stats["cross_system_learnings_created"] += 1
            
            logger.info(
                f"[OUTCOME-AGGREGATOR] Created cross-system learning: "
                f"{pattern.get('pattern_type')} (confidence={pattern.get('confidence', 0):.2f})"
            )
            
        except ImportError:
            logger.warning("[OUTCOME-AGGREGATOR] Could not import LearningExample")
        except Exception as e:
            logger.error(f"[OUTCOME-AGGREGATOR] Error creating learning example: {e}", exc_info=True)
            try:
                self.session.rollback()
            except Exception:
                pass
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get aggregator statistics.
        
        Returns:
            Dictionary containing:
            - total_outcomes_recorded
            - outcomes_by_source
            - patterns_detected
            - cross_system_learnings_created
            - errors
            - current_outcome_count
            - current_pattern_count
        """
        with self._lock:
            return {
                "total_outcomes_recorded": self._stats["total_outcomes_recorded"],
                "outcomes_by_source": dict(self._stats["outcomes_by_source"]),
                "patterns_detected": self._stats["patterns_detected"],
                "cross_system_learnings_created": self._stats["cross_system_learnings_created"],
                "errors": self._stats["errors"],
                "current_outcome_count": len(self._outcomes),
                "current_pattern_count": len(self._patterns),
                "started_at": self._stats["started_at"],
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def get_patterns(self, min_confidence: float = 0.0) -> List[Dict[str, Any]]:
        """
        Get detected patterns with optional confidence filter.
        
        Args:
            min_confidence: Minimum confidence threshold (0.0 to 1.0)
            
        Returns:
            List of pattern dictionaries
        """
        with self._lock:
            patterns = self._patterns.copy()
        
        if min_confidence > 0:
            patterns = [p for p in patterns if p.get('confidence', 0) >= min_confidence]
        
        return patterns
    
    def clear(self) -> None:
        """Clear all stored outcomes and patterns (useful for testing)."""
        with self._lock:
            self._outcomes.clear()
            self._patterns.clear()
            self._stats = {
                "total_outcomes_recorded": 0,
                "outcomes_by_source": defaultdict(int),
                "patterns_detected": 0,
                "cross_system_learnings_created": 0,
                "errors": 0,
                "started_at": datetime.utcnow().isoformat()
            }
        logger.info("[OUTCOME-AGGREGATOR] Cleared all outcomes and patterns")


def get_outcome_aggregator(session: Optional[Session] = None) -> OutcomeAggregator:
    """
    Get or create global OutcomeAggregator singleton.
    
    Thread-safe singleton access. If a session is provided and differs
    from the current instance's session, updates the session.
    
    Args:
        session: Optional database session
        
    Returns:
        OutcomeAggregator singleton instance
    """
    global _aggregator_instance
    
    with _aggregator_lock:
        if _aggregator_instance is None:
            _aggregator_instance = OutcomeAggregator(session=session)
        elif session is not None and _aggregator_instance.session != session:
            # Update session if a new one is provided
            _aggregator_instance.session = session
        
        return _aggregator_instance
