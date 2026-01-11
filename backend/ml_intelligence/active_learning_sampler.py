"""
Active Learning Sampler - Optimal Training Example Selection

Intelligently selects the most valuable examples for training to
maximize learning efficiency with minimal data.

Strategies:
- Uncertainty Sampling
- Query-by-Committee
- Expected Model Change
- Diversity Sampling
- Core-Set Selection
- Adversarial Sampling
"""

import torch
import numpy as np
from typing import List, Tuple, Dict, Callable, Optional
from dataclasses import dataclass
from enum import Enum
import heapq
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import euclidean_distances


class SamplingStrategy(Enum):
    """Active learning sampling strategies"""
    UNCERTAINTY = "uncertainty"  # Select most uncertain examples
    ENTROPY = "entropy"  # Maximum entropy
    MARGIN = "margin"  # Smallest margin between top predictions
    QUERY_BY_COMMITTEE = "query_by_committee"  # Committee disagreement
    EXPECTED_MODEL_CHANGE = "expected_model_change"  # Largest gradient
    DIVERSITY = "diversity"  # Maximize diversity
    CORESET = "coreset"  # Representative core-set
    ADVERSARIAL = "adversarial"  # Near decision boundary


@dataclass
class SampleScore:
    """Score for a candidate sample"""
    sample_idx: int
    score: float
    metadata: Dict = None

    def __lt__(self, other):
        return self.score < other.score


class UncertaintySampler:
    """
    Uncertainty-based sampling

    Selects examples where the model is most uncertain
    """

    def __init__(self, model, device: str = None):
        self.model = model
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')

    def compute_uncertainty(
        self,
        x: torch.Tensor,
        num_mc_samples: int = 20
    ) -> np.ndarray:
        """
        Compute uncertainty scores using MC Dropout

        Args:
            x: Input samples [N, features]
            num_mc_samples: Number of MC samples

        Returns:
            Uncertainty scores [N]
        """
        self.model.train()  # Enable dropout

        predictions = []

        with torch.no_grad():
            for _ in range(num_mc_samples):
                pred = self.model(x.to(self.device))
                predictions.append(pred.cpu())

        predictions = torch.stack(predictions)  # [num_samples, N, output_dim]

        # Standard deviation as uncertainty
        uncertainty = predictions.std(dim=0).mean(dim=-1).numpy()

        self.model.eval()

        return uncertainty

    def select_samples(
        self,
        unlabeled_x: torch.Tensor,
        n_samples: int,
        num_mc_samples: int = 20
    ) -> List[int]:
        """
        Select most uncertain samples

        Args:
            unlabeled_x: Unlabeled samples [N, features]
            n_samples: Number of samples to select
            num_mc_samples: MC samples for uncertainty

        Returns:
            List of selected indices
        """
        uncertainties = self.compute_uncertainty(unlabeled_x, num_mc_samples)

        # Select top-k uncertain
        top_indices = np.argsort(uncertainties)[::-1][:n_samples]

        return top_indices.tolist()


class EntropySampler:
    """
    Entropy-based sampling for classification

    Selects examples with maximum prediction entropy
    """

    def __init__(self, model, device: str = None):
        self.model = model
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')

    def compute_entropy(self, x: torch.Tensor) -> np.ndarray:
        """
        Compute prediction entropy

        Args:
            x: Input samples [N, features]

        Returns:
            Entropy scores [N]
        """
        self.model.eval()

        with torch.no_grad():
            logits = self.model(x.to(self.device))
            probs = torch.softmax(logits, dim=-1)

            # Entropy: -sum(p * log(p))
            entropy = -(probs * torch.log(probs + 1e-10)).sum(dim=-1)

        return entropy.cpu().numpy()

    def select_samples(
        self,
        unlabeled_x: torch.Tensor,
        n_samples: int
    ) -> List[int]:
        """Select samples with highest entropy"""
        entropies = self.compute_entropy(unlabeled_x)

        top_indices = np.argsort(entropies)[::-1][:n_samples]

        return top_indices.tolist()


class MarginSampler:
    """
    Margin-based sampling

    Selects examples where the margin between top-2 predictions is smallest
    """

    def __init__(self, model, device: str = None):
        self.model = model
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')

    def compute_margin(self, x: torch.Tensor) -> np.ndarray:
        """
        Compute margin scores (difference between top-2 predictions)

        Args:
            x: Input samples [N, features]

        Returns:
            Margin scores [N] (lower = more uncertain)
        """
        self.model.eval()

        with torch.no_grad():
            logits = self.model(x.to(self.device))
            probs = torch.softmax(logits, dim=-1)

            # Get top-2 probabilities
            top2_probs, _ = torch.topk(probs, k=2, dim=-1)

            # Margin = difference between top 2
            margin = top2_probs[:, 0] - top2_probs[:, 1]

        return margin.cpu().numpy()

    def select_samples(
        self,
        unlabeled_x: torch.Tensor,
        n_samples: int
    ) -> List[int]:
        """Select samples with smallest margin"""
        margins = self.compute_margin(unlabeled_x)

        # Smallest margins first
        top_indices = np.argsort(margins)[:n_samples]

        return top_indices.tolist()


class QueryByCommittee:
    """
    Query-by-Committee sampling

    Uses disagreement among multiple models
    """

    def __init__(self, models: List, device: str = None):
        self.models = models
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')

    def compute_disagreement(
        self,
        x: torch.Tensor,
        method: str = 'vote_entropy'
    ) -> np.ndarray:
        """
        Compute committee disagreement

        Args:
            x: Input samples [N, features]
            method: 'vote_entropy' or 'variance'

        Returns:
            Disagreement scores [N]
        """
        predictions = []

        for model in self.models:
            model.eval()
            with torch.no_grad():
                pred = model(x.to(self.device))
                predictions.append(pred.cpu())

        predictions = torch.stack(predictions)  # [num_models, N, output_dim]

        if method == 'vote_entropy':
            # For classification: entropy of vote distribution
            votes = torch.argmax(predictions, dim=-1)  # [num_models, N]

            disagreement = []
            for i in range(x.size(0)):
                vote_counts = torch.bincount(votes[:, i])
                vote_probs = vote_counts.float() / len(self.models)

                # Entropy
                entropy = -(vote_probs * torch.log(vote_probs + 1e-10)).sum()
                disagreement.append(entropy.item())

            return np.array(disagreement)

        elif method == 'variance':
            # Variance across committee
            disagreement = predictions.var(dim=0).mean(dim=-1).numpy()
            return disagreement

        else:
            raise ValueError(f"Unknown method: {method}")

    def select_samples(
        self,
        unlabeled_x: torch.Tensor,
        n_samples: int,
        method: str = 'vote_entropy'
    ) -> List[int]:
        """Select samples with highest disagreement"""
        disagreement = self.compute_disagreement(unlabeled_x, method)

        top_indices = np.argsort(disagreement)[::-1][:n_samples]

        return top_indices.tolist()


class ExpectedModelChangeSampler:
    """
    Expected Model Change (EMC) sampling

    Selects examples that would most change the model if labeled
    Approximated by gradient magnitude
    """

    def __init__(self, model, device: str = None):
        self.model = model
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')

    def compute_gradient_magnitude(
        self,
        x: torch.Tensor
    ) -> np.ndarray:
        """
        Compute gradient magnitude for each sample

        Args:
            x: Input samples [N, features]

        Returns:
            Gradient magnitudes [N]
        """
        self.model.train()

        x = x.to(self.device)
        x.requires_grad = True

        # Forward pass
        output = self.model(x)

        # Backward on output (using sum as pseudo-loss)
        pseudo_loss = output.sum()
        pseudo_loss.backward()

        # Gradient magnitude
        grad_magnitude = x.grad.norm(dim=-1).cpu().numpy()

        x.requires_grad = False
        self.model.eval()

        return grad_magnitude

    def select_samples(
        self,
        unlabeled_x: torch.Tensor,
        n_samples: int
    ) -> List[int]:
        """Select samples with largest gradient magnitude"""
        grad_magnitudes = self.compute_gradient_magnitude(unlabeled_x)

        top_indices = np.argsort(grad_magnitudes)[::-1][:n_samples]

        return top_indices.tolist()


class DiversitySampler:
    """
    Diversity-based sampling

    Selects diverse samples using K-Means clustering
    """

    def __init__(self, embedding_model=None):
        self.embedding_model = embedding_model

    def select_samples(
        self,
        unlabeled_x: torch.Tensor,
        n_samples: int,
        embeddings: Optional[np.ndarray] = None
    ) -> List[int]:
        """
        Select diverse samples using K-Means

        Args:
            unlabeled_x: Unlabeled samples [N, features]
            n_samples: Number of samples to select
            embeddings: Pre-computed embeddings (optional)

        Returns:
            List of selected indices
        """
        if embeddings is None:
            if self.embedding_model:
                self.embedding_model.eval()
                with torch.no_grad():
                    embeddings = self.embedding_model(unlabeled_x).cpu().numpy()
            else:
                embeddings = unlabeled_x.cpu().numpy()

        # K-Means clustering
        kmeans = KMeans(n_clusters=n_samples, random_state=42)
        kmeans.fit(embeddings)

        # Select nearest point to each cluster center
        distances = euclidean_distances(embeddings, kmeans.cluster_centers_)
        selected_indices = []

        for cluster_idx in range(n_samples):
            # Find nearest point to this cluster center
            cluster_distances = distances[:, cluster_idx]
            nearest_idx = np.argmin(cluster_distances)

            selected_indices.append(nearest_idx)

        return selected_indices


class CoreSetSampler:
    """
    Core-Set selection

    Selects a representative subset that covers the data distribution
    Using greedy k-Center algorithm
    """

    def __init__(self):
        pass

    def select_samples(
        self,
        unlabeled_x: torch.Tensor,
        labeled_x: Optional[torch.Tensor],
        n_samples: int,
        embeddings_unlabeled: Optional[np.ndarray] = None,
        embeddings_labeled: Optional[np.ndarray] = None
    ) -> List[int]:
        """
        Greedy k-Center core-set selection

        Args:
            unlabeled_x: Unlabeled samples
            labeled_x: Already labeled samples (optional)
            n_samples: Number of samples to select
            embeddings_unlabeled: Embeddings for unlabeled
            embeddings_labeled: Embeddings for labeled

        Returns:
            List of selected indices
        """
        if embeddings_unlabeled is None:
            embeddings_unlabeled = unlabeled_x.cpu().numpy()

        # Initialize with labeled set
        if labeled_x is not None and embeddings_labeled is not None:
            selected_embeddings = embeddings_labeled
        else:
            # Start with random point
            selected_embeddings = embeddings_unlabeled[0:1]

        selected_indices = []

        for _ in range(n_samples):
            # Compute distances from unlabeled to selected
            distances = euclidean_distances(
                embeddings_unlabeled,
                selected_embeddings
            )

            # Minimum distance to any selected point
            min_distances = distances.min(axis=1)

            # Select point with maximum minimum distance (furthest from selected)
            next_idx = np.argmax(min_distances)

            selected_indices.append(next_idx)

            # Add to selected set
            selected_embeddings = np.vstack([
                selected_embeddings,
                embeddings_unlabeled[next_idx:next_idx+1]
            ])

        return selected_indices


class ActiveLearningSampler:
    """
    Main Active Learning Sampler

    Orchestrates different sampling strategies
    """

    def __init__(
        self,
        model,
        strategy: SamplingStrategy = SamplingStrategy.UNCERTAINTY,
        committee_models: List = None,
        device: str = None
    ):
        self.model = model
        self.strategy = strategy
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')

        # Initialize samplers
        self.uncertainty_sampler = UncertaintySampler(model, device)
        self.entropy_sampler = EntropySampler(model, device)
        self.margin_sampler = MarginSampler(model, device)
        self.emc_sampler = ExpectedModelChangeSampler(model, device)
        self.diversity_sampler = DiversitySampler()
        self.coreset_sampler = CoreSetSampler()

        if committee_models:
            self.qbc_sampler = QueryByCommittee(committee_models, device)
        else:
            self.qbc_sampler = None

    def select_samples(
        self,
        unlabeled_pool: torch.Tensor,
        n_samples: int,
        labeled_pool: Optional[torch.Tensor] = None,
        embeddings_unlabeled: Optional[np.ndarray] = None,
        embeddings_labeled: Optional[np.ndarray] = None
    ) -> List[int]:
        """
        Select samples using configured strategy

        Args:
            unlabeled_pool: Pool of unlabeled samples
            n_samples: Number to select
            labeled_pool: Already labeled samples (for core-set)
            embeddings_unlabeled: Pre-computed embeddings
            embeddings_labeled: Pre-computed embeddings for labeled

        Returns:
            List of selected indices
        """
        if self.strategy == SamplingStrategy.UNCERTAINTY:
            return self.uncertainty_sampler.select_samples(unlabeled_pool, n_samples)

        elif self.strategy == SamplingStrategy.ENTROPY:
            return self.entropy_sampler.select_samples(unlabeled_pool, n_samples)

        elif self.strategy == SamplingStrategy.MARGIN:
            return self.margin_sampler.select_samples(unlabeled_pool, n_samples)

        elif self.strategy == SamplingStrategy.QUERY_BY_COMMITTEE:
            if self.qbc_sampler is None:
                raise ValueError("QBC requires committee_models")
            return self.qbc_sampler.select_samples(unlabeled_pool, n_samples)

        elif self.strategy == SamplingStrategy.EXPECTED_MODEL_CHANGE:
            return self.emc_sampler.select_samples(unlabeled_pool, n_samples)

        elif self.strategy == SamplingStrategy.DIVERSITY:
            return self.diversity_sampler.select_samples(
                unlabeled_pool, n_samples, embeddings_unlabeled
            )

        elif self.strategy == SamplingStrategy.CORESET:
            return self.coreset_sampler.select_samples(
                unlabeled_pool, labeled_pool, n_samples,
                embeddings_unlabeled, embeddings_labeled
            )

        else:
            raise ValueError(f"Unknown strategy: {self.strategy}")

    def hybrid_selection(
        self,
        unlabeled_pool: torch.Tensor,
        n_samples: int,
        weights: Dict[SamplingStrategy, float] = None
    ) -> List[int]:
        """
        Hybrid selection combining multiple strategies

        Args:
            unlabeled_pool: Pool of unlabeled samples
            n_samples: Number to select
            weights: Strategy weights (normalized automatically)

        Returns:
            List of selected indices
        """
        if weights is None:
            weights = {
                SamplingStrategy.UNCERTAINTY: 0.5,
                SamplingStrategy.DIVERSITY: 0.5
            }

        # Normalize weights
        total_weight = sum(weights.values())
        weights = {k: v / total_weight for k, v in weights.items()}

        # Compute scores for each strategy
        all_scores = np.zeros(unlabeled_pool.size(0))

        for strategy, weight in weights.items():
            if strategy == SamplingStrategy.UNCERTAINTY:
                scores = self.uncertainty_sampler.compute_uncertainty(unlabeled_pool)
            elif strategy == SamplingStrategy.ENTROPY:
                scores = self.entropy_sampler.compute_entropy(unlabeled_pool)
            elif strategy == SamplingStrategy.MARGIN:
                scores = -self.margin_sampler.compute_margin(unlabeled_pool)  # Negate for consistency
            else:
                # Skip strategies that don't have simple scoring
                continue

            # Normalize scores to [0, 1]
            scores = (scores - scores.min()) / (scores.max() - scores.min() + 1e-8)

            all_scores += weight * scores

        # Select top-k
        top_indices = np.argsort(all_scores)[::-1][:n_samples]

        return top_indices.tolist()


# Singleton instance
_active_sampler_instance = None


def get_active_sampler(
    model,
    strategy: SamplingStrategy = SamplingStrategy.UNCERTAINTY,
    committee_models: List = None
) -> ActiveLearningSampler:
    """Get active learning sampler instance"""
    global _active_sampler_instance

    if _active_sampler_instance is None:
        _active_sampler_instance = ActiveLearningSampler(
            model,
            strategy,
            committee_models
        )

    return _active_sampler_instance
