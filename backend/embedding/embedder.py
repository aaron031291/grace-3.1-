"""
Embedding module for generating text embeddings using Qwen3-Embedding-4B model.
"""

import os
import numpy as np
from pathlib import Path
from typing import List, Union, Optional, Tuple
import torch
from sentence_transformers import SentenceTransformer

# Import settings
try:
    from settings import settings
    USE_SETTINGS = True
except ImportError:
    USE_SETTINGS = False


class EmbeddingModel:
    """
    Wrapper for Qwen3-Embedding-4B model for text embeddings.
    
    IMPORTANT: Use get_embedding_model() function to get instances.
    Direct instantiation should only happen via the singleton factory.
    """
    
    # Class variable to track instances
    _instance_count = 0
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        device: Optional[str] = None,
        normalize_embeddings: bool = True,
        max_length: Optional[int] = None,
    ):
        """
        Initialize the embedding model.
        
        NOTE: This should only be called by get_embedding_model() singleton factory.
        
        Args:
            model_path: Path to the model directory. If None, uses default from settings
            device: Device to run model on ('cuda', 'cpu'). Defaults to 'cpu' for stability
            normalize_embeddings: Whether to normalize embeddings to unit length
            max_length: Maximum sequence length. Model supports up to 32k tokens
        """
        # Track instance creation
        EmbeddingModel._instance_count += 1
        instance_num = EmbeddingModel._instance_count
        
        # SAFETY CHECK: Should never create more than 1 instance
        if instance_num > 1:
            print(f"[WARN]  WARNING: EmbeddingModel instance #{instance_num} created!")
            print(f"[WARN]  This should not happen - use get_embedding_model() singleton instead!")
            print(f"[WARN]  Stack trace:")
            import traceback
            traceback.print_stack()
        
        print(f"[EMBEDDING] Creating EmbeddingModel instance #{instance_num}...")
        
        self.normalize_embeddings = normalize_embeddings
        self.max_length = max_length or 32768  # 32k context length
        
        # Set device - DEFAULT TO CPU to avoid CUDA memory issues
        if device is None:
            if USE_SETTINGS:
                device = settings.EMBEDDING_DEVICE
            # CRITICAL: Default to CPU to avoid out-of-memory errors
            device = device or "cpu"
        
        # Force CPU if device not explicitly set and not available
        if device == 'cuda' and not torch.cuda.is_available():
            print("[WARN] CUDA requested but not available, falling back to CPU")
            device = 'cpu'
        
        self.device = "cuda"
        
        # Determine model path
        if model_path is None:
            if USE_SETTINGS:
                model_path = settings.EMBEDDING_MODEL_PATH
            else:
                backend_dir = Path(__file__).parent.parent
                model_path = str(backend_dir / "models" / "embedding" / "qwen_4b")
        
        if not Path(model_path).exists():
            raise FileNotFoundError(f"Model path does not exist: {model_path}")
        
        print(f"[EMBEDDING] [LOADING] Instantiating EmbeddingModel class...")
        print(f"[EMBEDDING]   Model path: {model_path}")
        print(f"[EMBEDDING]   Device: {self.device}")
        
        # Load the model with reduced memory footprint
        try:
            print(f"[EMBEDDING]   Loading model weights (this may take a moment)...")
            self.model = SentenceTransformer(
                model_path, 
                device=self.device, 
                trust_remote_code=True
            )
        except Exception as e:
            print(f"[WARN] Failed to load model on {self.device}: {e}")
            print("Retrying with CPU...")
            self.device = 'cpu'
            self.model = SentenceTransformer(
                model_path, 
                device='cpu', 
                trust_remote_code=True
            )
        
        self.model_path = model_path
        
        print(f"[EMBEDDING] [OK] Model loaded successfully")
        if self.device == 'cuda':
            if torch.cuda.is_available():
                print(f"[EMBEDDING]   GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
                print(f"[EMBEDDING]   GPU Used: {torch.cuda.memory_allocated(0) / 1e9:.2f} GB")
    
    def __del__(self):
        """Destructor to unload model from VRAM."""
        self.unload_model()
    
    def unload_model(self):
        """
        Unload the model from VRAM and clear cache.
        Call this when you're done using the model to free up memory.
        """
        if hasattr(self, 'model') and self.model is not None:
            try:
                # Move model to CPU first
                if self.device != 'cpu':
                    self.model.to('cpu')
                
                # Delete the model
                del self.model
                self.model = None
                
                # Clear CUDA cache if using GPU
                if self.device == 'cuda' and torch.cuda.is_available():
                    torch.cuda.empty_cache()
                
                print("[OK] Model unloaded from VRAM")
            except Exception as e:
                print(f"[WARN] Warning while unloading model: {e}")
    
    def _ensure_model_loaded(self):
        """Ensure model is loaded, raise error if not."""
        if self.model is None:
            raise RuntimeError("Model has been unloaded. Create a new instance to use embeddings.")
    
    def embed_text(
        self,
        text: Union[str, List[str]],
        normalize: Optional[bool] = None,
        instruction: Optional[str] = None,
        batch_size: int = 32,
        convert_to_numpy: bool = True,
        convert_to_tensor: bool = False,
    ) -> Union[np.ndarray, torch.Tensor]:
        """
        Generate embeddings for text(s).
        
        Args:
            text: Single text string or list of text strings
            normalize: Override default normalization setting for this call
            instruction: Optional instruction to guide the embedding (instruction-aware model)
            batch_size: Batch size for processing (default 8 to prevent memory issues on CPU)
            convert_to_numpy: Convert output to numpy array
            convert_to_tensor: Convert output to torch tensor
            
        Returns:
            Embeddings as numpy array or torch tensor depending on convert_to_* flags
            Shape: (num_texts, embedding_dim) or (embedding_dim,) for single text
        """
        self._ensure_model_loaded()
        
        is_single_text = isinstance(text, str)
        texts = [text] if is_single_text else text
        
        # Add instruction prefix if provided
        if instruction:
            texts = [f"{instruction} {t}" for t in texts]
        
        # Reduce batch size on CPU to avoid memory issues
        if self.device == 'cpu':
            batch_size = min(batch_size, 8)  # Cap at 8 for CPU
        
        # Generate embeddings with smaller batch size
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=convert_to_numpy,
            convert_to_tensor=convert_to_tensor,
            normalize_embeddings=normalize if normalize is not None else self.normalize_embeddings,
            show_progress_bar=False,  # Disable progress bar to reduce clutter

        )
        
        # Clear torch cache if using CUDA
        if self.device == 'cuda' and torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        # Return single embedding if input was single text
        if is_single_text:
            embeddings = embeddings[0]
        
        return embeddings
    
    def embed_with_scores(
        self,
        texts: List[str],
        normalize: Optional[bool] = None,
        instruction: Optional[str] = None,
        batch_size: int = 32,
    ) -> Tuple[np.ndarray, List[float]]:
        """
        Generate embeddings and return with their statistical scores.
        
        Args:
            texts: List of text strings
            normalize: Override default normalization setting
            instruction: Optional instruction to guide the embedding
            batch_size: Batch size for processing
            
        Returns:
            Tuple of (embeddings, norm_scores) where norm_scores is L2 norm of each embedding
        """
        embeddings = self.embed_text(
            texts,
            normalize=normalize,
            instruction=instruction,
            batch_size=batch_size,
            convert_to_numpy=True,
        )
        
        # Calculate L2 norm for each embedding
        norms = np.linalg.norm(embeddings, axis=1).tolist()
        
        return embeddings, norms
    
    def similarity(
        self,
        text1: Union[str, List[str]],
        text2: Union[str, List[str]],
        metric: str = "cosine",
    ) -> Union[float, np.ndarray]:
        """
        Calculate similarity between texts.
        
        Args:
            text1: Single text or list of texts
            text2: Single text or list of texts
            metric: Similarity metric ('cosine', 'euclidean', 'manhattan')
            
        Returns:
            Similarity score(s). Float for single pair, array for multiple pairs
        """
        from sklearn.metrics.pairwise import cosine_similarity, euclidean_distances
        
        embeddings1 = self.embed_text(text1, convert_to_numpy=True)
        embeddings2 = self.embed_text(text2, convert_to_numpy=True)
        
        # Ensure 2D arrays for calculation
        if len(embeddings1.shape) == 1:
            embeddings1 = embeddings1.reshape(1, -1)
        if len(embeddings2.shape) == 1:
            embeddings2 = embeddings2.reshape(1, -1)
        
        if metric == "cosine":
            similarities = cosine_similarity(embeddings1, embeddings2)
        elif metric == "euclidean":
            similarities = -euclidean_distances(embeddings1, embeddings2)
        elif metric == "manhattan":
            similarities = -np.abs(embeddings1[:, np.newaxis] - embeddings2).sum(axis=2)
        else:
            raise ValueError(f"Unknown metric: {metric}")
        
        # Return scalar if both inputs were single texts
        if isinstance(text1, str) and isinstance(text2, str):
            return float(similarities[0, 0])
        
        return similarities
    
    def most_similar(
        self,
        query: str,
        candidates: List[str],
        top_k: int = 5,
        metric: str = "cosine",
        instruction: Optional[str] = None,
    ) -> List[Tuple[str, float]]:
        """
        Find most similar candidates to a query.
        
        Args:
            query: Query text
            candidates: List of candidate texts
            top_k: Number of top results to return
            metric: Similarity metric to use
            instruction: Optional instruction for embeddings
            
        Returns:
            List of (text, similarity_score) tuples, sorted by similarity descending
        """
        query_embedding = self.embed_text(
            query,
            instruction=instruction,
            convert_to_numpy=True,
        )
        
        candidate_embeddings = self.embed_text(
            candidates,
            instruction=instruction,
            convert_to_numpy=True,
        )
        
        from sklearn.metrics.pairwise import cosine_similarity, euclidean_distances
        
        query_embedding = query_embedding.reshape(1, -1)
        
        if metric == "cosine":
            similarities = cosine_similarity(query_embedding, candidate_embeddings)[0]
        elif metric == "euclidean":
            similarities = -euclidean_distances(query_embedding, candidate_embeddings)[0]
        elif metric == "manhattan":
            similarities = -np.abs(query_embedding - candidate_embeddings).sum(axis=1)
        else:
            raise ValueError(f"Unknown metric: {metric}")
        
        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = [
            (candidates[i], float(similarities[i]))
            for i in top_indices
        ]
        
        return results
    
    def cluster_texts(
        self,
        texts: List[str],
        num_clusters: int = 5,
        instruction: Optional[str] = None,
    ) -> List[List[int]]:
        """
        Cluster texts using K-means clustering.
        
        Args:
            texts: List of texts to cluster
            num_clusters: Number of clusters to create
            instruction: Optional instruction for embeddings
            
        Returns:
            List of cluster assignments for each text
        """
        from sklearn.cluster import KMeans
        
        embeddings = self.embed_text(
            texts,
            instruction=instruction,
            convert_to_numpy=True,
        )
        
        kmeans = KMeans(n_clusters=min(num_clusters, len(texts)), random_state=42)
        cluster_labels = kmeans.fit_predict(embeddings)
        
        # Organize by cluster
        clusters = [[] for _ in range(num_clusters)]
        for idx, label in enumerate(cluster_labels):
            clusters[label].append(idx)
        
        return [c for c in clusters if c]  # Remove empty clusters
    
    def get_embedding_dimension(self) -> int:
        """Get the embedding dimension of the model."""
        self._ensure_model_loaded()
        return self.model.get_sentence_embedding_dimension()
    
    def get_model_info(self) -> dict:
        """Get information about the loaded model."""
        return {
            "model_path": self.model_path,
            "device": self.device,
            "embedding_dimension": self.get_embedding_dimension() if self.model is not None else None,
            "max_length": self.max_length,
            "normalize_embeddings": self.normalize_embeddings,
            "model_loaded": self.model is not None,
        }


# Global instance for convenience - STRICTLY ENFORCED SINGLETON
_embedding_model_instance = None  # Renamed for clarity
_embedding_model_loaded = False  # Track whether model has been loaded
_cache_version = 0  # Cache version for invalidation


def invalidate_embedding_cache() -> None:
    """
    Invalidate the embedding model cache, forcing reload on next access.
    
    Use this when:
    - Model configuration changes
    - Model needs to be reloaded
    - Cache coherence issues detected
    """
    global _embedding_model_instance, _embedding_model_loaded, _cache_version
    _embedding_model_instance = None
    _embedding_model_loaded = False
    _cache_version += 1
    print(f"[EMBEDDING] Cache invalidated (version: {_cache_version})")


def get_embedding_model(
    model_path: Optional[str] = None,
    device: Optional[str] = None,
    reset: bool = False,
) -> EmbeddingModel:
    """
    Get or create the global embedding model instance (singleton pattern).
    The model is loaded ONLY ONCE on first call and reused thereafter.
    
    CRITICAL: This is the ONLY way to get the embedding model.
    Direct EmbeddingModel() instantiation should never happen in production code.
    
    Args:
        model_path: Path to model (only used on first initialization, ignored on subsequent calls)
        device: Device to use (only used on first initialization, ignored on subsequent calls)
        reset: Force reload the model (not recommended in production)
        
    Returns:
        EmbeddingModel instance (always the same singleton instance)
    """
    global _embedding_model_instance, _embedding_model_loaded
    
    # FAST PATH: If model is already loaded, return immediately without logging
    if _embedding_model_loaded and not reset:
        return _embedding_model_instance
    
    # SLOW PATH: First initialization or reset requested
    if _embedding_model_instance is not None and not reset:
        return _embedding_model_instance
    
    print(f"[EMBEDDING] Creating new embedding model instance (singleton)...")
    print(f"[EMBEDDING]   model_path={model_path}, device={device}, reset={reset}")
    
    _embedding_model_instance = EmbeddingModel(model_path=model_path, device=device)
    _embedding_model_loaded = True
    
    print(f"[EMBEDDING] [OK] Embedding model singleton created and ready")
    return _embedding_model_instance


def embed(
    text: Union[str, List[str]],
    instruction: Optional[str] = None,
    batch_size: int = 32,
) -> Union[np.ndarray, List[np.ndarray]]:
    """
    Convenience function to embed text using the default model.
    
    Args:
        text: Single text or list of texts
        instruction: Optional instruction for the embeddings
        batch_size: Batch size for processing
        
    Returns:
        Embeddings as numpy arrays
    """
    model = get_embedding_model()
    return model.embed_text(text, instruction=instruction, batch_size=batch_size)


def similarity(text1: str, text2: str) -> float:
    """
    Convenience function to calculate similarity between two texts.
    
    Args:
        text1: First text
        text2: Second text
        
    Returns:
        Cosine similarity score
    """
    model = get_embedding_model()
    return model.similarity(text1, text2)


def most_similar(query: str, candidates: List[str], top_k: int = 5) -> List[Tuple[str, float]]:
    """
    Convenience function to find most similar candidates.
    
    Args:
        query: Query text
        candidates: List of candidate texts
        top_k: Number of results to return
        
    Returns:
        List of (text, similarity_score) tuples
    """
    model = get_embedding_model()
    return model.most_similar(query, candidates, top_k=top_k)
