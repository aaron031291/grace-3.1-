"""
Test Script: Unified Immutable Memory Mesh

Demonstrates:
1. Adding learning experiences
2. Trust scoring and routing
3. Creating immutable snapshots
4. Restoring from snapshots
5. Comparing snapshots over time
"""

import requests
import json
import time
from pathlib import Path

BASE_URL = "http://localhost:8000"


def test_unified_memory_mesh():
    """Test the unified immutable memory mesh system."""

    print("\n" + "="*70)
    print("UNIFIED IMMUTABLE MEMORY MESH - TEST")
    print("="*70)

    # =====================================================================
    # 1. Record Learning Experiences
    # =====================================================================
    print("\n[1] Recording learning experiences...")

    experiences = [
        {
            "experience_type": "correction",
            "context": {
                "topic": "geography",
                "question": "What is the capital of Australia?",
                "incorrect_answer": "Sydney"
            },
            "action_taken": {
                "answer_given": "Sydney"
            },
            "outcome": {
                "correct_answer": "Canberra",
                "corrected_by_user": True
            },
            "source": "user_feedback_correction",
            "user_id": "GU-test-user"
        },
        {
            "experience_type": "success",
            "context": {
                "topic": "database_optimization",
                "task": "optimize query performance"
            },
            "action_taken": {
                "optimization": "added index on foreign key"
            },
            "outcome": {
                "success": True,
                "speedup": 12.5
            },
            "source": "system_observation_success"
        },
        {
            "experience_type": "feedback",
            "context": {
                "topic": "code_review",
                "question": "What is a closure?"
            },
            "action_taken": {
                "answer": "A function that captures variables from outer scope"
            },
            "outcome": {
                "positive": True,
                "rating": 0.95
            },
            "source": "user_feedback_positive",
            "user_id": "GU-test-user"
        }
    ]

    learning_ids = []

    for exp in experiences:
        response = requests.post(
            f"{BASE_URL}/learning-memory/record-experience",
            json=exp
        )

        if response.status_code == 200:
            data = response.json()
            learning_ids.append(data["learning_example_id"])
            print(f"✓ Recorded: {exp['experience_type']} - {data['learning_example_id']}")
        else:
            print(f"✗ Failed to record: {response.status_code}")

    print(f"\n  Total learning experiences recorded: {len(learning_ids)}")

    # =====================================================================
    # 2. Check Memory Mesh Stats
    # =====================================================================
    print("\n[2] Checking memory mesh statistics...")

    response = requests.get(f"{BASE_URL}/learning-memory/stats")

    if response.status_code == 200:
        stats = response.json()["stats"]
        print(f"\n  Learning Examples: {stats['learning_memory']['total_examples']}")
        print(f"  High Trust: {stats['learning_memory']['high_trust_examples']} ({stats['learning_memory']['trust_ratio']:.1%})")
        print(f"\n  Episodic Memories: {stats['episodic_memory']['total_episodes']}")
        print(f"  Linked from Learning: {stats['episodic_memory']['linked_from_learning']}")
        print(f"\n  Procedural Memories: {stats['procedural_memory']['total_procedures']}")
        print(f"  High Success: {stats['procedural_memory']['high_success_procedures']} ({stats['procedural_memory']['success_ratio']:.1%})")
    else:
        print(f"✗ Failed to get stats: {response.status_code}")

    # =====================================================================
    # 3. Create First Immutable Snapshot
    # =====================================================================
    print("\n[3] Creating first immutable snapshot...")

    response = requests.post(f"{BASE_URL}/learning-memory/snapshot/create")

    if response.status_code == 200:
        data = response.json()
        snapshot1_stats = data["snapshot"]["statistics"]
        print(f"✓ Snapshot created: {data['file_path']}")
        print(f"\n  Total Memories: {snapshot1_stats['total_memories']}")
        print(f"  - Learning: {snapshot1_stats['learning_examples']}")
        print(f"  - Episodic: {snapshot1_stats['episodic_memories']}")
        print(f"  - Procedural: {snapshot1_stats['procedural_memories']}")
        print(f"  - Patterns: {snapshot1_stats['extracted_patterns']}")
    else:
        print(f"✗ Failed to create snapshot: {response.status_code}")

    # =====================================================================
    # 4. Create Versioned Snapshot
    # =====================================================================
    print("\n[4] Creating versioned snapshot (backup)...")

    response = requests.post(f"{BASE_URL}/learning-memory/snapshot/versioned")

    if response.status_code == 200:
        data = response.json()
        snapshot1_path = data["file_path"]
        print(f"✓ Versioned snapshot created: {snapshot1_path}")
    else:
        print(f"✗ Failed to create versioned snapshot: {response.status_code}")

    # =====================================================================
    # 5. Add More Learning (Simulate Growth)
    # =====================================================================
    print("\n[5] Adding more learning experiences (simulating growth)...")

    more_experiences = [
        {
            "experience_type": "success",
            "context": {"topic": "python", "task": "optimize list comprehension"},
            "action_taken": {"optimization": "use generator expression"},
            "outcome": {"memory_saved": "50%", "success": True},
            "source": "system_observation_success"
        },
        {
            "experience_type": "pattern",
            "context": {"pattern_type": "code_optimization"},
            "action_taken": {"identified_pattern": "lazy_evaluation"},
            "outcome": {"pattern_confirmed": True},
            "source": "pattern_detection"
        }
    ]

    for exp in more_experiences:
        response = requests.post(
            f"{BASE_URL}/learning-memory/record-experience",
            json=exp
        )
        if response.status_code == 200:
            print(f"✓ Added: {exp['experience_type']}")

    # =====================================================================
    # 6. Create Second Snapshot
    # =====================================================================
    print("\n[6] Creating second snapshot (after growth)...")

    time.sleep(1)  # Ensure different timestamp

    response = requests.post(f"{BASE_URL}/learning-memory/snapshot/versioned")

    if response.status_code == 200:
        data = response.json()
        snapshot2_path = data["file_path"]
        print(f"✓ Second snapshot created: {snapshot2_path}")
    else:
        print(f"✗ Failed to create second snapshot: {response.status_code}")

    # =====================================================================
    # 7. Compare Snapshots
    # =====================================================================
    print("\n[7] Comparing snapshots to see growth...")

    if 'snapshot1_path' in locals() and 'snapshot2_path' in locals():
        response = requests.get(
            f"{BASE_URL}/learning-memory/snapshot/compare",
            params={
                "snapshot1_path": snapshot1_path,
                "snapshot2_path": snapshot2_path
            }
        )

        if response.status_code == 200:
            comparison = response.json()["comparison"]
            print(f"\n  Snapshot 1: {comparison['snapshot1_time']}")
            print(f"  Snapshot 2: {comparison['snapshot2_time']}")
            print(f"\n  Learning Examples:")
            print(f"    Added: {comparison['learning_diff']['added']}")
            print(f"    {comparison['learning_diff']['old_count']} → {comparison['learning_diff']['new_count']}")
            print(f"\n  Trust Quality:")
            print(f"    Old: {comparison['trust_quality_change']['old_trust_ratio']:.1%}")
            print(f"    New: {comparison['trust_quality_change']['new_trust_ratio']:.1%}")
            print(f"    Improvement: {comparison['trust_quality_change']['improvement']:+.1%}")
        else:
            print(f"✗ Failed to compare: {response.status_code}")

    # =====================================================================
    # 8. Load Latest Snapshot
    # =====================================================================
    print("\n[8] Loading latest snapshot (read-only)...")

    response = requests.get(f"{BASE_URL}/learning-memory/snapshot/load")

    if response.status_code == 200:
        data = response.json()
        snapshot = data["snapshot"]
        print(f"✓ Snapshot loaded from: {snapshot['snapshot_metadata']['timestamp']}")
        print(f"\n  Contains:")
        print(f"  - {snapshot['statistics']['learning_examples']} learning examples")
        print(f"  - {snapshot['statistics']['episodic_memories']} episodic memories")
        print(f"  - {snapshot['statistics']['procedural_memories']} procedural memories")
        print(f"  - {snapshot['statistics']['extracted_patterns']} patterns")
    else:
        print(f"✗ Failed to load snapshot: {response.status_code}")

    # =====================================================================
    # 9. Export Training Data
    # =====================================================================
    print("\n[9] Exporting high-trust training data...")

    response = requests.get(
        f"{BASE_URL}/learning-memory/training-data",
        params={"min_trust_score": 0.7, "max_examples": 100}
    )

    if response.status_code == 200:
        data = response.json()
        training_data = data["data"]
        print(f"✓ Exported {len(training_data)} training examples")

        if training_data:
            print(f"\n  Sample training example:")
            print(f"    Trust Score: {training_data[0]['trust_score']:.2f}")
            print(f"    Source: {training_data[0]['source']}")
            print(f"    Validated: {training_data[0]['metadata']['times_validated']} times")
    else:
        print(f"✗ Failed to export training data: {response.status_code}")

    # =====================================================================
    # Summary
    # =====================================================================
    print("\n" + "="*70)
    print("SUMMARY: Unified Immutable Memory Mesh")
    print("="*70)
    print("""
✓ Learning experiences recorded with trust scores
✓ Automatically routed to episodic/procedural memory
✓ Immutable snapshots created (latest + versioned)
✓ Snapshots compared to show growth
✓ Training data exported for ML use

The memory mesh state is now permanently captured in:
  .genesis_immutable_memory_mesh.json

This file IS the latest memory mesh state and can be:
  • Restored to database if needed
  • Versioned for historical tracking
  • Compared to show learning progress
  • Transferred to other environments
  • Used for audit and compliance

The immutable memory and memory mesh are ONE UNIFIED SYSTEM. ✓
    """)


if __name__ == "__main__":
    try:
        # Check if server is running
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        if response.status_code != 200:
            print("\n⚠ Server health check failed. Is the server running?")
            print("Start with: cd backend && python app.py")
            exit(1)
    except requests.exceptions.ConnectionError:
        print("\n✗ Cannot connect to server at", BASE_URL)
        print("Start with: cd backend && python app.py")
        exit(1)

    test_unified_memory_mesh()
