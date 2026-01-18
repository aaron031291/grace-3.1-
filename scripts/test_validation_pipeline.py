#!/usr/bin/env python3
"""Test the healing validation pipeline."""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from cognitive.healing_validation_pipeline import (
    HealingValidationPipeline, 
    ValidationGate,
    Patch,
    HealingRun
)
from cognitive.autonomous_healing_system import TrustLevel

def main():
    print("=" * 70)
    print("Healing Validation Pipeline Test")
    print("=" * 70)
    
    pipeline = HealingValidationPipeline()
    print("\n[OK] Pipeline initialized")
    print(f"  Available gates: {[g.value for g in ValidationGate]}")
    
    # Test 1: Snapshot/Rollback
    print("\n--- Test 1: Snapshot & Rollback ---")
    test_files = ["cognitive/code_analyzer_self_healing.py"]
    snapshot_id = pipeline.create_snapshot(test_files)
    snap_str = str(snapshot_id)[:30] if snapshot_id else "None"
    print(f"  Created snapshot: {snap_str}...")
    print(f"  Snapshots stored: {len(pipeline._snapshots)}")
    
    # Test 2: Validation gates
    print("\n--- Test 2: Validation Gates ---")
    
    # Syntax check
    passed, results = pipeline.validate([ValidationGate.SYNTAX_CHECK], test_files)
    print(f"  SYNTAX_CHECK: {'PASSED' if passed else 'FAILED'}")
    
    # Lint check (if available)
    passed, results = pipeline.validate([ValidationGate.LINT_CHECK], test_files)
    print(f"  LINT_CHECK: {'PASSED' if passed else 'FAILED (or not installed)'}")
    
    # Test 3: Trust level enforcement
    print("\n--- Test 3: Trust Level Enforcement ---")
    for level in [TrustLevel.SUGGEST_ONLY, TrustLevel.LOW_RISK_AUTO, TrustLevel.HIGH_RISK_AUTO]:
        required = pipeline.get_required_gates_for_trust_level(level.value)
        print(f"  {level.name}: {[g.value for g in required]}")
    
    # Test 4: Healing run tracking
    print("\n--- Test 4: Healing Run Creation ---")
    run = HealingRun(
        run_id="TEST-001",
        started_at=datetime.utcnow(),
        detected_issues=[{"id": "G012", "file": "test.py"}],
        trust_level=TrustLevel.MEDIUM_RISK_AUTO.value,
    )
    print(f"  Created HealingRun: {run.run_id}")
    print(f"  Status: {run.overall_result}")
    print(f"  Trust level: {run.trust_level}")
    
    print("\n" + "=" * 70)
    print("All tests complete!")
    print("=" * 70)

if __name__ == "__main__":
    main()
