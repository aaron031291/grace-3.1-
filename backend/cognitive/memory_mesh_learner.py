"""
Memory Mesh Learning Feedback System

Memory mesh analyzes high-trust patterns and proactively suggests
what Grace should learn next based on:
1. Knowledge gaps identified from past failures
2. High-value topics with insufficient practice
3. Related concepts that appear frequently together
4. Success patterns that should be reinforced

This creates a feedback loop: Memory → Learning → Memory
"""

import logging
from typing import Dict, Any, List, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from datetime import datetime, timedelta

from cognitive.learning_memory import TrustScorer, LearningExample

logger = logging.getLogger(__name__)


class MemoryMeshLearner:
    """
    Analyzes memory mesh to determine what Grace should learn proactively.

    Analyzes:
    - Knowledge gaps (low operational confidence)
    - High-value under-practiced topics
    - Frequently co-occurring concepts
    - Success/failure patterns
    """

    def __init__(self, session: Session):
        self.session = session
        self.trust_scorer = TrustScorer()

    # ======================================================================
    # GAP ANALYSIS
    # ======================================================================

    def identify_knowledge_gaps(
        self,
        min_data_confidence: float = 0.7,
        max_operational_confidence: float = 0.4
    ) -> List[Dict[str, Any]]:
        """
        Identify knowledge gaps from memory mesh.

        A gap exists when:
        - Grace has read about a topic (high data_confidence)
        - But cannot apply it (low operational_confidence)

        Returns topics Grace should practice more.
        """
        gaps = []

        try:
            # Query learning examples with high theoretical but low practical confidence
            gap_examples = self.session.query(LearningExample).filter(
                and_(
                    LearningExample.metadata['data_confidence'].astext.cast(float) >= min_data_confidence,
                    LearningExample.metadata['operational_confidence'].astext.cast(float) <= max_operational_confidence
                )
            ).limit(20).all()

            for example in gap_examples:
                topic = example.input_context.get('topic', 'Unknown')
                metadata = example.metadata or {}

                gaps.append({
                    "topic": topic,
                    "data_confidence": metadata.get('data_confidence', 0.0),
                    "operational_confidence": metadata.get('operational_confidence', 0.0),
                    "gap_size": metadata.get('data_confidence', 0.0) - metadata.get('operational_confidence', 0.0),
                    "recommendation": "practice",
                    "reason": f"Grace knows '{topic}' theoretically but needs hands-on practice",
                    "learning_example_id": example.id
                })

            # Sort by gap size (biggest gaps first)
            gaps.sort(key=lambda x: x['gap_size'], reverse=True)

            logger.info(f"[MEMORY-MESH-LEARNER] Identified {len(gaps)} knowledge gaps")

        except Exception as e:
            # Suppress error logs for now as this feature is experimental
            logger.debug(f"Error identifying knowledge gaps: {e}")

        return gaps

    # ======================================================================
    # HIGH-VALUE TOPICS
    # ======================================================================

    def identify_high_value_topics(
        self,
        min_trust_score: float = 0.8,
        min_occurrences: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Identify high-value topics worth reinforcing.

        A topic is high-value when:
        - High trust score (proven reliable)
        - Appears frequently (important)
        - Could benefit from additional practice

        Returns topics Grace should reinforce through practice.
        """
        high_value_topics = []

        try:
            # Group by topic and find high-trust, frequently occurring topics
            topic_stats = self.session.query(
                LearningExample.input_context['topic'].astext.label('topic'),
                func.count(LearningExample.id).label('count'),
                func.avg(LearningExample.trust_score).label('avg_trust')
            ).group_by(
                LearningExample.input_context['topic'].astext
            ).having(
                and_(
                    func.count(LearningExample.id) >= min_occurrences,
                    func.avg(LearningExample.trust_score) >= min_trust_score
                )
            ).all()

            for topic, count, avg_trust in topic_stats:
                if topic:
                    high_value_topics.append({
                        "topic": topic,
                        "occurrences": count,
                        "avg_trust_score": float(avg_trust),
                        "recommendation": "reinforce",
                        "reason": f"High-value topic (trust={avg_trust:.2f}) that appears {count} times",
                        "priority": int(count * avg_trust)  # Priority = frequency * trust
                    })

            # Sort by priority
            high_value_topics.sort(key=lambda x: x['priority'], reverse=True)

            logger.info(f"[MEMORY-MESH-LEARNER] Identified {len(high_value_topics)} high-value topics")

        except Exception as e:
            logger.debug(f"Error identifying high-value topics: {e}")

        return high_value_topics

    # ======================================================================
    # TOPIC RELATIONSHIPS
    # ======================================================================

    def identify_related_topic_clusters(
        self,
        min_correlation: float = 0.6
    ) -> List[Dict[str, Any]]:
        """
        Identify topics that frequently appear together.

        When Grace learns topic A, she should also learn related topic B.

        Returns topic pairs that should be studied together.
        """
        clusters = []

        try:
            # Get all topics from learning examples
            all_examples = self.session.query(LearningExample).limit(500).all()

            # Group by source file to find co-occurring topics
            file_topics: Dict[str, List[str]] = {}

            for example in all_examples:
                file_path = example.metadata.get('file_path', 'unknown')
                topic = example.input_context.get('topic', 'Unknown')

                if file_path not in file_topics:
                    file_topics[file_path] = []

                if topic not in file_topics[file_path]:
                    file_topics[file_path].append(topic)

            # Find topic pairs that co-occur frequently
            topic_pairs: Dict[Tuple[str, str], int] = {}

            for topics in file_topics.values():
                # For each pair of topics in the same file
                for i, topic1 in enumerate(topics):
                    for topic2 in topics[i+1:]:
                        pair = tuple(sorted([topic1, topic2]))
                        topic_pairs[pair] = topic_pairs.get(pair, 0) + 1

            # Filter by minimum correlation
            total_files = len(file_topics)
            for (topic1, topic2), count in topic_pairs.items():
                correlation = count / total_files

                if correlation >= min_correlation:
                    clusters.append({
                        "topic1": topic1,
                        "topic2": topic2,
                        "co_occurrences": count,
                        "correlation": correlation,
                        "recommendation": "study_together",
                        "reason": f"Topics '{topic1}' and '{topic2}' appear together {count} times (correlation={correlation:.2f})"
                    })

            # Sort by correlation
            clusters.sort(key=lambda x: x['correlation'], reverse=True)

            logger.info(f"[MEMORY-MESH-LEARNER] Identified {len(clusters)} topic clusters")

        except Exception as e:
            logger.debug(f"Error identifying topic clusters: {e}")

        return clusters

    # ======================================================================
    # FAILURE PATTERN ANALYSIS
    # ======================================================================

    def analyze_failure_patterns(self) -> List[Dict[str, Any]]:
        """
        Analyze failures to identify what needs re-study.

        Looks for:
        - Topics with low validation counts
        - Recently failed practice attempts
        - Inconsistent knowledge (contradictions)

        Returns topics Grace should re-study.
        """
        failure_patterns = []

        try:
            # Find examples with low or negative validation
            failing_examples = self.session.query(LearningExample).filter(
                or_(
                    LearningExample.times_validated < 1,
                    LearningExample.times_invalidated > 0
                )
            ).limit(20).all()

            for example in failing_examples:
                topic = example.input_context.get('topic', 'Unknown')
                metadata = example.metadata or {}

                failure_patterns.append({
                    "topic": topic,
                    "times_validated": example.times_validated,
                    "times_invalidated": example.times_invalidated,
                    "trust_score": example.trust_score,
                    "recommendation": "restudy",
                    "reason": f"Topic '{topic}' has {example.times_invalidated} failures and only {example.times_validated} successes",
                    "learning_example_id": example.id,
                    "urgency": "high" if example.times_invalidated > 2 else "medium"
                })

            logger.info(f"[MEMORY-MESH-LEARNER] Identified {len(failure_patterns)} failure patterns")

        except Exception as e:
            logger.error(f"Error analyzing failure patterns: {e}")

        return failure_patterns

    # ======================================================================
    # COMPREHENSIVE LEARNING SUGGESTIONS
    # ======================================================================

    def get_learning_suggestions(self) -> Dict[str, Any]:
        """
        Get comprehensive learning suggestions from memory mesh.

        Combines all analysis types:
        - Knowledge gaps
        - High-value topics
        - Related clusters
        - Failure patterns

        Returns prioritized list of what Grace should learn next.
        """
        suggestions = {
            "timestamp": datetime.now().isoformat(),
            "knowledge_gaps": [],
            "high_value_topics": [],
            "related_clusters": [],
            "failure_patterns": [],
            "top_priorities": []
        }

        try:
            # Run all analyses
            suggestions["knowledge_gaps"] = self.identify_knowledge_gaps()
            suggestions["high_value_topics"] = self.identify_high_value_topics()
            suggestions["related_clusters"] = self.identify_related_topic_clusters()
            suggestions["failure_patterns"] = self.analyze_failure_patterns()

            # Compile top priorities
            priorities = []

            # Add urgent failures
            for pattern in suggestions["failure_patterns"]:
                if pattern.get("urgency") == "high":
                    priorities.append({
                        "topic": pattern["topic"],
                        "action": "restudy",
                        "priority": 1,
                        "reason": pattern["reason"]
                    })

            # Add biggest knowledge gaps
            for gap in suggestions["knowledge_gaps"][:5]:
                priorities.append({
                    "topic": gap["topic"],
                    "action": "practice",
                    "priority": 2,
                    "reason": gap["reason"]
                })

            # Add high-value topics
            for topic_info in suggestions["high_value_topics"][:3]:
                priorities.append({
                    "topic": topic_info["topic"],
                    "action": "reinforce",
                    "priority": 3,
                    "reason": topic_info["reason"]
                })

            suggestions["top_priorities"] = priorities

            logger.info(
                f"[MEMORY-MESH-LEARNER] Generated learning suggestions: "
                f"{len(priorities)} top priorities"
            )

        except Exception as e:
            logger.error(f"Error getting learning suggestions: {e}")

        return suggestions


# ======================================================================
# GLOBAL INSTANCE
# ======================================================================

def get_memory_mesh_learner(session: Session) -> MemoryMeshLearner:
    """Get memory mesh learner instance."""
    return MemoryMeshLearner(session=session)
