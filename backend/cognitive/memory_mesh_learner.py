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
            # Query learning examples; filter in Python (example_metadata is Text, not SA MetaData)
            import json
            all_examples = self.session.query(LearningExample).limit(200).all()
            gap_examples = []
            for example in all_examples:
                meta = {}
                if getattr(example, 'example_metadata', None):
                    try:
                        meta = json.loads(example.example_metadata) if isinstance(example.example_metadata, str) else (example.example_metadata or {})
                    except Exception:
                        pass
                dc = float(meta.get('data_confidence', 0))
                oc = float(meta.get('operational_confidence', 1))
                if dc >= min_data_confidence and oc <= max_operational_confidence:
                    gap_examples.append(example)
                if len(gap_examples) >= 20:
                    break

            for example in gap_examples:
                ctx = example.input_context if isinstance(example.input_context, dict) else {}
                if isinstance(example.input_context, str):
                    try:
                        ctx = json.loads(example.input_context)
                    except Exception:
                        ctx = {}
                topic = ctx.get('topic', 'Unknown')
                meta = {}
                if getattr(example, 'example_metadata', None):
                    try:
                        meta = json.loads(example.example_metadata) if isinstance(example.example_metadata, str) else (example.example_metadata or {})
                    except Exception:
                        pass
                dc = float(meta.get('data_confidence', 0))
                oc = float(meta.get('operational_confidence', 0))
                gaps.append({
                    "topic": topic,
                    "data_confidence": dc,
                    "operational_confidence": oc,
                    "gap_size": dc - oc,
                    "recommendation": "practice",
                    "reason": f"Grace knows '{topic}' theoretically but needs hands-on practice",
                    "learning_example_id": example.id
                })

            # Sort by gap size (biggest gaps first)
            gaps.sort(key=lambda x: x['gap_size'], reverse=True)

            logger.info(f"[MEMORY-MESH-LEARNER] Identified {len(gaps)} knowledge gaps")

        except Exception as e:
            logger.error("[MEMORY-MESH-LEARNER] FAILED identifying knowledge gaps (fix LearningExample/example_metadata): %s", e, exc_info=True)

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
            # Fetch examples and group by topic in Python (input_context is Text, not JSON column)
            import json
            examples = self.session.query(LearningExample).filter(
                LearningExample.trust_score >= min_trust_score
            ).limit(500).all()
            topic_counts = {}
            topic_trust_sum = {}
            for ex in examples:
                ctx = ex.input_context if isinstance(ex.input_context, dict) else {}
                if isinstance(ex.input_context, str):
                    try:
                        ctx = json.loads(ex.input_context)
                    except Exception:
                        ctx = {}
                topic = (ctx.get('topic') or '').strip()
                if not topic:
                    continue
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
                topic_trust_sum[topic] = topic_trust_sum.get(topic, 0) + (ex.trust_score or 0)
            for topic, count in topic_counts.items():
                if count >= min_occurrences:
                    avg_trust = topic_trust_sum[topic] / count
                    if avg_trust >= min_trust_score:
                        high_value_topics.append({
                            "topic": topic,
                            "occurrences": count,
                            "avg_trust_score": float(avg_trust),
                            "recommendation": "reinforce",
                            "reason": f"High-value topic (trust={avg_trust:.2f}) that appears {count} times",
                            "priority": int(count * avg_trust)
                        })

            # Sort by priority
            high_value_topics.sort(key=lambda x: x['priority'], reverse=True)

            logger.info(f"[MEMORY-MESH-LEARNER] Identified {len(high_value_topics)} high-value topics")

        except Exception as e:
            logger.error("[MEMORY-MESH-LEARNER] FAILED identifying high-value topics: %s", e, exc_info=True)

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
        """
        clusters = []

        try:
            import json

            def _parse(val):
                if isinstance(val, dict): return val
                if isinstance(val, str):
                    try: return json.loads(val)
                    except Exception: return {}
                return {}

            all_examples = self.session.query(LearningExample).limit(500).all()
            file_topics: Dict[str, List[str]] = {}

            for example in all_examples:
                meta = _parse(getattr(example, 'example_metadata', None) or getattr(example, 'metadata', None))
                ctx = _parse(example.input_context)
                file_path = meta.get('file_path', 'unknown')
                topic = ctx.get('topic', '').strip() or 'Unknown'

                if file_path not in file_topics:
                    file_topics[file_path] = []
                if topic not in file_topics[file_path]:
                    file_topics[file_path].append(topic)

            topic_pairs: Dict[tuple, int] = {}
            for topics in file_topics.values():
                for i, topic1 in enumerate(topics):
                    for topic2 in topics[i+1:]:
                        pair = tuple(sorted([topic1, topic2]))
                        topic_pairs[pair] = topic_pairs.get(pair, 0) + 1

            total_files = max(len(file_topics), 1)
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

            clusters.sort(key=lambda x: x['correlation'], reverse=True)
            logger.info("[MEMORY-MESH-LEARNER] Identified %d topic clusters", len(clusters))

        except Exception as e:
            logger.debug("Error identifying topic clusters: %s", e)

        return clusters


    # ======================================================================
    # FAILURE PATTERN ANALYSIS
    # ======================================================================

    def analyze_failure_patterns(self) -> List[Dict[str, Any]]:
        """
        Analyze failures to identify what needs re-study.
        """
        failure_patterns = []

        try:
            import json

            def _parse(val):
                if isinstance(val, dict): return val
                if isinstance(val, str):
                    try: return json.loads(val)
                    except Exception: return {}
                return {}

            # Find examples with low or negative validation
            failing_examples = self.session.query(LearningExample).filter(
                or_(
                    LearningExample.times_validated < 1,
                    LearningExample.times_invalidated > 0
                )
            ).limit(20).all()

            for example in failing_examples:
                ctx = _parse(example.input_context)
                topic = ctx.get('topic', 'Unknown')
                metadata = _parse(getattr(example, 'example_metadata', None) or getattr(example, 'metadata', None))

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

            logger.info("[MEMORY-MESH-LEARNER] Identified %d failure patterns", len(failure_patterns))

        except Exception as e:
            logger.error("[MEMORY-MESH-LEARNER] Error analyzing failure patterns: %s", e)

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
            "timestamp": datetime.utcnow().isoformat(),
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

            try:
                from api._genesis_tracker import track
                track(
                    key_type="gap_identified",
                    what=f"Memory mesh analysis: {len(suggestions['knowledge_gaps'])} gaps, "
                         f"{len(suggestions['failure_patterns'])} failures, "
                         f"{len(priorities)} priorities",
                    who="memory_mesh_learner",
                    how="identify_gaps + high_value + failures + clusters",
                    output_data={
                        "gap_count": len(suggestions["knowledge_gaps"]),
                        "failure_count": len(suggestions["failure_patterns"]),
                        "priority_count": len(priorities),
                        "top_topics": [p["topic"] for p in priorities[:5]],
                    },
                    tags=["memory-mesh", "learning", "gap-analysis"],
                )
            except Exception:
                pass

        except Exception as e:
            logger.error(f"Error getting learning suggestions: {e}")

        return suggestions


# ======================================================================
# GLOBAL INSTANCE
# ======================================================================

def get_memory_mesh_learner(session: Session) -> MemoryMeshLearner:
    """Get memory mesh learner instance."""
    return MemoryMeshLearner(session=session)
