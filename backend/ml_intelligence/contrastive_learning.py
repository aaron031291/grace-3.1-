"""
Contrastive Learning - Better Representation Learning

Learns better embeddings by contrasting similar vs dissimilar examples.

Implementations:
- SimCLR: Contrastive learning with data augmentation
- Supervised Contrastive Learning
- Triplet Loss
- N-Pair Loss
- Hard Negative Mining

Classes:
- `ContrastiveBatch`
- `NTXentLoss`
- `TripletLoss`
- `SupervisedContrastiveLoss`
- `HardNegativeMiner`
- `ContrastiveLearner`

Key Methods:
- `forward()`
- `compute_distance()`
- `forward()`
- `forward()`
- `compute_pairwise_distances()`
- `mine_hard_negatives()`
- `forward()`
- `train_step()`
- `encode()`
- `compute_similarity()`
- `get_training_stats()`
- `save_model()`
- `load_model()`
- `get_contrastive_learner()`
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class ContrastiveBatch:
    """Batch for contrastive learning"""
    anchors: torch.Tensor  # [N, D]
    positives: torch.Tensor  # [N, D]
    negatives: Optional[torch.Tensor] = None  # [N, K, D] or [N*K, D]
    labels: Optional[torch.Tensor] = None  # [N]


class NTXentLoss(nn.Module):
    """
    Normalized Temperature-scaled Cross-Entropy Loss (NT-Xent)

    Used in SimCLR and other contrastive methods
    """

    def __init__(self, temperature: float = 0.5):
        super().__init__()
        self.temperature = temperature

    def forward(
        self,
        z_i: torch.Tensor,
        z_j: torch.Tensor
    ) -> torch.Tensor:
        """
        Compute NT-Xent loss

        Args:
            z_i: Embeddings from view 1 [N, D]
            z_j: Embeddings from view 2 [N, D]

        Returns:
            Loss scalar
        """
        batch_size = z_i.size(0)

        # Normalize embeddings
        z_i = F.normalize(z_i, dim=1)
        z_j = F.normalize(z_j, dim=1)

        # Concatenate
        representations = torch.cat([z_i, z_j], dim=0)  # [2N, D]

        # Similarity matrix
        similarity_matrix = torch.matmul(representations, representations.T)  # [2N, 2N]

        # Mask out self-similarity
        mask = torch.eye(2 * batch_size, dtype=torch.bool, device=z_i.device)
        similarity_matrix = similarity_matrix.masked_fill(mask, -9e15)

        # Positive pairs: (i, i+N) and (i+N, i)
        positives = torch.cat([
            torch.arange(batch_size, 2 * batch_size),
            torch.arange(0, batch_size)
        ]).to(z_i.device)

        # Apply temperature
        similarity_matrix = similarity_matrix / self.temperature

        # Compute loss
        loss = F.cross_entropy(
            similarity_matrix,
            positives,
            reduction='mean'
        )

        return loss


class TripletLoss(nn.Module):
    """
    Triplet Loss

    Minimizes distance to positive, maximizes distance to negative
    """

    def __init__(self, margin: float = 1.0, distance_metric: str = 'euclidean'):
        super().__init__()
        self.margin = margin
        self.distance_metric = distance_metric

    def compute_distance(
        self,
        x1: torch.Tensor,
        x2: torch.Tensor
    ) -> torch.Tensor:
        """Compute pairwise distance"""
        if self.distance_metric == 'euclidean':
            return torch.norm(x1 - x2, p=2, dim=1)
        elif self.distance_metric == 'cosine':
            return 1.0 - F.cosine_similarity(x1, x2)
        else:
            raise ValueError(f"Unknown distance metric: {self.distance_metric}")

    def forward(
        self,
        anchor: torch.Tensor,
        positive: torch.Tensor,
        negative: torch.Tensor
    ) -> torch.Tensor:
        """
        Compute triplet loss

        Args:
            anchor: Anchor embeddings [N, D]
            positive: Positive embeddings [N, D]
            negative: Negative embeddings [N, D]

        Returns:
            Loss scalar
        """
        # Distances
        pos_dist = self.compute_distance(anchor, positive)
        neg_dist = self.compute_distance(anchor, negative)

        # Triplet loss with margin
        loss = F.relu(pos_dist - neg_dist + self.margin)

        return loss.mean()


class SupervisedContrastiveLoss(nn.Module):
    """
    Supervised Contrastive Loss

    Uses label information to form positives and negatives
    """

    def __init__(self, temperature: float = 0.07):
        super().__init__()
        self.temperature = temperature

    def forward(
        self,
        features: torch.Tensor,
        labels: torch.Tensor
    ) -> torch.Tensor:
        """
        Compute supervised contrastive loss

        Args:
            features: Embeddings [N, D]
            labels: Labels [N]

        Returns:
            Loss scalar
        """
        batch_size = features.size(0)

        # Normalize features
        features = F.normalize(features, dim=1)

        # Similarity matrix
        similarity_matrix = torch.matmul(features, features.T)  # [N, N]

        # Mask for positives (same label, excluding self)
        labels = labels.view(-1, 1)
        mask_positives = (labels == labels.T).fill_diagonal_(False)

        # Mask for self
        mask_self = torch.eye(batch_size, dtype=torch.bool, device=features.device)

        # Apply temperature
        similarity_matrix = similarity_matrix / self.temperature

        # Numerical stability
        max_sim = similarity_matrix.max()
        similarity_matrix = similarity_matrix - max_sim.detach()

        # Exponentials
        exp_sim = torch.exp(similarity_matrix)

        # Sum over negatives (everything except self)
        sum_negatives = exp_sim.masked_fill(mask_self, 0).sum(dim=1, keepdim=True)

        # Log probabilities for positives
        log_prob = similarity_matrix - torch.log(sum_negatives + 1e-8)

        # Mean over positives
        num_positives = mask_positives.sum(dim=1)
        loss_per_anchor = -(log_prob * mask_positives).sum(dim=1) / (num_positives + 1e-8)

        # Mean over batch
        loss = loss_per_anchor.mean()

        return loss


class HardNegativeMiner:
    """
    Hard Negative Mining

    Selects the hardest negatives for more effective training
    """

    def __init__(
        self,
        distance_metric: str = 'euclidean',
        mining_strategy: str = 'hard'  # 'hard', 'semi_hard', 'all'
    ):
        self.distance_metric = distance_metric
        self.mining_strategy = mining_strategy

    def compute_pairwise_distances(
        self,
        embeddings: torch.Tensor
    ) -> torch.Tensor:
        """
        Compute pairwise distance matrix

        Args:
            embeddings: [N, D]

        Returns:
            Distance matrix [N, N]
        """
        if self.distance_metric == 'euclidean':
            # Squared Euclidean distance
            dot_product = torch.matmul(embeddings, embeddings.T)
            squared_norm = torch.diag(dot_product)

            distances = squared_norm.unsqueeze(0) - 2.0 * dot_product + squared_norm.unsqueeze(1)
            distances = F.relu(distances)  # Numerical stability

            return torch.sqrt(distances + 1e-8)

        elif self.distance_metric == 'cosine':
            # Cosine distance
            normalized = F.normalize(embeddings, dim=1)
            similarity = torch.matmul(normalized, normalized.T)
            return 1.0 - similarity

        else:
            raise ValueError(f"Unknown distance metric: {self.distance_metric}")

    def mine_hard_negatives(
        self,
        embeddings: torch.Tensor,
        labels: torch.Tensor,
        margin: float = 1.0
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Mine hard triplets

        Args:
            embeddings: [N, D]
            labels: [N]
            margin: Triplet margin

        Returns:
            (anchor_indices, positive_indices, negative_indices)
        """
        # Pairwise distances
        distance_matrix = self.compute_pairwise_distances(embeddings)

        # Masks
        labels = labels.view(-1, 1)
        mask_positives = (labels == labels.T).fill_diagonal_(False)
        mask_negatives = (labels != labels.T)

        # For each anchor, find hardest positive and hardest negative
        anchor_indices = []
        positive_indices = []
        negative_indices = []

        for i in range(embeddings.size(0)):
            # Positive distances for this anchor
            pos_dists = distance_matrix[i].masked_fill(~mask_positives[i], float('inf'))

            # Negative distances for this anchor
            neg_dists = distance_matrix[i].masked_fill(~mask_negatives[i], float('inf'))

            if self.mining_strategy == 'hard':
                # Hardest positive (largest distance among positives)
                if pos_dists.min() < float('inf'):
                    hard_pos_idx = torch.argmax(pos_dists)

                    # Hardest negative (smallest distance among negatives)
                    if neg_dists.min() < float('inf'):
                        hard_neg_idx = torch.argmin(neg_dists)

                        anchor_indices.append(i)
                        positive_indices.append(hard_pos_idx.item())
                        negative_indices.append(hard_neg_idx.item())

            elif self.mining_strategy == 'semi_hard':
                # Semi-hard: negative closer than positive but still violates margin
                if pos_dists.min() < float('inf'):
                    hard_pos_idx = torch.argmax(pos_dists)
                    hard_pos_dist = pos_dists[hard_pos_idx]

                    # Find negatives within margin
                    semi_hard_mask = (
                        (neg_dists < hard_pos_dist + margin) &
                        (neg_dists > hard_pos_dist)
                    )

                    if semi_hard_mask.any():
                        # Select hardest semi-hard negative
                        semi_hard_negs = neg_dists.masked_fill(~semi_hard_mask, float('inf'))
                        hard_neg_idx = torch.argmin(semi_hard_negs)

                        anchor_indices.append(i)
                        positive_indices.append(hard_pos_idx.item())
                        negative_indices.append(hard_neg_idx.item())

        if len(anchor_indices) == 0:
            # No valid triplets found
            return None, None, None

        return (
            torch.tensor(anchor_indices, device=embeddings.device),
            torch.tensor(positive_indices, device=embeddings.device),
            torch.tensor(negative_indices, device=embeddings.device)
        )


class ContrastiveLearner:
    """
    Main Contrastive Learning Interface

    Coordinates different contrastive learning approaches
    """

    def __init__(
        self,
        encoder: nn.Module,
        projection_dim: int = 128,
        loss_type: str = 'ntxent',  # 'ntxent', 'triplet', 'supervised'
        temperature: float = 0.5,
        margin: float = 1.0,
        device: str = None
    ):
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        self.encoder = encoder.to(self.device)

        # Projection head (for SimCLR-style learning)
        self.projection_head = nn.Sequential(
            nn.Linear(encoder.output_dim if hasattr(encoder, 'output_dim') else 512, 512),
            nn.ReLU(),
            nn.Linear(512, projection_dim)
        ).to(self.device)

        # Loss function
        self.loss_type = loss_type
        if loss_type == 'ntxent':
            self.loss_fn = NTXentLoss(temperature)
        elif loss_type == 'triplet':
            self.loss_fn = TripletLoss(margin)
        elif loss_type == 'supervised':
            self.loss_fn = SupervisedContrastiveLoss(temperature)
        else:
            raise ValueError(f"Unknown loss type: {loss_type}")

        # Hard negative miner
        self.negative_miner = HardNegativeMiner()

        # Optimizer
        self.optimizer = torch.optim.Adam(
            list(self.encoder.parameters()) + list(self.projection_head.parameters()),
            lr=1e-3
        )

        # Training statistics
        self.training_stats = defaultdict(list)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass through encoder and projection"""
        encoding = self.encoder(x)
        projection = self.projection_head(encoding)
        return projection

    def train_step(
        self,
        batch: ContrastiveBatch
    ) -> Dict[str, float]:
        """
        Single training step

        Args:
            batch: ContrastiveBatch

        Returns:
            Dict with loss and metrics
        """
        self.encoder.train()
        self.projection_head.train()

        # Move to device
        anchors = batch.anchors.to(self.device)
        positives = batch.positives.to(self.device)

        # Forward pass
        z_anchors = self.forward(anchors)
        z_positives = self.forward(positives)

        # Compute loss
        if self.loss_type == 'ntxent':
            loss = self.loss_fn(z_anchors, z_positives)

        elif self.loss_type == 'triplet':
            negatives = batch.negatives.to(self.device)
            z_negatives = self.forward(negatives)
            loss = self.loss_fn(z_anchors, z_positives, z_negatives)

        elif self.loss_type == 'supervised':
            labels = batch.labels.to(self.device)
            # Combine anchors and positives
            all_embeddings = torch.cat([z_anchors, z_positives], dim=0)
            all_labels = torch.cat([labels, labels], dim=0)
            loss = self.loss_fn(all_embeddings, all_labels)

        else:
            raise ValueError(f"Unknown loss type: {self.loss_type}")

        # Backward pass
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        # Statistics
        metrics = {
            'loss': loss.item()
        }

        self.training_stats['loss'].append(loss.item())

        return metrics

    def encode(
        self,
        x: torch.Tensor,
        use_projection: bool = False
    ) -> torch.Tensor:
        """
        Encode inputs to embeddings

        Args:
            x: Input tensor
            use_projection: Whether to use projection head

        Returns:
            Embeddings
        """
        self.encoder.eval()

        with torch.no_grad():
            x = x.to(self.device)
            encoding = self.encoder(x)

            if use_projection:
                encoding = self.projection_head(encoding)

        return encoding.cpu()

    def compute_similarity(
        self,
        x1: torch.Tensor,
        x2: torch.Tensor,
        metric: str = 'cosine'
    ) -> torch.Tensor:
        """
        Compute similarity between embeddings

        Args:
            x1: First input
            x2: Second input
            metric: 'cosine' or 'euclidean'

        Returns:
            Similarity scores
        """
        # Encode
        emb1 = self.encode(x1)
        emb2 = self.encode(x2)

        if metric == 'cosine':
            emb1 = F.normalize(emb1, dim=1)
            emb2 = F.normalize(emb2, dim=1)
            similarity = (emb1 * emb2).sum(dim=1)

        elif metric == 'euclidean':
            similarity = -torch.norm(emb1 - emb2, p=2, dim=1)

        else:
            raise ValueError(f"Unknown metric: {metric}")

        return similarity

    def get_training_stats(self) -> Dict:
        """Get training statistics"""
        if not self.training_stats['loss']:
            return {}

        recent_losses = self.training_stats['loss'][-100:]

        return {
            'total_steps': len(self.training_stats['loss']),
            'recent_avg_loss': np.mean(recent_losses),
            'recent_std_loss': np.std(recent_losses),
            'min_loss': min(self.training_stats['loss']),
            'max_loss': max(self.training_stats['loss'])
        }

    def save_model(self, path: str):
        """Save model"""
        torch.save({
            'encoder_state': self.encoder.state_dict(),
            'projection_state': self.projection_head.state_dict(),
            'optimizer_state': self.optimizer.state_dict(),
            'training_stats': dict(self.training_stats)
        }, path)

    def load_model(self, path: str):
        """Load model"""
        checkpoint = torch.load(path, map_location=self.device)

        self.encoder.load_state_dict(checkpoint['encoder_state'])
        self.projection_head.load_state_dict(checkpoint['projection_state'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state'])
        self.training_stats = defaultdict(list, checkpoint.get('training_stats', {}))


# Singleton instance
_contrastive_learner_instance = None


def get_contrastive_learner(
    encoder: nn.Module,
    loss_type: str = 'ntxent'
) -> ContrastiveLearner:
    """Get contrastive learner instance"""
    global _contrastive_learner_instance

    if _contrastive_learner_instance is None and encoder is not None:
        _contrastive_learner_instance = ContrastiveLearner(
            encoder=encoder,
            loss_type=loss_type
        )

    return _contrastive_learner_instance
