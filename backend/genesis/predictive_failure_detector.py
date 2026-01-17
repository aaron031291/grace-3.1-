import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import statistics
from models.genesis_key_models import GenesisKey
from genesis.code_change_analyzer import ChangeAnalysis
class FailurePrediction:
    logger = logging.getLogger(__name__)
    """Prediction of a test failure."""
    test_id: str
    failure_probability: float  # 0.0-1.0
    confidence: float  # 0.0-1.0
    predicted_failure_type: Optional[str] = None
    reasons: List[str] = field(default_factory=list)
    suggested_fixes: List[str] = field(default_factory=list)
    historical_evidence: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PredictionModel:
    """Simple ML model for failure prediction."""
    test_id: str
    failure_rate: float = 0.0
    recent_failures: int = 0
    change_sensitivity: float = 0.5  # How sensitive to code changes
    time_since_last_failure: float = 1.0  # Days
    pattern_matches: List[str] = field(default_factory=list)


class PredictiveFailureDetector:
    """
    Predicts test failures before running tests.
    
    Uses:
    - Historical failure patterns
    - Code change analysis
    - Test characteristics
    - Change similarity matching
    """
    
    def __init__(self):
        self.prediction_models: Dict[str, PredictionModel] = {}
        self.historical_failures: List[Dict[str, Any]] = []
        self.pattern_cache: Dict[str, List[str]] = {}
        self.prediction_accuracy: List[Tuple[bool, bool]] = []  # (predicted, actual)
    
    def predict_failures(
        self,
        genesis_key: GenesisKey,
        change_analysis: ChangeAnalysis,
        test_ids: List[str]
    ) -> List[FailurePrediction]:
        """
        Predict which tests will fail based on code change.
        
        Args:
            genesis_key: Genesis Key representing the change
            change_analysis: Semantic analysis of the change
            test_ids: List of tests that will run
            
        Returns:
            List of failure predictions, sorted by probability
        """
        predictions = []
        
        for test_id in test_ids:
            prediction = self._predict_test_failure(
                test_id=test_id,
                genesis_key=genesis_key,
                change_analysis=change_analysis
            )
            if prediction:
                predictions.append(prediction)
        
        # Sort by failure probability (highest first)
        predictions.sort(key=lambda p: p.failure_probability, reverse=True)
        
        logger.info(
            f"[PredictiveDetector] Predicted {len([p for p in predictions if p.failure_probability > 0.5])} "
            f"likely failures from {len(test_ids)} tests"
        )
        
        return predictions
    
    def _predict_test_failure(
        self,
        test_id: str,
        genesis_key: GenesisKey,
        change_analysis: ChangeAnalysis
    ) -> Optional[FailurePrediction]:
        """Predict if a specific test will fail."""
        
        # Get or create prediction model
        model = self.prediction_models.get(test_id)
        if not model:
            model = PredictionModel(test_id=test_id)
            self.prediction_models[test_id] = model
        
        # Calculate failure probability
        failure_prob = 0.0
        reasons = []
        confidence = 0.0
        
        # Factor 1: Historical failure rate (weight: 0.3)
        if model.failure_rate > 0:
            failure_prob += 0.3 * model.failure_rate
            reasons.append(f"Historical failure rate: {model.failure_rate:.1%}")
            confidence += 0.3
        
        # Factor 2: Recent failures (weight: 0.25)
        if model.recent_failures > 0:
            recent_weight = min(1.0, model.recent_failures / 5.0)
            failure_prob += 0.25 * recent_weight
            reasons.append(f"Failed {model.recent_failures} times recently")
            confidence += 0.25
        
        # Factor 3: Change sensitivity (weight: 0.2)
        # Tests that fail when related code changes
        if model.change_sensitivity > 0.5:
            sensitivity_score = (model.change_sensitivity - 0.5) * 2.0
            failure_prob += 0.2 * sensitivity_score
            reasons.append(f"High change sensitivity: {model.change_sensitivity:.2f}")
            confidence += 0.2
        
        # Factor 4: Pattern matching (weight: 0.15)
        # Similar changes that caused failures before
        pattern_matches = self._find_similar_failures(genesis_key, change_analysis)
        if pattern_matches:
            pattern_score = min(1.0, len(pattern_matches) / 3.0)
            failure_prob += 0.15 * pattern_score
            reasons.append(f"Similar failures in history: {len(pattern_matches)}")
            confidence += 0.15
        
        # Factor 5: Risk score from change analysis (weight: 0.1)
        if change_analysis.risk_score > 0.5:
            risk_score = (change_analysis.risk_score - 0.5) * 2.0
            failure_prob += 0.1 * risk_score
            reasons.append(f"High-risk change: {change_analysis.risk_score:.2f}")
            confidence += 0.1
        
        # Cap at 1.0
        failure_prob = min(1.0, failure_prob)
        confidence = min(1.0, confidence)
        
        # Determine failure type
        failure_type = self._predict_failure_type(model, change_analysis)
        
        # Generate suggested fixes
        suggested_fixes = self._suggest_fixes(failure_type, change_analysis)
        
        return FailurePrediction(
            test_id=test_id,
            failure_probability=failure_prob,
            confidence=confidence,
            predicted_failure_type=failure_type,
            reasons=reasons,
            suggested_fixes=suggested_fixes,
            historical_evidence={
                "failure_rate": model.failure_rate,
                "recent_failures": model.recent_failures,
                "change_sensitivity": model.change_sensitivity
            }
        )
    
    def _find_similar_failures(
        self,
        genesis_key: GenesisKey,
        change_analysis: ChangeAnalysis
    ) -> List[str]:
        """Find similar changes that caused failures."""
        matches = []
        
        # Simple pattern matching based on:
        # - Changed functions/classes
        # - File path similarity
        # - Change type
        
        for failure in self.historical_failures[-100:]:  # Last 100 failures
            similarity = 0.0
            
            # Check file path similarity
            if failure.get('file_path') == genesis_key.file_path:
                similarity += 0.5
            
            # Check function/class similarity
            failure_functions = failure.get('affected_functions', [])
            if any(f in change_analysis.affected_functions for f in failure_functions):
                similarity += 0.3
            
            # Check change type similarity
            if failure.get('change_type') in [c.change_type.value for c in change_analysis.changes]:
                similarity += 0.2
            
            if similarity > 0.5:
                matches.append(failure.get('test_id', 'unknown'))
        
        return matches
    
    def _predict_failure_type(
        self,
        model: PredictionModel,
        change_analysis: ChangeAnalysis
    ) -> str:
        """Predict what type of failure will occur."""
        
        # Analyze change types
        has_deletions = any(
            c.change_type.value.endswith('_deleted')
            for c in change_analysis.changes
        )
        
        has_modifications = any(
            c.change_type.value.endswith('_modified')
            for c in change_analysis.changes
        )
        
        if has_deletions:
            return "missing_functionality"  # Function/class was deleted
        elif has_modifications and change_analysis.risk_score > 0.7:
            return "regression"  # High-risk modification
        elif model.recent_failures > 2:
            return "flaky_test"  # Test is flaky
        else:
            return "unknown"
    
    def _suggest_fixes(
        self,
        failure_type: str,
        change_analysis: ChangeAnalysis
    ) -> List[str]:
        """Suggest fixes based on predicted failure type."""
        fixes = []
        
        if failure_type == "missing_functionality":
            fixes.append("Check if deleted function is still needed")
            fixes.append("Update tests to match new API")
        
        elif failure_type == "regression":
            fixes.append("Review high-risk changes carefully")
            fixes.append("Add additional test coverage")
        
        elif failure_type == "flaky_test":
            fixes.append("Investigate test stability")
            fixes.append("Add retry logic or fix timing issues")
        
        return fixes
    
    def record_actual_result(
        self,
        test_id: str,
        predicted_failure: Optional[FailurePrediction],
        actual_failed: bool
    ):
        """Record actual test result to improve predictions."""
        
        # Update prediction accuracy
        if predicted_failure:
            predicted = predicted_failure.failure_probability > 0.5
            self.prediction_accuracy.append((predicted, actual_failed))
        
        # Update model
        model = self.prediction_models.get(test_id)
        if not model:
            model = PredictionModel(test_id=test_id)
            self.prediction_models[test_id] = model
        
        # Update failure rate
        if actual_failed:
            model.recent_failures += 1
            # Record in history
            self.historical_failures.append({
                "test_id": test_id,
                "timestamp": datetime.utcnow().isoformat(),
                "failed": True
            })
        else:
            # Decay recent failures
            model.recent_failures = max(0, model.recent_failures - 0.5)
            model.time_since_last_failure = 0.0
        
        # Update failure rate (moving average)
        total_runs = len([f for f in self.historical_failures if f.get('test_id') == test_id])
        failures = len([f for f in self.historical_failures if f.get('test_id') == test_id and f.get('failed')])
        if total_runs > 0:
            model.failure_rate = failures / total_runs
        
        # Update change sensitivity (if test failed after code change)
        if actual_failed and predicted_failure:
            # Increase sensitivity
            model.change_sensitivity = min(1.0, model.change_sensitivity + 0.1)
        
        # Keep only last 1000 failures
        if len(self.historical_failures) > 1000:
            self.historical_failures = self.historical_failures[-1000:]
    
    def get_prediction_accuracy(self) -> Dict[str, float]:
        """Get accuracy metrics for predictions."""
        if not self.prediction_accuracy:
            return {"accuracy": 0.0, "precision": 0.0, "recall": 0.0}
        
        total = len(self.prediction_accuracy)
        correct = sum(1 for pred, actual in self.prediction_accuracy if pred == actual)
        
        true_positives = sum(1 for pred, actual in self.prediction_accuracy if pred and actual)
        false_positives = sum(1 for pred, actual in self.prediction_accuracy if pred and not actual)
        false_negatives = sum(1 for pred, actual in self.prediction_accuracy if not pred and actual)
        
        accuracy = correct / total if total > 0 else 0.0
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
        
        return {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "total_predictions": total
        }


# Global instance
_detector: Optional[PredictiveFailureDetector] = None


def get_predictive_failure_detector() -> PredictiveFailureDetector:
    """Get or create global predictive failure detector instance."""
    global _detector
    if _detector is None:
        _detector = PredictiveFailureDetector()
    return _detector
