import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Set, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from collections import defaultdict
import json
class MemoryRelationship:
    logger = logging.getLogger(__name__)
    """Represents a relationship between two memories."""
    
    def __init__(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
        strength: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.source_id = source_id
        self.target_id = target_id
        self.relationship_type = relationship_type
        self.strength = strength
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow()


class MemoryRelationshipsGraph:
    """
    Graph of relationships between memories.
    
    Enables:
    - Finding related memories
    - Understanding memory connections
    - Graph-based queries
    - Memory navigation
    """
    
    def __init__(self, session: Session):
        """Initialize memory relationships graph."""
        self.session = session
        self.relationships: Dict[str, List[MemoryRelationship]] = defaultdict(list)
        self._build_graph()
        
        logger.info(
            f"[MEMORY-RELATIONSHIPS] Graph initialized: "
            f"{len(self.relationships)} memory nodes, "
            f"{sum(len(rels) for rels in self.relationships.values())} relationships"
        )
    
    def _build_graph(self):
        """Build relationship graph from database."""
        logger.info("[MEMORY-RELATIONSHIPS] Building relationship graph...")
        
        # Learning → Episodic relationships
        learning_examples = self.session.query(LearningExample).filter(
            LearningExample.episodic_episode_id.isnot(None)
        ).all()
        
        for ex in learning_examples:
            rel = MemoryRelationship(
                source_id=f"learning_{ex.id}",
                target_id=f"episodic_{ex.episodic_episode_id}",
                relationship_type="promoted_to_episodic",
                strength=ex.trust_score,
                metadata={"trust_score": ex.trust_score}
            )
            self.relationships[rel.source_id].append(rel)
        
        # Learning → Procedural relationships
        learning_with_procedures = self.session.query(LearningExample).filter(
            LearningExample.procedure_id.isnot(None)
        ).all()
        
        for ex in learning_with_procedures:
            rel = MemoryRelationship(
                source_id=f"learning_{ex.id}",
                target_id=f"procedural_{ex.procedure_id}",
                relationship_type="promoted_to_procedural",
                strength=ex.trust_score,
                metadata={"trust_score": ex.trust_score}
            )
            self.relationships[rel.source_id].append(rel)
        
        # Episodic → Procedural relationships (via learning)
        episodes = self.session.query(Episode).all()
        for ep in episodes:
            # Find learning examples that created this episode
            related_learning = self.session.query(LearningExample).filter(
                LearningExample.episodic_episode_id == ep.id
            ).all()
            
            for ex in related_learning:
                if ex.procedure_id:
                    rel = MemoryRelationship(
                        source_id=f"episodic_{ep.id}",
                        target_id=f"procedural_{ex.procedure_id}",
                        relationship_type="episodic_to_procedural",
                        strength=(ep.trust_score + ex.trust_score) / 2.0,
                        metadata={
                            "episode_trust": ep.trust_score,
                            "learning_trust": ex.trust_score
                        }
                    )
                    self.relationships[rel.source_id].append(rel)
        
        # Genesis Key relationships
        learning_with_genesis = self.session.query(LearningExample).filter(
            LearningExample.genesis_key_id.isnot(None)
        ).all()
        
        for ex in learning_with_genesis:
            rel = MemoryRelationship(
                source_id=f"genesis_{ex.genesis_key_id}",
                target_id=f"learning_{ex.id}",
                relationship_type="genesis_source",
                strength=1.0,
                metadata={"source": ex.source}
            )
            self.relationships[rel.source_id].append(rel)
        
        # Pattern relationships (patterns link multiple learning examples)
        patterns = self.session.query(LearningPattern).all()
        for pattern in patterns:
            if pattern.supporting_examples:
                for ex_id in pattern.supporting_examples[:10]:  # Limit to 10
                    rel = MemoryRelationship(
                        source_id=f"learning_{ex_id}",
                        target_id=f"pattern_{pattern.id}",
                        relationship_type="supports_pattern",
                        strength=pattern.trust_score,
                        metadata={"pattern_name": pattern.pattern_name}
                    )
                    self.relationships[rel.source_id].append(rel)
        
        logger.info(
            f"[MEMORY-RELATIONSHIPS] Graph built: "
            f"{len(self.relationships)} nodes, "
            f"{sum(len(rels) for rels in self.relationships.values())} edges"
        )
    
    def get_related_memories(
        self,
        memory_id: str,
        memory_type: str = "learning",
        relationship_types: Optional[List[str]] = None,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get memories related to a given memory.
        
        Args:
            memory_id: ID of the memory
            memory_type: Type of memory (learning, episodic, procedural, pattern)
            relationship_types: Filter by relationship types
            max_results: Maximum results to return
            
        Returns:
            List of related memories with relationship info
        """
        source_id = f"{memory_type}_{memory_id}"
        
        if source_id not in self.relationships:
            return []
        
        related = []
        for rel in self.relationships[source_id]:
            if relationship_types and rel.relationship_type not in relationship_types:
                continue
            
            # Parse target memory info
            target_parts = rel.target_id.split("_", 1)
            if len(target_parts) == 2:
                target_type, target_id = target_parts
                
                related.append({
                    "memory_id": target_id,
                    "memory_type": target_type,
                    "relationship_type": rel.relationship_type,
                    "strength": rel.strength,
                    "metadata": rel.metadata
                })
        
        # Sort by strength
        related.sort(key=lambda x: x["strength"], reverse=True)
        
        return related[:max_results]
    
    def get_memory_path(
        self,
        start_id: str,
        start_type: str,
        end_id: str,
        end_type: str,
        max_depth: int = 5
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Find path between two memories.
        
        Uses breadth-first search to find shortest path.
        
        Args:
            start_id: Starting memory ID
            start_type: Starting memory type
            end_id: Ending memory ID
            end_type: Ending memory type
            max_depth: Maximum search depth
            
        Returns:
            Path as list of memory nodes, or None if no path found
        """
        start_node = f"{start_type}_{start_id}"
        end_node = f"{end_type}_{end_id}"
        
        if start_node == end_node:
            return [{"memory_id": start_id, "memory_type": start_type}]
        
        # BFS
        queue = [(start_node, [{"memory_id": start_id, "memory_type": start_type}])]
        visited = {start_node}
        
        depth = 0
        while queue and depth < max_depth:
            depth += 1
            next_level = []
            
            for current_node, path in queue:
                if current_node not in self.relationships:
                    continue
                
                for rel in self.relationships[current_node]:
                    target = rel.target_id
                    
                    if target == end_node:
                        # Found path!
                        target_parts = target.split("_", 1)
                        if len(target_parts) == 2:
                            target_type, target_id = target_parts
                            return path + [{
                                "memory_id": target_id,
                                "memory_type": target_type,
                                "relationship": rel.relationship_type
                            }]
                    
                    if target not in visited:
                        visited.add(target)
                        target_parts = target.split("_", 1)
                        if len(target_parts) == 2:
                            target_type, target_id = target_parts
                            next_level.append((
                                target,
                                path + [{
                                    "memory_id": target_id,
                                    "memory_type": target_type,
                                    "relationship": rel.relationship_type
                                }]
                            ))
            
            queue = next_level
        
        return None  # No path found
    
    def get_memory_cluster(
        self,
        memory_id: str,
        memory_type: str,
        max_depth: int = 2
    ) -> Dict[str, Any]:
        """
        Get cluster of related memories around a central memory.
        
        Args:
            memory_id: Central memory ID
            memory_type: Central memory type
            max_depth: How many hops to explore
            
        Returns:
            Cluster with central memory and related memories
        """
        central_id = f"{memory_type}_{memory_id}"
        
        cluster = {
            "central_memory": {
                "id": memory_id,
                "type": memory_type
            },
            "related_memories": [],
            "cluster_size": 1
        }
        
        visited = {central_id}
        to_explore = [(central_id, 0)]  # (node, depth)
        
        while to_explore:
            current_node, depth = to_explore.pop(0)
            
            if depth >= max_depth:
                continue
            
            if current_node not in self.relationships:
                continue
            
            for rel in self.relationships[current_node]:
                target = rel.target_id
                
                if target not in visited:
                    visited.add(target)
                    target_parts = target.split("_", 1)
                    
                    if len(target_parts) == 2:
                        target_type, target_id = target_parts
                        
                        cluster["related_memories"].append({
                            "memory_id": target_id,
                            "memory_type": target_type,
                            "relationship_type": rel.relationship_type,
                            "strength": rel.strength,
                            "depth": depth + 1,
                            "metadata": rel.metadata
                        })
                        
                        cluster["cluster_size"] += 1
                        
                        # Explore further
                        if depth + 1 < max_depth:
                            to_explore.append((target, depth + 1))
        
        return cluster
    
    def get_graph_statistics(self) -> Dict[str, Any]:
        """Get statistics about the relationship graph."""
        total_nodes = len(self.relationships)
        total_edges = sum(len(rels) for rels in self.relationships.values())
        
        # Count by relationship type
        rel_type_counts = defaultdict(int)
        for rels in self.relationships.values():
            for rel in rels:
                rel_type_counts[rel.relationship_type] += 1
        
        # Count by memory type
        node_type_counts = defaultdict(int)
        for node_id in self.relationships.keys():
            node_type = node_id.split("_")[0] if "_" in node_id else "unknown"
            node_type_counts[node_type] += 1
        
        return {
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "average_degree": total_edges / total_nodes if total_nodes > 0 else 0,
            "relationship_types": dict(rel_type_counts),
            "node_types": dict(node_type_counts),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def rebuild_graph(self):
        """Rebuild the relationship graph from database."""
        logger.info("[MEMORY-RELATIONSHIPS] Rebuilding graph...")
        self.relationships.clear()
        self._build_graph()


def get_memory_relationships_graph(session: Session) -> MemoryRelationshipsGraph:
    """Factory function to get memory relationships graph."""
    return MemoryRelationshipsGraph(session=session)
