import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta
class DeterministicTimeProof:
    logger = logging.getLogger(__name__)
    """
    Proof that an operation's time is deterministic based on TimeSense predictions.
    """
    operation_id: str
    primitive_type: Optional[str]
    predicted_time_ms: float
    actual_time_ms: Optional[float]
    within_predicted_bounds: Optional[bool]
    time_confidence: float
    determinism_score: float  # 0.0-1.0, how deterministic the timing was
    violations: List[str]
    
    def is_deterministic(self, tolerance: float = 0.2) -> bool:
        """
        Check if operation was deterministic based on time bounds.
        
        Args:
            tolerance: Allowed deviation from prediction (0.2 = 20%)
        
        Returns:
            True if operation completed within predicted bounds
        """
        if self.actual_time_ms is None:
            return False
        
        if self.within_predicted_bounds is not None:
            return self.within_predicted_bounds
        
        # Check if actual time is within tolerance of prediction
        error_ratio = abs(self.actual_time_ms - self.predicted_time_ms) / self.predicted_time_ms
        return error_ratio <= tolerance and len(self.violations) == 0


class TimeSenseDeterminismValidator:
    """
    Validates determinism using TimeSense predictions.
    
    For deterministic operations:
    - Operations must complete within predicted time bounds
    - Time uncertainty reduces determinism confidence
    - Repeated operations should have consistent timing
    """
    
    def __init__(self):
        self.operation_history: Dict[str, List[float]] = {}  # Track operation times
        
    def validate_time_determinism(
        self,
        operation_id: str,
        primitive_type: Optional[PrimitiveType],
        predicted_time: Optional[PredictionResult],
        actual_time_ms: Optional[float] = None
    ) -> DeterministicTimeProof:
        """
        Validate that operation timing is deterministic.
        
        Args:
            operation_id: Unique operation identifier
            primitive_type: Type of primitive operation
            predicted_time: TimeSense prediction result
            actual_time_ms: Actual execution time (if available)
        
        Returns:
            DeterministicTimeProof with validation results
        """
        violations = []
        
        if not TIMESENSE_AVAILABLE or not predicted_time:
            return DeterministicTimeProof(
                operation_id=operation_id,
                primitive_type=primitive_type.value if primitive_type else None,
                predicted_time_ms=0.0,
                actual_time_ms=actual_time_ms,
                within_predicted_bounds=None,
                time_confidence=0.0,
                determinism_score=0.0,
                violations=["TimeSense not available or no prediction"]
            )
        
        # Extract prediction bounds
        p50_ms = predicted_time.p50_ms
        p95_ms = predicted_time.p95_ms
        confidence = predicted_time.confidence
        
        # Check if we have an actual time to validate against
        within_bounds = None
        if actual_time_ms is not None:
            # Operation completed - check if within predicted bounds
            within_bounds = actual_time_ms <= p95_ms
            
            if not within_bounds:
                violations.append(
                    f"Operation exceeded predicted time bounds: "
                    f"actual={actual_time_ms:.1f}ms, predicted_p95={p95_ms:.1f}ms"
                )
            
            # Track for consistency analysis
            if operation_id not in self.operation_history:
                self.operation_history[operation_id] = []
            self.operation_history[operation_id].append(actual_time_ms)
        
        # Calculate determinism score
        determinism_score = self._calculate_determinism_score(
            predicted_time=predicted_time,
            actual_time_ms=actual_time_ms,
            operation_history=self.operation_history.get(operation_id, [])
        )
        
        # Time uncertainty reduces determinism
        if confidence < 0.7:
            violations.append(
                f"Low time prediction confidence ({confidence:.2f}) reduces determinism"
            )
        
        if predicted_time.is_extrapolation:
            violations.append(
                "Time prediction based on extrapolation - reduced determinism"
            )
        
        if predicted_time.is_stale:
            violations.append(
                "Time prediction based on stale calibration - reduced determinism"
            )
        
        return DeterministicTimeProof(
            operation_id=operation_id,
            primitive_type=primitive_type.value if primitive_type else None,
            predicted_time_ms=p50_ms,
            actual_time_ms=actual_time_ms,
            within_predicted_bounds=within_bounds,
            time_confidence=confidence,
            determinism_score=determinism_score,
            violations=violations
        )
    
    def _calculate_determinism_score(
        self,
        predicted_time: PredictionResult,
        actual_time_ms: Optional[float],
        operation_history: List[float]
    ) -> float:
        """
        Calculate determinism score based on time predictions and history.
        
        Returns:
            Score from 0.0 (non-deterministic) to 1.0 (fully deterministic)
        """
        score = 1.0
        
        # Factor 1: Prediction confidence (0.7 weight)
        score *= (0.3 + predicted_time.confidence * 0.7)
        
        # Factor 2: Within bounds (0.2 weight)
        if actual_time_ms is not None:
            if actual_time_ms <= predicted_time.p95_ms:
                # Within p95 - good
                pass
            elif actual_time_ms <= predicted_time.p99_ms:
                # Within p99 but exceeded p95 - slight penalty
                score *= 0.9
            else:
                # Exceeded p99 - significant penalty
                score *= 0.5
        
        # Factor 3: Consistency (0.1 weight)
        if len(operation_history) >= 3:
            # Check coefficient of variation (lower = more consistent)
            mean_time = sum(operation_history) / len(operation_history)
            variance = sum((t - mean_time) ** 2 for t in operation_history) / len(operation_history)
            std_dev = variance ** 0.5
            cv = std_dev / mean_time if mean_time > 0 else 1.0
            
            # Low CV = high consistency = more deterministic
            consistency_factor = max(0.5, 1.0 - cv)
            score *= (0.9 + consistency_factor * 0.1)
        
        # Penalties
        if predicted_time.is_extrapolation:
            score *= 0.8  # Extrapolation reduces determinism
        
        if predicted_time.is_stale:
            score *= 0.85  # Stale data reduces determinism
        
        return max(0.0, min(1.0, score))
    
    def get_operation_time_history(self, operation_id: str) -> List[float]:
        """Get historical timing data for an operation."""
        return self.operation_history.get(operation_id, [])
    
    def check_time_consistency(self, operation_id: str, threshold: float = 0.3) -> bool:
        """
        Check if operation has consistent timing across runs.
        
        Args:
            operation_id: Operation identifier
            threshold: Maximum coefficient of variation for consistency
        
        Returns:
            True if operation timing is consistent
        """
        history = self.operation_history.get(operation_id, [])
        
        if len(history) < 2:
            return True  # Need at least 2 samples
        
        mean_time = sum(history) / len(history)
        if mean_time == 0:
            return True
        
        variance = sum((t - mean_time) ** 2 for t in history) / len(history)
        std_dev = variance ** 0.5
        cv = std_dev / mean_time
        
        return cv <= threshold


def add_time_determinism_to_context(
    decision_context: Any,
    time_proof: DeterministicTimeProof
) -> Dict[str, Any]:
    """
    Add TimeSense determinism information to decision context.
    
    Args:
        decision_context: Decision context (OODA loop context)
        time_proof: Deterministic time proof
    
    Returns:
        Dictionary with time determinism information
    """
    return {
        'time_determinism': {
            'is_deterministic': time_proof.is_deterministic(),
            'determinism_score': time_proof.determinism_score,
            'time_confidence': time_proof.time_confidence,
            'predicted_time_ms': time_proof.predicted_time_ms,
            'actual_time_ms': time_proof.actual_time_ms,
            'within_bounds': time_proof.within_predicted_bounds,
            'violations': time_proof.violations
        }
    }


def validate_operation_determinism(
    operation_id: str,
    primitive_type: PrimitiveType,
    size: float,
    actual_time_ms: Optional[float] = None,
    model_name: Optional[str] = None
) -> DeterministicTimeProof:
    """
    Convenience function to validate operation determinism.
    
    Args:
        operation_id: Operation identifier
        primitive_type: Type of operation
        size: Operation size (tokens, bytes, etc.)
        actual_time_ms: Actual execution time
        model_name: Model name (for LLM/embedding operations)
    
    Returns:
        DeterministicTimeProof
    """
    validator = TimeSenseDeterminismValidator()
    
    # Get time prediction
    prediction = None
    if TIMESENSE_AVAILABLE and TimeEstimator:
        try:
            prediction = predict_time(primitive_type, size, model_name)
        except Exception as e:
            logger.warning(f"[TIMESENSE-DETERMINISM] Prediction failed: {e}")
    
    return validator.validate_time_determinism(
        operation_id=operation_id,
        primitive_type=primitive_type,
        predicted_time=prediction,
        actual_time_ms=actual_time_ms
    )
