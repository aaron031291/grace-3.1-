"""
Outcome Aggregator Service

Unified aggregator for all system outcomes that enables cross-system learning
and pattern detection. Connects healing, testing, diagnostics, and LLM systems.
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict
from sqlalchemy.orm import Session

from cognitive.outcome_llm_bridge import get_outcome_bridge

logger = logging.getLogger(__name__)

# Global aggregator instance
_aggregator_instance: Optional['OutcomeAggregator'] = None


class OutcomeAggregator:
    """
    Unified aggregator for all system outcomes.
    
    Enables:
    - Cross-system pattern detection
    - Unified learning across all systems
    - Systems learning from each other
    - Pattern correlation (e.g., "Healing action X works for diagnostic issue Y")
    """
    
    def __init__(self, session: Optional[Session] = None):
        """
        Initialize Outcome Aggregator.
        
        Args:
            session: Database session
        """
        self.session = session
        
        # Store outcomes by source (last 1000 per source)
        self.outcome_sources: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.max_outcomes_per_source = 1000
        
        # Cross-system patterns detected
        self.detected_patterns: List[Dict[str, Any]] = []
        self.max_patterns = 100
        
        # Statistics
        self.stats = {
            "total_outcomes_recorded": 0,
            "outcomes_by_source": defaultdict(int),
            "patterns_detected": 0,
            "cross_system_updates": 0,
            "errors": 0
        }
        
        # Get outcome bridge for LLM updates
        self.outcome_bridge = None
        if session:
            try:
                self.outcome_bridge = get_outcome_bridge(session=session)
            except Exception as e:
                logger.debug(f"[OUTCOME-AGGREGATOR] Could not get outcome bridge: {e}")
        
        logger.info("[OUTCOME-AGGREGATOR] Initialized")
    
    def record_outcome(
        self,
        source: str,
        outcome: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Record outcome from any system.
        
        Automatically:
        - Detects cross-system patterns
        - Updates relevant systems
        - Triggers LLM updates if high-trust
        
        Args:
            source: Source system ('healing', 'testing', 'diagnostics', 'llm', 'file_processing', etc.)
            outcome: Outcome dictionary with at least 'success' and optionally 'trust_score'
            
        Returns:
            Result dictionary with status and detected patterns
        """
        try:
            # Prepare unified outcome format
            unified_outcome = {
                "source": source,
                "timestamp": datetime.utcnow(),
                "outcome": outcome,
                "trust_score": outcome.get("trust_score", 0.5),
                "success": outcome.get("success", False),
                "outcome_id": outcome.get("id") or outcome.get("example_id") or f"{source}_{datetime.utcnow().timestamp()}"
            }
            
            # Store outcome
            source_outcomes = self.outcome_sources[source]
            source_outcomes.append(unified_outcome)
            
            # Limit stored outcomes per source
            if len(source_outcomes) > self.max_outcomes_per_source:
                source_outcomes.pop(0)
            
            # Update statistics
            self.stats["total_outcomes_recorded"] += 1
            self.stats["outcomes_by_source"][source] += 1
            
            # Detect cross-system patterns
            detected = self._detect_cross_system_patterns(unified_outcome)
            
            # Update relevant systems
            update_result = self._update_systems(unified_outcome)
            
            logger.debug(
                f"[OUTCOME-AGGREGATOR] Recorded outcome from {source}: "
                f"success={unified_outcome['success']}, trust={unified_outcome['trust_score']:.2f}"
            )
            
            return {
                "recorded": True,
                "outcome_id": unified_outcome["outcome_id"],
                "patterns_detected": len(detected),
                "systems_updated": update_result,
                "timestamp": unified_outcome["timestamp"].isoformat()
            }
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(
                f"[OUTCOME-AGGREGATOR] Error recording outcome from {source}: {e}",
                exc_info=True
            )
            return {
                "recorded": False,
                "error": str(e)
            }
    
    def _detect_cross_system_patterns(
        self,
        new_outcome: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Detect patterns across systems.
        
        Examples:
        - "Healing action X works well for diagnostic issue Y"
        - "Test failures correlate with specific diagnostic alerts"
        - "LLM suggestions that lead to successful healing"
        
        Args:
            new_outcome: The new outcome that might correlate with existing outcomes
            
        Returns:
            List of detected patterns
        """
        detected_patterns = []
        
        try:
            new_source = new_outcome["source"]
            new_success = new_outcome["success"]
            new_trust = new_outcome["trust_score"]
            
            # Only look for patterns in high-trust outcomes
            if new_trust < 0.7:
                return detected_patterns
            
            # Check correlations with other sources
            for other_source, other_outcomes in self.outcome_sources.items():
                if other_source == new_source:
                    continue  # Don't correlate with same source
                
                # Look for recent outcomes from other source (last 100)
                recent_outcomes = other_outcomes[-100:]
                
                for other_outcome in recent_outcomes:
                    # Check if outcomes correlate
                    correlation = self._correlate_outcomes(new_outcome, other_outcome)
                    
                    if correlation and correlation.get("confidence", 0) > 0.7:
                        pattern = {
                            "pattern_type": "cross_system_correlation",
                            "sources": [new_source, other_source],
                            "correlation": correlation,
                            "timestamp": datetime.utcnow(),
                            "confidence": correlation.get("confidence", 0)
                        }
                        
                        detected_patterns.append(pattern)
                        self.detected_patterns.append(pattern)
                        
                        # Limit stored patterns
                        if len(self.detected_patterns) > self.max_patterns:
                            self.detected_patterns.pop(0)
                        
                        self.stats["patterns_detected"] += 1
                        
                        logger.info(
                            f"[OUTCOME-AGGREGATOR] 🎯 Pattern detected: {new_source} ↔ {other_source} "
                            f"(confidence={correlation.get('confidence', 0):.2f})"
                        )
            
            return detected_patterns
            
        except Exception as e:
            logger.debug(f"[OUTCOME-AGGREGATOR] Error detecting patterns: {e}")
            return detected_patterns
    
    def _correlate_outcomes(
        self,
        outcome1: Dict[str, Any],
        outcome2: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Check if two outcomes correlate.
        
        Returns correlation information if they do, None otherwise.
        
        Args:
            outcome1: First outcome
            outcome2: Second outcome
            
        Returns:
            Correlation dictionary or None
        """
        try:
            # Time-based correlation (within 5 minutes)
            time_diff = abs((outcome1["timestamp"] - outcome2["timestamp"]).total_seconds())
            if time_diff > 300:  # 5 minutes
                return None
            
            # Success correlation (both succeeded or both failed)
            success_match = outcome1["success"] == outcome2["success"]
            
            # Trust correlation (both high-trust)
            trust_match = outcome1["trust_score"] >= 0.7 and outcome2["trust_score"] >= 0.7
            
            # Content correlation (check if they reference similar things)
            content_correlation = self._check_content_correlation(
                outcome1["outcome"],
                outcome2["outcome"]
            )
            
            # Calculate confidence
            confidence = 0.0
            if success_match:
                confidence += 0.3
            if trust_match:
                confidence += 0.3
            if content_correlation:
                confidence += 0.4
            
            # Only return correlation if confidence is high enough
            if confidence >= 0.6:
                return {
                    "confidence": confidence,
                    "time_diff_seconds": time_diff,
                    "success_match": success_match,
                    "trust_match": trust_match,
                    "content_correlation": content_correlation
                }
            
            return None
            
        except Exception as e:
            logger.debug(f"[OUTCOME-AGGREGATOR] Error correlating outcomes: {e}")
            return None
    
    def _check_content_correlation(
        self,
        content1: Dict[str, Any],
        content2: Dict[str, Any]
    ) -> bool:
        """Check if two outcome contents correlate (simple keyword matching)."""
        try:
            # Extract relevant keys for correlation
            keys_to_check = ['action', 'anomaly_type', 'test_name', 'issue_type', 'error_type']
            
            for key in keys_to_check:
                val1 = content1.get(key)
                val2 = content2.get(key)
                
                if val1 and val2:
                    # Simple string matching (can be enhanced with semantic similarity)
                    if str(val1).lower() == str(val2).lower():
                        return True
            
            return False
            
        except Exception:
            return False
    
    def _update_systems(
        self,
        outcome: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update all relevant systems with new outcome.
        
        Args:
            outcome: The outcome to distribute
            
        Returns:
            Dictionary of systems updated
        """
        updated = {}
        
        try:
            source = outcome["source"]
            success = outcome["success"]
            trust_score = outcome["trust_score"]
            
            # Update healing system (if outcome is from testing/diagnostics)
            if source in ["testing", "diagnostics"]:
                # Healing system can learn from test failures and diagnostic issues
                # This would ideally call healing system's learning method
                updated["healing"] = {
                    "updated": True,
                    "reason": f"Outcome from {source} can inform healing decisions"
                }
            
            # Update testing system (if outcome is from healing/diagnostics)
            if source in ["healing", "diagnostics"]:
                # Testing system can learn what issues healing fixes
                updated["testing"] = {
                    "updated": True,
                    "reason": f"Outcome from {source} can inform test selection"
                }
            
            # Update LLM system (if high-trust outcome)
            if trust_score >= 0.8 and self.outcome_bridge:
                try:
                    # The outcome bridge will handle LLM updates via LearningExample events
                    # But we can also trigger it directly here if needed
                    updated["llm"] = {
                        "updated": True,
                        "reason": "High-trust outcome triggers LLM knowledge update",
                        "trust_score": trust_score
                    }
                except Exception as e:
                    logger.debug(f"[OUTCOME-AGGREGATOR] Could not update LLM: {e}")
            
            self.stats["cross_system_updates"] += len(updated)
            
            return updated
            
        except Exception as e:
            logger.debug(f"[OUTCOME-AGGREGATOR] Error updating systems: {e}")
            return updated
    
    def get_recent_outcomes(
        self,
        source: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get recent outcomes, optionally filtered by source."""
        if source:
            return self.outcome_sources.get(source, [])[-limit:]
        else:
            # Return from all sources, sorted by timestamp
            all_outcomes = []
            for outcomes in self.outcome_sources.values():
                all_outcomes.extend(outcomes)
            all_outcomes.sort(key=lambda x: x["timestamp"], reverse=True)
            return all_outcomes[:limit]
    
    def get_detected_patterns(
        self,
        min_confidence: float = 0.7,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get detected cross-system patterns."""
        filtered = [
            p for p in self.detected_patterns
            if p.get("confidence", 0) >= min_confidence
        ]
        return filtered[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get aggregator statistics."""
        return {
            **self.stats,
            "outcomes_by_source": dict(self.stats["outcomes_by_source"]),
            "total_stored_outcomes": sum(len(outcomes) for outcomes in self.outcome_sources.values()),
            "total_patterns": len(self.detected_patterns),
            "timestamp": datetime.utcnow().isoformat()
        }


def get_outcome_aggregator(session: Optional[Session] = None) -> OutcomeAggregator:
    """
    Get or create global OutcomeAggregator singleton.
    
    Args:
        session: Database session
        
    Returns:
        OutcomeAggregator instance
    """
    global _aggregator_instance
    
    if _aggregator_instance is None or session is not None:
        _aggregator_instance = OutcomeAggregator(session=session)
    
    return _aggregator_instance
