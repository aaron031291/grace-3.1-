#!/usr/bin/env python3
"""
Fill Knowledge Gaps using Reverse KNN.

This script:
1. Detects knowledge gaps from failed healing attempts
2. Uses reverse KNN to find similar problems
3. Learns solutions from external sources
4. Creates fix patterns to fill gaps
"""
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

import logging
import json
from cognitive.gap_filler import get_gap_filler
from cognitive.gap_detector import get_gap_detector

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def find_gaps_from_healing_results(results_path: str = "backend/tests/healing_results.json"):
    """Find knowledge gaps from healing results."""
    gaps = []
    
    try:
        with open(results_path) as f:
            results = json.load(f)
        
        gap_detector = get_gap_detector()
        
        # Extract failed actions
        for action in results.get("healing_actions", []):
            execution = action.get("execution_results", {})
            
            # Failed actions
            for failed in execution.get("failed", []):
                error_msg = failed.get("error", "") or failed.get("message", "")
                if error_msg:
                    gap = gap_detector.detect_gap(error_msg, attempted_fixes=[])
                    if gap:
                        gaps.append(gap)
            
            # Anomalies that couldn't be fixed
            anomaly = action.get("anomaly", {})
            error_msg = anomaly.get("error_message", "") or anomaly.get("details", "")
            if error_msg:
                gap = gap_detector.detect_gap(error_msg, attempted_fixes=[])
                if gap:
                    gaps.append(gap)
    
    except Exception as e:
        logger.error(f"Error finding gaps: {e}")
    
    return gaps


def main():
    """Main gap filling process."""
    logger.info("=" * 80)
    logger.info("GRACE KNOWLEDGE GAP FILLING (REVERSE KNN)")
    logger.info("=" * 80)
    logger.info("")
    
    # Step 1: Find gaps
    logger.info("Step 1: Finding knowledge gaps...")
    gaps = find_gaps_from_healing_results()
    logger.info(f"Found {len(gaps)} knowledge gaps")
    logger.info("")
    
    if not gaps:
        logger.info("No gaps found. Grace's knowledge is complete!")
        return
    
    # Step 2: Fill gaps using reverse KNN
    logger.info("Step 2: Filling gaps using reverse KNN...")
    gap_filler = get_gap_filler()
    
    filled = []
    for i, gap in enumerate(gaps, 1):
        logger.info(f"Filling gap {i}/{len(gaps)}: {gap.error_message[:80]}...")
        result = gap_filler.fill_gap(gap.error_message, gap.attempted_fixes, k=5)
        
        if result.get("success"):
            filled.append(result)
            logger.info(f"  ✓ Filled! Found {result['similar_problems_found']} similar problems")
            logger.info(f"    Confidence: {result['confidence']:.2f}")
        else:
            logger.info(f"  ✗ Could not fill: {result.get('reason')}")
        logger.info("")
    
    # Summary
    logger.info("=" * 80)
    logger.info("GAP FILLING COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Gaps found: {len(gaps)}")
    logger.info(f"Gaps filled: {len(filled)}")
    logger.info("")
    
    if filled:
        logger.info("New fix patterns created:")
        for result in filled:
            pattern = result['fix_pattern']
            logger.info(f"  - {pattern['issue_type']} (confidence: {pattern['confidence']:.2f})")
            logger.info(f"    Sources: {', '.join(pattern['sources'])}")
        logger.info("")
        logger.info("These patterns can be added to the knowledge base!")
    
    # Save results
    results = {
        "gaps_found": len(gaps),
        "gaps_filled": len(filled),
        "filled_gaps": filled,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    results_file = backend_path.parent / "backend" / "logs" / "gap_filling_results.json"
    results_file.parent.mkdir(parents=True, exist_ok=True)
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Results saved to: {results_file}")


if __name__ == "__main__":
    from datetime import datetime
    try:
        main()
        sys.exit(0)
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
