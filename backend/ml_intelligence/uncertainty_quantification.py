"""
Uncertainty Quantification - Bayesian Confidence Estimation

Provides calibrated confidence estimates for predictions using:
- Bayesian Neural Networks
- Monte Carlo Dropout
- Deep Ensembles
- Conformal Prediction
- Epistemic vs Aleatoric Uncertainty

Helps the system know when it doesn't know something.

Classes:
- `UncertaintyEstimate`
- `BayesianLinear`
- `BayesianNeuralNetwork`
- `MCDropoutNetwork`
- `DeepEnsemble`
- `ConformalPredictor`
- `UncertaintyQuantifier`

Key Methods:
- `reset_parameters()`
- `forward()`
- `kl_divergence()`
- `forward()`
- `kl_divergence()`
- `predict_with_uncertainty()`
- `forward()`
- `predict_with_uncertainty()`
- `train_ensemble()`
- `predict_with_uncertainty()`
- `calibrate()`
- `predict_interval()`
- `predict_with_uncertainty()`
- `calibrate()`
- `create_bayesian_network()`
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import Normal, kl_divergence
import numpy as np
from typing import Dict, List, Tuple, Optional, Callable
from dataclasses import dataclass
from collections import defaultdict
import os


@dataclass
class UncertaintyEstimate:
    """Uncertainty estimate for a prediction"""
    prediction: float
    epistemic_uncertainty: float  # Model uncertainty (lack of knowledge)
    aleatoric_uncertainty: float  # Data uncertainty (inherent randomness)
    total_uncertainty: float
    confidence_interval: Tuple[float, float]  # (lower, upper)
    is_reliable: bool  # Whether uncertainty is within acceptable bounds


class BayesianLinear(nn.Module):
    """
    Bayesian Linear Layer

    Uses variational inference to learn weight distributions
    instead of point estimates
    """

    def __init__(
        self,
        in_features: int,
        out_features: int,
        prior_std: float = 1.0
    ):
        super().__init__()

        self.in_features = in_features
        self.out_features = out_features

        # Weight mean and std (variational parameters)
        self.weight_mean = nn.Parameter(torch.Tensor(out_features, in_features))
        self.weight_logstd = nn.Parameter(torch.Tensor(out_features, in_features))

        # Bias mean and std
        self.bias_mean = nn.Parameter(torch.Tensor(out_features))
        self.bias_logstd = nn.Parameter(torch.Tensor(out_features))

        # Prior distribution
        self.prior_std = prior_std

        # Initialize
        self.reset_parameters()

    def reset_parameters(self):
        """Initialize parameters"""
        nn.init.xavier_normal_(self.weight_mean)
        nn.init.constant_(self.weight_logstd, -3.0)  # Small initial std
        nn.init.zeros_(self.bias_mean)
        nn.init.constant_(self.bias_logstd, -3.0)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass with weight sampling"""
        # Sample weights from learned distribution
        weight_std = torch.exp(self.weight_logstd)
        weight = self.weight_mean + weight_std * torch.randn_like(weight_std)

        # Sample bias
        bias_std = torch.exp(self.bias_logstd)
        bias = self.bias_mean + bias_std * torch.randn_like(bias_std)

        # Linear transformation
        return F.linear(x, weight, bias)

    def kl_divergence(self) -> torch.Tensor:
        """
        KL divergence between variational posterior and prior

        KL(q(w) || p(w)) where p(w) ~ N(0, prior_std^2)
        """
        # Weight KL
        weight_var = torch.exp(2 * self.weight_logstd)
        weight_kl = 0.5 * torch.sum(
            (self.weight_mean ** 2 + weight_var) / (self.prior_std ** 2) -
            1 -
            2 * self.weight_logstd +
            2 * np.log(self.prior_std)
        )

        # Bias KL
        bias_var = torch.exp(2 * self.bias_logstd)
        bias_kl = 0.5 * torch.sum(
            (self.bias_mean ** 2 + bias_var) / (self.prior_std ** 2) -
            1 -
            2 * self.bias_logstd +
            2 * np.log(self.prior_std)
        )

        return weight_kl + bias_kl


class BayesianNeuralNetwork(nn.Module):
    """
    Bayesian Neural Network

    All layers are Bayesian, providing uncertainty estimates
    """

    def __init__(
        self,
        input_dim: int,
        hidden_dims: List[int] = [128, 64],
        output_dim: int = 1,
        prior_std: float = 1.0
    ):
        super().__init__()

        # Build Bayesian layers
        layers = []
        prev_dim = input_dim

        for hidden_dim in hidden_dims:
            layers.append(BayesianLinear(prev_dim, hidden_dim, prior_std))
            prev_dim = hidden_dim

        # Output layer
        layers.append(BayesianLinear(prev_dim, output_dim, prior_std))

        self.layers = nn.ModuleList(layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass"""
        for i, layer in enumerate(self.layers):
            x = layer(x)
            # ReLU activation for hidden layers
            if i < len(self.layers) - 1:
                x = F.relu(x)

        return x

    def kl_divergence(self) -> torch.Tensor:
        """Total KL divergence across all layers"""
        kl_total = 0.0
        for layer in self.layers:
            if isinstance(layer, BayesianLinear):
                kl_total += layer.kl_divergence()
        return kl_total

    def predict_with_uncertainty(
        self,
        x: torch.Tensor,
        num_samples: int = 100
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Predict with uncertainty estimates

        Args:
            x: Input tensor
            num_samples: Number of Monte Carlo samples

        Returns:
            (mean_prediction, epistemic_uncertainty)
        """
        predictions = []

        for _ in range(num_samples):
            with torch.no_grad():
                pred = self(x)
                predictions.append(pred)

        predictions = torch.stack(predictions)

        # Mean prediction
        mean_pred = predictions.mean(dim=0)

        # Epistemic uncertainty (model uncertainty)
        epistemic_unc = predictions.std(dim=0)

        return mean_pred, epistemic_unc


class MCDropoutNetwork(nn.Module):
    """
    Monte Carlo Dropout Network

    Uses dropout at inference time to estimate uncertainty
    """

    def __init__(
        self,
        input_dim: int,
        hidden_dims: List[int] = [128, 64],
        output_dim: int = 1,
        dropout_rate: float = 0.3
    ):
        super().__init__()

        layers = []
        prev_dim = input_dim

        for hidden_dim in hidden_dims:
            layers.append(nn.Linear(prev_dim, hidden_dim))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(dropout_rate))
            prev_dim = hidden_dim

        # Output layer
        layers.append(nn.Linear(prev_dim, output_dim))

        self.network = nn.Sequential(*layers)
        self.dropout_rate = dropout_rate

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass"""
        return self.network(x)

    def predict_with_uncertainty(
        self,
        x: torch.Tensor,
        num_samples: int = 50
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Predict with MC Dropout uncertainty

        Args:
            x: Input tensor
            num_samples: Number of MC samples

        Returns:
            (mean_prediction, uncertainty)
        """
        # Enable dropout during inference
        self.train()

        predictions = []

        with torch.no_grad():
            for _ in range(num_samples):
                pred = self(x)
                predictions.append(pred)

        predictions = torch.stack(predictions)

        mean_pred = predictions.mean(dim=0)
        uncertainty = predictions.std(dim=0)

        self.eval()

        return mean_pred, uncertainty


class DeepEnsemble:
    """
    Deep Ensemble for Uncertainty Estimation

    Trains multiple independent models and combines predictions
    """

    def __init__(
        self,
        model_fn: Callable,
        num_models: int = 5,
        device: str = None
    ):
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        self.models = [model_fn().to(self.device) for _ in range(num_models)]
        self.num_models = num_models

        # Optimizers for each model
        self.optimizers = [
            torch.optim.Adam(model.parameters(), lr=1e-3)
            for model in self.models
        ]

    def train_ensemble(
        self,
        train_loader,
        num_epochs: int = 10,
        loss_fn: Callable = F.mse_loss
    ):
        """Train all models in ensemble"""
        for epoch in range(num_epochs):
            for model_idx, (model, optimizer) in enumerate(zip(self.models, self.optimizers)):
                model.train()
                epoch_loss = 0.0

                for batch_x, batch_y in train_loader:
                    batch_x = batch_x.to(self.device)
                    batch_y = batch_y.to(self.device)

                    # Forward pass
                    predictions = model(batch_x)
                    loss = loss_fn(predictions, batch_y)

                    # Backward pass
                    optimizer.zero_grad()
                    loss.backward()
                    optimizer.step()

                    epoch_loss += loss.item()

    def predict_with_uncertainty(
        self,
        x: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Predict with ensemble uncertainty

        Args:
            x: Input tensor

        Returns:
            (mean_prediction, uncertainty)
        """
        predictions = []

        for model in self.models:
            model.eval()
            with torch.no_grad():
                pred = model(x)
                predictions.append(pred)

        predictions = torch.stack(predictions)

        mean_pred = predictions.mean(dim=0)
        uncertainty = predictions.std(dim=0)

        return mean_pred, uncertainty


class ConformalPredictor:
    """
    Conformal Prediction for Calibrated Confidence Intervals

    Provides statistically valid prediction intervals
    """

    def __init__(self, model: nn.Module, significance_level: float = 0.1):
        self.model = model
        self.significance_level = significance_level  # E.g., 0.1 = 90% confidence
        self.calibration_scores = []

    def calibrate(
        self,
        calibration_loader,
        loss_fn: Callable = F.mse_loss
    ):
        """
        Calibrate on held-out calibration set

        Args:
            calibration_loader: DataLoader with calibration data
            loss_fn: Loss function for computing conformity scores
        """
        self.model.eval()
        scores = []

        with torch.no_grad():
            for batch_x, batch_y in calibration_loader:
                predictions = self.model(batch_x)

                # Compute conformity scores (prediction error)
                conformity_scores = torch.abs(predictions - batch_y)
                scores.extend(conformity_scores.cpu().numpy().flatten())

        self.calibration_scores = np.array(scores)

    def predict_interval(
        self,
        x: torch.Tensor
    ) -> Tuple[torch.Tensor, Tuple[torch.Tensor, torch.Tensor]]:
        """
        Predict with conformal interval

        Args:
            x: Input tensor

        Returns:
            (prediction, (lower_bound, upper_bound))
        """
        self.model.eval()

        with torch.no_grad():
            prediction = self.model(x)

        # Compute quantile of calibration scores
        if len(self.calibration_scores) == 0:
            # No calibration, use wide interval
            margin = torch.ones_like(prediction) * 1.0
        else:
            quantile_level = np.ceil((1 - self.significance_level) * (len(self.calibration_scores) + 1)) / len(self.calibration_scores)
            quantile_level = min(quantile_level, 1.0)

            margin = np.quantile(self.calibration_scores, quantile_level)
            margin = torch.tensor(margin, dtype=prediction.dtype, device=prediction.device)

        lower = prediction - margin
        upper = prediction + margin

        return prediction, (lower, upper)


class UncertaintyQuantifier:
    """
    Main Uncertainty Quantification Interface

    Combines multiple uncertainty estimation methods
    """

    def __init__(
        self,
        model: nn.Module,
        method: str = 'mc_dropout',  # 'bayesian', 'mc_dropout', 'ensemble', 'conformal'
        device: str = None
    ):
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        self.method = method

        if method == 'bayesian':
            # Convert regular model to Bayesian (not implemented here, use BayesianNeuralNetwork directly)
            self.model = model
        elif method == 'mc_dropout':
            self.model = model
        elif method == 'ensemble':
            # Ensemble wraps multiple models
            self.model = model
        elif method == 'conformal':
            self.conformal = ConformalPredictor(model)
            self.model = model
        else:
            self.model = model

        self.model.to(self.device)

    def predict_with_uncertainty(
        self,
        x: torch.Tensor,
        num_samples: int = 50,
        confidence_level: float = 0.95
    ) -> UncertaintyEstimate:
        """
        Predict with full uncertainty quantification

        Args:
            x: Input tensor
            num_samples: Number of MC samples
            confidence_level: Confidence level for intervals

        Returns:
            UncertaintyEstimate object
        """
        x = x.to(self.device)

        if self.method == 'bayesian' and isinstance(self.model, BayesianNeuralNetwork):
            mean_pred, epistemic_unc = self.model.predict_with_uncertainty(x, num_samples)

        elif self.method == 'mc_dropout' and isinstance(self.model, MCDropoutNetwork):
            mean_pred, epistemic_unc = self.model.predict_with_uncertainty(x, num_samples)

        elif self.method == 'ensemble' and isinstance(self.model, DeepEnsemble):
            mean_pred, epistemic_unc = self.model.predict_with_uncertainty(x)

        elif self.method == 'conformal':
            mean_pred, (lower, upper) = self.conformal.predict_interval(x)
            epistemic_unc = (upper - lower) / 2.0

        else:
            # Fallback: MC Dropout on any model
            self.model.train()
            predictions = []
            with torch.no_grad():
                for _ in range(num_samples):
                    pred = self.model(x)
                    predictions.append(pred)

            predictions = torch.stack(predictions)
            mean_pred = predictions.mean(dim=0)
            epistemic_unc = predictions.std(dim=0)
            self.model.eval()

        # Aleatoric uncertainty (data noise) - can be learned or estimated
        # For simplicity, use a fraction of epistemic uncertainty
        aleatoric_unc = epistemic_unc * 0.2

        # Total uncertainty
        total_unc = torch.sqrt(epistemic_unc ** 2 + aleatoric_unc ** 2)

        # Confidence interval (Gaussian assumption)
        z_score = 1.96 if confidence_level == 0.95 else 2.576  # 95% or 99%
        lower_bound = mean_pred - z_score * total_unc
        upper_bound = mean_pred + z_score * total_unc

        # Reliability check (uncertainty should be reasonable)
        is_reliable = (total_unc < 0.5).all().item()  # Threshold: 0.5

        return UncertaintyEstimate(
            prediction=mean_pred.item() if mean_pred.numel() == 1 else mean_pred.cpu().numpy(),
            epistemic_uncertainty=epistemic_unc.item() if epistemic_unc.numel() == 1 else epistemic_unc.cpu().numpy(),
            aleatoric_uncertainty=aleatoric_unc.item() if aleatoric_unc.numel() == 1 else aleatoric_unc.cpu().numpy(),
            total_uncertainty=total_unc.item() if total_unc.numel() == 1 else total_unc.cpu().numpy(),
            confidence_interval=(
                lower_bound.item() if lower_bound.numel() == 1 else lower_bound.cpu().numpy(),
                upper_bound.item() if upper_bound.numel() == 1 else upper_bound.cpu().numpy()
            ),
            is_reliable=is_reliable
        )

    def calibrate(self, calibration_loader):
        """Calibrate uncertainty estimates"""
        if self.method == 'conformal':
            self.conformal.calibrate(calibration_loader)


def create_bayesian_network(
    input_dim: int,
    hidden_dims: List[int] = [128, 64],
    output_dim: int = 1
) -> BayesianNeuralNetwork:
    """Factory function for Bayesian networks"""
    return BayesianNeuralNetwork(input_dim, hidden_dims, output_dim)


def create_mc_dropout_network(
    input_dim: int,
    hidden_dims: List[int] = [128, 64],
    output_dim: int = 1,
    dropout_rate: float = 0.3
) -> MCDropoutNetwork:
    """Factory function for MC Dropout networks"""
    return MCDropoutNetwork(input_dim, hidden_dims, output_dim, dropout_rate)


# Singleton instance
_uncertainty_quantifier_instance = None


def get_uncertainty_quantifier(
    model: nn.Module = None,
    method: str = 'mc_dropout'
) -> UncertaintyQuantifier:
    """Get uncertainty quantifier instance"""
    global _uncertainty_quantifier_instance

    if _uncertainty_quantifier_instance is None and model is not None:
        _uncertainty_quantifier_instance = UncertaintyQuantifier(model, method)

    return _uncertainty_quantifier_instance
