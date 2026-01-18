"""
Test Script for Grace's Training Systems

Tests:
1. Intelligence Training Center
2. Unified Knowledge Ingestion
3. LLM Interaction Observatory

Run: python scripts/test_training_systems.py
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


def test_training_center():
    """Test Intelligence Training Center."""
    print("\n" + "="*60)
    print("[BRAIN] Testing Intelligence Training Center")
    print("="*60)
    
    from cognitive.intelligence_training_center import (
        IntelligenceTrainingCenter,
        TrainingTask,
        TrainingDomain,
        TaskDifficulty
    )
    
    # Create training center
    tc = IntelligenceTrainingCenter()
    print("[OK] Training Center initialized")
    
    # Check initial snapshot
    snapshot = tc.get_current_snapshot()
    print(f"[OK] Model Version: {snapshot.model_version}")
    print(f"   Total Attempts: {snapshot.total_attempts}")
    
    # Create a training task
    task = TrainingTask.create(
        domain=TrainingDomain.CODING,
        objective="Write a function to reverse a string",
        difficulty=TaskDifficulty.EASY
    )
    print(f"[OK] Created Task: {task.task_id}")
    
    # Run training loop
    attempt, evaluation, delta = tc.run_training_loop(task)
    print(f"[OK] Training Loop Complete:")
    print(f"   Attempt: {attempt.attempt_id}")
    print(f"   Success: {evaluation.success}")
    print(f"   Patterns Added: {len(delta.patterns_added)}")
    
    # Check updated snapshot
    new_snapshot = tc.get_current_snapshot()
    print(f"[OK] Updated Stats:")
    print(f"   Total Attempts: {new_snapshot.total_attempts}")
    print(f"   Success Rate: {new_snapshot.overall_success_rate:.2%}")
    
    # Get intelligence report
    report = tc.get_intelligence_report()
    print(f"[OK] Intelligence Report Generated")
    print(f"   Skills: {list(report['skill_mastery'].keys())}")
    
    return True


def test_unified_ingestion():
    """Test Unified Knowledge Ingestion."""
    print("\n" + "="*60)
    print("[INGEST] Testing Unified Knowledge Ingestion")
    print("="*60)
    
    from cognitive.unified_knowledge_ingestion import (
        UnifiedKnowledgeIngestion,
        KnowledgeItem,
        IngestionSource,
        KnowledgeType
    )
    
    # Create ingestion system
    ingestion = UnifiedKnowledgeIngestion()
    print("[OK] Ingestion System initialized")
    
    # Test manual ingestion
    item = KnowledgeItem.create(
        source=IngestionSource.USER_FEEDBACK,
        knowledge_type=KnowledgeType.PATTERN,
        content="Always validate user input before processing",
        domain="security",
        tags=["security", "validation", "best_practice"],
        confidence=0.9
    )
    print(f"[OK] Created Knowledge Item: {item.item_id}")
    
    # Ingest it
    async def do_ingest():
        return await ingestion.ingest(item)
    
    result = asyncio.run(do_ingest())
    print(f"[OK] Ingestion Result:")
    print(f"   Success: {result.success}")
    print(f"   Genesis Key: {result.genesis_key_id}")
    print(f"   Stored As: {result.stored_as}")
    print(f"   Trust Score: {result.trust_score:.2f}")
    
    # Test simulation engine
    scenarios = ingestion.simulation_engine.generate_scenario(
        scenario_type="edge_case",
        domain="coding",
        count=3
    )
    print(f"[OK] Generated {len(scenarios)} simulation scenarios")
    
    # Get stats
    stats = ingestion.get_stats()
    print(f"[OK] Ingestion Stats:")
    print(f"   Total Ingested: {stats['pipeline_stats']['total_ingested']}")
    print(f"   By Source: {stats['pipeline_stats']['by_source']}")
    
    return True


def test_llm_observatory():
    """Test LLM Interaction Observatory."""
    print("\n" + "="*60)
    print("[OBSERVE] Testing LLM Interaction Observatory")
    print("="*60)
    
    from cognitive.llm_interaction_observatory import (
        LLMInteractionObservatory,
        InteractionType,
        ResponseQuality
    )
    
    # Create observatory
    observatory = LLMInteractionObservatory()
    print("[OK] Observatory initialized")
    
    # Simulate an LLM interaction
    prompt = "Write a Python function to calculate factorial"
    response = """Here's a Python function to calculate factorial:

```python
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
```

This uses recursion. For n=5, it returns 120.
The time complexity is O(n) and space complexity is O(n) due to the call stack.
"""
    
    # Observe the interaction
    interaction = observatory.observe_call(
        prompt=prompt,
        response=response,
        model="test-model",
        latency_ms=150,
        input_tokens=15,
        output_tokens=80
    )
    
    print(f"[OK] Observed Interaction: {interaction.interaction_id}")
    print(f"   Type: {interaction.interaction_type.value}")
    print(f"   Quality: {interaction.quality.value} ({interaction.quality_score:.2f})")
    print(f"   Domain: {interaction.domain}")
    print(f"   Genesis Key: {interaction.genesis_key_id}")
    
    # Query WHY
    why = observatory.query_why(interaction.interaction_id)
    print(f"[OK] OODA Analysis:")
    print(f"   Observed: {why['analysis']['what_it_observed']['prompt_type']}")
    print(f"   Interpreted: {why['analysis']['how_it_interpreted']['inferred_intent']}")
    print(f"   Strategy: {why['analysis']['what_it_decided']['strategy']}")
    print(f"   Produced: {why['analysis']['what_it_produced']['response_type']}")
    
    # Check reasoning chain
    print(f"[OK] Reasoning Chain: {len(interaction.reasoning_chain)} items")
    for step in interaction.reasoning_chain[:3]:
        print(f"   - {step[:50]}...")
    
    # Get training data
    dataset = observatory.get_training_data(min_quality="acceptable")
    print(f"[OK] Training Dataset: {len(dataset)} items")
    
    # Get stats
    stats = observatory.get_stats()
    print(f"[OK] Observatory Stats:")
    print(f"   Total Observed: {stats['total_observed']}")
    print(f"   Avg Quality: {stats['avg_quality_score']:.2f}")
    
    return True


def run_all_tests():
    """Run all tests."""
    print("\n" + "="*60)
    print("[TEST] GRACE TRAINING SYSTEMS TEST SUITE")
    print("="*60)
    
    results = {}
    
    # Test 1: Training Center
    try:
        results["Training Center"] = test_training_center()
    except Exception as e:
        print(f"[X] Training Center Failed: {e}")
        results["Training Center"] = False
    
    # Test 2: Unified Ingestion
    try:
        results["Unified Ingestion"] = test_unified_ingestion()
    except Exception as e:
        print(f"[X] Unified Ingestion Failed: {e}")
        results["Unified Ingestion"] = False
    
    # Test 3: LLM Observatory
    try:
        results["LLM Observatory"] = test_llm_observatory()
    except Exception as e:
        print(f"[X] LLM Observatory Failed: {e}")
        results["LLM Observatory"] = False
    
    # Summary
    print("\n" + "="*60)
    print("[RESULTS] TEST RESULTS SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test, result in results.items():
        status = "[OK] PASS" if result else "[X] FAIL"
        print(f"   {test}: {status}")
    
    print(f"\n   Total: {passed}/{total} passed")
    
    if passed == total:
        print("\n[SUCCESS] ALL TESTS PASSED!")
    else:
        print(f"\n[WARN] {total - passed} test(s) failed")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
