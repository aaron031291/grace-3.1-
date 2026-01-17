import logging
import time
from contextlib import contextmanager
from typing import Dict, Any, Optional, Callable
from functools import wraps
from timesense.engine import get_timesense_engine, TimeSenseEngine
from timesense.primitives import PrimitiveType
class TimeEstimator:
    logger = logging.getLogger(__name__)
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
