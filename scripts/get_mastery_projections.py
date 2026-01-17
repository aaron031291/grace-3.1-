#!/usr/bin/env python3
"""
Get Mastery Projections for Coding Agent and Self-Healing

Uses TimeSense to project when Grace will reach mastery levels for:
1. Coding Agent (code generation mastery)
2. Self-Healing (healing mastery)
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import math


# ==================== MASTERY THRESHOLDS ====================

MASTERY_THRESHOLDS = {
    "Novice": {"topics": 0, "success_rate": 0.0},
    "Beginner": {"topics": 5, "success_rate": 0.5},
    "Intermediate": {"topics": 20, "success_rate": 0.7},
    "Advanced": {"topics": 40, "success_rate": 0.85},
    "Expert": {"topics": 80, "success_rate": 0.95}
}


# ==================== ENHANCEMENT SPEEDUPS ====================

# Combined speedups from all enhancements
MULTI_INSTANCE_SPEEDUP = 5.0  # 5 domains parallel
PARALLEL_PROCESSING_SPEEDUP = 3.0  # Multiple files simultaneously
KNOWLEDGE_RETRIEVAL_SPEEDUP = 1.5  # Pattern reuse
DOMAIN_LEARNING_SPEEDUP = 1.2  # Focused expertise

TOTAL_SPEEDUP = MULTI_INSTANCE_SPEEDUP * PARALLEL_PROCESSING_SPEEDUP * KNOWLEDGE_RETRIEVAL_SPEEDUP * DOMAIN_LEARNING_SPEEDUP

# Average cycle duration (with enhancements)
ENHANCED_CYCLE_TIME_HOURS = 2.0 / PARALLEL_PROCESSING_SPEEDUP  # ~0.67 hours per cycle


# ==================== PROJECTION FUNCTIONS ====================

def project_to_mastery(
    category: str,
    current_topics: int,
    current_success_rate: float,
    current_cycles: int = 0,
    velocity: float = 0.025,  # 2.5% improvement per cycle
    acceleration: float = 0.001  # Slight acceleration
) -> Dict[str, Any]:
    """
    Project when Grace will reach mastery levels.
    
    Uses trajectory modeling with enhancements.
    """
    # Determine current mastery
    current_mastery = get_mastery_level(current_topics, current_success_rate)
    
    # Target: Expert level
    target_topics = MASTERY_THRESHOLDS["Expert"]["topics"]
    target_success_rate = MASTERY_THRESHOLDS["Expert"]["success_rate"]
    
    # Calculate gaps
    topics_gap = max(0, target_topics - current_topics)
    success_rate_gap = max(0, target_success_rate - current_success_rate)
    
    # Project cycles needed
    # Topics: ~5 topics per cycle (with knowledge retrieval)
    cycles_for_topics = topics_gap / 5.0
    
    # Success rate: Use trajectory projection
    if success_rate_gap > 0:
        # Quadratic projection: rate = current + velocity*cycles + 0.5*acceleration*cycles^2
        # Solve for cycles: target = current + velocity*cycles + 0.5*acceleration*cycles^2
        a = 0.5 * acceleration
        b = velocity
        c = -success_rate_gap
        
        if abs(acceleration) < 0.001:
            # Linear projection
            cycles_for_rate = success_rate_gap / velocity if velocity > 0 else 1000
        else:
            # Quadratic projection
            discriminant = b * b - 4 * a * c
            if discriminant >= 0:
                cycles_for_rate = (-b + math.sqrt(discriminant)) / (2 * a)
                if cycles_for_rate < 0:
                    cycles_for_rate = success_rate_gap / velocity if velocity > 0 else 1000
            else:
                cycles_for_rate = success_rate_gap / velocity if velocity > 0 else 1000
    else:
        cycles_for_rate = 0
    
    # Take maximum (both must be achieved)
    estimated_cycles = max(cycles_for_topics, cycles_for_rate)
    
    # Apply knowledge retrieval speedup (reduces cycles needed)
    estimated_cycles = estimated_cycles / KNOWLEDGE_RETRIEVAL_SPEEDUP
    
    # Apply domain learning speedup
    estimated_cycles = estimated_cycles / DOMAIN_LEARNING_SPEEDUP
    
    # Calculate time (with parallel processing speedup)
    estimated_hours = estimated_cycles * ENHANCED_CYCLE_TIME_HOURS
    estimated_days = estimated_hours / 24.0
    
    # Project to 90% success rate
    if current_success_rate < 0.90:
        gap_to_90 = 0.90 - current_success_rate
        cycles_to_90 = gap_to_90 / velocity if velocity > 0 else 1000
        cycles_to_90 = cycles_to_90 / KNOWLEDGE_RETRIEVAL_SPEEDUP / DOMAIN_LEARNING_SPEEDUP
        hours_to_90 = cycles_to_90 * ENHANCED_CYCLE_TIME_HOURS
        days_to_90 = hours_to_90 / 24.0
    else:
        cycles_to_90 = 0
        days_to_90 = 0
    
    return {
        "category": category,
        "current_mastery": current_mastery,
        "current_topics": current_topics,
        "current_success_rate": current_success_rate,
        "current_cycles": current_cycles,
        "target_mastery": "Expert",
        "target_topics": target_topics,
        "target_success_rate": target_success_rate,
        "90pct_success": {
            "estimated_days": days_to_90,
            "estimated_hours": hours_to_90 if days_to_90 > 0 else 0,
            "estimated_cycles": int(cycles_to_90),
            "already_achieved": current_success_rate >= 0.90
        },
        "expert_mastery": {
            "estimated_days": estimated_days,
            "estimated_hours": estimated_hours,
            "estimated_cycles": int(estimated_cycles),
            "already_achieved": current_mastery == "Expert"
        },
        "trajectory": {
            "velocity": velocity,
            "acceleration": acceleration
        }
    }


def get_mastery_level(topics: int, success_rate: float) -> str:
    """Get mastery level from topics and success rate."""
    if topics >= 80 and success_rate >= 0.95:
        return "Expert"
    elif topics >= 40 and success_rate >= 0.85:
        return "Advanced"
    elif topics >= 20 and success_rate >= 0.70:
        return "Intermediate"
    elif topics >= 5 and success_rate >= 0.50:
        return "Beginner"
    else:
        return "Novice"


def get_current_stats() -> Dict[str, Dict[str, Any]]:
    """
    Get current stats for coding agent and self-healing.
    
    This would normally query the database, but for now we'll use estimates.
    """
    # Try to get actual stats from API or database
    try:
        import requests
        response = requests.get("http://localhost:8000/training-knowledge/progress")
        if response.status_code == 200:
            data = response.json()
            # Extract stats from response
            return {
                "coding_agent": {
                    "topics": data.get("coding_agent", {}).get("topics", 0),
                    "success_rate": data.get("coding_agent", {}).get("success_rate", 0.0),
                    "cycles": data.get("coding_agent", {}).get("cycles", 0)
                },
                "self_healing": {
                    "topics": data.get("self_healing", {}).get("topics", 0),
                    "success_rate": data.get("self_healing", {}).get("success_rate", 0.0),
                    "cycles": data.get("self_healing", {}).get("cycles", 0)
                }
            }
    except:
        pass
    
    # Default estimates (if API not available)
    return {
        "coding_agent": {
            "topics": 0,  # Will be updated from actual data
            "success_rate": 0.0,
            "cycles": 0
        },
        "self_healing": {
            "topics": 0,  # Will be updated from actual data
            "success_rate": 0.0,
            "cycles": 0
        }
    }


def display_projections(projections: Dict[str, Dict[str, Any]]):
    """Display mastery projections in human-readable format."""
    print("=" * 80)
    print("GRACE MASTERY PROJECTIONS (Coding Agent & Self-Healing)")
    print("=" * 80)
    print()
    print(f"Enhancements Applied: {TOTAL_SPEEDUP:.1f}x speedup")
    print(f"  - Multi-Instance: {MULTI_INSTANCE_SPEEDUP}x")
    print(f"  - Parallel Processing: {PARALLEL_PROCESSING_SPEEDUP}x")
    print(f"  - Knowledge Retrieval: {KNOWLEDGE_RETRIEVAL_SPEEDUP}x")
    print(f"  - Domain Learning: {DOMAIN_LEARNING_SPEEDUP}x")
    print()
    print("=" * 80)
    print()
    
    for category, proj in projections.items():
        print(f"[{category.upper().replace('_', ' ')}]")
        print("-" * 80)
        print(f"Current Mastery: {proj['current_mastery']}")
        print(f"Current Topics: {proj['current_topics']}")
        print(f"Current Success Rate: {proj['current_success_rate']:.1%}")
        print(f"Current Cycles: {proj['current_cycles']}")
        print()
        
        # 90% Success Rate
        p90 = proj["90pct_success"]
        if p90["already_achieved"]:
            print("✅ 90% Success Rate: ALREADY ACHIEVED")
        else:
            print("🎯 90% Success Rate:")
            print(f"   Estimated Time: {p90['estimated_days']:.1f} days ({p90['estimated_hours']:.1f} hours)")
            print(f"   Estimated Cycles: {p90['estimated_cycles']} cycles")
            print(f"   Current: {proj['current_success_rate']:.1%} → Target: 90.0%")
        print()
        
        # Expert Mastery
        expert = proj["expert_mastery"]
        if expert["already_achieved"]:
            print("✅ Expert Mastery: ALREADY ACHIEVED")
        else:
            print("🎯 Expert Mastery:")
            print(f"   Estimated Time: {expert['estimated_days']:.1f} days ({expert['estimated_hours']:.1f} hours)")
            print(f"   Estimated Cycles: {expert['estimated_cycles']} cycles")
            print(f"   Topics: {proj['current_topics']}/{proj['target_topics']}")
            print(f"   Success Rate: {proj['current_success_rate']:.1%} → {proj['target_success_rate']:.1%}")
        print()
        
        # Trajectory
        traj = proj["trajectory"]
        print(f"Learning Trajectory:")
        print(f"   Velocity: {traj['velocity']:.4f} per cycle ({traj['velocity']*100:.1f}% improvement)")
        print(f"   Acceleration: {traj['acceleration']:.4f} per cycle")
        print()
        print()
    
    print("=" * 80)
    print("Note: Projections assume continuous training with all enhancements active")
    print("=" * 80)


# ==================== MAIN ====================

def main():
    """Get and display mastery projections."""
    print("Getting current stats...")
    
    # Get current stats
    stats = get_current_stats()
    
    # If no actual data, use example estimates
    if stats["coding_agent"]["topics"] == 0 and stats["self_healing"]["topics"] == 0:
        print("WARNING: No training data found. Using example estimates.")
        print("   (Run training cycles to get actual projections)")
        print()
        
        # Example: Starting from scratch
        stats = {
            "coding_agent": {
                "topics": 0,
                "success_rate": 0.0,
                "cycles": 0
            },
            "self_healing": {
                "topics": 0,
                "success_rate": 0.0,
                "cycles": 0
            }
        }
    
    # Project for coding agent
    coding_projection = project_to_mastery(
        category="coding_agent",
        current_topics=stats["coding_agent"]["topics"],
        current_success_rate=stats["coding_agent"]["success_rate"],
        current_cycles=stats["coding_agent"]["cycles"]
    )
    
    # Project for self-healing
    healing_projection = project_to_mastery(
        category="self_healing",
        current_topics=stats["self_healing"]["topics"],
        current_success_rate=stats["self_healing"]["success_rate"],
        current_cycles=stats["self_healing"]["cycles"]
    )
    
    # Display
    display_projections({
        "coding_agent": coding_projection,
        "self_healing": healing_projection
    })


if __name__ == "__main__":
    main()
