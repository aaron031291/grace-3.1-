import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from collections import defaultdict
from cognitive.learning_memory import LearningExample, LearningPattern
from cognitive.episodic_memory import Episode
from cognitive.procedural_memory import Procedure
from cognitive.memory_relationships import get_memory_relationships_graph
from cognitive.memory_lifecycle_manager import get_memory_lifecycle_manager
logger = logging.getLogger(__name__)

class SmartMemoryRetrieval:
    """
    Smart, context-aware memory retrieval system.
    
    Features:
    - Priority-based retrieval (high-value memories first)
    - Context-aware filtering
    - Relationship-aware expansion
    - Caching for performance
    - Resource-efficient queries
    """
    
    def __init__(
        self,
        session: Session,
        knowledge_base_path,
        max_results: int = 20,
        cache_size: int = 100
    ):
        """
        Initialize smart memory retrieval.
        
        Args:
            session: Database session
            knowledge_base_path: Path to knowledge base
            max_results: Maximum results per query
            cache_size: Cache size for frequently accessed memories
        """
        self.session = session
        self.kb_path = knowledge_base_path
        self.max_results = max_results
        self.cache_size = cache_size
        
        # Initialize components
        self.relationships_graph = get_memory_relationships_graph(session)
        self.lifecycle_manager = get_memory_lifecycle_manager(session, knowledge_base_path)
        
        # Simple in-memory cache (for resource efficiency)
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
        
        logger.info(
            f"[SMART-MEMORY-RETRIEVAL] Initialized: "
            f"max_results={max_results}, cache_size={cache_size}"
        )
    
    def _get_priority_score(
        self,
        memory: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Calculate priority score for a memory.
        
        Priority = f(trust, recency, usage, context_relevance)
        
        Args:
            memory: Memory object (LearningExample, Episode, Procedure)
            context: Optional context for relevance scoring
            
        Returns:
            Priority score (0-1)
        """
        # Base priority from trust
        if hasattr(memory, 'trust_score'):
            base_priority = memory.trust_score
        elif hasattr(memory, 'success_rate'):
            base_priority = memory.success_rate
        else:
            base_priority = 0.5
        
        # Recency weight
        created_at = getattr(memory, 'created_at', None) or getattr(memory, 'timestamp', None)
        if created_at:
            days_old = (datetime.utcnow() - created_at).days
            recency_weight = max(0.1, 1.0 - (days_old / 365.0))
        else:
            recency_weight = 0.5
        
        # Usage weight
        usage_count = getattr(memory, 'times_referenced', 0) or getattr(memory, 'usage_count', 0) or 0
        usage_weight = min(1.0, usage_count / 10.0)
        
        # Context relevance (if provided)
        context_relevance = 1.0
        if context:
            # Simple keyword matching for context relevance
            context_text = str(context).lower()
            memory_text = str(getattr(memory, 'input_context', '') or 
                            getattr(memory, 'problem', '') or 
                            getattr(memory, 'goal', '')).lower()
            
            # Count matching words
            context_words = set(context_text.split())
            memory_words = set(memory_text.split())
            if context_words and memory_words:
                overlap = len(context_words & memory_words)
                context_relevance = min(1.0, overlap / max(len(context_words), 1))
        
        # Weighted combination
        priority = (
            base_priority * 0.4 +        # Trust/success is most important
            recency_weight * 0.3 +       # Recency matters
            usage_weight * 0.2 +         # Usage indicates value
            context_relevance * 0.1      # Context relevance
        )
        
        return priority
    
    def retrieve_learning_memories(
        self,
        context: Optional[Dict[str, Any]] = None,
        min_trust: float = 0.0,
        max_results: Optional[int] = None,
        include_related: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Retrieve learning memories with smart prioritization.
        
        Args:
            context: Optional context for relevance filtering
            min_trust: Minimum trust score
            max_results: Maximum results (default: self.max_results)
            include_related: Include related memories via relationships graph
            
        Returns:
            List of learning memories with priority scores
        """
        max_results = max_results or self.max_results
        
        # Query with trust filter
        query = self.session.query(LearningExample).filter(
            LearningExample.trust_score >= min_trust
        )
        
        # Get all matching memories
        memories = query.limit(max_results * 2).all()  # Get more for prioritization
        
        # Calculate priorities
        prioritized = []
        for mem in memories:
            priority = self._get_priority_score(mem, context)
            prioritized.append({
                "memory": mem,
                "priority": priority,
                "id": mem.id,
                "type": mem.example_type,
                "trust_score": mem.trust_score
            })
        
        # Sort by priority
        prioritized.sort(key=lambda x: x["priority"], reverse=True)
        
        # Take top results
        results = prioritized[:max_results]
        
        # Expand with related memories if requested
        if include_related:
            expanded = []
            for result in results:
                expanded.append(result)
                
                # Get related memories
                related = self.relationships_graph.get_related_memories(
                    memory_id=result["id"],
                    memory_type="learning",
                    max_results=3
                )
                
                for rel in related:
                    # Avoid duplicates
                    if not any(r["id"] == rel["memory_id"] for r in expanded):
                        expanded.append({
                            "memory_id": rel["memory_id"],
                            "memory_type": rel["memory_type"],
                            "relationship": rel["relationship_type"],
                            "strength": rel["strength"],
                            "related_to": result["id"]
                        })
            
            results = expanded[:max_results]
        
        logger.info(
            f"[SMART-MEMORY-RETRIEVAL] Retrieved {len(results)} learning memories "
            f"(min_trust={min_trust}, context={'yes' if context else 'no'})"
        )
        
        return results
    
    def retrieve_episodic_memories(
        self,
        problem_context: Optional[str] = None,
        min_trust: float = 0.7,
        max_results: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve episodic memories relevant to a problem.
        
        Args:
            problem_context: Problem description for relevance matching
            min_trust: Minimum trust score (default 0.7 for episodic)
            max_results: Maximum results
            
        Returns:
            List of episodic memories
        """
        max_results = max_results or self.max_results
        
        query = self.session.query(Episode).filter(
            Episode.trust_score >= min_trust
        )
        
        episodes = query.limit(max_results * 2).all()
        
        # Prioritize by relevance to problem
        context = {"problem": problem_context} if problem_context else None
        prioritized = []
        
        for ep in episodes:
            priority = self._get_priority_score(ep, context)
            prioritized.append({
                "memory": ep,
                "priority": priority,
                "id": ep.id,
                "problem": ep.problem,
                "trust_score": ep.trust_score,
                "prediction_error": ep.prediction_error
            })
        
        prioritized.sort(key=lambda x: x["priority"], reverse=True)
        results = prioritized[:max_results]
        
        logger.info(
            f"[SMART-MEMORY-RETRIEVAL] Retrieved {len(results)} episodic memories "
            f"(problem_context={'yes' if problem_context else 'no'})"
        )
        
        return results
    
    def retrieve_procedures(
        self,
        goal: Optional[str] = None,
        min_success_rate: float = 0.7,
        max_results: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve procedures relevant to a goal.
        
        Args:
            goal: Goal description for relevance matching
            min_success_rate: Minimum success rate
            max_results: Maximum results
            
        Returns:
            List of procedures
        """
        max_results = max_results or self.max_results
        
        query = self.session.query(Procedure).filter(
            Procedure.success_rate >= min_success_rate
        )
        
        procedures = query.limit(max_results * 2).all()
        
        # Prioritize by relevance to goal
        context = {"goal": goal} if goal else None
        prioritized = []
        
        for proc in procedures:
            priority = self._get_priority_score(proc, context)
            prioritized.append({
                "memory": proc,
                "priority": priority,
                "id": proc.id,
                "name": proc.name,
                "goal": proc.goal,
                "success_rate": proc.success_rate,
                "trust_score": proc.trust_score,
                "usage_count": proc.usage_count
            })
        
        prioritized.sort(key=lambda x: x["priority"], reverse=True)
        results = prioritized[:max_results]
        
        logger.info(
            f"[SMART-MEMORY-RETRIEVAL] Retrieved {len(results)} procedures "
            f"(goal={'yes' if goal else 'no'})"
        )
        
        return results
    
    def retrieve_contextual_memories(
        self,
        context: Dict[str, Any],
        memory_types: Optional[List[str]] = None,
        max_results_per_type: int = 10
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Retrieve memories across all types based on context.
        
        Args:
            context: Context dictionary (problem, goal, etc.)
            memory_types: Types to retrieve (default: all)
            max_results_per_type: Max results per memory type
            
        Returns:
            Dictionary of memories by type
        """
        memory_types = memory_types or ["learning", "episodic", "procedural"]
        
        results = {}
        
        if "learning" in memory_types:
            results["learning"] = self.retrieve_learning_memories(
                context=context,
                max_results=max_results_per_type
            )
        
        if "episodic" in memory_types:
            problem = context.get("problem") or context.get("query")
            results["episodic"] = self.retrieve_episodic_memories(
                problem_context=problem,
                max_results=max_results_per_type
            )
        
        if "procedural" in memory_types:
            goal = context.get("goal") or context.get("task")
            results["procedural"] = self.retrieve_procedures(
                goal=goal,
                max_results=max_results_per_type
            )
        
        logger.info(
            f"[SMART-MEMORY-RETRIEVAL] Retrieved contextual memories: "
            f"{sum(len(v) for v in results.values())} total across {len(results)} types"
        )
        
        return results
    
    def get_memory_cluster_for_context(
        self,
        context: Dict[str, Any],
        max_cluster_size: int = 20
    ) -> Dict[str, Any]:
        """
        Get a cluster of related memories for a given context.
        
        Uses relationships graph to find connected memories.
        
        Args:
            context: Context dictionary
            max_cluster_size: Maximum memories in cluster
            
        Returns:
            Memory cluster with central and related memories
        """
        # First, find most relevant memory
        learning_memories = self.retrieve_learning_memories(
            context=context,
            max_results=1
        )
        
        if not learning_memories:
            return {"cluster": [], "size": 0}
        
        # Use first memory as central
        central = learning_memories[0]
        central_id = central["id"]
        
        # Get cluster from relationships graph
        cluster = self.relationships_graph.get_memory_cluster(
            memory_id=central_id,
            memory_type="learning",
            max_depth=2
        )
        
        # Limit cluster size
        if cluster["cluster_size"] > max_cluster_size:
            cluster["related_memories"] = cluster["related_memories"][:max_cluster_size - 1]
            cluster["cluster_size"] = len(cluster["related_memories"]) + 1
        
        logger.info(
            f"[SMART-MEMORY-RETRIEVAL] Retrieved memory cluster: "
            f"{cluster['cluster_size']} memories"
        )
        
        return cluster


def get_smart_memory_retrieval(
    session: Session,
    knowledge_base_path,
    max_results: int = 20
) -> SmartMemoryRetrieval:
    """Factory function to get smart memory retrieval."""
    return SmartMemoryRetrieval(
        session=session,
        knowledge_base_path=knowledge_base_path,
        max_results=max_results
    )
