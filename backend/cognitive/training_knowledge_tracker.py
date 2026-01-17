"""
Training Knowledge Tracker

Tracks and displays what Grace learns from self-healing training practice.

Shows:
1. Topics learned from practice cycles
2. Knowledge patterns accumulated
3. Skills developed over time
4. Problem perspectives mastered
5. Learning progression
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, Counter
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class LearnedTopic:
    """A topic/pattern Grace has learned."""
    topic_id: str
    topic_name: str
    category: str  # "syntax", "logic", "performance", "security", etc.
    first_learned: datetime
    last_practiced: datetime
    practice_count: int
    success_rate: float
    trust_score: float
    related_patterns: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)


@dataclass
class LearningProgress:
    """Learning progress summary."""
    total_topics: int
    topics_by_category: Dict[str, int]
    average_trust_score: float
    total_practice_sessions: int
    success_rate_trend: List[float]
    mastery_levels: Dict[str, str]  # category -> mastery level
    recently_learned: List[str]
    improving_skills: List[str]


class TrainingKnowledgeTracker:
    """
    Tracks and displays what Grace learns from training.
    
    Analyzes:
    1. Knowledge gained from practice cycles
    2. Topics learned from fixes
    3. Patterns accumulated over time
    4. Skills developed
    5. Problem perspectives mastered
    """
    
    def __init__(
        self,
        session,
        knowledge_base_path: Path,
        training_system=None
    ):
        """Initialize Training Knowledge Tracker."""
        self.session = session
        self.kb_path = knowledge_base_path
        self.training_system = training_system
        
        # Topic tracking
        self.learned_topics: Dict[str, LearnedTopic] = {}
        self.topic_statistics: Dict[str, Any] = {}
        
        # Category tracking
        self.topics_by_category: Dict[str, List[str]] = defaultdict(list)
        self.category_mastery: Dict[str, float] = {}
        
        logger.info("[KNOWLEDGE-TRACKER] Initialized knowledge tracking")
    
    # ==================== KNOWLEDGE EXTRACTION ====================
    
    def extract_learned_topics(
        self,
        training_cycles: List[Any]
    ) -> List[LearnedTopic]:
        """
        Extract learned topics from training cycles.
        
        Analyzes:
        - knowledge_gained from each cycle
        - patterns from fixes
        - problem perspectives practiced
        - success patterns
        """
        topics = []
        
        for cycle in training_cycles:
            # Extract knowledge from cycle
            cycle_topics = self._extract_cycle_topics(cycle)
            topics.extend(cycle_topics)
            
            # Extract patterns from fixes
            fix_patterns = self._extract_fix_patterns(cycle)
            topics.extend(fix_patterns)
        
        # Consolidate topics
        consolidated = self._consolidate_topics(topics)
        
        return consolidated
    
    def _extract_cycle_topics(self, cycle: Any) -> List[LearnedTopic]:
        """Extract topics from a single cycle."""
        topics = []
        
        # Extract from knowledge_gained
        for knowledge in cycle.knowledge_gained or []:
            topic = self._parse_knowledge_to_topic(knowledge, cycle)
            if topic:
                topics.append(topic)
        
        # Extract from problem perspective
        perspective = cycle.problem_perspective.value if hasattr(cycle, 'problem_perspective') else "unknown"
        if perspective:
            topic = LearnedTopic(
                topic_id=f"perspective_{perspective}_{cycle.cycle_id}",
                topic_name=f"{perspective.replace('_', ' ').title()} Patterns",
                category=perspective.split('_')[0] if '_' in perspective else perspective,
                first_learned=cycle.started_at if hasattr(cycle, 'started_at') else datetime.utcnow(),
                last_practiced=cycle.completed_at or datetime.utcnow(),
                practice_count=len(cycle.files_fixed or []),
                success_rate=(len(cycle.files_fixed or []) / len(cycle.files_collected or [1])) if cycle.files_collected else 0.0,
                trust_score=0.7,  # Default trust
                examples=[f"Fixed {len(cycle.files_fixed or [])} files in cycle {cycle.cycle_id}"]
            )
            topics.append(topic)
        
        return topics
    
    def _parse_knowledge_to_topic(self, knowledge: str, cycle: Any) -> Optional[LearnedTopic]:
        """Parse knowledge string into a LearnedTopic."""
        if not knowledge:
            return None
        
        # Extract category from knowledge
        knowledge_lower = knowledge.lower()
        category = "general"
        
        if "syntax" in knowledge_lower:
            category = "syntax"
        elif "logic" in knowledge_lower or "logical" in knowledge_lower:
            category = "logic"
        elif "performance" in knowledge_lower or "optimization" in knowledge_lower:
            category = "performance"
        elif "security" in knowledge_lower or "vulnerability" in knowledge_lower:
            category = "security"
        elif "architecture" in knowledge_lower or "design" in knowledge_lower:
            category = "architecture"
        elif "quality" in knowledge_lower or "code quality" in knowledge_lower:
            category = "quality"
        
        # Extract topic name (first few words)
        topic_name = knowledge[:50].strip()
        if len(knowledge) > 50:
            topic_name += "..."
        
        topic_id = f"topic_{hash(knowledge) % 10000}"
        
        return LearnedTopic(
            topic_id=topic_id,
            topic_name=topic_name,
            category=category,
            first_learned=cycle.started_at if hasattr(cycle, 'started_at') else datetime.utcnow(),
            last_practiced=datetime.utcnow(),
            practice_count=1,
            success_rate=1.0,
            trust_score=0.8,
            examples=[knowledge]
        )
    
    def _extract_fix_patterns(self, cycle: Any) -> List[LearnedTopic]:
        """Extract patterns from fixed files."""
        topics = []
        
        # Analyze fixed files for patterns
        fixed_files = cycle.files_fixed or []
        
        if fixed_files:
            # Extract common patterns from file paths
            pattern_counter = Counter()
            for file_path in fixed_files:
                file_name = Path(file_path).name
                # Extract pattern type from filename or path
                if "syntax" in file_path.lower() or "error" in file_path.lower():
                    pattern_counter["syntax_errors"] += 1
                elif "logic" in file_path.lower() or "bug" in file_path.lower():
                    pattern_counter["logic_errors"] += 1
                elif "performance" in file_path.lower() or "optimization" in file_path.lower():
                    pattern_counter["performance_issues"] += 1
                elif "security" in file_path.lower() or "vulnerability" in file_path.lower():
                    pattern_counter["security_issues"] += 1
            
            # Create topics from patterns
            for pattern, count in pattern_counter.items():
                topic = LearnedTopic(
                    topic_id=f"pattern_{pattern}_{cycle.cycle_id}",
                    topic_name=f"{pattern.replace('_', ' ').title()} Fix Pattern",
                    category=pattern.split('_')[0],
                    first_learned=cycle.started_at if hasattr(cycle, 'started_at') else datetime.utcnow(),
                    last_practiced=datetime.utcnow(),
                    practice_count=count,
                    success_rate=1.0,
                    trust_score=0.8,
                    examples=[f"Fixed {count} files with {pattern}"]
                )
                topics.append(topic)
        
        return topics
    
    def _consolidate_topics(self, topics: List[LearnedTopic]) -> List[LearnedTopic]:
        """Consolidate similar topics."""
        consolidated: Dict[str, LearnedTopic] = {}
        
        for topic in topics:
            # Check if similar topic exists
            key = f"{topic.category}_{topic.topic_name.lower()[:30]}"
            
            if key in consolidated:
                # Merge with existing topic
                existing = consolidated[key]
                existing.practice_count += topic.practice_count
                existing.last_practiced = max(existing.last_practiced, topic.last_practiced)
                existing.success_rate = (existing.success_rate + topic.success_rate) / 2
                existing.examples.extend(topic.examples)
            else:
                consolidated[key] = topic
        
        return list(consolidated.values())
    
    # ==================== KNOWLEDGE DISPLAY ====================
    
    def get_learned_topics_summary(self) -> Dict[str, Any]:
        """
        Get summary of all learned topics.
        
        Returns:
            Summary with topics by category, statistics, and progress
        """
        # Extract topics from training cycles
        if self.training_system:
            cycles = self.training_system.cycles_completed or []
            topics = self.extract_learned_topics(cycles)
        else:
            topics = []
        
        # Organize by category
        topics_by_category = defaultdict(list)
        for topic in topics:
            topics_by_category[topic.category].append(topic)
        
        # Calculate statistics
        total_topics = len(topics)
        category_counts = {cat: len(topics) for cat, topics in topics_by_category.items()}
        
        average_trust = sum(t.trust_score for t in topics) / len(topics) if topics else 0.0
        total_practice = sum(t.practice_count for t in topics)
        
        # Calculate mastery levels
        mastery_levels = {}
        for category, cat_topics in topics_by_category.items():
            avg_success = sum(t.success_rate for t in cat_topics) / len(cat_topics) if cat_topics else 0.0
            total_practice_count = sum(t.practice_count for t in cat_topics)
            
            if avg_success >= 0.9 and total_practice_count >= 50:
                mastery_levels[category] = "Expert"
            elif avg_success >= 0.75 and total_practice_count >= 20:
                mastery_levels[category] = "Advanced"
            elif avg_success >= 0.6 and total_practice_count >= 10:
                mastery_levels[category] = "Intermediate"
            elif total_practice_count >= 5:
                mastery_levels[category] = "Beginner"
            else:
                mastery_levels[category] = "Novice"
        
        # Recently learned (last 7 days)
        recent_cutoff = datetime.utcnow() - timedelta(days=7)
        recently_learned = [
            t.topic_name for t in topics
            if t.first_learned >= recent_cutoff
        ]
        
        # Improving skills (increasing success rate)
        improving_skills = []
        for category, cat_topics in topics_by_category.items():
            if len(cat_topics) >= 3:
                # Check if success rate is improving
                sorted_topics = sorted(cat_topics, key=lambda t: t.first_learned)
                recent_success = sum(t.success_rate for t in sorted_topics[-3:]) / 3
                early_success = sum(t.success_rate for t in sorted_topics[:3]) / 3 if len(sorted_topics) >= 3 else 0.0
                
                if recent_success > early_success + 0.1:
                    improving_skills.append(category)
        
        return {
            "total_topics": total_topics,
            "topics_by_category": {
                cat: [
                    {
                        "topic_name": t.topic_name,
                        "practice_count": t.practice_count,
                        "success_rate": t.success_rate,
                        "trust_score": t.trust_score,
                        "last_practiced": t.last_practiced.isoformat(),
                        "examples": t.examples[:3]
                    }
                    for t in topics
                ]
                for cat, topics in topics_by_category.items()
            },
            "category_counts": category_counts,
            "average_trust_score": average_trust,
            "total_practice_sessions": total_practice,
            "mastery_levels": mastery_levels,
            "recently_learned": recently_learned[:10],
            "improving_skills": improving_skills,
            "topics_detail": [
                {
                    "topic_id": t.topic_id,
                    "topic_name": t.topic_name,
                    "category": t.category,
                    "practice_count": t.practice_count,
                    "success_rate": t.success_rate,
                    "trust_score": t.trust_score,
                    "first_learned": t.first_learned.isoformat(),
                    "last_practiced": t.last_practiced.isoformat(),
                    "examples": t.examples[:3]
                }
                for t in topics
            ]
        }
    
    def get_learning_progress(self) -> LearningProgress:
        """Get learning progress summary."""
        summary = self.get_learned_topics_summary()
        
        # Calculate success rate trend (would need historical data)
        success_rate_trend = []  # Would calculate from historical cycles
        
        return LearningProgress(
            total_topics=summary["total_topics"],
            topics_by_category={k: len(v) for k, v in summary["topics_by_category"].items()},
            average_trust_score=summary["average_trust_score"],
            total_practice_sessions=summary["total_practice_sessions"],
            success_rate_trend=success_rate_trend,
            mastery_levels=summary["mastery_levels"],
            recently_learned=summary["recently_learned"],
            improving_skills=summary["improving_skills"]
        )
    
    def display_learned_topics(self) -> str:
        """
        Display learned topics in human-readable format.
        
        Returns:
            Formatted string showing what Grace has learned
        """
        summary = self.get_learned_topics_summary()
        
        output = []
        output.append("=" * 70)
        output.append("GRACE'S LEARNED TOPICS FROM SELF-HEALING TRAINING")
        output.append("=" * 70)
        output.append()
        
        output.append(f"Total Topics Learned: {summary['total_topics']}")
        output.append(f"Average Trust Score: {summary['average_trust_score']:.2f}")
        output.append(f"Total Practice Sessions: {summary['total_practice_sessions']}")
        output.append()
        
        output.append("Topics by Category:")
        output.append("-" * 70)
        
        for category, topics in summary["topics_by_category"].items():
            output.append(f"\n[{category.upper()}] - {len(topics)} topics")
            
            # Mastery level
            mastery = summary["mastery_levels"].get(category, "Novice")
            output.append(f"  Mastery Level: {mastery}")
            
            # Top topics in this category
            sorted_topics = sorted(topics, key=lambda t: t["practice_count"], reverse=True)
            for i, topic in enumerate(sorted_topics[:5], 1):
                output.append(f"  {i}. {topic['topic_name']}")
                output.append(f"     Practice: {topic['practice_count']} times")
                output.append(f"     Success Rate: {topic['success_rate']:.1%}")
                output.append(f"     Trust Score: {topic['trust_score']:.2f}")
                if topic['examples']:
                    output.append(f"     Examples: {topic['examples'][0][:60]}...")
                output.append()
        
        output.append("Recently Learned (Last 7 Days):")
        output.append("-" * 70)
        for i, topic in enumerate(summary["recently_learned"], 1):
            output.append(f"  {i}. {topic}")
        
        output.append()
        output.append("Improving Skills:")
        output.append("-" * 70)
        for skill in summary["improving_skills"]:
            output.append(f"  - {skill.title()} (success rate improving)")
        
        output.append()
        output.append("=" * 70)
        
        return "\n".join(output)


def get_training_knowledge_tracker(
    session,
    knowledge_base_path: Path,
    training_system=None
) -> TrainingKnowledgeTracker:
    """Factory function to get Training Knowledge Tracker."""
    return TrainingKnowledgeTracker(
        session=session,
        knowledge_base_path=knowledge_base_path,
        training_system=training_system
    )
