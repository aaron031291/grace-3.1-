import logging
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from datetime import datetime, timedelta
import json
from models.database_models import LearningExample
from cognitive.episodic_memory import Episode
from cognitive.procedural_memory import Procedure
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
                return {
                    "error": "genesis_key_not_found",
                    "message": f"No learning journey exists for Genesis Key {genesis_key_id}. The specified Genesis Key may not exist in the system, or Grace has not yet begun learning from this source.",
                    "genesis_key_id": genesis_key_id
                }

            # Learning examples
            learning_examples = self.session.query(LearningExample).filter(
                LearningExample.genesis_key_id == genesis_key_id
            ).order_by(LearningExample.created_at).all()

            # Episodes
            episodes = self.session.query(Episode).filter(
                Episode.genesis_key_id == genesis_key_id
            ).order_by(Episode.timestamp).all()

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

            # Calculate metrics
            knowledge_depth = self._calculate_knowledge_depth(
                learning_examples,
                episodes,
                procedures
            )
            learning_velocity = self._calculate_learning_velocity(learning_examples)
            
            # Build chain
            chain = {
                "genesis_key_id": genesis_key_id,
                "genesis_key_name": genesis_key.name if genesis_key else "Unknown",
                "source": genesis_key.source if genesis_key else "Unknown",
                "created_at": genesis_key.created_at.isoformat() if genesis_key and genesis_key.created_at else None,

                "learning_journey": {
                    "total_examples": len(learning_examples),
                    "high_trust_examples": sum(1 for ex in learning_examples if ex.trust_score >= 0.7),
                    "trust_evolution": trust_evolution,
                    "trust_trend": trust_trend,
                    "trust_trend_nlp": self._format_trust_trend_nlp(
                        trust_trend, 
                        sum(trust_evolution) / len(trust_evolution) if trust_evolution else 0
                    ),
                    "avg_trust": sum(trust_evolution) / len(trust_evolution) if trust_evolution else 0,

                    "episodes_created": len(episodes),
                    "high_trust_episodes": sum(1 for ep in episodes if ep.trust_score >= 0.7),

                    "skills_emerged": len(procedures),
                    "high_success_skills": sum(1 for p in procedures if p.success_rate >= 0.7)
                },

                "knowledge_depth": {
                    **knowledge_depth,
                    "nlp_description": self._format_knowledge_depth_nlp(knowledge_depth)
                },

                "learning_velocity": {
                    **learning_velocity,
                    "nlp_description": self._format_velocity_nlp(
                        learning_velocity.get("velocity", "unknown"),
                        learning_velocity.get("examples_per_day", 0),
                        learning_velocity.get("time_span_days", 0.0)
                    )
                }
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
            return {}

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
    
    def _format_trust_trend_nlp(self, trend: str, avg_trust: float = 0.0) -> str:
        """Convert trust trend to enterprise-grade natural language with insights."""
        trend_map = {
            "improving": f"Grace's confidence in this knowledge base demonstrates a positive trajectory, indicating growing reliability and validation through successful application. The current average confidence level of {avg_trust:.0%} suggests this source is becoming increasingly trustworthy as Grace gains more experience with it.",
            "stable": f"Grace maintains consistent confidence levels (averaging {avg_trust:.0%}), indicating reliable and predictable knowledge quality. This stability suggests the source provides coherent and validated information without significant contradictions or uncertainty.",
            "declining": f"Grace's confidence has been declining, currently averaging {avg_trust:.0%}. This trend may indicate emerging inconsistencies, conflicting information, or observations that challenge previous assumptions. Reviewing recent learning examples for contradictions may provide insights into the declining confidence.",
            "insufficient_data": "Insufficient learning data exists to establish a meaningful confidence trend. Grace requires additional learning examples to assess knowledge reliability and determine patterns in trust evolution."
        }
        return trend_map.get(trend, f"Trust trend analysis: {trend} (average confidence: {avg_trust:.0%})")
    
    def _format_velocity_nlp(self, velocity: str, examples_per_day: float, time_span_days: float = 0.0) -> str:
        """Convert learning velocity to enterprise-grade natural language with context."""
        time_context = ""
        if time_span_days > 0:
            if time_span_days < 1:
                time_context = f" within the past {time_span_days * 24:.1f} hours"
            elif time_span_days < 7:
                time_context = f" over the past {time_span_days:.1f} days"
            elif time_span_days < 30:
                weeks = time_span_days / 7
                time_context = f" over the past {weeks:.1f} weeks"
            else:
                months = time_span_days / 30
                time_context = f" over the past {months:.1f} months"
        
        velocity_map = {
            "rapid": f"Grace demonstrates exceptional learning velocity, processing an average of {examples_per_day:.1f} examples per day{time_context}. This accelerated pace indicates high engagement with the source material and suggests rapid knowledge acquisition. Such velocity typically correlates with comprehensive knowledge base development and deep understanding formation.",
            "steady": f"Grace maintains a steady, sustainable learning pace of {examples_per_day:.1f} examples per day{time_context}. This consistent rate indicates reliable knowledge ingestion and suggests a well-balanced approach to learning that allows for proper processing and integration of new information into Grace's cognitive framework.",
            "slow": f"Grace is learning gradually at a rate of {examples_per_day:.1f} examples per day{time_context}. While slower, this measured pace may indicate more deliberate and thorough processing of complex information. Consider whether the source material requires more careful analysis or if additional engagement opportunities exist.",
            "minimal": f"Learning activity is minimal, with only {examples_per_day:.2f} examples processed per day{time_context}. This low velocity suggests limited exposure to new material from this source. To accelerate learning, consider increasing the frequency of interactions or expanding the scope of source material available to Grace.",
            "not_enough_data": "Insufficient temporal data exists to calculate meaningful learning velocity. Grace requires multiple learning examples with timestamps to assess the rate of knowledge acquisition. Once more examples are available, velocity analysis will provide insights into learning dynamics.",
            "unknown": "Unable to determine learning velocity due to missing or incomplete timestamp data in the learning examples. Ensuring proper timestamp recording will enable velocity tracking and provide valuable insights into Grace's learning patterns."
        }
        return velocity_map.get(velocity, f"Learning velocity assessment: {velocity} ({examples_per_day:.2f} examples/day)")
    
    def _format_knowledge_depth_nlp(self, depth_data: Dict[str, Any]) -> str:
        """Convert knowledge depth metrics to enterprise-grade natural language with comprehensive analysis."""
        layers = depth_data.get("depth_layers", 0)
        max_layers = depth_data.get("max_depth", 3)
        mastery = depth_data.get("mastery_score", 0.0)
        breadth = depth_data.get("breadth_types", 0)
        overall_depth = depth_data.get("overall_depth", 0.0)
        
        # Build sophisticated description of depth layers
        depth_components = []
        if layers >= 1:
            depth_components.append("established foundational understanding through example-based learning")
        if layers >= 2:
            depth_components.append("developed episodic memory structures capturing concrete experiences")
        if layers >= 3:
            depth_components.append("extracted procedural knowledge, transforming experiences into actionable skills")
        
        # Create depth assessment
        if layers == 0:
            depth_assessment = "Grace has just begun the learning process and has not yet established significant knowledge structures."
        elif layers == 1:
            depth_assessment = f"Grace has {depth_components[0]}, representing the initial stage of knowledge acquisition."
        elif layers == 2:
            depth_assessment = f"Grace has progressed to intermediate depth: {depth_components[0]} and {depth_components[1]}."
        else:
            depth_assessment = f"Grace has achieved comprehensive knowledge depth: {', '.join(depth_components)}."
        
        # Add mastery assessment
        mastery_assessment = ""
        if mastery > 0:
            if mastery >= 0.8:
                mastery_assessment = f" The procedural skills demonstrate exceptional mastery ({mastery:.0%}), indicating highly reliable and well-validated knowledge."
            elif mastery >= 0.6:
                mastery_assessment = f" Procedural knowledge shows strong mastery levels ({mastery:.0%}), suggesting well-developed and consistently successful skills."
            elif mastery >= 0.4:
                mastery_assessment = f" Mastery levels are developing ({mastery:.0%}), with skills showing promise but requiring further validation."
            else:
                mastery_assessment = f" Mastery is still emerging ({mastery:.0%}), indicating skills are in early stages of development."
        
        # Add breadth assessment
        breadth_assessment = ""
        if breadth > 1:
            if breadth >= 5:
                breadth_assessment = f" The knowledge spans {breadth} distinct experience types, demonstrating exceptional diversity and comprehensive coverage."
            elif breadth >= 3:
                breadth_assessment = f" Knowledge encompasses {breadth} different experience types, showing good diversity in learning."
            else:
                breadth_assessment = f" Learning includes {breadth} different types of experiences, providing some variety in knowledge."
        
        # Overall depth assessment
        overall_assessment = ""
        if overall_depth >= 0.8:
            overall_assessment = " Overall, Grace demonstrates exceptional knowledge depth and mastery."
        elif overall_depth >= 0.6:
            overall_assessment = " Grace has achieved substantial knowledge depth."
        elif overall_depth >= 0.4:
            overall_assessment = " Knowledge depth is developing but has room for growth."
        else:
            overall_assessment = " Knowledge depth is in early stages, with significant potential for expansion."
        
        return f"{depth_assessment}{mastery_assessment}{breadth_assessment}{overall_assessment}"

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
            # Get a friendly name for the source
            source_name = (genesis_key.name or genesis_key.source or "an unknown source").strip()
            if not source_name or source_name == "Unknown":
                source_name = "this source"
            
            # Enhanced genesis key description
            where_info = ""
            if genesis_key.where_location:
                where_info = f" (located at {genesis_key.where_location})"
            
            who_info = ""
            if genesis_key.who_actor and genesis_key.who_actor != "system":
                who_info = f" initiated by {genesis_key.who_actor}"
            
            timeline.append({
                "timestamp": genesis_key.created_at.isoformat(),
                "event_type": "genesis_key_created",
                "description": f"Grace began learning from '{source_name}'",
                "nlp_description": f"Grace's learning journey commenced with discovery of '{source_name}'{where_info}{who_info}. This marks the initial point of knowledge acquisition from this source, establishing the foundation for future learning and memory formation.",
                "data": {
                    "genesis_key_id": genesis_key.id,
                    "source": genesis_key.source,
                    "where_location": genesis_key.where_location,
                    "who_actor": genesis_key.who_actor
                }
            })

        # Learning examples
        for ex in learning_examples:
            if ex.created_at:
                # Enhanced trust description with context
                if ex.trust_score >= 0.8:
                    trust_desc = "exceptional confidence"
                    trust_detail = "indicating highly reliable and well-validated information"
                elif ex.trust_score >= 0.7:
                    trust_desc = "high confidence"
                    trust_detail = "reflecting strong reliability and validation"
                elif ex.trust_score >= 0.5:
                    trust_desc = "moderate confidence"
                    trust_detail = "suggesting acceptable reliability with some uncertainty"
                elif ex.trust_score >= 0.3:
                    trust_desc = "guarded confidence"
                    trust_detail = "indicating cautious acceptance with noted limitations"
                else:
                    trust_desc = "low confidence"
                    trust_detail = "requiring careful evaluation and additional validation"
                
                example_type_label = ex.example_type.replace('_', ' ').title() if ex.example_type else 'example'
                timeline.append({
                    "timestamp": ex.created_at.isoformat(),
                    "event_type": "learning_ingested",
                    "description": f"Grace learned a new example with {trust_desc} (trust: {ex.trust_score:.2f})",
                    "nlp_description": f"Grace ingested a new {example_type_label.lower()} with {trust_desc} ({trust_detail}), contributing to the expanding knowledge base",
                    "data": {
                        "learning_id": ex.id,
                        "example_type": ex.example_type,
                        "trust_score": ex.trust_score
                    }
                })

        # Episodes
        for ep in episodes:
            if ep.timestamp:
                # Enhanced episode trust description
                if ep.trust_score >= 0.8:
                    trust_desc = "exceptional confidence"
                    trust_context = "forming a highly reliable episodic memory"
                elif ep.trust_score >= 0.7:
                    trust_desc = "high confidence"
                    trust_context = "creating a strong episodic memory"
                elif ep.trust_score >= 0.5:
                    trust_desc = "moderate confidence"
                    trust_context = "storing an episodic memory with acceptable reliability"
                elif ep.trust_score >= 0.3:
                    trust_desc = "guarded confidence"
                    trust_context = "forming an episodic memory requiring careful interpretation"
                else:
                    trust_desc = "low confidence"
                    trust_context = "capturing an episodic memory with noted uncertainty"
                
                timeline.append({
                    "timestamp": ep.timestamp.isoformat(),
                    "event_type": "episode_created",
                    "description": f"Grace formed a memory of a concrete experience with {trust_desc}",
                    "nlp_description": f"Grace encoded a concrete experience into episodic memory with {trust_desc}, {trust_context} that can inform future decision-making",
                    "data": {
                        "episode_id": ep.id,
                        "trust_score": ep.trust_score
                    }
                })

        # Procedures
        for proc in procedures:
            if proc.created_at:
                # Enhanced procedure success description
                proc_name_formatted = proc.name.replace('_', ' ').title()
                if proc.success_rate >= 0.9:
                    success_desc = "exceptional success rate"
                    success_context = "demonstrating mastery-level reliability and effectiveness"
                elif proc.success_rate >= 0.7:
                    success_desc = "high success rate"
                    success_context = "showing strong reliability and consistent effectiveness"
                elif proc.success_rate >= 0.5:
                    success_desc = "moderate success rate"
                    success_context = "indicating developing reliability with room for improvement"
                elif proc.success_rate >= 0.3:
                    success_desc = "emerging success rate"
                    success_context = "demonstrating early-stage development requiring further validation"
                else:
                    success_desc = "developing success rate"
                    success_context = "in initial stages of formation with limited validation"
                
                timeline.append({
                    "timestamp": proc.created_at.isoformat(),
                    "event_type": "procedure_emerged",
                    "description": f"Grace developed a new skill: '{proc_name_formatted}' with {success_desc} ({proc.success_rate:.0%})",
                    "nlp_description": f"Grace extracted procedural knowledge for '{proc_name_formatted}' with a {success_desc} of {proc.success_rate:.0%}, {success_context}. This skill can now be applied to similar scenarios",
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
                GenesisKey.name,
                func.count(LearningExample.id).label('example_count')
            ).outerjoin(
                LearningExample,
                GenesisKey.id == LearningExample.genesis_key_id
            ).group_by(
                GenesisKey.id, GenesisKey.name
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
        genesis_key_id: str,
        format: str = "markdown"
    ) -> str:
        """
        Generate enterprise-grade natural language narrative of learning journey.

        Args:
            genesis_key_id: Genesis Key ID
            format: Output format - "markdown", "plain", or "executive"

        Returns:
            Comprehensive natural language narrative
        """
        chain = self.get_memory_chain(genesis_key_id, include_timeline=True)

        if not chain:
            return f"**Learning Journey Not Found**\n\nNo learning journey exists for Genesis Key {genesis_key_id}. Grace has not yet begun learning from this source, or the Genesis Key may not exist in the system."

        journey = chain["learning_journey"]
        depth = chain["knowledge_depth"]
        velocity = chain["learning_velocity"]
        genesis_name = chain.get('genesis_key_name') or chain.get('source') or 'this source'
        
        # Format creation date
        created_at = chain.get('created_at', 'recently')
        if created_at and created_at != 'recently':
            try:
                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                created_at_formatted = dt.strftime("%B %d, %Y at %I:%M %p")
            except:
                created_at_formatted = created_at
        else:
            created_at_formatted = "recently"
        
        # Build executive summary
        total_examples = journey.get('total_examples', 0)
        high_trust_pct = (journey.get('high_trust_examples', 0) / total_examples * 100) if total_examples > 0 else 0
        episodes = journey.get('episodes_created', 0)
        skills = journey.get('skills_emerged', 0)
        
        # Build enterprise-grade narrative
        narrative_parts = [
            f"# Learning Journey Analysis: {genesis_name}",
            "",
            "## Executive Summary",
            "",
            f"Grace's learning journey from '{genesis_name}' began on {created_at_formatted}. Over the course of this engagement, Grace has processed {total_examples} learning example{'s' if total_examples != 1 else ''}, with {high_trust_pct:.0%} achieving high confidence ratings. "
        ]
        
        # Add summary insights
        if total_examples > 0:
            narrative_parts.append(
                f"The knowledge acquisition process has resulted in {episodes} episodic memory formation{'s' if episodes != 1 else ''} and the development of {skills} procedural skill{'s' if skills != 1 else ''}, "
            )
        
        if depth.get('depth_layers', 0) == 3:
            narrative_parts.append("demonstrating comprehensive three-layer knowledge depth.")
        elif depth.get('depth_layers', 0) == 2:
            narrative_parts.append("showing progression to intermediate knowledge depth with episodic memory formation.")
        elif depth.get('depth_layers', 0) == 1:
            narrative_parts.append("establishing foundational knowledge through example-based learning.")
        else:
            narrative_parts.append("with learning still in initial stages.")
        
        narrative_parts.extend([
            "",
            "## Detailed Analysis",
            "",
            "### Knowledge Acquisition Metrics",
            "",
            f"**Learning Volume**: {total_examples} total learning example{'s' if total_examples != 1 else ''} processed",
            f"**High Confidence Examples**: {journey.get('high_trust_examples', 0)} out of {total_examples} ({high_trust_pct:.0%})",
            f"**Average Confidence Level**: {journey.get('avg_trust', 0):.0%}",
            "",
            "### Trust and Confidence Analysis",
            "",
            journey.get('trust_trend_nlp', f"Trust trend analysis unavailable. Raw trend: {journey.get('trust_trend', 'unknown')}"),
            "",
            "### Memory Formation and Knowledge Structures",
            "",
            f"**Episodic Memories**: {episodes} concrete experience{'s' if episodes != 1 else ''} encoded"
        ])
        
        if episodes > 0:
            high_trust_episodes = journey.get('high_trust_episodes', 0)
            episode_trust_pct = (high_trust_episodes / episodes * 100) if episodes > 0 else 0
            narrative_parts.append(f"  - {high_trust_episodes} high-confidence memory{'ies' if high_trust_episodes != 1 else ''} ({episode_trust_pct:.0%})")
        
        narrative_parts.append(f"**Procedural Skills**: {skills} skill{'s' if skills != 1 else ''} developed")
        
        if skills > 0:
            high_success = journey.get('high_success_skills', 0)
            success_pct = (high_success / skills * 100) if skills > 0 else 0
            narrative_parts.append(f"  - {high_success} highly successful skill{'s' if high_success != 1 else ''} ({success_pct:.0%})")
        
        narrative_parts.extend([
            "",
            "### Knowledge Depth Assessment",
            "",
            depth.get('nlp_description', 'Knowledge depth information unavailable.'),
            "",
            "### Learning Velocity Analysis",
            "",
            velocity.get('nlp_description', 'Learning velocity information unavailable.'),
        ])
        
        # Add timeline summary if available
        if chain.get('timeline'):
            timeline = chain['timeline']
            time_span = velocity.get('time_span_days', 0)
            
            narrative_parts.extend([
                "",
                "## Learning Timeline and Milestones",
                "",
                f"The learning journey spans {time_span:.1f} day{'s' if time_span != 1 else ''}, with {len(timeline)} significant learning event{'s' if len(timeline) != 1 else ''} recorded:",
                ""
            ])
            
            # Group events by type for better organization
            for i, event in enumerate(timeline[:15], 1):  # Show first 15 events
                timestamp = event.get('timestamp', '')
                if timestamp:
                    try:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        time_str = dt.strftime("%m/%d/%Y %I:%M %p")
                    except:
                        time_str = timestamp[:16]  # First part of ISO format
                else:
                    time_str = "Unknown time"
                
                narrative_parts.append(f"**{i}. {time_str}** - {event.get('nlp_description', event.get('description', 'Unknown event'))}")
            
            if len(timeline) > 15:
                narrative_parts.append(f"\n*... and {len(timeline) - 15} additional learning events recorded.*")
        
        narrative_parts.extend([
            "",
            "---",
            f"*Report generated for Genesis Key: {genesis_key_id}*"
        ])
        
        return "\n".join(narrative_parts)
    
    def get_nlp_summary(
        self,
        genesis_key_id: str
    ) -> Dict[str, Any]:
        """
        Get NLP-friendly summary of learning journey as structured data.
        
        Args:
            genesis_key_id: Genesis Key ID
            
        Returns:
            Dictionary with NLP-friendly descriptions for all metrics
        """
        chain = self.get_memory_chain(genesis_key_id, include_timeline=True)
        
        if not chain:
            return {
                "summary": f"I couldn't find a learning journey for Genesis Key {genesis_key_id}.",
                "status": "not_found"
            }
        
        journey = chain.get("learning_journey", {})
        depth = chain.get("knowledge_depth", {})
        velocity = chain.get("learning_velocity", {})
        genesis_name = chain.get('genesis_key_name') or chain.get('source') or 'this source'
        
        return {
            "status": "found",
            "source_name": genesis_name,
            "overview": {
                "introduction": f"Grace has been learning from '{genesis_name}' since {chain.get('created_at', 'recently')}.",
                "total_examples": journey.get('total_examples', 0),
                "example_description": f"Grace has processed {journey.get('total_examples', 0)} learning example{'s' if journey.get('total_examples', 0) != 1 else ''} from this source."
            },
            "trust_analysis": {
                "trend": journey.get('trust_trend_nlp', 'Unable to determine trust trend'),
                "trend_category": journey.get('trust_trend', 'unknown'),
                "average_confidence": f"{journey.get('avg_trust', 0):.0%}",
                "average_confidence_raw": journey.get('avg_trust', 0),
                "high_confidence_count": journey.get('high_trust_examples', 0),
                "high_confidence_percentage": f"{(journey.get('high_trust_examples', 0) / journey.get('total_examples', 1) * 100):.1f}%" if journey.get('total_examples', 0) > 0 else "0%",
                "description": f"On average, Grace's confidence level is {journey.get('avg_trust', 0):.0%}, with {journey.get('high_trust_examples', 0)} out of {journey.get('total_examples', 0)} examples receiving high confidence scores."
            },
            "memory_formation": {
                "episodes": journey.get('episodes_created', 0),
                "skills": journey.get('skills_emerged', 0),
                "description": f"Grace has formed {journey.get('episodes_created', 0)} episodic memor{'ies' if journey.get('episodes_created', 0) != 1 else 'y'} and developed {journey.get('skills_emerged', 0)} procedural skill{'s' if journey.get('skills_emerged', 0) != 1 else ''} from this learning."
            },
            "knowledge_depth": {
                "description": depth.get('nlp_description', 'Knowledge depth information unavailable.')
            },
            "learning_pace": {
                "description": velocity.get('nlp_description', 'Learning velocity information unavailable.')
            },
            "full_narrative": self.get_learning_narrative(genesis_key_id),
            "insights": self._generate_insights(chain),
            "recommendations": self._generate_recommendations(chain)
        }
    
    def _generate_insights(self, chain: Dict[str, Any]) -> List[str]:
        """Generate enterprise-grade insights from learning chain data."""
        insights = []
        journey = chain.get("learning_journey", {})
        depth = chain.get("knowledge_depth", {})
        velocity = chain.get("learning_velocity", {})
        
        total_examples = journey.get('total_examples', 0)
        avg_trust = journey.get('avg_trust', 0)
        trust_trend = journey.get('trust_trend', 'unknown')
        episodes = journey.get('episodes_created', 0)
        skills = journey.get('skills_emerged', 0)
        depth_layers = depth.get('depth_layers', 0)
        mastery = depth.get('mastery_score', 0)
        velocity_type = velocity.get('velocity', 'unknown')
        
        # Trust insights
        if avg_trust >= 0.8:
            insights.append("Exceptional confidence levels indicate highly reliable and well-validated knowledge source.")
        elif avg_trust >= 0.6:
            insights.append("Strong confidence levels suggest reliable knowledge with good validation.")
        elif avg_trust < 0.4:
            insights.append("Lower confidence levels may indicate inconsistent or conflicting information that requires review.")
        
        if trust_trend == "improving" and avg_trust >= 0.7:
            insights.append("Improving trust trend combined with high average confidence suggests excellent knowledge quality and growing expertise.")
        elif trust_trend == "declining":
            insights.append("Declining trust trend warrants investigation into recent learning examples for potential inconsistencies or quality issues.")
        
        # Depth insights
        if depth_layers == 3 and mastery >= 0.7:
            insights.append("Complete three-layer knowledge depth with high mastery indicates comprehensive understanding and practical skill development.")
        elif depth_layers == 3 and mastery < 0.5:
            insights.append("Full knowledge depth achieved, but mastery levels suggest procedural skills may benefit from additional validation and refinement.")
        elif depth_layers == 2:
            insights.append("Progress to episodic memory formation demonstrates successful transition from basic learning to experience-based knowledge.")
        elif depth_layers == 1 and total_examples > 5:
            insights.append("Sufficient learning examples exist but episodic memory formation has not yet occurred, suggesting potential focus on encouraging experience-based learning.")
        
        # Velocity insights
        if velocity_type == "rapid" and avg_trust >= 0.7:
            insights.append("Rapid learning velocity combined with high confidence indicates efficient and effective knowledge acquisition.")
        elif velocity_type == "slow" and total_examples > 10:
            insights.append("Slower learning pace may indicate complex material requiring careful processing, or potential opportunities to increase engagement frequency.")
        
        # Skill insights
        if skills > 0:
            high_success_skills = journey.get('high_success_skills', 0)
            if high_success_skills == skills:
                insights.append("All developed skills demonstrate high success rates, indicating effective procedural knowledge extraction and validation.")
            elif high_success_skills == 0:
                insights.append("Procedural skills have been extracted but none yet demonstrate high success rates, suggesting need for further validation and refinement.")
        
        # Volume insights
        if total_examples >= 50:
            insights.append("Extensive learning volume provides robust foundation for knowledge analysis and skill development.")
        elif total_examples < 5:
            insights.append("Limited learning examples suggest early stage engagement; additional examples would strengthen knowledge base and confidence metrics.")
        
        if not insights:
            insights.append("Learning journey is in initial stages; continued engagement will provide more comprehensive insights.")
        
        return insights
    
    def _generate_recommendations(self, chain: Dict[str, Any]) -> List[str]:
        """Generate actionable enterprise-grade recommendations based on learning chain analysis."""
        recommendations = []
        journey = chain.get("learning_journey", {})
        depth = chain.get("knowledge_depth", {})
        velocity = chain.get("learning_velocity", {})
        
        total_examples = journey.get('total_examples', 0)
        avg_trust = journey.get('avg_trust', 0)
        trust_trend = journey.get('trust_trend', 'unknown')
        episodes = journey.get('episodes_created', 0)
        skills = journey.get('skills_emerged', 0)
        depth_layers = depth.get('depth_layers', 0)
        mastery = depth.get('mastery_score', 0)
        velocity_type = velocity.get('velocity', 'unknown')
        
        # Recommendations based on trust
        if avg_trust < 0.5:
            recommendations.append("Review recent learning examples to identify sources of uncertainty and improve knowledge quality.")
        
        if trust_trend == "declining":
            recommendations.append("Investigate declining trust trend by examining recent examples for contradictions or quality degradation.")
        
        # Recommendations based on depth
        if total_examples >= 10 and depth_layers == 1:
            recommendations.append("Encourage episodic memory formation by providing opportunities for Grace to process experiences and outcomes.")
        
        if depth_layers == 2 and skills == 0 and total_examples >= 20:
            recommendations.append("Focus on extracting procedural knowledge from episodic memories to develop actionable skills.")
        
        if depth_layers == 3 and mastery < 0.6:
            recommendations.append("Strengthen procedural skill mastery through additional validation cycles and refinement based on outcomes.")
        
        # Recommendations based on velocity
        if velocity_type == "minimal" and total_examples < 10:
            recommendations.append("Increase engagement frequency or expand source material to accelerate learning velocity and knowledge accumulation.")
        
        # Recommendations based on skills
        if skills > 0:
            high_success = journey.get('high_success_skills', 0)
            if high_success < skills * 0.5:
                recommendations.append("Review procedural skills with lower success rates to identify improvement opportunities and enhance reliability.")
        
        # General recommendations
        if total_examples < 5:
            recommendations.append("Continue providing learning examples to establish stronger knowledge foundation and enable more comprehensive analysis.")
        
        if episodes == 0 and total_examples >= 5:
            recommendations.append("Monitor for opportunities to form episodic memories from concrete experiences to deepen knowledge structures.")
        
        if not recommendations:
            recommendations.append("Current learning journey demonstrates healthy progression; maintain current engagement patterns to sustain knowledge development.")
        
        return recommendations


# ================================================================
# FACTORY FUNCTION
# ================================================================

def get_genesis_memory_chain(session: Session) -> GenesisMemoryChain:
    """Get Genesis Memory Chain tracker"""
    return GenesisMemoryChain(session=session)
