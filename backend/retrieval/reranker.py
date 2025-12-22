"""
Reranker module for improving retrieval results using cross-encoders.
Uses sentence-transformers/msmarco-bert-base-dot-v5 for relevance scoring.
"""

import logging
from typing import List, Dict, Any, Optional
import torch
from threading import Lock
from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)

# Global reranker instance with lock for thread-safe singleton
_reranker = None
_reranker_lock = Lock()


class DocumentReranker:
    """Reranks retrieved chunks using cross-encoder models."""
    
    def __init__(
        self,
        model_name: str = "sentence-transformers/msmarco-bert-base-dot-v5",
        device: Optional[str] = None,
        use_half_precision: bool = True,
    ):
        """
        Initialize the reranker model.
        
        Args:
            model_name: Hugging Face model identifier
            device: Device to run model on ('cuda', 'cpu'). Auto-detected if None
            use_half_precision: Use FP16 (half precision) for faster inference and lower VRAM
        """
        # Set device
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = device
        self.use_half_precision = use_half_precision and device == "cuda"
        
        self.model_name = model_name
        
        print(f"Loading reranker model: {model_name}")
        print(f"Using device: {self.device}")
        if self.use_half_precision:
            print("Using half precision (FP16) for inference")
        
        # Load the cross-encoder model
        self.model = CrossEncoder(model_name, device=self.device)
        
        # Convert to half precision if enabled and on GPU
        if self.use_half_precision:
            self.model.model = self.model.model.half()
            print("✓ Model converted to FP16")
        
        print("✓ Reranker model loaded successfully")
    
    def rerank(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        top_k: Optional[int] = None,
        score_threshold: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """
        Rerank chunks based on relevance to query using cross-encoder.
        
        Args:
            query: Query text
            chunks: List of chunk dictionaries with 'text' field
            top_k: Return only top k chunks. If None, return all
            score_threshold: Minimum rerank score (0-1)
            
        Returns:
            Reranked list of chunks, sorted by relevance score
        """
        if not chunks:
            logger.debug("No chunks to rerank")
            return chunks
        
        try:
            # Prepare pairs for cross-encoder (query, chunk_text)
            query_chunk_pairs = [
                [query, chunk.get("text", "")]
                for chunk in chunks
            ]
            
            # Get scores from cross-encoder
            # The model handles FP16 conversion internally if needed
            with torch.no_grad():
                if self.use_half_precision:
                    # Ensure model is in eval mode for inference
                    self.model.model.eval()
                scores = self.model.predict(query_chunk_pairs, convert_to_numpy=True)
            
            # Add rerank scores to chunks
            reranked_chunks = []
            for chunk, score in zip(chunks, scores):
                chunk_copy = chunk.copy()
                chunk_copy["rerank_score"] = float(score)
                reranked_chunks.append(chunk_copy)
            
            # Sort by rerank score in descending order
            reranked_chunks.sort(key=lambda x: x["rerank_score"], reverse=True)
            
            # Filter by threshold
            filtered_chunks = [
                chunk for chunk in reranked_chunks
                if chunk["rerank_score"] >= score_threshold
            ]
            
            # Return top k if specified
            if top_k:
                filtered_chunks = filtered_chunks[:top_k]
            
            logger.debug(
                f"Reranked {len(chunks)} chunks, kept {len(filtered_chunks)} "
                f"(threshold={score_threshold}, top_k={top_k})"
            )
            
            return filtered_chunks
        
        except Exception as e:
            logger.error(f"Reranking error: {e}", exc_info=True)
            # Return original chunks if reranking fails
            return chunks
    
    def unload_model(self):
        """
        Unload the model from VRAM and clear cache.
        """
        if hasattr(self, 'model') and self.model is not None:
            try:
                # Move model to CPU first
                if self.device != 'cpu':
                    self.model.model.to('cpu')
                
                # Delete the model
                del self.model
                self.model = None
                
                # Clear CUDA cache if using GPU
                if self.device == 'cuda' and torch.cuda.is_available():
                    torch.cuda.empty_cache()
                
                print("✓ Reranker model unloaded from VRAM")
            except Exception as e:
                logger.warning(f"Warning while unloading reranker model: {e}")
    
    def __del__(self):
        """Destructor to unload model."""
        self.unload_model()


def get_reranker(
    model_name: str = "sentence-transformers/msmarco-bert-base-dot-v5",
    device: Optional[str] = None,
    use_half_precision: bool = True,
    reset: bool = False,
) -> DocumentReranker:
    """
    Get or create the global reranker instance (thread-safe singleton).
    
    This function ensures the reranker model is loaded only once into VRAM,
    even if called multiple times from different threads.
    
    Args:
        model_name: Hugging Face model identifier
        device: Device to use (only used on first initialization)
        use_half_precision: Use FP16 for lower memory usage (only used on first initialization)
        reset: Force reload the model (clears singleton)
        
    Returns:
        DocumentReranker instance (same instance across all calls)
    """
    global _reranker
    
    # Double-checked locking pattern for thread safety
    if _reranker is None or reset:
        with _reranker_lock:
            # Check again inside lock in case another thread initialized it
            if _reranker is None or reset:
                logger.info(f"Initializing reranker singleton with model: {model_name}")
                _reranker = DocumentReranker(
                    model_name=model_name,
                    device=device,
                    use_half_precision=use_half_precision
                )
    
    return _reranker
