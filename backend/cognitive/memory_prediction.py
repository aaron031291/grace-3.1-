import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from collections import defaultdict, deque
import json
from cognitive.learning_memory import LearningExample
from cognitive.episodic_memory import Episode
from cognitive.procedural_memory import Procedure
class MemoryPredictionSystem:
    logger = logging.getLogger(__name__)
    """
    Predicts which memories will be needed and pre-loads them.
    
    Uses pattern recognition to predict memory access:
    - Temporal patterns
    - Context patterns
    - Sequential patterns
    - Usage patterns
    """
    
    def __init__(
        self,
        session: Session,
        prediction_window_hours: int = 24,
        max_predictions: int = 50
    ):
        """
        Initialize memory prediction system.
        
        Args:
            session: Database session
            prediction_window_hours: How far ahead to predict
            max_predictions: Maximum predictions to generate
        """
        self.session = session
        self.prediction_window_hours = prediction_window_hours
        self.max_predictions = max_predictions
        
        # Pattern storage (simple in-memory for efficiency)
        self.temporal_patterns: Dict[int, List[str]] = defaultdict(list)  # hour -> memory_ids
        self.context_patterns: Dict[str, List[str]] = defaultdict(list)  # context_hash -> memory_ids
        self.sequential_patterns: Dict[str, List[str]] = defaultdict(list)  # memory_id -> next_memory_ids
        self.usage_history: deque = deque(maxlen=1000)  # Recent memory accesses
        
        logger.info(
            f"[MEMORY-PREDICTION] Initialized: "
            f"window={prediction_window_hours}h, max={max_predictions}"
        )
    
    def record_access(
        self,
        memory_id: str,
        memory_type: str,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Record memory access for pattern learning.
        
        Args:
            memory_id: ID of accessed memory
            memory_type: Type of memory
            context: Optional context
        """
        now = datetime.utcnow()
        hour = now.hour
        
        # Record temporal pattern
        self.temporal_patterns[hour].append(memory_id)
        
        # Record context pattern
        if context:
            context_hash = self._hash_context(context)
            self.context_patterns[context_hash].append(memory_id)
        
        # Record sequential pattern
        if len(self.usage_history) > 0:
            last_memory = self.usage_history[-1]
            self.sequential_patterns[last_memory["id"]].append(memory_id)
        
        # Add to history
        self.usage_history.append({
            "id": memory_id,
            "type": memory_type,
            "timestamp": now,
            "context": context
        })
    
    def _hash_context(self, context: Dict[str, Any]) -> str:
        """Create hash of context for pattern matching."""
        import hashlib
        context_str = json.dumps(context, sort_keys=True)
        return hashlib.md5(context_str.encode()).hexdigest()[:16]
    
    def predict_by_temporal_pattern(self) -> List[Dict[str, Any]]:
        """
        Predict memories based on temporal patterns.
        
        Returns memories that are typically accessed at current time.
        
        Returns:
            List of predicted memories with confidence scores
        """
        now = datetime.utcnow()
        current_hour = now.hour
        
        # Get memories typically accessed at this hour
        typical_memories = self.temporal_patterns.get(current_hour, [])
        
        # Count frequency
        memory_counts = defaultdict(int)
        for mem_id in typical_memories:
            memory_counts[mem_id] += 1
        
        # Calculate confidence (frequency-based)
        max_count = max(memory_counts.values()) if memory_counts else 1
        predictions = []
        
        for mem_id, count in memory_counts.items():
            confidence = min(1.0, count / max_count)
            predictions.append({
                "memory_id": mem_id,
                "prediction_type": "temporal",
                "confidence": confidence,
                "reason": f"Typically accessed at hour {current_hour}"
            })
        
        # Sort by confidence
        predictions.sort(key=lambda x: x["confidence"], reverse=True)
        
        logger.info(
            f"[MEMORY-PREDICTION] Temporal prediction: "
            f"{len(predictions)} memories for hour {current_hour}"
        )
        
        return predictions[:self.max_predictions]
    
    def predict_by_context(
        self,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Predict memories based on context similarity.
        
        Args:
            context: Current context
            
        Returns:
            List of predicted memories
        """
        context_hash = self._hash_context(context)
        
        # Find similar contexts (simple hash-based)
        similar_contexts = []
        for ctx_hash, memory_ids in self.context_patterns.items():
            # Simple similarity: same hash or similar structure
            if ctx_hash == context_hash:
                similar_contexts.extend(memory_ids)
            elif self._contexts_similar(context, ctx_hash):
                similar_contexts.extend(memory_ids)
        
        # Count frequency
        memory_counts = defaultdict(int)
        for mem_id in similar_contexts:
            memory_counts[mem_id] += 1
        
        # Calculate confidence
        max_count = max(memory_counts.values()) if memory_counts else 1
        predictions = []
        
        for mem_id, count in memory_counts.items():
            confidence = min(1.0, count / max_count)
            predictions.append({
                "memory_id": mem_id,
                "prediction_type": "context",
                "confidence": confidence,
                "reason": "Similar contexts accessed this memory"
            })
        
        predictions.sort(key=lambda x: x["confidence"], reverse=True)
        
        logger.info(
            f"[MEMORY-PREDICTION] Context prediction: "
            f"{len(predictions)} memories for context"
        )
        
        return predictions[:self.max_predictions]
    
    def _contexts_similar(
        self,
        context: Dict[str, Any],
        context_hash: str
    ) -> bool:
        """Check if contexts are similar (simplified)."""
        # For now, only exact matches
        # Could be enhanced with semantic similarity
        return False
    
    def predict_by_sequence(
        self,
        current_memory_id: str
    ) -> List[Dict[str, Any]]:
        """
        Predict next memories based on sequential patterns.
        
        Args:
            current_memory_id: Currently accessed memory
            
        Returns:
            List of predicted next memories
        """
        next_memories = self.sequential_patterns.get(current_memory_id, [])
        
        # Count frequency
        memory_counts = defaultdict(int)
        for mem_id in next_memories:
            memory_counts[mem_id] += 1
        
        # Calculate confidence
        max_count = max(memory_counts.values()) if memory_counts else 1
        predictions = []
        
        for mem_id, count in memory_counts.items():
            confidence = min(1.0, count / max_count)
            predictions.append({
                "memory_id": mem_id,
                "prediction_type": "sequential",
                "confidence": confidence,
                "reason": f"Often accessed after {current_memory_id}"
            })
        
        predictions.sort(key=lambda x: x["confidence"], reverse=True)
        
        logger.info(
            f"[MEMORY-PREDICTION] Sequential prediction: "
            f"{len(predictions)} next memories"
        )
        
        return predictions[:self.max_predictions]
    
    def predict_all(
        self,
        context: Optional[Dict[str, Any]] = None,
        current_memory_id: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Generate all types of predictions.
        
        Args:
            context: Optional current context
            current_memory_id: Optional currently accessed memory
            
        Returns:
            Dictionary of predictions by type
        """
        predictions = {
            "temporal": self.predict_by_temporal_pattern()
        }
        
        if context:
            predictions["context"] = self.predict_by_context(context)
        
        if current_memory_id:
            predictions["sequential"] = self.predict_by_sequence(current_memory_id)
        
        # Combine and deduplicate
        all_predictions = {}
        for pred_type, preds in predictions.items():
            for pred in preds:
                mem_id = pred["memory_id"]
                if mem_id not in all_predictions:
                    all_predictions[mem_id] = pred
                else:
                    # Combine confidences
                    all_predictions[mem_id]["confidence"] = max(
                        all_predictions[mem_id]["confidence"],
                        pred["confidence"]
                    )
                    all_predictions[mem_id]["prediction_type"] += f",{pred_type}"
        
        # Sort by combined confidence
        final_predictions = sorted(
            all_predictions.values(),
            key=lambda x: x["confidence"],
            reverse=True
        )[:self.max_predictions]
        
        logger.info(
            f"[MEMORY-PREDICTION] Combined prediction: "
            f"{len(final_predictions)} unique memories"
        )
        
        return {
            "predictions": final_predictions,
            "by_type": predictions,
            "total": len(final_predictions)
        }
    
    def get_prediction_statistics(self) -> Dict[str, Any]:
        """Get statistics about prediction patterns."""
        return {
            "temporal_patterns": len(self.temporal_patterns),
            "context_patterns": len(self.context_patterns),
            "sequential_patterns": len(self.sequential_patterns),
            "usage_history_size": len(self.usage_history),
            "avg_pattern_size": (
                sum(len(v) for v in self.temporal_patterns.values()) / 
                len(self.temporal_patterns) if self.temporal_patterns else 0
            )
        }


def get_memory_prediction_system(
    session: Session,
    prediction_window_hours: int = 24
) -> MemoryPredictionSystem:
    """Factory function to get memory prediction system."""
    return MemoryPredictionSystem(
        session=session,
        prediction_window_hours=prediction_window_hours
    )
