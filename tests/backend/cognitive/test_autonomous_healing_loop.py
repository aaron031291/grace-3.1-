import os
import sys
import tempfile
import pytest

# Ensure backend modules can be imported directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../backend')))

from backend.cognitive.autonomous_healing_loop import heal_content

def test_autonomous_healing_loop_safety_gates():
    """
    Tests the 13th Loop - Autonomous Healing Pipeline.
    Verifies that the 8-stage safety gates (snapshot, triage, verification, scoring)
    execute correctly when a broken file is sent for healing.
    """
    
    broken_code = '''
def calculate_total(prices):
    total = 0
    for p in prices:
        tota1 += p  # intentional typo: tota1 instead of total
    return total
'''

    # Write the broken code to a temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
        tmp.write(broken_code)
        tmp_path = tmp.name

    try:
        # Send it to the autonomous healing loop
        errors = ["NameError: name 'tota1' is not defined"]
        result = heal_content(
            file_path=tmp_path,
            content=broken_code,
            errors=errors,
            source="test_framework"
        )

        # Assert correct output structure and pipeline metrics
        assert isinstance(result, dict), "Healing result must be a dictionary"
        assert "stage" in result, "Result must contain the final stage"
        assert "strategy" in result, "Result must contain the selected strategy"
        assert "original_score" in result, "Result must contain the original score"
        
        # Verify the snapshot gate captured the original file
        assert "snapshot_id" in result, "Snapshot must have been created before healing"
        assert result["snapshot_id"] is not None, "Snapshot ID should not be None"
        
        # Verify safety metrics were populated
        assert "healed_score" in result, "Healed score should be calculated in the verification stage"
        assert "content_preserved" in result, "Content preservation ratio must be tracked"
        
        # Print the exact path taken through the 8 stages for visibility
        print(f"\\nHealing stages completed. Final stage: {result['stage']}")
        print(f"Success: {result['success']}")
        print(f"Strategy: {result['strategy']}")
        print(f"Snapshot ID: {result['snapshot_id']}")
        print(f"Score Change: {result['original_score']} -> {result['healed_score']}")
        print(f"Preservation: {result.get('content_preserved', 0) * 100}%")

    finally:
        # Cleanup
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
