import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Set
from sqlalchemy.orm import Session
from collections import defaultdict
from cognitive.learning_memory import LearningExample
from cognitive.episodic_memory import Episode
from cognitive.procedural_memory import Procedure
class MemorySynthesis:
    logger = logging.getLogger(__name__)
    """
    Synthesizes multiple memories into consolidated insights.
    
    Creates:
    - Composite knowledge from multiple sources
    - General principles from specific examples
    - Best practices from successful patterns
    - Consolidated summaries
    """
    
    def __init__(self, session: Session):
        """Initialize memory synthesis system."""
        self.session = session
        logger.info("[MEMORY-SYNTHESIS] Initialized")
    
    def synthesize_learning_examples(
        self,
        example_ids: List[str],
        synthesis_type: str = "composite"
    ) -> Dict[str, Any]:
        """
        Synthesize multiple learning examples into one insight.
        
        Args:
            example_ids: IDs of learning examples to synthesize
            synthesis_type: Type of synthesis (composite, principle, best_practice)
            
        Returns:
            Synthesized insight
        """
        logger.info(
            f"[MEMORY-SYNTHESIS] Synthesizing {len(example_ids)} learning examples "
            f"(type: {synthesis_type})"
        )
        
        # Get examples
        examples = self.session.query(LearningExample).filter(
            LearningExample.id.in_(example_ids)
        ).all()
        
        if not examples:
            return {"error": "No examples found"}
        
        if synthesis_type == "composite":
            return self._create_composite_insight(examples)
        elif synthesis_type == "principle":
            return self._extract_principle(examples)
        elif synthesis_type == "best_practice":
            return self._extract_best_practice(examples)
        else:
            return self._create_composite_insight(examples)
    
    def _create_composite_insight(
        self,
        examples: List[LearningExample]
    ) -> Dict[str, Any]:
        """Create composite insight from examples."""
        # Aggregate trust scores
        avg_trust = sum(ex.trust_score for ex in examples) / len(examples)
        
        # Extract common patterns
        common_types = defaultdict(int)
        common_sources = defaultdict(int)
        
        for ex in examples:
            common_types[ex.example_type] += 1
            common_sources[ex.source] += 1
        
        # Create composite
        synthesis = {
            "synthesis_type": "composite",
            "source_count": len(examples),
            "source_ids": [ex.id for ex in examples],
            "avg_trust_score": avg_trust,
            "composite_trust": avg_trust,  # Weighted by trust
            "common_types": dict(common_types),
            "common_sources": dict(common_sources),
            "synthesis_summary": self._create_summary(examples),
            "created_at": datetime.utcnow().isoformat()
        }
        
        return synthesis
    
    def _extract_principle(
        self,
        examples: List[LearningExample]
    ) -> Dict[str, Any]:
        """Extract general principle from examples."""
        # Filter high-trust examples
        high_trust = [ex for ex in examples if ex.trust_score >= 0.7]
        
        if not high_trust:
            return {"error": "No high-trust examples to extract principle"}
        
        # Extract commonalities
        principles = []
        
        # Principle 1: Trust-based
        avg_trust = sum(ex.trust_score for ex in high_trust) / len(high_trust)
        principles.append({
            "principle": "High trust examples are reliable",
            "evidence": len(high_trust),
            "avg_trust": avg_trust
        })
        
        # Principle 2: Source-based
        source_counts = defaultdict(int)
        for ex in high_trust:
            source_counts[ex.source] += 1
        
        top_source = max(source_counts.items(), key=lambda x: x[1]) if source_counts else None
        if top_source:
            principles.append({
                "principle": f"Source '{top_source[0]}' is reliable",
                "evidence": top_source[1],
                "reliability": top_source[1] / len(high_trust)
            })
        
        return {
            "synthesis_type": "principle",
            "source_count": len(examples),
            "high_trust_count": len(high_trust),
            "principles": principles,
            "created_at": datetime.utcnow().isoformat()
        }
    
    def _extract_best_practice(
        self,
        examples: List[LearningExample]
    ) -> Dict[str, Any]:
        """Extract best practice from successful examples."""
        # Filter successful examples (high trust, validated)
        successful = [
            ex for ex in examples
            if ex.trust_score >= 0.8 and (ex.times_validated or 0) > 0
        ]
        
        if not successful:
            return {"error": "No successful examples to extract best practice"}
        
        # Extract common success factors
        best_practices = []
        
        # Practice 1: High trust + validation
        best_practices.append({
            "practice": "Use high-trust, validated examples",
            "success_rate": len(successful) / len(examples),
            "avg_trust": sum(ex.trust_score for ex in successful) / len(successful)
        })
        
        # Practice 2: Source reliability
        reliable_sources = defaultdict(int)
        for ex in successful:
            reliable_sources[ex.source] += 1
        
        if reliable_sources:
            top_source = max(reliable_sources.items(), key=lambda x: x[1])
            best_practices.append({
                "practice": f"Prefer source '{top_source[0]}'",
                "success_count": top_source[1],
                "reliability": top_source[1] / len(successful)
            })
        
        return {
            "synthesis_type": "best_practice",
            "source_count": len(examples),
            "successful_count": len(successful),
            "best_practices": best_practices,
            "created_at": datetime.utcnow().isoformat()
        }
    
    def _create_summary(self, examples: List[LearningExample]) -> str:
        """Create text summary of examples."""
        if not examples:
            return "No examples to summarize"
        
        types = [ex.example_type for ex in examples]
        unique_types = set(types)
        
        summary = f"Synthesis of {len(examples)} learning examples"
        if unique_types:
            summary += f" across {len(unique_types)} types: {', '.join(list(unique_types)[:3])}"
        
        avg_trust = sum(ex.trust_score for ex in examples) / len(examples)
        summary += f". Average trust: {avg_trust:.2f}"
        
        return summary
    
    def synthesize_procedures(
        self,
        procedure_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Synthesize multiple procedures into consolidated procedure.
        
        Args:
            procedure_ids: IDs of procedures to synthesize
            
        Returns:
            Synthesized procedure
        """
        logger.info(f"[MEMORY-SYNTHESIS] Synthesizing {len(procedure_ids)} procedures")
        
        procedures = self.session.query(Procedure).filter(
            Procedure.id.in_(procedure_ids)
        ).all()
        
        if not procedures:
            return {"error": "No procedures found"}
        
        # Aggregate success rates
        avg_success = sum(p.success_rate for p in procedures) / len(procedures)
        avg_trust = sum(p.trust_score for p in procedures) / len(procedures)
        total_usage = sum(p.usage_count or 0 for p in procedures)
        
        # Extract common steps
        all_steps = []
        for proc in procedures:
            if proc.steps:
                if isinstance(proc.steps, list):
                    all_steps.extend(proc.steps)
                elif isinstance(proc.steps, dict):
                    all_steps.append(proc.steps)
        
        return {
            "synthesis_type": "procedure_consolidation",
            "source_count": len(procedures),
            "source_ids": [p.id for p in procedures],
            "avg_success_rate": avg_success,
            "avg_trust_score": avg_trust,
            "total_usage": total_usage,
            "common_steps": all_steps[:10],  # Limit to 10
            "synthesis_summary": f"Consolidated {len(procedures)} procedures with {avg_success:.2%} avg success",
            "created_at": datetime.utcnow().isoformat()
        }
    
    def synthesize_episodes(
        self,
        episode_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Synthesize multiple episodes into pattern.
        
        Args:
            episode_ids: IDs of episodes to synthesize
            
        Returns:
            Synthesized pattern
        """
        logger.info(f"[MEMORY-SYNTHESIS] Synthesizing {len(episode_ids)} episodes")
        
        episodes = self.session.query(Episode).filter(
            Episode.id.in_(episode_ids)
        ).all()
        
        if not episodes:
            return {"error": "No episodes found"}
        
        # Aggregate prediction errors
        avg_error = sum(ep.prediction_error for ep in episodes) / len(episodes)
        avg_trust = sum(ep.trust_score for ep in episodes) / len(episodes)
        
        # Extract common problems
        problems = [ep.problem for ep in episodes if ep.problem]
        
        return {
            "synthesis_type": "episode_pattern",
            "source_count": len(episodes),
            "source_ids": [ep.id for ep in episodes],
            "avg_prediction_error": avg_error,
            "avg_trust_score": avg_trust,
            "common_problems": problems[:5],  # Top 5
            "synthesis_summary": f"Pattern from {len(episodes)} episodes with {avg_error:.2f} avg error",
            "created_at": datetime.utcnow().isoformat()
        }


def get_memory_synthesis(session: Session) -> MemorySynthesis:
    """Factory function to get memory synthesis system."""
    return MemorySynthesis(session=session)
