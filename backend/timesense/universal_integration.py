"""
Universal TimeSense Integration Helper

Provides a standardized way to integrate TimeSense into any component.
This module ensures consistent TimeSense integration across all Grace components.
"""

import logging
from contextlib import contextmanager
from typing import Optional, Callable, Any, Dict
from functools import wraps

logger = logging.getLogger(__name__)

# TimeSense availability check
try:
    from timesense.integration import track_operation, TimeEstimator, predict_time
    from timesense.primitives import PrimitiveType
    TIMESENSE_AVAILABLE = True
except ImportError:
    TIMESENSE_AVAILABLE = False
    from contextlib import nullcontext
    def track_operation(*args, **kwargs):
        return nullcontext()
    def predict_time(*args, **kwargs):
        return None
    TimeEstimator = None
    PrimitiveType = None


def ensure_timesense_available():
    """Ensure TimeSense is available, raise helpful error if not."""
    if not TIMESENSE_AVAILABLE:
        logger.warning(
            "[TIMESENSE] TimeSense not available. Install timesense package for time tracking. "
            "Operations will continue without time prediction."
        )


@contextmanager
def track_with_timesense(
    primitive_type: Optional[Any] = None,
    size: float = 1.0,
    model_name: Optional[str] = None,
    task_id: Optional[str] = None,
    fallback_name: Optional[str] = None
):
    """
    Universal TimeSense tracking context manager.
    
    Usage:
        with track_with_timesense(PrimitiveType.EMBED_TEXT, num_tokens, model_name="qwen"):
            result = embedding_model.embed(text)
    
    Args:
        primitive_type: PrimitiveType enum value or string
        size: Size metric for the operation
        model_name: Optional model name
        task_id: Optional task ID
        fallback_name: Optional fallback operation name if primitive_type unavailable
    
    Returns:
        Context manager for tracking
    """
    if not TIMESENSE_AVAILABLE:
        yield None
        return
    
    try:
        # Convert string to PrimitiveType if needed
        if isinstance(primitive_type, str) and PrimitiveType:
            try:
                primitive_type = PrimitiveType(primitive_type)
            except (ValueError, AttributeError):
                logger.debug(f"[TIMESENSE] Unknown primitive type: {primitive_type}")
                primitive_type = None
        
        if primitive_type is None:
            # No tracking available
            yield None
            return
        
        with track_operation(primitive_type, size, task_id=task_id, model_name=model_name):
            yield None
    except Exception as e:
        logger.debug(f"[TIMESENSE] Tracking failed: {e}")
        yield None


def timesense_tracked(
    primitive_type: Optional[Any] = None,
    size_extractor: Optional[Callable] = None,
    model_name_extractor: Optional[Callable] = None,
    fallback_name: Optional[str] = None
):
    """
    Decorator to automatically track function execution with TimeSense.
    
    Usage:
        @timesense_tracked(PrimitiveType.EMBED_TEXT, lambda self, texts: len(texts) * 50)
        def embed_text(self, texts):
            ...
    
    Args:
        primitive_type: PrimitiveType enum value or string
        size_extractor: Function to extract size from function arguments
        model_name_extractor: Function to extract model name from arguments
        fallback_name: Fallback operation name
    
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not TIMESENSE_AVAILABLE:
                return func(*args, **kwargs)
            
            # Extract size and model name
            size = 1.0
            if size_extractor:
                try:
                    size = size_extractor(*args, **kwargs)
                except Exception as e:
                    logger.debug(f"[TIMESENSE] Size extraction failed: {e}")
            
            model_name = None
            if model_name_extractor:
                try:
                    model_name = model_name_extractor(*args, **kwargs)
                except Exception as e:
                    logger.debug(f"[TIMESENSE] Model name extraction failed: {e}")
            
            # Track operation
            with track_with_timesense(primitive_type, size, model_name=model_name):
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


def estimate_operation_time(
    primitive_type: Optional[Any] = None,
    size: float = 1.0,
    model_name: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Estimate operation time without tracking.
    
    Args:
        primitive_type: PrimitiveType enum value or string
        size: Size metric
        model_name: Optional model name
    
    Returns:
        Dict with time estimate or None
    """
    if not TIMESENSE_AVAILABLE or not predict_time:
        return None
    
    try:
        # Convert string to PrimitiveType if needed
        if isinstance(primitive_type, str) and PrimitiveType:
            try:
                primitive_type = PrimitiveType(primitive_type)
            except (ValueError, AttributeError):
                return None
        
        if primitive_type is None:
            return None
        
        prediction = predict_time(primitive_type, size, model_name)
        if prediction:
            return {
                'p50_ms': prediction.p50_ms,
                'p90_ms': prediction.p90_ms,
                'p95_ms': prediction.p95_ms,
                'p99_ms': prediction.p99_ms,
                'confidence': prediction.confidence,
                'human_readable': prediction.human_readable(),
                'warnings': prediction.warnings
            }
    except Exception as e:
        logger.debug(f"[TIMESENSE] Time estimation failed: {e}")
    
    return None


# Export for easy importing
__all__ = [
    'TIMESENSE_AVAILABLE',
    'track_with_timesense',
    'timesense_tracked',
    'estimate_operation_time',
    'ensure_timesense_available',
    'TimeEstimator',
    'PrimitiveType'
]
