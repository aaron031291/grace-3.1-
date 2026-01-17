"""
Enhanced Trust Scorer - Advanced Deterministic Trust Calculation

This module provides an enhanced trust scoring system with:
- Adaptive weighting based on context
- Confidence intervals
- Uncertainty measures
- Temporal decay
- Multi-factor analysis

Maintains 100% determinism while providing richer trust information.
"""

import math
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum


class ContextType(Enum):
    """Context types for adaptive weighting."""
    SAFETY_CRITICAL = "safety_critical"
    OPERATIONAL = "operational"
    THEORETICAL = "theoretical"
    GENERAL = "general"


@dataclass
class TrustScoreResult:
    """
    Comprehensive trust score result with confidence intervals and uncertainty.
    """
    trust_score: float  # Main trust score (0-1)
    confidence_interval: Tuple[float, float]  # (lower, upper) bounds
    uncertainty: float  # Uncertainty measure (0-1, where 0 = certain, 1 = uncertain)
    factors: Dict[str, Any]  # Breakdown of contributing factors
    context_type: str  # Context type used
    calculated_at: datetime  # When this was calculated
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/serialization."""
        return {
            'trust_score': self.trust_score,
            'confidence_interval': {
                'lower': self.confidence_interval[0],
                'upper': self.confidence_interval[1]
            },
            'uncertainty': self.uncertainty,
            'factors': self.factors,
            'context_type': self.context_type,
            'calculated_at': self.calculated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TrustScoreResult':
        """Create from dictionary."""
        return cls(
            trust_score=data['trust_score'],
            confidence_interval=(
                data['confidence_interval']['lower'],
                data['confidence_interval']['upper']
            ),
            uncertainty=data['uncertainty'],
            factors=data['factors'],
            context_type=data['context_type'],
            calculated_at=datetime.fromisoformat(data['calculated_at'])
        )


class AdaptiveTrustScorer:
    """
    Enhanced trust scorer with adaptive weighting and confidence intervals.
    
    Maintains 100% determinism while providing richer trust information.
    """
    
    def __init__(self):
        """Initialize the adaptive trust scorer."""
        # Source reliability weights (same as original)
        self.source_weights = {
            'user_feedback_positive': 0.9,
            'user_feedback_negative': 0.8,
            'system_observation_success': 0.85,
            'system_observation_failure': 0.9,
            'external_api_validated': 0.7,
            'external_api_unvalidated': 0.4,
            'inferred': 0.3,
            'assumed': 0.1,
            'academic_paper': 0.95,
            'technical_book': 0.90,
            'official_documentation': 0.85,
            'blog_post': 0.60,
            'forum_post': 0.40,
            'unknown': 0.5
        }
        
        # Context-specific weight profiles
        self.weight_profiles = {
            ContextType.SAFETY_CRITICAL: {
                'source_reliability': 0.50,
                'data_confidence': 0.25,
                'operational_confidence': 0.15,
                'consistency_score': 0.10
            },
            ContextType.OPERATIONAL: {
                'source_reliability': 0.30,
                'data_confidence': 0.25,
                'operational_confidence': 0.35,
                'consistency_score': 0.10
            },
            ContextType.THEORETICAL: {
                'source_reliability': 0.45,
                'data_confidence': 0.30,
                'operational_confidence': 0.10,
                'consistency_score': 0.15
            },
            ContextType.GENERAL: {
                'source_reliability': 0.40,
                'data_confidence': 0.30,
                'operational_confidence': 0.20,
                'consistency_score': 0.10
            }
        }
    
    def calculate_trust_score(
        self,
        source: str,
        outcome_quality: float,
        consistency_score: float,
        validation_history: Dict[str, int],
        age_days: float = 0.0,
        operational_confidence: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> TrustScoreResult:
        """
        Calculate comprehensive trust score with adaptive weighting.
        
        Args:
            source: Source of learning example
            outcome_quality: Quality of outcome (0-1)
            consistency_score: Consistency with other knowledge (0-1)
            validation_history: {'validated': N, 'invalidated': M}
            age_days: Age in days (default: 0 for new examples)
            operational_confidence: Operational confidence (0-1), if None uses outcome_quality
            context: Optional context dict for adaptive weighting
            
        Returns:
            TrustScoreResult with trust score, confidence interval, and uncertainty
        """
        # Use operational_confidence if provided, otherwise use outcome_quality
        data_confidence = operational_confidence if operational_confidence is not None else outcome_quality
        
        # Classify context
        context_type = self._classify_context(context or {})
        
        # Get adaptive weights
        weights = self.weight_profiles[context_type]
        
        # Get source reliability
        source_reliability = self.source_weights.get(source, 0.5)
        
        # TimeSense integration: Get time determinism score if available
        time_determinism_score = None
        if context:
            time_determinism = context.get('time_determinism')
            if time_determinism and isinstance(time_determinism, dict):
                time_determinism_score = time_determinism.get('determinism_score', 1.0)
        
        # Calculate base score with adaptive weights
        # Include time determinism if available (10% weight, reduces other weights slightly)
        if time_determinism_score is not None:
            # Adjust weights to accommodate time determinism
            adjusted_weights = {
                'source_reliability': weights['source_reliability'] * 0.92,
                'data_confidence': weights['data_confidence'] * 0.92,
                'operational_confidence': weights['operational_confidence'] * 0.92,
                'consistency_score': weights['consistency_score'] * 0.92,
                'time_determinism': 0.08  # 8% weight for time determinism
            }
            base_score = (
                source_reliability * adjusted_weights['source_reliability'] +
                data_confidence * adjusted_weights['data_confidence'] +
                (operational_confidence if operational_confidence is not None else outcome_quality) * adjusted_weights['operational_confidence'] +
                consistency_score * adjusted_weights['consistency_score'] +
                time_determinism_score * adjusted_weights['time_determinism']
            )
        else:
            # Original calculation without time determinism
            base_score = (
                source_reliability * weights['source_reliability'] +
                data_confidence * weights['data_confidence'] +
                (operational_confidence if operational_confidence is not None else outcome_quality) * weights['operational_confidence'] +
                consistency_score * weights['consistency_score']
            )
        
        # Apply validation history adjustments
        validated = validation_history.get('validated', 0)
        invalidated = validation_history.get('invalidated', 0)
        total_validations = validated + invalidated
        
        validation_ratio = None
        if total_validations > 0:
            validation_ratio = validated / total_validations
            # Boost for high validation ratio, penalty for low
            # More validations = more confidence
            validation_adjustment = (validation_ratio - 0.5) * 0.2
            base_score += validation_adjustment
        else:
            validation_ratio = 0.5  # Neutral if no validation
        
        # Calculate confidence interval
        confidence_interval = self._calculate_confidence_interval(
            base_score,
            source_reliability,
            data_confidence,
            operational_confidence if operational_confidence is not None else outcome_quality,
            consistency_score,
            total_validations
        )
        
        # Calculate uncertainty
        uncertainty = self._calculate_uncertainty(
            confidence_interval,
            total_validations,
            consistency_score,
            source_reliability
        )
        
        # Apply temporal decay if applicable
        if age_days > 0:
            temporal_decay = self._calculate_temporal_decay(age_days, context)
            base_score *= temporal_decay
            # Adjust confidence interval proportionally
            interval_width = confidence_interval[1] - confidence_interval[0]
            center = (confidence_interval[0] + confidence_interval[1]) / 2
            new_center = center * temporal_decay
            confidence_interval = (
                max(0.0, new_center - interval_width / 2),
                min(1.0, new_center + interval_width / 2)
            )
        
        # Ensure bounds
        base_score = max(0.0, min(1.0, base_score))
        
        return TrustScoreResult(
            trust_score=base_score,
            confidence_interval=confidence_interval,
            uncertainty=uncertainty,
            factors={
                'source_reliability': source_reliability,
                'data_confidence': data_confidence,
                'operational_confidence': operational_confidence if operational_confidence is not None else outcome_quality,
                'consistency_score': consistency_score,
                'time_determinism': time_determinism_score,  # Time determinism factor
                'validation_ratio': validation_ratio,
                'validation_count': total_validations,
                'weights_used': weights,
                'context_type': context_type.value,
                'age_days': age_days,
                'source': source
            },
            context_type=context_type.value,
            calculated_at=datetime.utcnow()
        )
    
    def _classify_context(self, context: Dict[str, Any]) -> ContextType:
        """
        Classify context type for adaptive weighting.
        
        Args:
            context: Context dictionary
            
        Returns:
            ContextType enum
        """
        if context.get('safety_critical', False):
            return ContextType.SAFETY_CRITICAL
        elif context.get('operational', False) or context.get('practice_based', False):
            return ContextType.OPERATIONAL
        elif context.get('theoretical', False) or context.get('academic', False):
            return ContextType.THEORETICAL
        else:
            return ContextType.GENERAL
    
    def _calculate_confidence_interval(
        self,
        base_score: float,
        source_reliability: float,
        data_confidence: float,
        operational_confidence: float,
        consistency_score: float,
        validation_count: int
    ) -> Tuple[float, float]:
        """
        Calculate 95% confidence interval using component variance estimation.
        
        Args:
            base_score: Base trust score
            source_reliability: Source reliability score
            data_confidence: Data confidence score
            operational_confidence: Operational confidence score
            consistency_score: Consistency score
            validation_count: Number of validations
            
        Returns:
            Tuple of (lower_bound, upper_bound)
        """
        # Estimate variance from component scores
        # Higher variance in components = wider confidence interval
        component_variance = (
            (source_reliability * 0.1) ** 2 +
            (data_confidence * 0.1) ** 2 +
            (operational_confidence * 0.15) ** 2 +
            (consistency_score * 0.1) ** 2
        ) / 4
        
        # Reduce variance with more validations (more data = more confidence)
        if validation_count > 0:
            # Each validation reduces variance by ~10%
            component_variance *= (1 / (1 + validation_count * 0.1))
        
        # Standard error (approximate, using 95% CI multiplier)
        std_error = (component_variance ** 0.5) * 1.96  # 95% confidence interval
        
        lower = max(0.0, base_score - std_error)
        upper = min(1.0, base_score + std_error)
        
        return (lower, upper)
    
    def _calculate_uncertainty(
        self,
        confidence_interval: Tuple[float, float],
        validation_count: int,
        consistency_score: float,
        source_reliability: float
    ) -> float:
        """
        Calculate uncertainty measure (0-1, where 0 = certain, 1 = uncertain).
        
        Args:
            confidence_interval: Confidence interval bounds
            validation_count: Number of validations
            consistency_score: Consistency score
            source_reliability: Source reliability
            
        Returns:
            Uncertainty measure (0-1)
        """
        # Base uncertainty from interval width
        interval_width = confidence_interval[1] - confidence_interval[0]
        base_uncertainty = interval_width
        
        # Increase uncertainty if low validation count
        if validation_count < 3:
            base_uncertainty += 0.2
        elif validation_count < 10:
            base_uncertainty += 0.1
        
        # Increase uncertainty if low consistency
        if consistency_score < 0.6:
            base_uncertainty += 0.15
        elif consistency_score < 0.8:
            base_uncertainty += 0.05
        
        # Increase uncertainty if low source reliability
        if source_reliability < 0.5:
            base_uncertainty += 0.1
        
        return min(1.0, base_uncertainty)
    
    def _calculate_temporal_decay(
        self,
        age_days: float,
        context: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Calculate temporal decay factor.
        
        Knowledge decays over time at different rates based on domain:
        - Fast-changing domains (tech): 50% decay in 180 days
        - Medium domains (science): 50% decay in 365 days
        - Slow-changing domains (math): 50% decay in 730 days
        
        Args:
            age_days: Age in days
            context: Optional context for domain-specific decay
            
        Returns:
            Decay factor (0-1)
        """
        # Determine domain type from context
        domain_type = context.get('domain_type', 'medium') if context else 'medium'
        
        # Half-life in days based on domain
        half_life_days = {
            'fast': 180.0,   # Tech, current events
            'medium': 365.0,  # Science, general knowledge
            'slow': 730.0     # Math, fundamental principles
        }.get(domain_type, 365.0)
        
        # Exponential decay: decay_rate = 0.5^(age/half_life)
        decay_rate = 0.5 ** (age_days / half_life_days)
        
        # Minimum decay (never go below 0.7 for old but validated knowledge)
        # This ensures that well-validated knowledge doesn't decay too much
        return max(0.7, decay_rate)
    
    def calculate_simple_trust_score(
        self,
        source: str,
        outcome_quality: float,
        consistency_score: float,
        validation_history: Dict[str, int],
        age_days: float = 0.0
    ) -> float:
        """
        Calculate simple trust score (backward compatible with original interface).
        
        This method provides the same interface as the original TrustScorer
        for backward compatibility.
        
        Args:
            source: Source of learning example
            outcome_quality: Quality of outcome (0-1)
            consistency_score: Consistency with other knowledge (0-1)
            validation_history: {'validated': N, 'invalidated': M}
            age_days: Age in days
            
        Returns:
            Trust score (0-1)
        """
        result = self.calculate_trust_score(
            source=source,
            outcome_quality=outcome_quality,
            consistency_score=consistency_score,
            validation_history=validation_history,
            age_days=age_days,
            context={}  # Use general context
        )
        
        return result.trust_score


class TrustScoreCache:
    """
    Caching layer for trust scores to improve performance.
    """
    
    def __init__(self, ttl_seconds: int = 3600):
        """
        Initialize trust score cache.
        
        Args:
            ttl_seconds: Time-to-live for cached scores in seconds
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = ttl_seconds
        self.stats = {
            'hits': 0,
            'misses': 0,
            'invalidations': 0,
            'size': 0
        }
    
    def get_trust_score(
        self,
        learning_example_id: int,
        recalculate: bool = False
    ) -> Optional[TrustScoreResult]:
        """
        Get cached trust score or return None if not cached/expired.
        
        Args:
            learning_example_id: ID of learning example
            recalculate: If True, skip cache
            
        Returns:
            TrustScoreResult if cached and valid, None otherwise
        """
        if recalculate:
            return None
        
        cache_key = f"trust_score_{learning_example_id}"
        
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            age = time.time() - cached['timestamp']
            
            if age < self.ttl:
                self.stats['hits'] += 1
                return TrustScoreResult.from_dict(cached['result'])
            else:
                # Expired, remove
                del self.cache[cache_key]
                self.stats['size'] = len(self.cache)
        
        self.stats['misses'] += 1
        return None
    
    def set_trust_score(
        self,
        learning_example_id: int,
        trust_score: TrustScoreResult
    ):
        """
        Cache trust score result.
        
        Args:
            learning_example_id: ID of learning example
            trust_score: Trust score result to cache
        """
        cache_key = f"trust_score_{learning_example_id}"
        self.cache[cache_key] = {
            'result': trust_score.to_dict(),
            'timestamp': time.time()
        }
        self.stats['size'] = len(self.cache)
    
    def invalidate(self, learning_example_id: int):
        """
        Invalidate cached trust score.
        
        Args:
            learning_example_id: ID of learning example
        """
        cache_key = f"trust_score_{learning_example_id}"
        if cache_key in self.cache:
            del self.cache[cache_key]
            self.stats['invalidations'] += 1
            self.stats['size'] = len(self.cache)
    
    def clear(self):
        """Clear all cached scores."""
        self.cache.clear()
        self.stats['size'] = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = self.stats['hits'] / total_requests if total_requests > 0 else 0.0
        
        return {
            **self.stats,
            'hit_rate': hit_rate,
            'total_requests': total_requests
        }


# Global instances
_adaptive_trust_scorer: Optional[AdaptiveTrustScorer] = None
_trust_score_cache: Optional[TrustScoreCache] = None


def get_adaptive_trust_scorer() -> AdaptiveTrustScorer:
    """Get or create global adaptive trust scorer instance."""
    global _adaptive_trust_scorer
    if _adaptive_trust_scorer is None:
        _adaptive_trust_scorer = AdaptiveTrustScorer()
    return _adaptive_trust_scorer


def get_trust_score_cache(ttl_seconds: int = 3600) -> TrustScoreCache:
    """Get or create global trust score cache instance."""
    global _trust_score_cache
    if _trust_score_cache is None:
        _trust_score_cache = TrustScoreCache(ttl_seconds=ttl_seconds)
    return _trust_score_cache
