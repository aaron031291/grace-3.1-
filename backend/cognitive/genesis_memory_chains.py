"""
Genesis Memory Chains

Tracks the complete learning journey for each Genesis Key:
- Episodic chain: All experiences related to that source
- Trust evolution: How understanding deepened over time
- Procedural emergence: Skills extracted from that source
- Knowledge graph: Connections between concepts

Grace Alignment: Maintains episodic continuity and learning narrative
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from datetime import datetime, timedelta
import json

from models.database_models import (
    LearningExample,
    Episode,
    Procedure
)
from models.genesis_key_models import GenesisKey

logger = logging.getLogger(__name__)


class GenesisMemoryChain:
    """
    Tracks complete memory chain for a Genesis Key.

    Represents Grace's learning journey from a specific source:
    - Initial ingestion → Learning examples → Episodes → Procedures
    """

    def __init__(self, session: Session):
        """
        Initialize Genesis Memory Chain tracker.

        Args:
            session: Database session
        """
        self.session = session
        logger.info("[GENESIS-MEMORY-CHAIN] Initialized")

    def get_memory_chain(
        self,
        genesis_key_id: str,
        include_timeline: bool = True
    ) -> Dict[str, Any]:
        """
        Get complete memory chain for Genesis Key.

        Args:
            genesis_key_id: Genesis Key ID
            include_timeline: Include detailed timeline

        Returns:
            Complete memory chain data
        """
        try:
            # Get Genesis Key
            genesis_key = self.session.query(GenesisKey).filter(
                GenesisKey.id == genesis_key_id
            ).first()

            if not genesis_key:
                logger.warning(
                    f"[GENESIS-MEMORY-CHAIN] Genesis Key not found: {genesis_key_id}"
                )
                return {}

            # Learning examples
            learning_examples = self.session.query(LearningExample).filter(
                LearningExample.genesis_key_id == genesis_key_id
            ).order_by(LearningExample.created_at).all()

            # Episodes
            episodes = self.session.query(Episode).filter(
                Episode.genesis_key_id == genesis_key_id
            ).order_by(Episode.created_at).all()

            # Procedures (via learning examples)
            procedures = self.session.query(Procedure).join(
                LearningExample,
                Procedure.id == LearningExample.procedure_id
            ).filter(
                LearningExample.genesis_key_id == genesis_key_id
            ).distinct().all()

            # Calculate trust evolution
            trust_evolution = [ex.trust_score for ex in learning_examples]
            trust_trend = self._calculate_trust_trend(trust_evolution)

            # Build chain
            chain = {
                "genesis_key_id": genesis_key_id,
                "genesis_key_name": genesis_key.key_id if genesis_key else "Unknown",
                "source": genesis_key.who_actor if genesis_key else "Unknown",
                "created_at": genesis_key.created_at.isoformat() if genesis_key and genesis_key.created_at else None,

                "learning_journey": {
                    "total_examples": len(learning_examples),
                    "high_trust_examples": sum(1 for ex in learning_examples if ex.trust_score >= 0.7),
                    "trust_evolution": trust_evolution,
                    "trust_trend": trust_trend,
                    "avg_trust": sum(trust_evolution) / len(trust_evolution) if trust_evolution else 0,

                    "episodes_created": len(episodes),
                    "high_trust_episodes": sum(1 for ep in episodes if ep.trust_score >= 0.7),

                    "skills_emerged": len(procedures),
                    "high_success_skills": sum(1 for p in procedures if p.success_rate >= 0.7)
                },

                "knowledge_depth": self._calculate_knowledge_depth(
                    learning_examples,
                    episodes,
                    procedures
                ),

                "learning_velocity": self._calculate_learning_velocity(learning_examples)
            }

            if include_timeline:
                chain["timeline"] = self._build_timeline(
                    genesis_key,
                    learning_examples,
                    episodes,
                    procedures
                )

            logger.info(
                f"[GENESIS-MEMORY-CHAIN] Retrieved chain for {genesis_key_id}: "
                f"{len(learning_examples)} examples, {len(episodes)} episodes, "
                f"{len(procedures)} procedures"
            )

            return chain

        except Exception as e:
            logger.error(f"[GENESIS-MEMORY-CHAIN] Error getting chain: {e}")
            raise

    def _calculate_trust_trend(self, trust_scores: List[float]) -> str:
        """
        Calculate overall trust trend.

        Args:
            trust_scores: List of trust scores over time

        Returns:
            "improving", "stable", or "declining"
        """
        if len(trust_scores) < 3:
            return "insufficient_data"

        # Compare first third vs last third
        first_third = trust_scores[:len(trust_scores) // 3]
        last_third = trust_scores[-len(trust_scores) // 3:]

        avg_first = sum(first_third) / len(first_third)
        avg_last = sum(last_third) / len(last_third)

        diff = avg_last - avg_first

        if diff > 0.1:
            return "improving"
        elif diff < -0.1:
            return "declining"
        else:
            return "stable"

    def _calculate_knowledge_depth(
        self,
        learning_examples: List[LearningExample],
        episodes: List[Episode],
        procedures: List[Procedure]
    ) -> Dict[str, Any]:
        """
        Calculate knowledge depth metrics.

        Args:
            learning_examples: Learning examples
            episodes: Episodes
            procedures: Procedures

        Returns:
            Knowledge depth metrics
        """
        # Depth = how many layers of memory formed
        depth_score = 0

        if learning_examples:
            depth_score += 1  # Layer 1: Learning
        if episodes:
            depth_score += 1  # Layer 2: Episodic
        if procedures:
            depth_score += 1  # Layer 3: Procedural

        # Breadth = variety of example types
        example_types = set(ex.example_type for ex in learning_examples)
        breadth_score = len(example_types)

        # Mastery = average procedure success rate
        if procedures:
            mastery_score = sum(p.success_rate for p in procedures) / len(procedures)
        else:
            mastery_score = 0.0

        return {
            "depth_layers": depth_score,
            "max_depth": 3,
            "breadth_types": breadth_score,
            "mastery_score": mastery_score,
            "overall_depth": (depth_score / 3 + mastery_score) / 2
        }

    def _calculate_learning_velocity(
        self,
        learning_examples: List[LearningExample]
    ) -> Dict[str, Any]:
        """
        Calculate learning velocity (rate of learning).

        Args:
            learning_examples: Learning examples ordered by time

        Returns:
            Learning velocity metrics
        """
        if len(learning_examples) < 2:
            return {
                "examples_per_day": 0,
                "velocity": "not_enough_data"
            }

        # Time span
        first_time = learning_examples[0].created_at
        last_time = learning_examples[-1].created_at

        if not first_time or not last_time:
            return {"examples_per_day": 0, "velocity": "unknown"}

        time_span = (last_time - first_time).total_seconds() / 86400  # days

        if time_span == 0:
            time_span = 1  # Avoid division by zero

        examples_per_day = len(learning_examples) / time_span

        # Velocity classification
        if examples_per_day > 10:
            velocity = "rapid"
        elif examples_per_day > 3:
            velocity = "steady"
        elif examples_per_day > 0.5:
            velocity = "slow"
        else:
            velocity = "minimal"

        return {
            "examples_per_day": examples_per_day,
            "total_examples": len(learning_examples),
            "time_span_days": time_span,
            "velocity": velocity
        }

    def _build_timeline(
        self,
        genesis_key: GenesisKey,
        learning_examples: List[LearningExample],
        episodes: List[Episode],
        procedures: List[Procedure]
    ) -> List[Dict[str, Any]]:
        """
        Build chronological timeline of events.

        Args:
            genesis_key: Genesis Key
            learning_examples: Learning examples
            episodes: Episodes
            procedures: Procedures

        Returns:
            Chronological timeline
        """
        timeline = []

        # Genesis Key creation
        if genesis_key and genesis_key.created_at:
            timeline.append({
                "timestamp": genesis_key.created_at.isoformat(),
                "event_type": "genesis_key_created",
                "description": f"Genesis Key '{genesis_key.key_id}' created",
                "data": {
                    "genesis_key_id": genesis_key.key_id,
                    "source": genesis_key.who_actor
                }
            })

        # Learning examples
        for ex in learning_examples:
            if ex.created_at:
                timeline.append({
                    "timestamp": ex.created_at.isoformat(),
                    "event_type": "learning_ingested",
                    "description": f"Learning example ingested (trust={ex.trust_score:.2f})",
                    "data": {
                        "learning_id": ex.id,
                        "example_type": ex.example_type,
                        "trust_score": ex.trust_score
                    }
                })

        # Episodes
        for ep in episodes:
            if ep.created_at:
                timeline.append({
                    "timestamp": ep.created_at.isoformat(),
                    "event_type": "episode_created",
                    "description": f"Episode created (trust={ep.trust_score:.2f})",
                    "data": {
                        "episode_id": ep.id,
                        "trust_score": ep.trust_score
                    }
                })

        # Procedures
        for proc in procedures:
            if proc.created_at:
                timeline.append({
                    "timestamp": proc.created_at.isoformat(),
                    "event_type": "procedure_emerged",
                    "description": f"Procedure '{proc.name}' emerged (success={proc.success_rate:.2f})",
                    "data": {
                        "procedure_id": proc.id,
                        "name": proc.name,
                        "success_rate": proc.success_rate
                    }
                })

        # Sort chronologically
        timeline.sort(key=lambda x: x["timestamp"])

        return timeline

    def get_all_genesis_chains(
        self,
        min_learning_examples: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Get memory chains for all Genesis Keys.

        Args:
            min_learning_examples: Minimum learning examples to include

        Returns:
            List of memory chain summaries
        """
        try:
            # Get all Genesis Keys with learning
            genesis_keys = self.session.query(
                GenesisKey.id,
                GenesisKey.key_id,
                func.count(LearningExample.id).label('example_count')
            ).outerjoin(
                LearningExample,
                GenesisKey.key_id == LearningExample.genesis_key_id
            ).group_by(
                GenesisKey.id, GenesisKey.key_id
            ).having(
                func.count(LearningExample.id) >= min_learning_examples
            ).all()

            chains = []
            for gk_id, gk_name, example_count in genesis_keys:
                chain_summary = self.get_memory_chain(
                    genesis_key_id=gk_id,
                    include_timeline=False
                )
                chains.append(chain_summary)

            logger.info(
                f"[GENESIS-MEMORY-CHAIN] Retrieved {len(chains)} chains"
            )

            return chains

        except Exception as e:
            logger.error(f"[GENESIS-MEMORY-CHAIN] Error getting all chains: {e}")
            return []

    def get_learning_narrative(
        self,
        genesis_key_id: str
    ) -> str:
        """
        Generate natural language narrative of learning journey.

        Args:
            genesis_key_id: Genesis Key ID

        Returns:
            Natural language narrative
        """
        chain = self.get_memory_chain(genesis_key_id, include_timeline=True)

        if not chain:
            return f"No learning journey found for Genesis Key {genesis_key_id}"

        journey = chain["learning_journey"]
        depth = chain["knowledge_depth"]
        velocity = chain["learning_velocity"]

        narrative = f"""
Genesis Key: {chain['genesis_key_name']}
Source: {chain['source']}

Learning Journey:
- Total learning examples: {journey['total_examples']}
- High-trust examples: {journey['high_trust_examples']}
- Average trust score: {journey['avg_trust']:.2f}
- Trust trend: {journey['trust_trend']}

Memory Formation:
- Episodes created: {journey['episodes_created']} (episodic memory)
- Skills emerged: {journey['skills_emerged']} (procedural memory)
- High-success skills: {journey['high_success_skills']}

Knowledge Depth:
- Depth layers: {depth['depth_layers']}/{depth['max_depth']}
- Mastery score: {depth['mastery_score']:.2f}
- Overall depth: {depth['overall_depth']:.2f}

Learning Velocity:
- Rate: {velocity['examples_per_day']:.2f} examples/day
- Velocity: {velocity['velocity']}
- Time span: {velocity.get('time_span_days', 0):.1f} days
"""

        return narrative.strip()


# ================================================================
# FACTORY FUNCTION
# ================================================================

def get_genesis_memory_chain(session: Session) -> GenesisMemoryChain:
    """Get Genesis Memory Chain tracker"""
    return GenesisMemoryChain(session=session)
