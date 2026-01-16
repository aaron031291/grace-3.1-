"""
TimeSense Integration Helper for GRACE

Provides easy-to-use decorators and context managers for integrating
TimeSense time prediction into GRACE operations.
"""

import logging
import time
from contextlib import contextmanager
from typing import Dict, Any, Optional, Callable
from functools import wraps

from timesense.engine import get_timesense_engine, TimeSenseEngine
from timesense.primitives import PrimitiveType

logger = logging.getLogger(__name__)


# Global engine instance cache
_engine: Optional[TimeSenseEngine] = None


def get_engine() -> TimeSenseEngine:
    """Get or initialize TimeSense engine."""
    global _engine
    if _engine is None:
        _engine = get_timesense_engine(auto_calibrate=True)
        if not _engine.is_ready():
            _engine.initialize_sync(quick_calibration=False)
    return _engine


@contextmanager
def track_operation(
    primitive_type: PrimitiveType,
    size: float,
    task_id: Optional[str] = None,
    model_name: Optional[str] = None
):
    """
    Context manager for tracking operation time with TimeSense.
    
    Usage:
        with track_operation(PrimitiveType.EMBED_TEXT, num_tokens, model_name="qwen"):
            embeddings = model.embed_text(texts)
    
    Returns:
        Tuple of (prediction_result, actual_duration_ms)
    """
    engine = get_engine()
    
    # Generate task ID if not provided
    if task_id is None:
        task_id = f"{primitive_type.value}_{int(time.time() * 1000)}"
    
    # Get prediction
    prediction = engine.start_task(
        task_id=task_id,
        primitive_type=primitive_type,
        size=size,
        metadata={"model_name": model_name}
    )
    
    if prediction:
        logger.debug(
            f"[TIMESENSE] Predicted {primitive_type.value}: "
            f"{prediction.human_readable()} (confidence: {prediction.confidence:.2f})"
        )
    
    start_time = time.time()
    try:
        yield prediction
    finally:
        actual_ms = (time.time() - start_time) * 1000
        
        # Record actual duration
        actual_size = size  # Could be updated if actual differs
        engine.end_task(task_id, actual_size=actual_size)
        
        if prediction:
            error_ratio = (actual_ms - prediction.p50_ms) / prediction.p50_ms if prediction.p50_ms > 0 else 0
            logger.debug(
                f"[TIMESENSE] Completed {primitive_type.value}: "
                f"actual={actual_ms:.1f}ms, predicted={prediction.p50_ms:.1f}ms, "
                f"error={error_ratio*100:.1f}%"
            )


def predict_time(primitive_type: PrimitiveType, size: float, model_name: Optional[str] = None):
    """Quick prediction without tracking."""
    engine = get_engine()
    return engine.predict(primitive_type, size, model_name)


def track_function(primitive_type: PrimitiveType, size_extractor: Callable = None):
    """
    Decorator to automatically track function execution time.
    
    Usage:
        @track_function(PrimitiveType.EMBED_TEXT, lambda self, texts: len(texts) * 50)
        def embed_text(self, texts):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract size if size_extractor provided
            size = 0
            if size_extractor:
                try:
                    size = size_extractor(*args, **kwargs)
                except Exception as e:
                    logger.warning(f"[TIMESENSE] Failed to extract size: {e}")
            
            task_id = f"{func.__name__}_{int(time.time() * 1000)}"
            with track_operation(primitive_type, size, task_id=task_id):
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


class TimeEstimator:
    """
    Helper class for common time estimation operations in GRACE.
    """
    
    @staticmethod
    def estimate_file_processing(
        file_size_bytes: int,
        include_embedding: bool = True,
        model_name: Optional[str] = None
    ):
        """Estimate time for file processing pipeline."""
        engine = get_engine()
        return engine.estimate_file_processing(file_size_bytes, include_embedding, model_name)
    
    @staticmethod
    def estimate_retrieval(
        query_tokens: int = 50,
        top_k: int = 10,
        num_vectors: int = 10000
    ):
        """Estimate time for RAG retrieval."""
        engine = get_engine()
        return engine.estimate_retrieval(query_tokens, top_k, num_vectors)
    
    @staticmethod
    def estimate_llm_response(
        prompt_tokens: int,
        max_output_tokens: int,
        model_name: Optional[str] = None
    ):
        """Estimate time for LLM response generation."""
        engine = get_engine()
        return engine.estimate_llm_response(prompt_tokens, max_output_tokens, model_name)
    
    @staticmethod
    def estimate_embedding(
        num_tokens: int,
        model_name: Optional[str] = None
    ):
        """Estimate time for embedding generation."""
        return predict_time(PrimitiveType.EMBED_TEXT, num_tokens, model_name)


def add_time_estimate_to_response(response: Dict[str, Any], prediction) -> Dict[str, Any]:
    """Add time estimate information to API response."""
    if prediction:
        response['time_estimate'] = {
            'p50_ms': prediction.p50_ms,
            'p95_ms': prediction.p95_ms,
            'human_readable': prediction.human_readable(),
            'confidence': prediction.confidence,
            'confidence_level': prediction.confidence_level.value,
            'warnings': prediction.warnings
        }
    return response
