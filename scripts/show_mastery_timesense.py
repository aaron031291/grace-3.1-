#!/usr/bin/env python3
"""
Show Mastery Projections Using TimeSense Directly

Shows how long it will take for Coding Agent and Self-Healing to reach mastery.
Uses TimeSense directly (no API server needed).
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime
from typing import Dict, Any, Optional


def get_timesense_estimate():
    """Get TimeSense estimate for training cycle duration."""
    try:
        # Try different import paths
        try:
            from backend.timesense.engine import get_timesense_engine
        except ImportError:
            try:
                from timesense.engine import get_timesense_engine
            except ImportError:
                import sys
                sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
                from timesense.engine import get_timesense_engine
        
        timesense = get_timesense_engine()
        
        # Initialize if needed
        if not hasattr(timesense, '_initialized') or not timesense._initialized:
            timesense.initialize_sync(quick_calibration=True)
        
        # Get cost model for training cycle
        cost_model = timesense.get_cost_model("training_cycle")
        
        if cost_model:
            return {
                "avg_duration_hours": cost_model.get("avg_duration_hours", 2.0),
                "confidence": cost_model.get("confidence", 0.5),
                "based_on": cost_model.get("based_on", "unknown")
            }
    except Exception as e:
        import traceback
        print(f"WARNING: TimeSense not available: {e}")
        print(f"   (This is okay - using fallback estimates)")
    
    return None


def calculate_mastery_projections():
    """Calculate mastery projections for both systems."""
    
    # Get TimeSense estimate
    timesense_estimate = get_timesense_estimate()
    
    if timesense_estimate:
        cycle_duration_hours = timesense_estimate["avg_duration_hours"]
        confidence = timesense_estimate["confidence"]
        based_on = timesense_estimate["based_on"]
        print(f"TimeSense Cycle Duration: {cycle_duration_hours:.2f} hours (confidence: {confidence:.1%}, based on: {based_on})")
    else:
        cycle_duration_hours = 2.0  # Fallback
        confidence = 0.3
        print(f"Using fallback cycle duration: {cycle_duration_hours} hours (low confidence)")
    
    print()
    
    # Enhancement speedups
    MULTI_INSTANCE = 5.0
    PARALLEL_PROCESSING = 3.0
    KNOWLEDGE_RETRIEVAL = 1.5
    DOMAIN_LEARNING = 1.2
    
    TOTAL_SPEEDUP = MULTI_INSTANCE * PARALLEL_PROCESSING * KNOWLEDGE_RETRIEVAL * DOMAIN_LEARNING
    
    # Enhanced cycle time (with parallel processing)
    enhanced_cycle_hours = cycle_duration_hours / PARALLEL_PROCESSING
    
    # Learning parameters
    VELOCITY = 0.025  # 2.5% improvement per cycle
    ACCELERATION = 0.001
    
    # Mastery targets
    TARGET_90PCT = 0.90
    TARGET_EXPERT_TOPICS = 80
    TARGET_EXPERT_RATE = 0.95
    
    # Starting point
    current_topics = 0
    current_success_rate = 0.0
    
    print("=" * 80)
    print("GRACE MASTERY PROJECTIONS (Coding Agent & Self-Healing)")
    print("=" * 80)
    print()
    print(f"TimeSense Cycle Duration: {cycle_duration_hours:.2f} hours")
    print(f"Enhanced Cycle Duration: {enhanced_cycle_hours:.2f} hours (with parallel processing)")
    print(f"Total Speedup: {TOTAL_SPEEDUP:.1f}x")
    print(f"  - Multi-Instance: {MULTI_INSTANCE}x")
    print(f"  - Parallel Processing: {PARALLEL_PROCESSING}x")
    print(f"  - Knowledge Retrieval: {KNOWLEDGE_RETRIEVAL}x")
    print(f"  - Domain Learning: {DOMAIN_LEARNING}x")
    print()
    print("=" * 80)
    print()
    
    for system_name in ["CODING AGENT", "SELF HEALING"]:
        print(f"[{system_name}]")
        print("-" * 80)
        print(f"Current Mastery: Novice")
        print(f"Current Topics: {current_topics}")
        print(f"Current Success Rate: {current_success_rate:.1%}")
        print()
        
        # Calculate 90% success rate
        gap_to_90 = TARGET_90PCT - current_success_rate
        cycles_to_90 = gap_to_90 / VELOCITY
        cycles_to_90 = cycles_to_90 / KNOWLEDGE_RETRIEVAL / DOMAIN_LEARNING
        hours_to_90 = cycles_to_90 * enhanced_cycle_hours
        days_to_90 = hours_to_90 / 24.0
        
        print(f"[TARGET] 90% Success Rate:")
        print(f"   Estimated Time: {days_to_90:.2f} days ({hours_to_90:.1f} hours)")
        print(f"   Estimated Cycles: {int(cycles_to_90)} cycles")
        print(f"   Current: {current_success_rate:.1%} -> Target: {TARGET_90PCT:.1%}")
        print()
        
        # Calculate Expert mastery
        topics_gap = TARGET_EXPERT_TOPICS - current_topics
        cycles_for_topics = topics_gap / 5.0  # ~5 topics per cycle
        cycles_for_topics = cycles_for_topics / KNOWLEDGE_RETRIEVAL / DOMAIN_LEARNING
        
        success_rate_gap = TARGET_EXPERT_RATE - current_success_rate
        cycles_for_rate = success_rate_gap / VELOCITY
        cycles_for_rate = cycles_for_rate / KNOWLEDGE_RETRIEVAL / DOMAIN_LEARNING
        
        cycles_to_expert = max(cycles_for_topics, cycles_for_rate)
        hours_to_expert = cycles_to_expert * enhanced_cycle_hours
        days_to_expert = hours_to_expert / 24.0
        
        print(f"[TARGET] Expert Mastery:")
        print(f"   Estimated Time: {days_to_expert:.2f} days ({hours_to_expert:.1f} hours)")
        print(f"   Estimated Cycles: {int(cycles_to_expert)} cycles")
        print(f"   Topics: {current_topics}/{TARGET_EXPERT_TOPICS}")
        print(f"   Success Rate: {current_success_rate:.1%} -> {TARGET_EXPERT_RATE:.1%}")
        if timesense_estimate:
            print(f"   Confidence: {confidence:.1%} (from TimeSense)")
        print()
        
        print(f"Learning Trajectory:")
        print(f"   Velocity: {VELOCITY:.4f} per cycle ({VELOCITY*100:.1f}% improvement)")
        print(f"   Acceleration: {ACCELERATION:.4f} per cycle")
        print()
        print()
    
    print("=" * 80)
    if timesense_estimate:
        print("Note: Projections use TimeSense cost models (calibrated to your system)")
    else:
        print("Note: Projections use fallback estimates (start API server for TimeSense)")
    print("=" * 80)


if __name__ == "__main__":
    calculate_mastery_projections()
