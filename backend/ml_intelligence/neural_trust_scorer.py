"""
Neural Trust Scorer - Deep Learning-based Trust Scoring System

Replaces rule-based trust scoring with a learned neural network that
adapts based on observed outcomes and feedback.

Features:
- Multi-layer feedforward network with attention
- Online learning with experience replay
- Confidence intervals via Monte Carlo dropout
- Feature engineering from learning examples
- Adversarial robustness testing

Classes:
- `TrustFeatures`
- `TrainingExample`
- `TrustScorerNetwork`
- `ExperienceReplay`
- `NeuralTrustScorer`

Key Methods:
- `forward()`
- `predict_with_uncertainty()`
- `add()`
- `sample()`
- `extract_features()`
- `features_to_tensor()`
- `predict_trust()`
- `update_from_outcome()`
- `train_step()`
- `adversarial_test()`
- `save_model()`
- `load_model()`
- `get_stats()`
- `get_neural_trust_scorer()`
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.optim import AdamW
from torch.utils.data import Dataset, DataLoader
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from collections import deque
import json
import os
from datetime import datetime


@dataclass
class TrustFeatures:
    """Extracted features for trust scoring"""
    source_reliability: float
    outcome_quality: float
    consistency_score: float
    validation_count: int
    invalidation_count: int
    age_days: float
    content_length: int
    has_code: bool
    has_structure: bool
    has_references: bool
    usage_frequency: float
    success_rate: float
    embedding: Optional[np.ndarray] = None


@dataclass
class TrainingExample:
    """Training example for neural trust scorer"""
    features: TrustFeatures
    true_outcome: float  # 0.0 = failure, 1.0 = success
    timestamp: datetime


class TrustScorerNetwork(nn.Module):
    """
    Neural network for trust score prediction

    Architecture:
    - Input: Feature vector + optional embedding
    - Multi-head attention over feature importance
    - Feedforward layers with residual connections
    - Dropout for uncertainty estimation
    - Output: Trust score [0, 1] + uncertainty
    """

    def __init__(
        self,
        feature_dim: int = 12,
        embedding_dim: int = 384,
        hidden_dims: List[int] = [256, 128, 64],
        num_attention_heads: int = 4,
        dropout_rate: float = 0.3,
        use_embeddings: bool = True
    ):
        super().__init__()

        self.use_embeddings = use_embeddings

        # Input projection
        input_dim = feature_dim
        if use_embeddings:
            input_dim += embedding_dim

        self.input_proj = nn.Linear(input_dim, hidden_dims[0])

        # Multi-head attention for feature importance
        self.attention = nn.MultiheadAttention(
            embed_dim=hidden_dims[0],
            num_heads=num_attention_heads,
            dropout=dropout_rate,
            batch_first=True
        )

        # Feedforward layers with residual connections
        self.layers = nn.ModuleList()
        for i in range(len(hidden_dims) - 1):
            self.layers.append(nn.Sequential(
                nn.Linear(hidden_dims[i], hidden_dims[i+1]),
                nn.LayerNorm(hidden_dims[i+1]),
                nn.ReLU(),
                nn.Dropout(dropout_rate)
            ))

        # Output layer
        self.output = nn.Linear(hidden_dims[-1], 1)

        # Uncertainty estimation head
        self.uncertainty_head = nn.Linear(hidden_dims[-1], 1)

    def forward(self, x: torch.Tensor, return_uncertainty: bool = False) -> torch.Tensor:
        """
        Forward pass

        Args:
            x: Input features [batch_size, feature_dim]
            return_uncertainty: If True, return (score, uncertainty)

        Returns:
            Trust score [0, 1] or (score, uncertainty)
        """
        # Input projection
        x = self.input_proj(x)
        x = F.relu(x)

        # Self-attention (reshape for attention)
        x_attn = x.unsqueeze(1)  # [batch, 1, hidden]
        attn_out, _ = self.attention(x_attn, x_attn, x_attn)
        x = x + attn_out.squeeze(1)  # Residual connection

        # Feedforward layers
        for layer in self.layers:
            residual = x
            x = layer(x)
            # Residual connection if dimensions match
            if residual.shape == x.shape:
                x = x + residual

        # Output
        trust_score = torch.sigmoid(self.output(x))

        if return_uncertainty:
            uncertainty = torch.sigmoid(self.uncertainty_head(x))
            return trust_score, uncertainty

        return trust_score

    def predict_with_uncertainty(
        self,
        x: torch.Tensor,
        num_samples: int = 20
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Monte Carlo dropout for uncertainty estimation

        Args:
            x: Input features
            num_samples: Number of MC samples

        Returns:
            (mean_score, std_score)
        """
        self.train()  # Enable dropout

        predictions = []
        with torch.no_grad():
            for _ in range(num_samples):
                pred = self(x)
                predictions.append(pred)

        predictions = torch.stack(predictions)
        mean_score = predictions.mean(dim=0)
        std_score = predictions.std(dim=0)

        self.eval()
        return mean_score, std_score


class ExperienceReplay:
    """Experience replay buffer for online learning"""

    def __init__(self, max_size: int = 10000):
        self.buffer = deque(maxlen=max_size)

    def add(self, example: TrainingExample):
        """Add training example to buffer"""
        self.buffer.append(example)

    def sample(self, batch_size: int) -> List[TrainingExample]:
        """Sample random batch"""
        indices = np.random.choice(len(self.buffer), size=min(batch_size, len(self.buffer)), replace=False)
        return [self.buffer[i] for i in indices]

    def __len__(self) -> int:
        return len(self.buffer)


class NeuralTrustScorer:
    """
    Neural Trust Scorer - Main interface

    Combines neural network with online learning and uncertainty estimation
    """

    def __init__(
        self,
        model_path: str = "models/neural_trust_scorer.pt",
        device: str = None,
        learning_rate: float = 1e-4,
        batch_size: int = 32,
        replay_buffer_size: int = 10000
    ):
        self.model_path = model_path
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        self.batch_size = batch_size

        # Initialize network
        self.network = TrustScorerNetwork().to(self.device)

        # Optimizer
        self.optimizer = AdamW(self.network.parameters(), lr=learning_rate, weight_decay=1e-5)

        # Experience replay
        self.replay_buffer = ExperienceReplay(max_size=replay_buffer_size)

        # Load model if exists
        if os.path.exists(model_path):
            self.load_model()

        # Training statistics
        self.training_stats = {
            'total_updates': 0,
            'total_loss': 0.0,
            'recent_losses': deque(maxlen=100)
        }

    def extract_features(self, learning_example: Dict) -> TrustFeatures:
        """
        Extract features from learning example

        Args:
            learning_example: Dict with learning example data

        Returns:
            TrustFeatures object
        """
        # Calculate derived metrics
        total_uses = learning_example.get('times_validated', 0) + learning_example.get('times_invalidated', 0)
        success_rate = learning_example.get('times_validated', 0) / max(total_uses, 1)

        # Age calculation
        created_at = learning_example.get('created_at', datetime.now())
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        age_days = (datetime.now() - created_at).days

        # Content analysis
        context = learning_example.get('input_context', '')
        output = learning_example.get('expected_output', '')
        content = f"{context} {output}"

        has_code = any(keyword in content.lower() for keyword in ['def ', 'class ', 'import ', 'function', '()', '{}'])
        has_structure = any(char in content for char in ['#', '*', '-', '1.', '2.'])
        has_references = any(keyword in content.lower() for keyword in ['http', 'see', 'reference', 'source', 'doc'])

        return TrustFeatures(
            source_reliability=learning_example.get('source_reliability', 0.5),
            outcome_quality=learning_example.get('outcome_quality', 0.5),
            consistency_score=learning_example.get('consistency_score', 0.5),
            validation_count=learning_example.get('times_validated', 0),
            invalidation_count=learning_example.get('times_invalidated', 0),
            age_days=age_days,
            content_length=len(content),
            has_code=has_code,
            has_structure=has_structure,
            has_references=has_references,
            usage_frequency=learning_example.get('times_referenced', 0) / max(age_days, 1),
            success_rate=success_rate,
            embedding=learning_example.get('embedding')
        )

    def features_to_tensor(self, features: TrustFeatures) -> torch.Tensor:
        """Convert features to tensor"""
        feature_vector = [
            features.source_reliability,
            features.outcome_quality,
            features.consistency_score,
            features.validation_count / 100.0,  # Normalize
            features.invalidation_count / 100.0,
            min(features.age_days / 365.0, 1.0),  # Normalize to [0, 1]
            min(features.content_length / 10000.0, 1.0),
            float(features.has_code),
            float(features.has_structure),
            float(features.has_references),
            features.usage_frequency,
            features.success_rate
        ]

        # Add embedding if available
        if features.embedding is not None and self.network.use_embeddings:
            feature_vector.extend(features.embedding.tolist())
        elif self.network.use_embeddings:
            # Pad with zeros if embedding expected but not provided
            feature_vector.extend([0.0] * 384)

        return torch.tensor(feature_vector, dtype=torch.float32, device=self.device)

    def predict_trust(
        self,
        learning_example: Dict,
        return_uncertainty: bool = True
    ) -> Tuple[float, Optional[float]]:
        """
        Predict trust score for learning example

        Args:
            learning_example: Learning example dict
            return_uncertainty: Whether to return uncertainty estimate

        Returns:
            (trust_score, uncertainty) or just trust_score
        """
        self.network.eval()

        # Extract features
        features = self.extract_features(learning_example)
        x = self.features_to_tensor(features).unsqueeze(0)

        with torch.no_grad():
            if return_uncertainty:
                mean_score, std_score = self.network.predict_with_uncertainty(x, num_samples=20)
                return mean_score.item(), std_score.item()
            else:
                score = self.network(x)
                return score.item(), None

    def update_from_outcome(
        self,
        learning_example: Dict,
        outcome_success: bool,
        perform_training: bool = True
    ):
        """
        Update model based on observed outcome

        Args:
            learning_example: Learning example dict
            outcome_success: Whether the outcome was successful
            perform_training: Whether to perform training update immediately
        """
        # Extract features
        features = self.extract_features(learning_example)

        # Create training example
        training_example = TrainingExample(
            features=features,
            true_outcome=1.0 if outcome_success else 0.0,
            timestamp=datetime.now()
        )

        # Add to replay buffer
        self.replay_buffer.add(training_example)

        # Perform training if requested and buffer has enough samples
        if perform_training and len(self.replay_buffer) >= self.batch_size:
            self.train_step()

    def train_step(self, num_batches: int = 1):
        """
        Perform training step using experience replay

        Args:
            num_batches: Number of batches to train on
        """
        self.network.train()

        total_loss = 0.0

        for _ in range(num_batches):
            # Sample batch
            batch = self.replay_buffer.sample(self.batch_size)

            # Prepare tensors
            X = torch.stack([self.features_to_tensor(ex.features) for ex in batch])
            y = torch.tensor([ex.true_outcome for ex in batch], dtype=torch.float32, device=self.device).unsqueeze(1)

            # Forward pass
            predictions, uncertainties = self.network(X, return_uncertainty=True)

            # Loss: Binary cross-entropy + uncertainty regularization
            bce_loss = F.binary_cross_entropy(predictions, y)

            # Encourage lower uncertainty for correct predictions
            uncertainty_loss = torch.mean(uncertainties * torch.abs(predictions - y))

            loss = bce_loss + 0.1 * uncertainty_loss

            # Backward pass
            self.optimizer.zero_grad()
            loss.backward()

            # Gradient clipping
            torch.nn.utils.clip_grad_norm_(self.network.parameters(), max_norm=1.0)

            self.optimizer.step()

            total_loss += loss.item()

        # Update statistics
        avg_loss = total_loss / num_batches
        self.training_stats['total_updates'] += num_batches
        self.training_stats['total_loss'] += total_loss
        self.training_stats['recent_losses'].append(avg_loss)

        self.network.eval()

        return avg_loss

    def adversarial_test(
        self,
        learning_example: Dict,
        epsilon: float = 0.1,
        num_samples: int = 10
    ) -> Dict:
        """
        Test adversarial robustness

        Perturbs input features and measures score stability

        Args:
            learning_example: Learning example to test
            epsilon: Perturbation magnitude
            num_samples: Number of perturbations to test

        Returns:
            Dict with robustness metrics
        """
        self.network.eval()

        # Get baseline prediction
        features = self.extract_features(learning_example)
        x_base = self.features_to_tensor(features)

        with torch.no_grad():
            base_score = self.network(x_base.unsqueeze(0)).item()

        # Generate adversarial perturbations
        perturbed_scores = []
        for _ in range(num_samples):
            # Random perturbation
            noise = torch.randn_like(x_base) * epsilon
            x_perturbed = x_base + noise

            with torch.no_grad():
                perturbed_score = self.network(x_perturbed.unsqueeze(0)).item()
                perturbed_scores.append(perturbed_score)

        # Calculate robustness metrics
        perturbed_scores = np.array(perturbed_scores)

        return {
            'base_score': base_score,
            'mean_perturbed_score': perturbed_scores.mean(),
            'std_perturbed_score': perturbed_scores.std(),
            'max_deviation': np.abs(perturbed_scores - base_score).max(),
            'robustness_score': 1.0 - np.abs(perturbed_scores - base_score).mean()
        }

    def save_model(self):
        """Save model to disk"""
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)

        checkpoint = {
            'network_state': self.network.state_dict(),
            'optimizer_state': self.optimizer.state_dict(),
            'training_stats': self.training_stats,
            'replay_buffer_size': len(self.replay_buffer)
        }

        torch.save(checkpoint, self.model_path)

    def load_model(self):
        """Load model from disk"""
        if not os.path.exists(self.model_path):
            return

        checkpoint = torch.load(self.model_path, map_location=self.device)

        self.network.load_state_dict(checkpoint['network_state'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state'])
        self.training_stats = checkpoint.get('training_stats', self.training_stats)

    def get_stats(self) -> Dict:
        """Get training statistics"""
        recent_loss = np.mean(list(self.training_stats['recent_losses'])) if self.training_stats['recent_losses'] else 0.0

        return {
            'total_updates': self.training_stats['total_updates'],
            'replay_buffer_size': len(self.replay_buffer),
            'recent_avg_loss': recent_loss,
            'device': self.device
        }


# Singleton instance
_neural_trust_scorer_instance = None


def get_neural_trust_scorer() -> NeuralTrustScorer:
    """Get singleton neural trust scorer instance"""
    global _neural_trust_scorer_instance

    if _neural_trust_scorer_instance is None:
        model_dir = os.path.join(os.path.dirname(__file__), '..', 'models')
        model_path = os.path.join(model_dir, 'neural_trust_scorer.pt')
        _neural_trust_scorer_instance = NeuralTrustScorer(model_path=model_path)

    return _neural_trust_scorer_instance
