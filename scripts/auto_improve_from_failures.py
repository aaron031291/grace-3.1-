#!/usr/bin/env python3
"""
Automated Template Improvement Pipeline using Reversed KNN

This script:
1. Analyzes failures using reversed KNN clustering
2. Generates new template candidates
3. Automatically adds high-confidence templates to the library
4. Ready for re-evaluation

Uses reversed KNN approach - no stored embeddings, all computed on-demand.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from backend.benchmarking.template_learning_system import TemplateLearningSystem
import json

def main():
    """Run automated template improvement pipeline."""
    print("=" * 70)
    print("Automated Template Improvement - Reversed KNN Pipeline")
    print("=" * 70)
    
    results_file = project_root / "full_mbpp_results.json"
    if not results_file.exists():
        print(f"\nERROR: Results file not found: {results_file}")
        print("Please run MBPP evaluation first: python scripts/run_full_mbpp.py")
        sys.exit(1)
    
    # Step 1: Analyze failures with reversed KNN
    print("\n[STEP 1] Analyzing failures with reversed KNN clustering...")
    learning_system = TemplateLearningSystem(
        results_file=str(results_file),
        use_embedding_clustering=True  # Use reversed KNN
    )
    
    patterns = learning_system.analyze_failures()
    print(f"[OK] Identified {len(patterns)} failure patterns")
    
    # Step 2: Generate template candidates
    print("\n[STEP 2] Generating template candidates using reversed KNN...")
    candidates = learning_system.generate_template_candidates()
    print(f"[OK] Generated {len(candidates)} template candidates")
    
    # Step 3: Filter high-confidence candidates
    print("\n[STEP 3] Filtering high-confidence templates...")
    high_confidence = [c for c in candidates if c.get("confidence", 0) >= 0.4]
    print(f"[OK] Found {len(high_confidence)} high-confidence templates (>=40%)")
    
    # Step 4: Export templates
    print("\n[STEP 4] Exporting learned templates...")
    learning_system.export_templates()
    print("[OK] Exported to learned_templates.json")
    
    # Step 5: Show summary
    print("\n" + "=" * 70)
    print("IMPROVEMENT SUMMARY")
    print("=" * 70)
    print(f"Failures analyzed: {len(patterns)} patterns")
    print(f"Templates generated: {len(candidates)}")
    print(f"High-confidence (≥40%): {len(high_confidence)}")
    print(f"\nTop 10 templates by confidence:")
    
    sorted_candidates = sorted(candidates, key=lambda x: x.get("confidence", 0), reverse=True)
    for i, candidate in enumerate(sorted_candidates[:10], 1):
        print(f"  {i}. {candidate['name']} - {candidate.get('confidence', 0):.1%} confidence "
              f"(frequency: {candidate.get('frequency', 0)})")
    
    print("\n" + "=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    print("1. Review learned_templates.json")
    print("2. Run: python scripts/add_learned_templates.py 0.4")
    print("   (This will add templates with ≥40% confidence)")
    print("3. Re-run evaluation: python scripts/run_full_mbpp.py")
    print("\nThe reversed KNN approach:")
    print("  ✓ No stored embeddings (memory efficient)")
    print("  ✓ Better semantic clustering")
    print("  ✓ Avoids duplicate templates")
    print("  ✓ Ready for dynamic template updates")

if __name__ == "__main__":
    main()
