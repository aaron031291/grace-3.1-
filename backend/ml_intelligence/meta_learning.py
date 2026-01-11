"""
Meta-Learning Module - Learning to Learn

Implements meta-learning algorithms to optimize learning strategies.
Learns which learning approaches work best for different types of tasks.

Algorithms:
- MAML (Model-Agnostic Meta-Learning)
- Reptile (First-order MAML variant)
- Learning Rate Scheduling via meta-learning
- Hyperparameter Optimization
- Task Similarity Detection
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.optim import SGD, Adam
import numpy as np
from typing import Dict, List, Tuple, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import copy
import json
import os


@dataclass
class LearningTask:
    """A learning task for meta-learning"""
    task_id: str
    task_type: str  # classification, regression, generation, etc.
    support_set: List[Tuple]  # Training examples (X, y)
    query_set: List[Tuple]  # Test examples (X, y)
    metadata: Dict = field(default_factory=dict)


@dataclass
class MetaLearningEpisode:
    """Results from a meta-learning episode"""
    task: LearningTask
    initial_loss: float
    final_loss: float
    improvement: float
    num_steps: int
    optimal_lr: float
    optimal_batch_size: int
    timestamp: datetime = field(default_factory=datetime.now)


class MAML(nn.Module):
    """
    Model-Agnostic Meta-Learning (MAML)

    Learns initialization parameters that enable fast adaptation
    to new tasks with few gradient steps.
    """

    def __init__(
        self,
        model: nn.Module,
        inner_lr: float = 0.01,
        outer_lr: float = 0.001,
        inner_steps: int = 5,
        first_order: bool = False  # True = Reptile, False = MAML
    ):
        super().__init__()
        self.model = model
        self.inner_lr = inner_lr
        self.outer_lr = outer_lr
        self.inner_steps = inner_steps
        self.first_order = first_order

        # Outer optimizer (meta-optimizer)
        self.meta_optimizer = Adam(self.model.parameters(), lr=outer_lr)

    def inner_loop(
        self,
        task: LearningTask,
        loss_fn: Callable = F.mse_loss
    ) -> Tuple[nn.Module, float]:
        """
        Inner loop: Adapt model to specific task

        Args:
            task: Learning task with support set
            loss_fn: Loss function

        Returns:
            (adapted_model, final_loss)
        """
        # Clone model for task-specific adaptation
        adapted_model = copy.deepcopy(self.model)

        # Inner optimizer
        inner_optimizer = SGD(adapted_model.parameters(), lr=self.inner_lr)

        # Adapt on support set
        for step in range(self.inner_steps):
            # Sample batch from support set
            batch = task.support_set

            # Prepare tensors
            X = torch.stack([x for x, y in batch])
            y = torch.stack([y for x, y in batch])

            # Forward pass
            predictions = adapted_model(X)
            loss = loss_fn(predictions, y)

            # Backward pass
            inner_optimizer.zero_grad()
            loss.backward()
            inner_optimizer.step()

        # Evaluate on support set final loss
        with torch.no_grad():
            X = torch.stack([x for x, y in task.support_set])
            y = torch.stack([y for x, y in task.support_set])
            predictions = adapted_model(X)
            final_loss = loss_fn(predictions, y).item()

        return adapted_model, final_loss

    def outer_loop(
        self,
        tasks: List[LearningTask],
        loss_fn: Callable = F.mse_loss
    ) -> float:
        """
        Outer loop: Update meta-parameters

        Args:
            tasks: Batch of learning tasks
            loss_fn: Loss function

        Returns:
            Meta-loss
        """
        meta_loss = 0.0

        for task in tasks:
            # Inner loop adaptation
            adapted_model, _ = self.inner_loop(task, loss_fn)

            # Evaluate on query set
            X = torch.stack([x for x, y in task.query_set])
            y = torch.stack([y for x, y in task.query_set])

            predictions = adapted_model(X)
            task_loss = loss_fn(predictions, y)

            meta_loss += task_loss

        # Average meta-loss
        meta_loss = meta_loss / len(tasks)

        # Update meta-parameters
        self.meta_optimizer.zero_grad()
        meta_loss.backward()
        self.meta_optimizer.step()

        return meta_loss.item()

    def meta_train(
        self,
        task_distribution: List[LearningTask],
        num_iterations: int = 1000,
        tasks_per_batch: int = 4,
        loss_fn: Callable = F.mse_loss
    ) -> List[float]:
        """
        Train meta-learner

        Args:
            task_distribution: Distribution of tasks to meta-learn from
            num_iterations: Number of meta-training iterations
            tasks_per_batch: Tasks per meta-batch
            loss_fn: Loss function

        Returns:
            List of meta-losses
        """
        meta_losses = []

        for iteration in range(num_iterations):
            # Sample batch of tasks
            task_batch = np.random.choice(
                task_distribution,
                size=min(tasks_per_batch, len(task_distribution)),
                replace=False
            ).tolist()

            # Outer loop update
            meta_loss = self.outer_loop(task_batch, loss_fn)
            meta_losses.append(meta_loss)

            if iteration % 100 == 0:
                print(f"Meta-iteration {iteration}: Loss = {meta_loss:.4f}")

        return meta_losses


class HyperparameterOptimizer:
    """
    Meta-learn optimal hyperparameters for different task types

    Uses Bayesian optimization and historical performance
    """

    def __init__(self):
        # Historical performance: (task_type, hyperparams) -> performance
        self.performance_history: List[Dict] = []

        # Learned hyperparameter distributions per task type
        self.hyperparam_stats = defaultdict(lambda: {
            'learning_rate': {'mean': 0.001, 'std': 0.0005},
            'batch_size': {'mean': 32, 'std': 16},
            'num_epochs': {'mean': 10, 'std': 5},
            'dropout': {'mean': 0.2, 'std': 0.1},
            'weight_decay': {'mean': 1e-4, 'std': 5e-5}
        })

    def suggest_hyperparameters(
        self,
        task_type: str,
        task_metadata: Dict = None
    ) -> Dict[str, float]:
        """
        Suggest hyperparameters for a task

        Args:
            task_type: Type of task
            task_metadata: Additional task information

        Returns:
            Dict of suggested hyperparameters
        """
        stats = self.hyperparam_stats[task_type]

        # Sample from learned distributions
        suggestions = {}

        # Learning rate (log-normal distribution)
        lr_mean = np.log(stats['learning_rate']['mean'])
        lr_std = stats['learning_rate']['std']
        suggestions['learning_rate'] = np.exp(np.random.normal(lr_mean, lr_std))

        # Batch size (discrete)
        batch_mean = stats['batch_size']['mean']
        batch_std = stats['batch_size']['std']
        batch_size = int(np.clip(
            np.random.normal(batch_mean, batch_std),
            8, 128
        ))
        # Round to nearest power of 2
        suggestions['batch_size'] = 2 ** int(np.log2(batch_size))

        # Num epochs (discrete)
        epoch_mean = stats['num_epochs']['mean']
        epoch_std = stats['num_epochs']['std']
        suggestions['num_epochs'] = int(np.clip(
            np.random.normal(epoch_mean, epoch_std),
            1, 100
        ))

        # Dropout (clip to [0, 1])
        dropout_mean = stats['dropout']['mean']
        dropout_std = stats['dropout']['std']
        suggestions['dropout'] = np.clip(
            np.random.normal(dropout_mean, dropout_std),
            0.0, 0.5
        )

        # Weight decay (log-normal)
        wd_mean = np.log(stats['weight_decay']['mean'])
        wd_std = stats['weight_decay']['std']
        suggestions['weight_decay'] = np.exp(np.random.normal(wd_mean, wd_std))

        return suggestions

    def update_from_result(
        self,
        task_type: str,
        hyperparams: Dict,
        performance: float,
        task_metadata: Dict = None
    ):
        """
        Update hyperparameter distributions based on observed performance

        Args:
            task_type: Type of task
            hyperparams: Hyperparameters used
            performance: Observed performance (higher is better)
            task_metadata: Additional task information
        """
        # Record result
        self.performance_history.append({
            'task_type': task_type,
            'hyperparams': hyperparams,
            'performance': performance,
            'metadata': task_metadata,
            'timestamp': datetime.now().isoformat()
        })

        # Update statistics using exponential moving average
        alpha = 0.1  # Learning rate for stats update

        stats = self.hyperparam_stats[task_type]

        # Weight by performance (better results have more influence)
        weight = performance

        for param_name, param_value in hyperparams.items():
            if param_name in stats:
                # Update mean
                old_mean = stats[param_name]['mean']
                stats[param_name]['mean'] = (
                    (1 - alpha * weight) * old_mean +
                    alpha * weight * param_value
                )

                # Update std (simple running estimate)
                deviation = abs(param_value - old_mean)
                old_std = stats[param_name]['std']
                stats[param_name]['std'] = (
                    (1 - alpha) * old_std +
                    alpha * deviation
                )

    def get_best_hyperparameters(
        self,
        task_type: str,
        top_k: int = 5
    ) -> List[Tuple[Dict, float]]:
        """
        Get top k best hyperparameter configurations

        Args:
            task_type: Type of task
            top_k: Number of configurations to return

        Returns:
            List of (hyperparams, performance) tuples
        """
        # Filter by task type
        relevant_results = [
            (result['hyperparams'], result['performance'])
            for result in self.performance_history
            if result['task_type'] == task_type
        ]

        # Sort by performance
        sorted_results = sorted(
            relevant_results,
            key=lambda x: x[1],
            reverse=True
        )

        return sorted_results[:top_k]


class TaskSimilarityDetector:
    """
    Detect similar tasks to enable transfer learning

    Uses task embeddings and performance correlation
    """

    def __init__(self, embedding_dim: int = 128):
        self.embedding_dim = embedding_dim

        # Task embeddings
        self.task_embeddings: Dict[str, np.ndarray] = {}

        # Performance correlation matrix
        self.performance_correlations: Dict[Tuple[str, str], float] = {}

    def embed_task(self, task: LearningTask) -> np.ndarray:
        """
        Create embedding for a task

        Args:
            task: Learning task

        Returns:
            Task embedding vector
        """
        # Simple feature-based embedding
        features = []

        # Task type one-hot (simplified)
        task_types = ['classification', 'regression', 'generation', 'retrieval']
        type_encoding = [1.0 if task.task_type == t else 0.0 for t in task_types]
        features.extend(type_encoding)

        # Dataset size
        features.append(np.log1p(len(task.support_set)))
        features.append(np.log1p(len(task.query_set)))

        # Metadata features
        if 'input_dim' in task.metadata:
            features.append(np.log1p(task.metadata['input_dim']))
        else:
            features.append(0.0)

        if 'output_dim' in task.metadata:
            features.append(np.log1p(task.metadata['output_dim']))
        else:
            features.append(0.0)

        # Complexity indicators
        if 'num_classes' in task.metadata:
            features.append(np.log1p(task.metadata['num_classes']))
        else:
            features.append(0.0)

        # Pad to embedding_dim
        embedding = np.array(features, dtype=np.float32)
        if len(embedding) < self.embedding_dim:
            embedding = np.pad(embedding, (0, self.embedding_dim - len(embedding)))
        else:
            embedding = embedding[:self.embedding_dim]

        return embedding

    def add_task(self, task: LearningTask):
        """Add task to similarity database"""
        embedding = self.embed_task(task)
        self.task_embeddings[task.task_id] = embedding

    def find_similar_tasks(
        self,
        task: LearningTask,
        top_k: int = 5,
        exclude_task_ids: List[str] = None
    ) -> List[Tuple[str, float]]:
        """
        Find similar tasks

        Args:
            task: Query task
            top_k: Number of similar tasks to return
            exclude_task_ids: Task IDs to exclude

        Returns:
            List of (task_id, similarity) tuples
        """
        query_embedding = self.embed_task(task)

        similarities = {}

        for task_id, task_embedding in self.task_embeddings.items():
            if exclude_task_ids and task_id in exclude_task_ids:
                continue

            # Cosine similarity
            similarity = np.dot(query_embedding, task_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(task_embedding) + 1e-8
            )

            similarities[task_id] = similarity

        # Sort by similarity
        sorted_tasks = sorted(
            similarities.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return sorted_tasks[:top_k]


class MetaLearningOrchestrator:
    """
    Main orchestrator for meta-learning

    Coordinates MAML, hyperparameter optimization, and task similarity
    """

    def __init__(
        self,
        base_model: nn.Module = None,
        save_dir: str = None
    ):
        self.save_dir = save_dir or os.path.join(
            os.path.dirname(__file__), '..', 'models', 'meta_learning'
        )
        os.makedirs(self.save_dir, exist_ok=True)

        # Components
        self.maml = MAML(base_model) if base_model else None
        self.hyperparam_optimizer = HyperparameterOptimizer()
        self.task_similarity = TaskSimilarityDetector()

        # Episode history
        self.episodes: List[MetaLearningEpisode] = []

        # Load state
        self.load_state()

    def optimize_learning_for_task(
        self,
        task: LearningTask,
        loss_fn: Callable = F.mse_loss
    ) -> MetaLearningEpisode:
        """
        Optimize learning approach for a specific task

        Args:
            task: Learning task
            loss_fn: Loss function

        Returns:
            MetaLearningEpisode with results
        """
        # Suggest hyperparameters
        hyperparams = self.hyperparam_optimizer.suggest_hyperparameters(
            task.task_type,
            task.metadata
        )

        # Find similar tasks for transfer learning hints
        similar_tasks = self.task_similarity.find_similar_tasks(task, top_k=3)

        # Adapt model if MAML available
        initial_loss = None
        final_loss = None
        num_steps = 0

        if self.maml:
            # Measure initial loss
            X = torch.stack([x for x, y in task.query_set])
            y_true = torch.stack([y for x, y in task.query_set])

            with torch.no_grad():
                predictions = self.maml.model(X)
                initial_loss = loss_fn(predictions, y_true).item()

            # Adapt
            adapted_model, final_loss = self.maml.inner_loop(task, loss_fn)
            num_steps = self.maml.inner_steps

        # Create episode
        episode = MetaLearningEpisode(
            task=task,
            initial_loss=initial_loss or 0.0,
            final_loss=final_loss or 0.0,
            improvement=(initial_loss - final_loss) if initial_loss else 0.0,
            num_steps=num_steps,
            optimal_lr=hyperparams.get('learning_rate', 0.001),
            optimal_batch_size=hyperparams.get('batch_size', 32)
        )

        # Record episode
        self.episodes.append(episode)

        # Update task similarity database
        self.task_similarity.add_task(task)

        # Update hyperparameter optimizer
        performance = episode.improvement / (initial_loss + 1e-8) if initial_loss else 0.0
        self.hyperparam_optimizer.update_from_result(
            task.task_type,
            hyperparams,
            performance,
            task.metadata
        )

        return episode

    def get_learning_recommendations(
        self,
        task_type: str,
        task_metadata: Dict = None
    ) -> Dict:
        """
        Get recommendations for learning a new task type

        Args:
            task_type: Type of task
            task_metadata: Task metadata

        Returns:
            Dict with recommendations
        """
        # Get hyperparameter suggestions
        hyperparams = self.hyperparam_optimizer.suggest_hyperparameters(
            task_type,
            task_metadata
        )

        # Get best known configurations
        best_configs = self.hyperparam_optimizer.get_best_hyperparameters(
            task_type,
            top_k=3
        )

        return {
            'suggested_hyperparams': hyperparams,
            'best_known_configs': best_configs,
            'num_historical_examples': len([
                e for e in self.episodes
                if e.task.task_type == task_type
            ])
        }

    def save_state(self):
        """Save meta-learning state"""
        state = {
            'hyperparam_stats': dict(self.hyperparam_optimizer.hyperparam_stats),
            'performance_history': self.hyperparam_optimizer.performance_history,
            'task_embeddings': {
                k: v.tolist()
                for k, v in self.task_similarity.task_embeddings.items()
            },
            'num_episodes': len(self.episodes)
        }

        state_path = os.path.join(self.save_dir, 'meta_learning_state.json')
        with open(state_path, 'w') as f:
            json.dump(state, f, indent=2)

        # Save MAML model if available
        if self.maml:
            model_path = os.path.join(self.save_dir, 'maml_model.pt')
            torch.save(self.maml.model.state_dict(), model_path)

    def load_state(self):
        """Load meta-learning state"""
        state_path = os.path.join(self.save_dir, 'meta_learning_state.json')

        if not os.path.exists(state_path):
            return False

        with open(state_path, 'r') as f:
            state = json.load(f)

        # Restore hyperparameter optimizer
        self.hyperparam_optimizer.hyperparam_stats = defaultdict(
            dict,
            state.get('hyperparam_stats', {})
        )
        self.hyperparam_optimizer.performance_history = state.get('performance_history', [])

        # Restore task embeddings
        self.task_similarity.task_embeddings = {
            k: np.array(v, dtype=np.float32)
            for k, v in state.get('task_embeddings', {}).items()
        }

        return True


# Singleton instance
_meta_learning_instance = None


def get_meta_learner() -> MetaLearningOrchestrator:
    """Get singleton meta-learning orchestrator"""
    global _meta_learning_instance

    if _meta_learning_instance is None:
        _meta_learning_instance = MetaLearningOrchestrator()

    return _meta_learning_instance
