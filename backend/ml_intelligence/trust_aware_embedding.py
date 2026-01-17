import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass
import logging
from embedding import EmbeddingModel, get_embedding_model
class TrustContext:
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    """Trust context for embedding generation"""
    trust_score: float  # Overall trust (0-1)
    source_reliability: float  # Source reliability (0-1)
    validation_count: int  # Times validated
    invalidation_count: int  # Times invalidated
    age_days: float = 0.0  # Age in days
    confidence_score: Optional[float] = None  # Alternative to trust_score
    
    def get_effective_trust(self) -> float:
        """Get effective trust score (trust_score or confidence_score)"""
        if self.confidence_score is not None:
            return self.confidence_score
        return self.trust_score


class TrustAwareEmbeddingModel:
    """
    Wraps EmbeddingModel to incorporate symbolic trust scores.
    
    This creates neuro-symbolic embeddings where:
    - Neural component: Semantic similarity (from base model)
    - Symbolic component: Trust scores from knowledge base
    - Integrated: Trust-enhanced embeddings and similarity
    """
    
    def __init__(
        self,
        base_model: Optional[EmbeddingModel] = None,
        trust_weight: float = 0.3,
        min_trust_threshold: float = 0.3
    ):
        """
        Initialize trust-aware embedding model.
        
        Args:
            base_model: Base EmbeddingModel instance (uses singleton if None)
            trust_weight: Weight of trust in similarity (0-1)
            min_trust_threshold: Minimum trust to include in results
        """
        self.base_model = base_model or get_embedding_model()
        self.trust_weight = trust_weight
        self.min_trust_threshold = min_trust_threshold
        
        logger.info(f"[TRUST-AWARE EMBEDDING] Initialized with trust_weight={trust_weight}, min_trust={min_trust_threshold}")
    
    def embed_text(
        self,
        text: Union[str, List[str]],
        trust_context: Optional[Union[TrustContext, List[TrustContext]]] = None,
        normalize: Optional[bool] = None,
        instruction: Optional[str] = None,
        batch_size: int = 32,
        convert_to_numpy: bool = True,
        convert_to_tensor: bool = False,
    ) -> Union[np.ndarray, List[np.ndarray]]:
        """
        Generate trust-enhanced embeddings for text.
        
        Args:
            text: Single text or list of texts
            trust_context: Trust context(s) for the text(s)
            normalize: Override default normalization
            instruction: Optional instruction for embedding
            batch_size: Batch size for processing
            convert_to_numpy: Convert to numpy array
            convert_to_tensor: Convert to torch tensor
            
        Returns:
            Embeddings (same format as base model)
        """
        # Get base embeddings
        base_embeddings = self.base_model.embed_text(
            text=text,
            normalize=normalize,
            instruction=instruction,
            batch_size=batch_size,
            convert_to_numpy=convert_to_numpy,
            convert_to_tensor=convert_to_tensor,
        )
        
        # If no trust context, return base embeddings
        if trust_context is None:
            return base_embeddings
        
        # Normalize trust context
        is_single_text = isinstance(text, str)
        is_single_context = isinstance(trust_context, TrustContext)
        
        if is_single_text:
            contexts = [trust_context] if trust_context else []
        else:
            contexts = trust_context if trust_context else []
        
        # Convert to numpy if tensor
        if convert_to_tensor and not convert_to_numpy:
            embeddings_np = base_embeddings.detach().cpu().numpy()
        else:
            embeddings_np = base_embeddings
        
        # Apply trust scaling to embeddings
        # High trust -> amplify embedding (move away from origin)
        # Low trust -> dampen embedding (move toward origin)
        if len(contexts) > 0:
            embeddings_np = self._apply_trust_scaling(embeddings_np, contexts)
        
        # Convert back if needed
        if convert_to_tensor and not convert_to_numpy:
            import torch
            return torch.tensor(embeddings_np)
        
        if is_single_text:
            return embeddings_np[0] if len(embeddings_np.shape) > 1 else embeddings_np
        return embeddings_np
    
    def _apply_trust_scaling(
        self,
        embeddings: np.ndarray,
        contexts: List[TrustContext]
    ) -> np.ndarray:
        """
        Apply trust scaling to embeddings.
        
        Strategy: Scale embeddings based on trust scores
        - High trust (0.8-1.0): Amplify by 1.0-1.2x
        - Medium trust (0.5-0.8): No scaling
        - Low trust (0.0-0.5): Dampen by 0.8-1.0x
        
        This makes high-trust embeddings more distinct in embedding space.
        """
        embeddings = embeddings.copy()
        
        if len(embeddings.shape) == 1:
            embeddings = embeddings.reshape(1, -1)
        
        for i, context in enumerate(contexts):
            if i >= len(embeddings):
                break
            
            trust = context.get_effective_trust()
            
            # Calculate scaling factor (1.0 = no change, 1.2 = amplify, 0.8 = dampen)
            if trust >= 0.8:
                # High trust: amplify
                scale = 1.0 + (trust - 0.8) * 1.0  # 1.0 to 1.2
            elif trust >= 0.5:
                # Medium trust: slight amplification
                scale = 1.0 + (trust - 0.5) * 0.33  # 1.0 to 1.1
            else:
                # Low trust: dampen
                scale = 0.8 + trust * 0.4  # 0.8 to 1.0
            
            embeddings[i] = embeddings[i] * scale
        
        return embeddings
    
    def similarity_with_trust(
        self,
        query: str,
        candidates: List[str],
        candidate_trust: List[TrustContext],
        top_k: int = 5,
        metric: str = "cosine",
        instruction: Optional[str] = None,
    ) -> List[Tuple[str, float, float]]:
        """
        Find most similar candidates with trust-weighted scoring.
        
        Returns:
            List of (text, similarity_score, trust_score) tuples
        """
        if len(candidates) != len(candidate_trust):
            raise ValueError("candidates and candidate_trust must have same length")
        
        # Get embeddings with trust context
        query_embedding = self.embed_text(query, instruction=instruction)
        candidate_embeddings = self.embed_text(
            candidates,
            trust_context=candidate_trust,
            instruction=instruction
        )
        
        # Calculate base similarities
        from sklearn.metrics.pairwise import cosine_similarity
        
        if len(query_embedding.shape) == 1:
            query_embedding = query_embedding.reshape(1, -1)
        if len(candidate_embeddings.shape) == 1:
            candidate_embeddings = candidate_embeddings.reshape(1, -1)
        
        similarities = cosine_similarity(query_embedding, candidate_embeddings)[0]
        
        # Combine neural similarity with symbolic trust
        trust_scores = [ctx.get_effective_trust() for ctx in candidate_trust]
        combined_scores = self._combine_similarity_trust(similarities, trust_scores)
        
        # Get top k
        top_indices = np.argsort(combined_scores)[::-1][:top_k]
        
        results = [
            (
                candidates[i],
                float(similarities[i]),
                trust_scores[i],
                float(combined_scores[i])
            )
            for i in top_indices
            if trust_scores[i] >= self.min_trust_threshold
        ]
        
        return results
    
    def _combine_similarity_trust(
        self,
        similarities: np.ndarray,
        trust_scores: List[float]
    ) -> np.ndarray:
        """
        Combine neural similarity with symbolic trust.
        
        Formula: combined = (1 - trust_weight) * similarity + trust_weight * trust_score
        
        This creates a neuro-symbolic score that balances:
        - Neural similarity (semantic match)
        - Symbolic trust (knowledge confidence)
        """
        similarities_np = np.array(similarities)
        trust_np = np.array(trust_scores)
        
        combined = (
            (1 - self.trust_weight) * similarities_np +
            self.trust_weight * trust_np
        )
        
        return combined
    
    def cluster_with_trust(
        self,
        texts: List[str],
        trust_contexts: List[TrustContext],
        num_clusters: int = 5,
        instruction: Optional[str] = None,
        trust_aware: bool = True,
    ) -> List[List[int]]:
        """
        Cluster texts with trust-aware clustering.
        
        When trust_aware=True:
        - High-trust texts form clusters more easily
        - Low-trust texts are more isolated
        - Trust influences cluster assignment
        """
        # Filter by minimum trust
        valid_indices = [
            i for i, ctx in enumerate(trust_contexts)
            if ctx.get_effective_trust() >= self.min_trust_threshold
        ]
        
        if len(valid_indices) < num_clusters:
            logger.warning(f"Only {len(valid_indices)} texts meet trust threshold, reducing clusters")
            num_clusters = max(1, len(valid_indices))
        
        valid_texts = [texts[i] for i in valid_indices]
        valid_contexts = [trust_contexts[i] for i in valid_indices]
        
        # Get trust-enhanced embeddings
        embeddings = self.embed_text(
            valid_texts,
            trust_context=valid_contexts,
            instruction=instruction,
            convert_to_numpy=True,
        )
        
        # Cluster using K-means
        from sklearn.cluster import KMeans
        
        kmeans = KMeans(n_clusters=min(num_clusters, len(valid_texts)), random_state=42)
        cluster_labels = kmeans.fit_predict(embeddings)
        
        # Map back to original indices
        clusters = [[] for _ in range(num_clusters)]
        for idx, label in enumerate(cluster_labels):
            original_idx = valid_indices[idx]
            clusters[label].append(original_idx)
        
        return [c for c in clusters if c]  # Remove empty clusters
    
    def get_embedding_dimension(self) -> int:
        """Get embedding dimension from base model."""
        return self.base_model.get_embedding_dimension()
    
    def get_model_info(self) -> dict:
        """Get model information."""
        info = self.base_model.get_model_info()
        info.update({
            "trust_aware": True,
            "trust_weight": self.trust_weight,
            "min_trust_threshold": self.min_trust_threshold,
        })
        return info


def get_trust_aware_embedding_model(
    base_model: Optional[EmbeddingModel] = None,
    trust_weight: float = 0.3,
    min_trust_threshold: float = 0.3,
) -> TrustAwareEmbeddingModel:
    """
    Get or create trust-aware embedding model instance.
    
    Note: This creates a new wrapper each time (lightweight).
    The base model is a singleton.
    
    Args:
        base_model: Base EmbeddingModel (uses singleton if None)
        trust_weight: Weight of trust in similarity (0-1)
        min_trust_threshold: Minimum trust to include
        
    Returns:
        TrustAwareEmbeddingModel instance
    """
    return TrustAwareEmbeddingModel(
        base_model=base_model,
        trust_weight=trust_weight,
        min_trust_threshold=min_trust_threshold,
    )
