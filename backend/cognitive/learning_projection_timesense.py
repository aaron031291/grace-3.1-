"""
Learning Projection with TimeSense

Uses TimeSense to estimate when Grace will reach exceptional mastery levels
based on her learning trajectory.

Projects:
1. When Grace will reach Expert mastery in each category
2. When Grace will reach 90%+ success rate
3. When Grace will accumulate target number of topics
4. Learning velocity and acceleration
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict
from pathlib import Path
import math

logger = logging.getLogger(__name__)


@dataclass
class MasteryProjection:
    """Projection for reaching mastery level."""
    category: str
    current_mastery: str  # "Novice", "Beginner", "Intermediate", "Advanced", "Expert"
    target_mastery: str
    current_topics: int
    target_topics: int
    current_success_rate: float
    target_success_rate: float
    estimated_days: float
    estimated_cycles: int
    confidence: float  # 0-1, how confident the projection is
    acceleration_factor: float  # Learning acceleration


@dataclass
class LearningTrajectory:
    """Learning trajectory over time."""
    category: str
    data_points: List[Tuple[datetime, float]]  # (timestamp, success_rate)
    velocity: float  # Success rate improvement per cycle
    acceleration: float  # Change in velocity per cycle
    current_rate: float
    projected_90pct: Optional[datetime] = None
    projected_expert: Optional[datetime] = None


class LearningProjectionTimeSense:
    """
    Uses TimeSense to project when Grace reaches exceptional levels.
    
    Models:
    - Learning velocity (topics/cycle, success_rate improvement/cycle)
    - Learning acceleration (how velocity changes)
    - Mastery progression (Novice → Expert)
    - Time estimates using TimeSense cost models
    """
    
    # Mastery thresholds (approximate)
    MASTERY_THRESHOLDS = {
        "Novice": {"topics": 0, "success_rate": 0.0},
        "Beginner": {"topics": 5, "success_rate": 0.5},
        "Intermediate": {"topics": 20, "success_rate": 0.7},
        "Advanced": {"topics": 40, "success_rate": 0.85},
        "Expert": {"topics": 80, "success_rate": 0.95}
    }
    
    # Exceptional level targets
    EXCEPTIONAL_TARGETS = {
        "90pct_success": {"success_rate": 0.90},
        "Expert": {"topics": 80, "success_rate": 0.95},
        "Elite": {"topics": 200, "success_rate": 0.98},
        "Master": {"topics": 500, "success_rate": 0.99}
    }
    
    def __init__(
        self,
        timesense_engine=None,
        training_system=None,
        knowledge_tracker=None
    ):
        """Initialize Learning Projection with TimeSense."""
        self.timesense = timesense_engine
        self.training_system = training_system
        self.knowledge_tracker = knowledge_tracker
        
        # Cycle configuration (for time estimation)
        self.avg_cycle_duration_hours = 2.0  # Average cycle duration
        self.files_per_cycle = 100
        
        logger.info("[LEARNING-PROJECTION] Initialized with TimeSense")
    
    # ==================== TRAJECTORY ANALYSIS ====================
    
    def analyze_learning_trajectory(
        self,
        cycles: List[Any]
    ) -> Dict[str, LearningTrajectory]:
        """
        Analyze learning trajectory from cycles.
        
        Calculates:
        - Success rate over time
        - Learning velocity (improvement rate)
        - Learning acceleration (change in velocity)
        """
        trajectories = {}
        
        # Group cycles by category
        cycles_by_category = defaultdict(list)
        for cycle in cycles:
            perspective = getattr(cycle, 'problem_perspective', None)
            if perspective:
                category = perspective.value.split('_')[0] if '_' in perspective.value else "general"
                cycles_by_category[category].append(cycle)
        
        # Analyze each category
        for category, cat_cycles in cycles_by_category.items():
            trajectory = self._analyze_category_trajectory(category, cat_cycles)
            if trajectory:
                trajectories[category] = trajectory
        
        return trajectories
    
    def _analyze_category_trajectory(
        self,
        category: str,
        cycles: List[Any]
    ) -> Optional[LearningTrajectory]:
        """Analyze trajectory for a single category."""
        if len(cycles) < 3:
            return None  # Need at least 3 data points
        
        # Sort cycles by time
        sorted_cycles = sorted(cycles, key=lambda c: getattr(c, 'started_at', datetime.utcnow()))
        
        # Extract data points (timestamp, success_rate)
        data_points = []
        for cycle in sorted_cycles:
            files_fixed = len(getattr(cycle, 'files_fixed', []))
            files_collected = len(getattr(cycle, 'files_collected', [1]))
            success_rate = files_fixed / files_collected if files_collected > 0 else 0.0
            
            timestamp = getattr(cycle, 'started_at', datetime.utcnow())
            data_points.append((timestamp, success_rate))
        
        if len(data_points) < 2:
            return None
        
        # Calculate velocity (average improvement per cycle)
        velocities = []
        for i in range(1, len(data_points)):
            dt = (data_points[i][0] - data_points[i-1][0]).total_seconds() / 3600  # Hours
            if dt > 0:
                ds = data_points[i][1] - data_points[i-1][1]  # Success rate change
                velocity = ds / (dt / self.avg_cycle_duration_hours)  # Per cycle
                velocities.append(velocity)
        
        avg_velocity = sum(velocities) / len(velocities) if velocities else 0.0
        
        # Calculate acceleration (change in velocity)
        accelerations = []
        for i in range(1, len(velocities)):
            acceleration = velocities[i] - velocities[i-1]
            accelerations.append(acceleration)
        
        avg_acceleration = sum(accelerations) / len(accelerations) if accelerations else 0.0
        
        # Current rate
        current_rate = data_points[-1][1] if data_points else 0.0
        
        return LearningTrajectory(
            category=category,
            data_points=data_points,
            velocity=avg_velocity,
            acceleration=avg_acceleration,
            current_rate=current_rate
        )
    
    # ==================== PROJECTION ====================
    
    def project_to_exceptional_level(
        self,
        category: str,
        current_topics: int,
        current_success_rate: float,
        trajectory: Optional[LearningTrajectory] = None,
        target_level: str = "Expert"
    ) -> MasteryProjection:
        """
        Project when Grace will reach exceptional level.
        
        Uses:
        - Current trajectory (velocity, acceleration)
        - TimeSense for cycle time estimates
        - Learning curve modeling
        
        Args:
            target_level: "Expert", "Elite", or "Master"
        """
        # Determine current mastery
        current_mastery = self._get_mastery_level(current_topics, current_success_rate)
        
        # Target level (Expert, Elite, or Master)
        if target_level == "Elite":
            target_mastery = "Elite"
            target_topics = self.EXCEPTIONAL_TARGETS["Elite"]["topics"]
            target_success_rate = self.EXCEPTIONAL_TARGETS["Elite"]["success_rate"]
        elif target_level == "Master":
            target_mastery = "Master"
            target_topics = self.EXCEPTIONAL_TARGETS["Master"]["topics"]
            target_success_rate = self.EXCEPTIONAL_TARGETS["Master"]["success_rate"]
        else:
            # Default: Expert level
            target_mastery = "Expert"
            target_topics = self.MASTERY_THRESHOLDS["Expert"]["topics"]
            target_success_rate = self.MASTERY_THRESHOLDS["Expert"]["success_rate"]
        
        # Project based on trajectory
        if trajectory:
            # Use trajectory to project
            estimated_cycles = self._project_cycles_with_trajectory(
                trajectory=trajectory,
                target_rate=target_success_rate
            )
            acceleration_factor = 1.0 + (trajectory.acceleration * 0.1)  # Modulate acceleration
        else:
            # Use simple linear projection (fallback)
            topics_needed = max(0, target_topics - current_topics)
            success_rate_gap = max(0, target_success_rate - current_success_rate)
            
            # Estimate cycles (simplified)
            cycles_for_topics = topics_needed / 5.0  # ~5 topics per cycle
            cycles_for_rate = success_rate_gap / 0.05  # ~5% improvement per cycle
            
            estimated_cycles = max(cycles_for_topics, cycles_for_rate)
            acceleration_factor = 1.0
        
        # Apply acceleration (learning gets harder as you approach mastery)
        # Diminishing returns curve
        estimated_cycles = estimated_cycles / acceleration_factor if acceleration_factor > 0 else estimated_cycles
        
        # Apply additional diminishing returns for Elite/Master (98%+ is much harder)
        if target_success_rate >= 0.98:
            if current_success_rate >= 0.90:
                # Already at 90%+, last few % points are much harder
                remaining_gap = target_success_rate - current_success_rate
                diminishing_factor = 1.0 + (remaining_gap * 2.0)  # Gets 2x harder per % point
                estimated_cycles = estimated_cycles * diminishing_factor
            elif current_success_rate >= 0.85:
                # At 85-90%, slight diminishing returns
                diminishing_factor = 1.0 + ((target_success_rate - current_success_rate) * 1.5)
                estimated_cycles = estimated_cycles * diminishing_factor
        
        # Use TimeSense to estimate time
        if self.timesense:
            try:
                # Estimate time per cycle using TimeSense
                cycle_time_model = self.timesense.get_cost_model("training_cycle")
                if cycle_time_model:
                    hours_per_cycle = cycle_time_model.get("avg_duration_hours", self.avg_cycle_duration_hours)
                else:
                    hours_per_cycle = self.avg_cycle_duration_hours
            except:
                hours_per_cycle = self.avg_cycle_duration_hours
        else:
            hours_per_cycle = self.avg_cycle_duration_hours
        
        estimated_hours = estimated_cycles * hours_per_cycle
        estimated_days = estimated_hours / 24.0
        
        # Confidence based on data points
        if trajectory and len(trajectory.data_points) >= 5:
            confidence = 0.85  # High confidence with good data
        elif trajectory and len(trajectory.data_points) >= 3:
            confidence = 0.70  # Medium confidence
        else:
            confidence = 0.50  # Low confidence with limited data
        
        return MasteryProjection(
            category=category,
            current_mastery=current_mastery,
            target_mastery=target_mastery,
            current_topics=current_topics,
            target_topics=target_topics,
            current_success_rate=current_success_rate,
            target_success_rate=target_success_rate,
            estimated_days=estimated_days,
            estimated_cycles=int(estimated_cycles),
            confidence=confidence,
            acceleration_factor=acceleration_factor
        )
    
    def _project_cycles_with_trajectory(
        self,
        trajectory: LearningTrajectory,
        target_rate: float
    ) -> float:
        """Project cycles needed using trajectory (velocity + acceleration)."""
        current_rate = trajectory.current_rate
        gap = target_rate - current_rate
        
        if gap <= 0:
            return 0.0  # Already at or past target
        
        velocity = trajectory.velocity
        acceleration = trajectory.acceleration
        
        if velocity <= 0:
            # No improvement, use conservative estimate
            return gap / 0.02  # 2% per cycle (conservative)
        
        # Quadratic projection: rate = current + velocity*cycles + 0.5*acceleration*cycles^2
        # Solve for cycles: target = current + velocity*cycles + 0.5*acceleration*cycles^2
        # 0.5*acceleration*cycles^2 + velocity*cycles - gap = 0
        
        if abs(acceleration) < 0.001:
            # Linear projection
            cycles = gap / velocity
        else:
            # Quadratic projection
            a = 0.5 * acceleration
            b = velocity
            c = -gap
            
            # Quadratic formula: (-b + sqrt(b^2 - 4ac)) / 2a
            discriminant = b * b - 4 * a * c
            if discriminant >= 0:
                cycles = (-b + math.sqrt(discriminant)) / (2 * a)
                if cycles < 0:
                    cycles = gap / velocity  # Fallback to linear
            else:
                cycles = gap / velocity  # Fallback to linear
        
        return max(1.0, cycles)  # At least 1 cycle
    
    def _get_mastery_level(self, topics: int, success_rate: float) -> str:
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
    
    # ==================== EXCEPTIONAL LEVEL PROJECTIONS ====================
    
    def get_exceptional_level_projections(
        self,
        trajectories: Dict[str, LearningTrajectory],
        knowledge_summary: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get projections for reaching exceptional levels.
        
        Returns projections for:
        - 90% success rate
        - Expert mastery
        - Elite mastery
        - Master mastery
        """
        projections = {}
        
        # Get current stats by category
        topics_by_category = knowledge_summary.get("topics_by_category", {})
        mastery_levels = knowledge_summary.get("mastery_levels", {})
        
        for category, topics_list in topics_by_category.items():
            current_topics = len(topics_list)
            
            # Calculate current success rate (average from topics)
            if topics_list:
                avg_success = sum(t.get("success_rate", 0.0) for t in topics_list) / len(topics_list)
            else:
                avg_success = 0.0
            
            # Get trajectory
            trajectory = trajectories.get(category)
            
            # Project to exceptional levels
            expert_projection = self.project_to_exceptional_level(
                category=category,
                current_topics=current_topics,
                current_success_rate=avg_success,
                trajectory=trajectory,
                target_level="Expert"
            )
            
            # Project to Elite (98%)
            elite_projection = self.project_to_exceptional_level(
                category=category,
                current_topics=current_topics,
                current_success_rate=avg_success,
                trajectory=trajectory,
                target_level="Elite"
            )
            
            # Project to 90% success rate
            if avg_success < 0.90:
                if trajectory:
                    cycles_to_90 = self._project_cycles_with_trajectory(trajectory, 0.90)
                else:
                    cycles_to_90 = (0.90 - avg_success) / 0.05
                
                # Use TimeSense for cycle duration
                if self.timesense:
                    try:
                        cycle_time_model = self.timesense.get_cost_model("training_cycle")
                        if cycle_time_model:
                            hours_per_cycle = cycle_time_model.get("avg_duration_hours", self.avg_cycle_duration_hours)
                        else:
                            hours_per_cycle = self.avg_cycle_duration_hours
                    except:
                        hours_per_cycle = self.avg_cycle_duration_hours
                else:
                    hours_per_cycle = self.avg_cycle_duration_hours
                
                hours_to_90 = cycles_to_90 * hours_per_cycle
                days_to_90 = hours_to_90 / 24.0
            else:
                cycles_to_90 = 0
                days_to_90 = 0
            
            projections[category] = {
                "category": category,
                "current_mastery": expert_projection.current_mastery,
                "current_topics": current_topics,
                "current_success_rate": avg_success,
                "projections": {
                    "90pct_success": {
                        "estimated_days": days_to_90,
                        "estimated_cycles": int(cycles_to_90),
                        "target_rate": 0.90,
                        "current_rate": avg_success,
                        "already_achieved": avg_success >= 0.90
                    },
                    "expert": {
                        "estimated_days": expert_projection.estimated_days,
                        "estimated_cycles": expert_projection.estimated_cycles,
                        "target_topics": expert_projection.target_topics,
                        "target_rate": expert_projection.target_success_rate,
                        "current_topics": current_topics,
                        "current_rate": avg_success,
                        "confidence": expert_projection.confidence,
                        "already_achieved": expert_projection.current_mastery == "Expert"
                    },
                    "elite": {
                        "estimated_days": elite_projection.estimated_days,
                        "estimated_hours": elite_projection.estimated_days * 24.0,
                        "estimated_cycles": elite_projection.estimated_cycles,
                        "target_topics": elite_projection.target_topics,
                        "target_rate": elite_projection.target_success_rate,
                        "current_topics": current_topics,
                        "current_rate": avg_success,
                        "confidence": elite_projection.confidence,
                        "already_achieved": avg_success >= 0.98
                    }
                },
                "trajectory": {
                    "velocity": trajectory.velocity if trajectory else 0.0,
                    "acceleration": trajectory.acceleration if trajectory else 0.0,
                    "data_points": len(trajectory.data_points) if trajectory else 0
                }
            }
        
        return projections
    
    # ==================== DISPLAY ====================
    
    def display_exceptional_projections(
        self,
        projections: Dict[str, Dict[str, Any]]
    ) -> str:
        """Display exceptional level projections in human-readable format."""
        output = []
        output.append("=" * 80)
        output.append("GRACE'S PATH TO EXCEPTIONAL MASTERY (TimeSense Projections)")
        output.append("=" * 80)
        output.append()
        
        for category, proj in projections.items():
            output.append(f"[{category.upper()}]")
            output.append("-" * 80)
            
            current = proj
            output.append(f"Current Mastery: {current['current_mastery']}")
            output.append(f"Current Topics: {current['current_topics']}")
            output.append(f"Current Success Rate: {current['current_success_rate']:.1%}")
            output.append()
            
            # 90% projection
            p90 = current["projections"]["90pct_success"]
            if p90["already_achieved"]:
                output.append("✅ 90% Success Rate: ALREADY ACHIEVED")
            else:
                output.append(f"🎯 90% Success Rate:")
                output.append(f"   Estimated Time: {p90['estimated_days']:.1f} days ({p90['estimated_cycles']} cycles)")
                output.append(f"   Current: {p90['current_rate']:.1%} → Target: {p90['target_rate']:.1%}")
            
            output.append()
            
            # Expert projection
            expert = current["projections"]["expert"]
            if expert["already_achieved"]:
                output.append("✅ Expert Mastery: ALREADY ACHIEVED")
            else:
                output.append(f"🎯 Expert Mastery:")
                output.append(f"   Estimated Time: {expert['estimated_days']:.1f} days ({expert['estimated_cycles']} cycles)")
                output.append(f"   Topics: {expert['current_topics']}/{expert['target_topics']}")
                output.append(f"   Success Rate: {expert['current_rate']:.1%} → {expert['target_rate']:.1%}")
                output.append(f"   Confidence: {expert['confidence']:.1%}")
            
            output.append()
            
            # Elite projection (98%)
            elite = current["projections"].get("elite")
            if elite:
                if elite["already_achieved"]:
                    output.append("✅ Elite Mastery (98%): ALREADY ACHIEVED")
                else:
                    output.append(f"🎯 Elite Mastery (98% Success Rate):")
                    output.append(f"   Estimated Time: {elite['estimated_days']:.2f} days ({elite.get('estimated_hours', elite['estimated_days'] * 24):.1f} hours)")
                    output.append(f"   Estimated Cycles: {elite['estimated_cycles']} cycles")
                    output.append(f"   Topics: {elite['current_topics']}/{elite['target_topics']}")
                    output.append(f"   Success Rate: {elite['current_rate']:.1%} → {elite['target_rate']:.1%}")
                    output.append(f"   Confidence: {elite['confidence']:.1%}")
                
                output.append()
            
            # Trajectory info
            traj = current["trajectory"]
            output.append(f"Learning Trajectory:")
            output.append(f"   Velocity: {traj['velocity']:.4f} per cycle")
            output.append(f"   Acceleration: {traj['acceleration']:.4f} per cycle")
            output.append(f"   Data Points: {traj['data_points']}")
            output.append()
            output.append()
        
        output.append("=" * 80)
        output.append("Note: Projections use TimeSense cost models for cycle duration estimation")
        output.append("=" * 80)
        
        return "\n".join(output)


def get_learning_projection_timesense(
    timesense_engine=None,
    training_system=None,
    knowledge_tracker=None
) -> LearningProjectionTimeSense:
    """Factory function to get Learning Projection with TimeSense."""
    return LearningProjectionTimeSense(
        timesense_engine=timesense_engine,
        training_system=training_system,
        knowledge_tracker=knowledge_tracker
    )
