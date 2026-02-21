"""
Test Grace's Active Learning Workflow

Tests the complete Study → Practice → Learn cycle:
1. Grace studies a topic from training materials
2. Grace practices the skill
3. Check skill assessment to see improvement
"""

import requests
import json
from datetime import datetime


BASE_URL = "http://localhost:5001"


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def test_study_phase():
    """Test Grace studying a topic."""
    print_section("PHASE 1: STUDY - Grace learns from training materials")

    payload = {
        "topic": "Python programming",
        "learning_objectives": [
            "Learn function syntax",
            "Understand parameters and return values",
            "Learn about decorators"
        ],
        "max_materials": 5
    }

    print("Request:")
    print(json.dumps(payload, indent=2))
    print("\nSending POST /training/study...")

    try:
        response = requests.post(f"{BASE_URL}/training/study", json=payload, timeout=30)

        if response.status_code == 200:
            result = response.json()
            print("\n[OK] Study phase completed!")
            print(f"\nMaterials studied: {result.get('materials_studied', 0)}")
            print(f"Concepts learned: {result.get('concepts_learned', 0)}")
            print(f"Examples stored: {result.get('examples_stored', 0)}")
            print(f"Average trust score: {result.get('average_trust_score', 0):.2f}")

            if 'focus_areas' in result:
                print("\nFocus areas identified:")
                for area in result['focus_areas']:
                    print(f"  - {area}")

            return True
        else:
            print(f"\n[ERROR] Study failed: {response.status_code}")
            print(response.text)
            return False

    except requests.exceptions.ConnectionError:
        print("\n[ERROR] Could not connect to Grace API. Is the server running?")
        print("Start the server with: python app.py")
        return False
    except Exception as e:
        print(f"\n[ERROR] Study phase failed: {e}")
        return False


def test_practice_phase():
    """Test Grace practicing a skill."""
    print_section("PHASE 2: PRACTICE - Grace applies knowledge in sandbox")

    payload = {
        "skill_name": "Python programming",
        "task_description": "Write a simple function to calculate factorial",
        "task_requirements": [
            "Handle edge cases (0 and 1)",
            "Use recursion or iteration"
        ],
        "complexity": 0.4,
        "sandbox_context": {
            "language": "python",
            "allow_imports": ["math"]
        }
    }

    print("Request:")
    print(json.dumps(payload, indent=2))
    print("\nSending POST /training/practice...")

    try:
        response = requests.post(f"{BASE_URL}/training/practice", json=payload, timeout=30)

        if response.status_code == 200:
            result = response.json()
            print("\n[OK] Practice phase completed!")
            print(f"\nTask: {result.get('task', {}).get('description')}")
            print(f"Approach: {result.get('approach', {}).get('strategy', 'unknown')}")
            print(f"Outcome: {'SUCCESS' if result.get('outcome', {}).get('success') else 'FAILED'}")
            print(f"Feedback: {result.get('outcome', {}).get('feedback', 'N/A')}")

            if 'learned' in result:
                print("\nWhat Grace learned:")
                for item in result['learned']:
                    print(f"  - {item}")

            return True
        else:
            print(f"\n[ERROR] Practice failed: {response.status_code}")
            print(response.text)
            return False

    except Exception as e:
        print(f"\n[ERROR] Practice phase failed: {e}")
        return False


def test_skill_assessment():
    """Test getting Grace's skill assessment."""
    print_section("PHASE 3: ASSESSMENT - Check Grace's proficiency")

    skill_name = "Python programming"
    print(f"Getting skill assessment for: {skill_name}")
    print(f"\nSending GET /training/skills/{skill_name}...")

    try:
        response = requests.get(f"{BASE_URL}/training/skills/{skill_name.replace(' ', '%20')}", timeout=10)

        if response.status_code == 200:
            result = response.json()
            print("\n[OK] Skill assessment retrieved!")
            print(f"\nSkill: {result.get('skill', 'N/A')}")
            print(f"Level: {result.get('level', 'N/A')}")
            print(f"Proficiency score: {result.get('proficiency_score', 0):.2f}")
            print(f"Success rate: {result.get('success_rate', 0) * 100:.1f}%")
            print(f"Tasks completed: {result.get('tasks_completed', 0)}")
            print(f"Practice hours: {result.get('practice_hours', 0):.1f}")
            print(f"Operational confidence: {result.get('operational_confidence', 0):.2f}")

            return True
        else:
            print(f"\n[ERROR] Assessment failed: {response.status_code}")
            print(response.text)
            return False

    except Exception as e:
        print(f"\n[ERROR] Assessment failed: {e}")
        return False


def test_learning_progress():
    """Test getting overall learning progress."""
    print_section("OVERALL PROGRESS - Grace's learning statistics")

    print("Sending GET /training/analytics/progress...")

    try:
        response = requests.get(f"{BASE_URL}/training/analytics/progress", timeout=10)

        if response.status_code == 200:
            result = response.json()
            print("\n[OK] Learning progress retrieved!")
            print(f"\nTotal skills: {result.get('total_skills', 0)}")
            print(f"Total tasks completed: {result.get('total_tasks_completed', 0)}")
            print(f"Overall success rate: {result.get('overall_success_rate', 0) * 100:.1f}%")

            if 'skills' in result and result['skills']:
                print("\nSkill breakdown:")
                for skill in result['skills']:
                    print(f"  - {skill['skill']}: {skill['level']} (proficiency: {skill['proficiency']:.2f})")

            return True
        else:
            print(f"\n[ERROR] Progress check failed: {response.status_code}")
            print(response.text)
            return False

    except Exception as e:
        print(f"\n[ERROR] Progress check failed: {e}")
        return False


def main():
    """Run complete training workflow test."""
    print("\n" + "=" * 80)
    print("  GRACE ACTIVE LEARNING SYSTEM - Workflow Test")
    print("  Testing Study > Practice > Learn Cycle")
    print("=" * 80)
    print(f"\nTimestamp: {datetime.now().isoformat()}")
    print(f"API URL: {BASE_URL}")

    # Test complete workflow
    results = {
        "study": test_study_phase(),
        "practice": test_practice_phase(),
        "assessment": test_skill_assessment(),
        "progress": test_learning_progress()
    }

    # Summary
    print_section("TEST SUMMARY")
    print("Results:")
    for phase, success in results.items():
        status = "[OK]" if success else "[FAILED]"
        print(f"  {status} {phase.capitalize()}")

    total_tests = len(results)
    passed_tests = sum(1 for success in results.values() if success)

    print(f"\nTests passed: {passed_tests}/{total_tests}")

    if passed_tests == total_tests:
        print("\n[SUCCESS] All tests passed! Grace's learning system is operational.")
    else:
        print(f"\n[PARTIAL] {total_tests - passed_tests} test(s) failed. Check errors above.")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
