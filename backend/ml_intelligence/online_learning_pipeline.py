"""
Online Learning Pipeline - Continuous Model Updates

Enables real-time model updates as new data arrives, without
requiring full retraining. Supports incremental learning for
embeddings, classifiers, and other models.

Features:
- Streaming mini-batch updates
- Catastrophic forgetting prevention (EWC)
- Dynamic model expansion
- Continuous evaluation
- Automatic checkpointing
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.optim import SGD, AdamW
import numpy as np
from typing import Dict, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import json
import os


@dataclass
class StreamingBatch:
    """A batch of data for online learning"""
    features: torch.Tensor
    labels: torch.Tensor
    metadata: Dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ModelCheckpoint:
    """Model checkpoint for recovery"""
    model_state: Dict
    optimizer_state: Dict
    metrics: Dict
    timestamp: datetime
    batch_count: int


class ElasticWeightConsolidation:
    """
    Elastic Weight Consolidation (EWC) for preventing catastrophic forgetting

    Penalizes changes to weights that are important for previous tasks
    """

    def __init__(self, model: nn.Module, fisher_samples: int = 200):
        self.model = model
        self.fisher_samples = fisher_samples
        self.fisher_information = {}
        self.optimal_params = {}

    def compute_fisher_information(self, dataloader):
        """
        Compute Fisher Information Matrix for current task

        Args:
            dataloader: DataLoader with current task data
        """
        self.model.eval()

        # Initialize Fisher information dict
        self.fisher_information = {
            name: torch.zeros_like(param)
            for name, param in self.model.named_parameters()
            if param.requires_grad
        }

        # Sample gradients
        num_samples = 0
        for batch_idx, (features, labels) in enumerate(dataloader):
            if num_samples >= self.fisher_samples:
                break

            # Forward pass
            output = self.model(features)
            loss = F.binary_cross_entropy(output, labels.unsqueeze(1).float())

            # Backward pass
            self.model.zero_grad()
            loss.backward()

            # Accumulate squared gradients (Fisher information)
            for name, param in self.model.named_parameters():
                if param.requires_grad and param.grad is not None:
                    self.fisher_information[name] += param.grad.data ** 2

            num_samples += features.size(0)

        # Average Fisher information
        for name in self.fisher_information:
            self.fisher_information[name] /= num_samples

        # Store optimal parameters for this task
        self.optimal_params = {
            name: param.clone()
            for name, param in self.model.named_parameters()
            if param.requires_grad
        }

    def penalty(self, ewc_lambda: float = 1000.0) -> torch.Tensor:
        """
        Compute EWC penalty term

        Args:
            ewc_lambda: Importance of previous tasks

        Returns:
            EWC penalty loss
        """
        loss = 0.0

        for name, param in self.model.named_parameters():
            if param.requires_grad and name in self.fisher_information:
                fisher = self.fisher_information[name]
                optimal = self.optimal_params[name]
                loss += (fisher * (param - optimal) ** 2).sum()

        return ewc_lambda * loss


class OnlineLearningPipeline:
    """
    Online Learning Pipeline

    Continuously updates models as new data streams in
    """

    def __init__(
        self,
        model: nn.Module,
        optimizer_fn: Callable = None,
        learning_rate: float = 1e-4,
        use_ewc: bool = True,
        ewc_lambda: float = 1000.0,
        checkpoint_dir: str = "checkpoints/online_learning",
        checkpoint_interval: int = 100,
        device: str = None
    ):
        self.model = model
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        self.model.to(self.device)

        # Optimizer
        if optimizer_fn is None:
            self.optimizer = AdamW(model.parameters(), lr=learning_rate, weight_decay=1e-5)
        else:
            self.optimizer = optimizer_fn(model.parameters())

        # EWC for catastrophic forgetting prevention
        self.use_ewc = use_ewc
        self.ewc_lambda = ewc_lambda
        self.ewc = ElasticWeightConsolidation(model) if use_ewc else None

        # Checkpointing
        self.checkpoint_dir = checkpoint_dir
        self.checkpoint_interval = checkpoint_interval
        os.makedirs(checkpoint_dir, exist_ok=True)

        # Statistics
        self.batch_count = 0
        self.total_samples = 0
        self.metrics_history = defaultdict(list)

        # Streaming statistics
        self.running_mean_loss = 0.0
        self.running_mean_accuracy = 0.0
        self.alpha = 0.01  # Exponential moving average factor

    def update(
        self,
        batch: StreamingBatch,
        loss_fn: Callable = F.binary_cross_entropy
    ) -> Dict[str, float]:
        """
        Update model with a new batch

        Args:
            batch: StreamingBatch with features and labels
            loss_fn: Loss function to use

        Returns:
            Dict with update metrics
        """
        self.model.train()

        # Move to device
        features = batch.features.to(self.device)
        labels = batch.labels.to(self.device)

        # Forward pass
        output = self.model(features)

        # Compute primary loss
        primary_loss = loss_fn(output, labels.unsqueeze(1).float())

        # Add EWC penalty if enabled
        total_loss = primary_loss
        ewc_penalty = 0.0
        if self.use_ewc and self.ewc is not None and self.ewc.fisher_information:
            ewc_penalty = self.ewc.penalty(self.ewc_lambda)
            total_loss = primary_loss + ewc_penalty

        # Backward pass
        self.optimizer.zero_grad()
        total_loss.backward()

        # Gradient clipping
        torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)

        self.optimizer.step()

        # Calculate metrics
        with torch.no_grad():
            predictions = (output > 0.5).float()
            accuracy = (predictions == labels.unsqueeze(1).float()).float().mean().item()

        # Update statistics
        self.batch_count += 1
        self.total_samples += features.size(0)

        # Exponential moving average
        self.running_mean_loss = (
            self.alpha * primary_loss.item() + (1 - self.alpha) * self.running_mean_loss
        )
        self.running_mean_accuracy = (
            self.alpha * accuracy + (1 - self.alpha) * self.running_mean_accuracy
        )

        # Record metrics
        metrics = {
            'batch_count': self.batch_count,
            'primary_loss': primary_loss.item(),
            'ewc_penalty': ewc_penalty if isinstance(ewc_penalty, float) else ewc_penalty.item(),
            'total_loss': total_loss.item(),
            'accuracy': accuracy,
            'running_mean_loss': self.running_mean_loss,
            'running_mean_accuracy': self.running_mean_accuracy,
            'timestamp': batch.timestamp.isoformat()
        }

        self.metrics_history['loss'].append(primary_loss.item())
        self.metrics_history['accuracy'].append(accuracy)

        # Checkpoint if needed
        if self.batch_count % self.checkpoint_interval == 0:
            self.checkpoint(metrics)

        return metrics

    def update_ewc(self, dataloader):
        """
        Update EWC Fisher information for new task

        Call this when transitioning to a new learning phase
        """
        if self.use_ewc and self.ewc is not None:
            self.ewc.compute_fisher_information(dataloader)

    def checkpoint(self, metrics: Dict):
        """Save model checkpoint"""
        checkpoint = ModelCheckpoint(
            model_state=self.model.state_dict(),
            optimizer_state=self.optimizer.state_dict(),
            metrics=metrics,
            timestamp=datetime.now(),
            batch_count=self.batch_count
        )

        checkpoint_path = os.path.join(
            self.checkpoint_dir,
            f"checkpoint_batch_{self.batch_count}.pt"
        )

        torch.save({
            'model_state': checkpoint.model_state,
            'optimizer_state': checkpoint.optimizer_state,
            'metrics': checkpoint.metrics,
            'timestamp': checkpoint.timestamp.isoformat(),
            'batch_count': checkpoint.batch_count
        }, checkpoint_path)

        # Also save as latest
        latest_path = os.path.join(self.checkpoint_dir, "latest.pt")
        torch.save({
            'model_state': checkpoint.model_state,
            'optimizer_state': checkpoint.optimizer_state,
            'metrics': checkpoint.metrics,
            'timestamp': checkpoint.timestamp.isoformat(),
            'batch_count': checkpoint.batch_count
        }, latest_path)

    def load_checkpoint(self, checkpoint_path: str = None):
        """
        Load model from checkpoint

        Args:
            checkpoint_path: Path to checkpoint, or None for latest
        """
        if checkpoint_path is None:
            checkpoint_path = os.path.join(self.checkpoint_dir, "latest.pt")

        if not os.path.exists(checkpoint_path):
            return False

        checkpoint = torch.load(checkpoint_path, map_location=self.device)

        self.model.load_state_dict(checkpoint['model_state'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state'])
        self.batch_count = checkpoint['batch_count']

        return True

    def get_metrics_summary(self) -> Dict:
        """Get summary of metrics"""
        if not self.metrics_history['loss']:
            return {}

        recent_window = 100
        recent_losses = self.metrics_history['loss'][-recent_window:]
        recent_accuracies = self.metrics_history['accuracy'][-recent_window:]

        return {
            'batch_count': self.batch_count,
            'total_samples': self.total_samples,
            'running_mean_loss': self.running_mean_loss,
            'running_mean_accuracy': self.running_mean_accuracy,
            'recent_avg_loss': np.mean(recent_losses),
            'recent_avg_accuracy': np.mean(recent_accuracies),
            'recent_std_loss': np.std(recent_losses),
            'recent_std_accuracy': np.std(recent_accuracies),
            'total_batches_seen': len(self.metrics_history['loss'])
        }


class IncrementalEmbeddingLearner:
    """
    Incremental learning for embedding models

    Allows embedding models to learn new concepts without forgetting old ones
    """

    def __init__(
        self,
        base_model,
        embedding_dim: int = 384,
        learning_rate: float = 1e-5,
        device: str = None
    ):
        self.base_model = base_model
        self.embedding_dim = embedding_dim
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')

        # Create learnable adapter layer
        self.adapter = nn.Sequential(
            nn.Linear(embedding_dim, embedding_dim),
            nn.LayerNorm(embedding_dim),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(embedding_dim, embedding_dim)
        ).to(self.device)

        # Optimizer for adapter only (freeze base model)
        self.optimizer = AdamW(self.adapter.parameters(), lr=learning_rate)

        # Seen concepts
        self.concept_embeddings = {}

    def adapt_embedding(self, text: str, base_embedding: np.ndarray) -> np.ndarray:
        """
        Adapt embedding using learned adapter

        Args:
            text: Original text
            base_embedding: Base embedding from frozen model

        Returns:
            Adapted embedding
        """
        self.adapter.eval()

        with torch.no_grad():
            # Convert to tensor
            base_tensor = torch.tensor(base_embedding, dtype=torch.float32, device=self.device)

            # Apply adapter
            adapted = self.adapter(base_tensor)

            # Residual connection
            output = base_tensor + adapted

            # Normalize
            output = F.normalize(output, p=2, dim=-1)

            return output.cpu().numpy()

    def learn_from_positive_pair(
        self,
        text1: str,
        text2: str,
        base_embedding1: np.ndarray,
        base_embedding2: np.ndarray,
        should_be_similar: bool = True
    ):
        """
        Learn from a pair of texts

        Args:
            text1: First text
            text2: Second text
            base_embedding1: Base embedding for text1
            base_embedding2: Base embedding for text2
            should_be_similar: Whether texts should be similar
        """
        self.adapter.train()

        # Convert to tensors
        emb1 = torch.tensor(base_embedding1, dtype=torch.float32, device=self.device)
        emb2 = torch.tensor(base_embedding2, dtype=torch.float32, device=self.device)

        # Apply adapter
        adapted1 = self.adapter(emb1)
        adapted2 = self.adapter(emb2)

        # Residual connections
        output1 = emb1 + adapted1
        output2 = emb2 + adapted2

        # Normalize
        output1 = F.normalize(output1, p=2, dim=-1)
        output2 = F.normalize(output2, p=2, dim=-1)

        # Contrastive loss
        similarity = F.cosine_similarity(output1.unsqueeze(0), output2.unsqueeze(0))

        if should_be_similar:
            # Maximize similarity
            loss = 1.0 - similarity
        else:
            # Minimize similarity
            loss = torch.clamp(similarity - 0.2, min=0.0)  # Margin of 0.2

        # Backward pass
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        return loss.item()

    def save_adapter(self, path: str):
        """Save adapter weights"""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        torch.save({
            'adapter_state': self.adapter.state_dict(),
            'optimizer_state': self.optimizer.state_dict(),
            'concept_embeddings': self.concept_embeddings
        }, path)

    def load_adapter(self, path: str):
        """Load adapter weights"""
        if not os.path.exists(path):
            return False

        checkpoint = torch.load(path, map_location=self.device)
        self.adapter.load_state_dict(checkpoint['adapter_state'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state'])
        self.concept_embeddings = checkpoint.get('concept_embeddings', {})

        return True


# Singleton instances
_online_pipeline_instance = None
_incremental_embedder_instance = None


def get_online_learning_pipeline(model: nn.Module) -> OnlineLearningPipeline:
    """Get online learning pipeline instance"""
    global _online_pipeline_instance

    if _online_pipeline_instance is None:
        checkpoint_dir = os.path.join(os.path.dirname(__file__), '..', 'checkpoints', 'online_learning')
        _online_pipeline_instance = OnlineLearningPipeline(
            model=model,
            checkpoint_dir=checkpoint_dir
        )

    return _online_pipeline_instance


def get_incremental_embedder(base_model) -> IncrementalEmbeddingLearner:
    """Get incremental embedding learner instance"""
    global _incremental_embedder_instance

    if _incremental_embedder_instance is None:
        _incremental_embedder_instance = IncrementalEmbeddingLearner(base_model=base_model)

    return _incremental_embedder_instance
