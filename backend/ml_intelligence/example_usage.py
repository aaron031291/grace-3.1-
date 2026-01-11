"""
ML Intelligence Module - Example Usage

Demonstrates how to use each component of the ML Intelligence module.
"""

import torch
import numpy as np
from datetime import datetime

# Example 1: Neural Trust Scorer
def example_neural_trust_scorer():
    """Example: Using neural trust scorer for learning examples"""
    from ml_intelligence import get_neural_trust_scorer

    print("=" * 60)
    print("Example 1: Neural Trust Scorer")
    print("=" * 60)

    scorer = get_neural_trust_scorer()

    # Learning example
    learning_example = {
        'input_context': 'How to implement async/await in Python',
        'expected_output': 'Use async def and await keywords',
        'actual_output': 'Use async def and await keywords',
        'source_reliability': 0.9,
        'outcome_quality': 0.85,
        'consistency_score': 0.8,
        'times_validated': 5,
        'times_invalidated': 1,
        'times_referenced': 10,
        'created_at': datetime(2024, 1, 1)
    }

    # Predict trust score
    trust_score, uncertainty = scorer.predict_trust(learning_example, return_uncertainty=True)
    print(f"\nTrust Score: {trust_score:.3f}")
    print(f"Uncertainty: {uncertainty:.3f}")

    # Update from outcome
    scorer.update_from_outcome(learning_example, outcome_success=True)
    print("\nUpdated model with positive outcome")

    # Test adversarial robustness
    robustness = scorer.adversarial_test(learning_example)
    print(f"\nRobustness Score: {robustness['robustness_score']:.3f}")
    print(f"Max Deviation: {robustness['max_deviation']:.3f}")


# Example 2: Multi-Armed Bandit
def example_bandit():
    """Example: Topic selection using multi-armed bandit"""
    from ml_intelligence import get_bandit, BanditAlgorithm, BanditContext

    print("\n" + "=" * 60)
    print("Example 2: Multi-Armed Bandit for Topic Selection")
    print("=" * 60)

    bandit = get_bandit(algorithm=BanditAlgorithm.THOMPSON_SAMPLING)

    # Add learning topics
    topics = [
        ("python_async", "Python Async Programming", {"difficulty": 0.7}),
        ("rust_ownership", "Rust Ownership Model", {"difficulty": 0.9}),
        ("react_hooks", "React Hooks", {"difficulty": 0.5}),
        ("kubernetes", "Kubernetes Basics", {"difficulty": 0.8}),
        ("graphql", "GraphQL API Design", {"difficulty": 0.6})
    ]

    for topic_id, topic_name, features in topics:
        bandit.add_arm(topic_id, topic_name, features)

    # Create context
    context = BanditContext(
        knowledge_gaps={"python_async": 0.8, "rust_ownership": 0.5},
        recent_failures=["python_async"],
        user_interests={"rust_ownership": 0.9},
        time_of_day=14,
        learning_velocity=1.2
    )

    # Select topics
    print("\nSelecting next 5 learning topics:")
    for i in range(5):
        topic_id = bandit.select_arm(context=context)
        print(f"  {i+1}. {topic_id}")

        # Simulate learning and update reward
        success = np.random.random() > 0.3  # 70% success rate
        reward = 1.0 if success else 0.0
        bandit.update_reward(topic_id, reward, context)

    # Get recommendations
    recommendations = bandit.recommend_next_topics(k=3, context=context)
    print("\nTop 3 recommended topics:")
    for topic_id, score in recommendations:
        print(f"  - {topic_id}: {score:.3f}")

    # Statistics
    stats = bandit.get_all_stats()
    print(f"\nTotal pulls: {stats['total_pulls']}")
    print(f"Number of topics: {stats['num_arms']}")


# Example 3: Meta-Learning
def example_meta_learning():
    """Example: Getting hyperparameter recommendations"""
    from ml_intelligence import get_meta_learner

    print("\n" + "=" * 60)
    print("Example 3: Meta-Learning for Hyperparameter Optimization")
    print("=" * 60)

    meta_learner = get_meta_learner()

    # Get recommendations for a classification task
    recommendations = meta_learner.get_learning_recommendations(
        task_type="classification",
        task_metadata={"num_classes": 10, "input_dim": 784}
    )

    print("\nSuggested Hyperparameters:")
    for param, value in recommendations['suggested_hyperparams'].items():
        print(f"  {param}: {value}")

    # Simulate training with these hyperparameters
    hyperparams = recommendations['suggested_hyperparams']
    performance = 0.92  # 92% accuracy

    # Update meta-learner with results
    meta_learner.hyperparam_optimizer.update_from_result(
        task_type="classification",
        hyperparams=hyperparams,
        performance=performance
    )

    print(f"\nUpdated meta-learner with performance: {performance:.2%}")

    # Get best known configurations
    best_configs = meta_learner.hyperparam_optimizer.get_best_hyperparameters(
        task_type="classification",
        top_k=3
    )

    if best_configs:
        print("\nTop 3 best known configurations:")
        for i, (config, perf) in enumerate(best_configs, 1):
            print(f"  {i}. Performance: {perf:.2%}")
            print(f"     Learning rate: {config.get('learning_rate', 'N/A')}")
            print(f"     Batch size: {config.get('batch_size', 'N/A')}")


# Example 4: Uncertainty Quantification
def example_uncertainty():
    """Example: Uncertainty estimation for predictions"""
    from ml_intelligence import MCDropoutNetwork, UncertaintyQuantifier

    print("\n" + "=" * 60)
    print("Example 4: Uncertainty Quantification")
    print("=" * 60)

    # Create MC Dropout network
    model = MCDropoutNetwork(
        input_dim=100,
        hidden_dims=[128, 64],
        output_dim=1,
        dropout_rate=0.3
    )

    # Create uncertainty quantifier
    quantifier = UncertaintyQuantifier(model, method='mc_dropout')

    # Test data
    x_test = torch.randn(5, 100)

    print("\nPredictions with Uncertainty:")
    for i in range(5):
        estimate = quantifier.predict_with_uncertainty(
            x_test[i:i+1],
            num_samples=50
        )

        print(f"\nSample {i+1}:")
        print(f"  Prediction: {estimate.prediction:.3f}")
        print(f"  Epistemic Uncertainty: {estimate.epistemic_uncertainty:.3f}")
        print(f"  Total Uncertainty: {estimate.total_uncertainty:.3f}")
        print(f"  95% CI: [{estimate.confidence_interval[0]:.3f}, {estimate.confidence_interval[1]:.3f}]")
        print(f"  Reliable: {estimate.is_reliable}")


# Example 5: Active Learning
def example_active_learning():
    """Example: Selecting most valuable training examples"""
    from ml_intelligence import get_active_sampler, SamplingStrategy

    print("\n" + "=" * 60)
    print("Example 5: Active Learning Sample Selection")
    print("=" * 60)

    # Simple model for demonstration
    class SimpleModel(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.fc = torch.nn.Sequential(
                torch.nn.Linear(100, 64),
                torch.nn.Dropout(0.3),
                torch.nn.ReLU(),
                torch.nn.Linear(64, 10)
            )

        def forward(self, x):
            return self.fc(x)

    model = SimpleModel()

    # Create active sampler
    sampler = get_active_sampler(
        model=model,
        strategy=SamplingStrategy.UNCERTAINTY
    )

    # Unlabeled pool
    unlabeled_pool = torch.randn(1000, 100)

    print("\nSelecting 10 most valuable samples using different strategies:")

    strategies = [
        SamplingStrategy.UNCERTAINTY,
        SamplingStrategy.ENTROPY,
        SamplingStrategy.MARGIN,
        SamplingStrategy.DIVERSITY
    ]

    for strategy in strategies:
        sampler.strategy = strategy
        selected = sampler.select_samples(unlabeled_pool, n_samples=10)
        print(f"\n  {strategy.value}: Selected indices {selected[:5]}... (showing first 5)")

    # Hybrid selection
    print("\nHybrid selection (60% uncertainty, 40% diversity):")
    selected = sampler.hybrid_selection(
        unlabeled_pool,
        n_samples=10,
        weights={
            SamplingStrategy.UNCERTAINTY: 0.6,
            SamplingStrategy.DIVERSITY: 0.4
        }
    )
    print(f"  Selected indices: {selected}")


# Example 6: Contrastive Learning
def example_contrastive_learning():
    """Example: Learning better representations"""
    from ml_intelligence import ContrastiveLearner, ContrastiveBatch

    print("\n" + "=" * 60)
    print("Example 6: Contrastive Learning")
    print("=" * 60)

    # Simple encoder
    class SimpleEncoder(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.encoder = torch.nn.Sequential(
                torch.nn.Linear(100, 256),
                torch.nn.ReLU(),
                torch.nn.Linear(256, 128)
            )
            self.output_dim = 128

        def forward(self, x):
            return self.encoder(x)

    encoder = SimpleEncoder()

    # Create contrastive learner
    learner = ContrastiveLearner(
        encoder=encoder,
        loss_type='ntxent',
        temperature=0.5
    )

    # Training data (simulated pairs)
    batch_size = 32
    anchors = torch.randn(batch_size, 100)
    positives = anchors + torch.randn(batch_size, 100) * 0.1  # Similar to anchors

    batch = ContrastiveBatch(
        anchors=anchors,
        positives=positives
    )

    # Training step
    print("\nTraining contrastive learner:")
    for epoch in range(5):
        metrics = learner.train_step(batch)
        print(f"  Epoch {epoch+1}: Loss = {metrics['loss']:.4f}")

    # Encode samples
    test_samples = torch.randn(5, 100)
    embeddings = learner.encode(test_samples)

    print(f"\nEncoded {len(test_samples)} samples to {embeddings.shape[1]}-dim embeddings")

    # Compute similarity
    similarity = learner.compute_similarity(test_samples[:2], test_samples[2:4])
    print(f"\nSimilarity between samples: {similarity}")


# Example 7: Full Integration
def example_full_integration():
    """Example: Using the integration orchestrator"""
    from ml_intelligence.integration_orchestrator import get_ml_orchestrator

    print("\n" + "=" * 60)
    print("Example 7: Full Integration Orchestrator")
    print("=" * 60)

    orchestrator = get_ml_orchestrator()

    # 1. Trust scoring
    learning_example = {
        'input_context': 'Python list comprehension',
        'expected_output': '[x**2 for x in range(10)]',
        'source_reliability': 0.9,
        'outcome_quality': 0.85,
        'consistency_score': 0.8,
        'times_validated': 3,
        'times_invalidated': 0,
        'created_at': datetime.now()
    }

    trust_score, uncertainty = orchestrator.compute_trust_score(learning_example)
    print(f"\n1. Trust Score: {trust_score:.3f} (±{uncertainty:.3f})")

    # 2. Topic selection
    topics = [
        {"topic_id": "python_generators", "topic_name": "Python Generators"},
        {"topic_id": "python_decorators", "topic_name": "Python Decorators"},
        {"topic_id": "python_metaclasses", "topic_name": "Python Metaclasses"}
    ]

    context = {"knowledge_gaps": {"python_generators": 0.7}, "learning_velocity": 1.0}

    selected_topic = orchestrator.select_next_learning_topic(topics, context=context)
    print(f"\n2. Selected Topic: {selected_topic}")

    # 3. Meta-learning recommendations
    recommendations = orchestrator.get_learning_recommendations(
        task_type="skill_learning",
        task_metadata={"difficulty": "intermediate"}
    )
    print(f"\n3. Recommended Learning Rate: {recommendations['suggested_hyperparams']['learning_rate']:.5f}")

    # 4. Statistics
    stats = orchestrator.get_statistics()
    print(f"\n4. System Statistics:")
    print(f"   Neural trust predictions: {stats['usage_stats']['neural_trust_predictions']}")
    print(f"   Bandit selections: {stats['usage_stats']['bandit_selections']}")

    # 5. Save models
    orchestrator.save_all_models()
    print("\n5. All models saved successfully")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("ML INTELLIGENCE MODULE - COMPREHENSIVE EXAMPLES")
    print("="*60)

    try:
        example_neural_trust_scorer()
        example_bandit()
        example_meta_learning()
        example_uncertainty()
        example_active_learning()
        example_contrastive_learning()
        example_full_integration()

        print("\n" + "="*60)
        print("ALL EXAMPLES COMPLETED SUCCESSFULLY!")
        print("="*60 + "\n")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
