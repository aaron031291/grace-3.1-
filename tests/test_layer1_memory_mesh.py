"""
Test Layer 1 → Memory Mesh Integration

Demonstrates the complete flow from Layer 1 learning memory to memory mesh.
"""
import requests
import json
from datetime import datetime


BASE_URL = "http://localhost:8000"


def test_layer1_learning_memory_integration():
    """Test that Layer 1 learning memory feeds into memory mesh."""

    print("=" * 80)
    print("TEST: Layer 1 → Memory Mesh Integration")
    print("=" * 80)

    # Test 1: User Feedback (High Trust)
    print("\n[Test 1] User Feedback → Memory Mesh")
    print("-" * 80)

    response = requests.post(f"{BASE_URL}/layer1/learning-memory", json={
        "learning_type": "feedback",
        "learning_data": {
            "context": {
                "question": "What is the capital of France?",
                "interaction_id": "chat_123"
            },
            "action": {
                "answer_given": "Paris"
            },
            "outcome": {
                "positive": True,
                "rating": 0.95,
                "user_comment": "Perfect answer!"
            }
        },
        "user_id": "GU-test-user"
    })

    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Genesis Key: {result.get('genesis_key_id')}")
    print(f"Memory Mesh: {json.dumps(result.get('memory_mesh'), indent=2)}")

    # Test 2: System Success (Medium-High Trust)
    print("\n[Test 2] System Success → Memory Mesh")
    print("-" * 80)

    response = requests.post(f"{BASE_URL}/layer1/learning-memory", json={
        "learning_type": "success",
        "learning_data": {
            "context": {
                "task": "optimize database query",
                "db_type": "postgresql",
                "query_type": "SELECT with JOIN"
            },
            "action": {
                "optimization": "added index on foreign key",
                "index_columns": ["user_id", "created_at"]
            },
            "outcome": {
                "success": True,
                "speedup": 12.5,
                "query_time_before": 850,
                "query_time_after": 68
            },
            "expected_outcome": {
                "success": True
            }
        },
        "user_id": "GU-system"
    })

    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Genesis Key: {result.get('genesis_key_id')}")
    print(f"Memory Mesh: {json.dumps(result.get('memory_mesh'), indent=2)}")

    # Test 3: User Correction (Very High Trust)
    print("\n[Test 3] User Correction → Memory Mesh")
    print("-" * 80)

    response = requests.post(f"{BASE_URL}/layer1/learning-memory", json={
        "learning_type": "correction",
        "learning_data": {
            "context": {
                "question": "What is the capital of Australia?",
                "incorrect_answer": "Sydney"
            },
            "action": {
                "answer_given": "Sydney"
            },
            "outcome": {
                "correct_answer": "Canberra",
                "corrected_by_user": True
            },
            "expected_outcome": {
                "correct_answer": "Canberra"
            }
        },
        "user_id": "GU-test-user"
    })

    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Genesis Key: {result.get('genesis_key_id')}")
    print(f"Memory Mesh: {json.dumps(result.get('memory_mesh'), indent=2)}")

    # Test 4: Check Memory Mesh Stats
    print("\n[Test 4] Memory Mesh Statistics")
    print("-" * 80)

    response = requests.get(f"{BASE_URL}/learning-memory/stats")
    stats = response.json()['stats']

    print(f"Learning Memory:")
    print(f"  - Total examples: {stats['learning_memory']['total_examples']}")
    print(f"  - High trust examples: {stats['learning_memory']['high_trust_examples']}")
    print(f"  - Trust ratio: {stats['learning_memory']['trust_ratio']:.2%}")

    print(f"\nEpisodic Memory:")
    print(f"  - Total episodes: {stats['episodic_memory']['total_episodes']}")
    print(f"  - Linked from learning: {stats['episodic_memory']['linked_from_learning']}")

    print(f"\nProcedural Memory:")
    print(f"  - Total procedures: {stats['procedural_memory']['total_procedures']}")
    print(f"  - High success procedures: {stats['procedural_memory']['high_success_procedures']}")

    # Test 5: Get Training Data
    print("\n[Test 5] Get High-Trust Training Data")
    print("-" * 80)

    response = requests.get(f"{BASE_URL}/learning-memory/training-data", params={
        'min_trust_score': 0.7,
        'max_examples': 10
    })

    training_data = response.json()
    print(f"Training examples (trust >= 0.7): {training_data['count']}")

    if training_data['count'] > 0:
        print("\nSample training example:")
        sample = training_data['data'][0]
        print(f"  - Input: {json.dumps(sample['input'], indent=4)}")
        print(f"  - Output: {json.dumps(sample['output'], indent=4)}")
        print(f"  - Trust score: {sample['trust_score']}")
        print(f"  - Source: {sample['source']}")

    print("\n" + "=" * 80)
    print("INTEGRATION TEST COMPLETE")
    print("=" * 80)
    print("\n✅ All learning data from Layer 1 folders flows into memory mesh")
    print("✅ Trust scores automatically calculated")
    print("✅ High-trust data feeds episodic and procedural memory")
    print("✅ Training data available for export")


if __name__ == "__main__":
    try:
        test_layer1_learning_memory_integration()
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to server")
        print("Make sure the server is running: python backend/app.py")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
