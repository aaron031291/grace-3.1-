import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Set
from sqlalchemy.orm import Session
from sqlalchemy import func
from collections import defaultdict
import json
logger = logging.getLogger(__name__)

class MemoryCluster:
    """Represents a cluster of related memories."""
    
    def __init__(
        self,
        cluster_id: str,
        cluster_type: str,
        memories: List[Any],
        centroid: Optional[Dict[str, Any]] = None
    ):
        self.cluster_id = cluster_id
        self.cluster_type = cluster_type
        self.memories = memories
        self.centroid = centroid
        self.created_at = datetime.utcnow()
        self.size = len(memories)
        
        # Calculate cluster properties
        self.avg_trust = self._calculate_avg_trust()
        self.avg_priority = self._calculate_avg_priority()
        self.topics = self._extract_topics()
    
    def _calculate_avg_trust(self) -> float:
        """Calculate average trust score for cluster."""
        trust_scores = []
        for mem in self.memories:
            if hasattr(mem, 'trust_score'):
                trust_scores.append(mem.trust_score)
            elif hasattr(mem, 'success_rate'):
                trust_scores.append(mem.success_rate)
        
        return sum(trust_scores) / len(trust_scores) if trust_scores else 0.0
    
    def _calculate_avg_priority(self) -> float:
        """Calculate average priority for cluster."""
        # Simple priority: trust + recency
        priorities = []
        for mem in self.memories:
            trust = getattr(mem, 'trust_score', 0) or getattr(mem, 'success_rate', 0) or 0
            
            created_at = getattr(mem, 'created_at', None) or getattr(mem, 'timestamp', None)
            if created_at:
                days_old = (datetime.utcnow() - created_at).days
                recency = max(0.1, 1.0 - (days_old / 365.0))
            else:
                recency = 0.5
            
            priorities.append((trust * 0.7 + recency * 0.3))
        
        return sum(priorities) / len(priorities) if priorities else 0.0
    
    def _extract_topics(self) -> List[str]:
        """Extract topics from cluster memories."""
        # Simple keyword extraction from memory content
        word_counts = defaultdict(int)
        
        for mem in self.memories:
            text = ""
            if hasattr(mem, 'input_context'):
                text += str(mem.input_context or "")
            if hasattr(mem, 'problem'):
                text += " " + str(mem.problem or "")
            if hasattr(mem, 'goal'):
                text += " " + str(mem.goal or "")
            
            # Extract keywords (simple approach)
            words = text.lower().split()
            for word in words:
                if len(word) > 4:  # Only meaningful words
                    word_counts[word] += 1
        
        # Top 5 topics
        topics = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        return [topic[0] for topic in topics]


class MemoryClusteringSystem:
    """
    Semantic clustering system for memories.
    
    Groups memories by:
    - Semantic similarity (topic-based)
    - Temporal proximity
    - Trust levels
    - Usage patterns
    """
    
    def __init__(
        self,
        session: Session,
        min_cluster_size: int = 3,
        max_clusters: int = 50
    ):
        """
        Initialize memory clustering system.
        
        Args:
            session: Database session
            min_cluster_size: Minimum memories per cluster
            max_clusters: Maximum number of clusters
        """
        self.session = session
        self.min_cluster_size = min_cluster_size
        self.max_clusters = max_clusters
        self.clusters: Dict[str, MemoryCluster] = {}
        
        logger.info(
            f"[MEMORY-CLUSTERING] Initialized: "
            f"min_size={min_cluster_size}, max_clusters={max_clusters}"
        )
    
    def cluster_by_topic(self) -> Dict[str, MemoryCluster]:
        """
        Cluster memories by topic/semantic similarity.
        
        Uses simple keyword-based clustering (resource-efficient).
        
        Returns:
            Dictionary of clusters by cluster_id
        """
        logger.info("[MEMORY-CLUSTERING] Clustering by topic...")
        
        # Get all learning examples
        examples = self.session.query(LearningExample).filter(
            LearningExample.trust_score >= 0.5
        ).limit(1000).all()  # Limit for resource efficiency
        
        # Group by example type (simple topic clustering)
        type_clusters = defaultdict(list)
        for ex in examples:
            type_clusters[ex.example_type].append(ex)
        
        # Create clusters
        clusters = {}
        cluster_id = 0
        
        for example_type, memories in type_clusters.items():
            if len(memories) >= self.min_cluster_size:
                cluster = MemoryCluster(
                    cluster_id=f"topic_{cluster_id}",
                    cluster_type="topic",
                    memories=memories,
                    centroid={"type": example_type}
                )
                clusters[cluster.cluster_id] = cluster
                cluster_id += 1
        
        self.clusters.update(clusters)
        
        logger.info(f"[MEMORY-CLUSTERING] Created {len(clusters)} topic clusters")
        
        return clusters
    
    def cluster_by_trust_level(self) -> Dict[str, MemoryCluster]:
        """
        Cluster memories by trust level.
        
        Groups: very_high (0.9+), high (0.7-0.9), medium (0.5-0.7), low (<0.5)
        
        Returns:
            Dictionary of clusters by trust level
        """
        logger.info("[MEMORY-CLUSTERING] Clustering by trust level...")
        
        examples = self.session.query(LearningExample).limit(1000).all()
        
        trust_clusters = {
            "very_high": [],
            "high": [],
            "medium": [],
            "low": []
        }
        
        for ex in examples:
            if ex.trust_score >= 0.9:
                trust_clusters["very_high"].append(ex)
            elif ex.trust_score >= 0.7:
                trust_clusters["high"].append(ex)
            elif ex.trust_score >= 0.5:
                trust_clusters["medium"].append(ex)
            else:
                trust_clusters["low"].append(ex)
        
        clusters = {}
        for trust_level, memories in trust_clusters.items():
            if len(memories) >= self.min_cluster_size:
                cluster = MemoryCluster(
                    cluster_id=f"trust_{trust_level}",
                    cluster_type="trust_level",
                    memories=memories,
                    centroid={"trust_level": trust_level}
                )
                clusters[cluster.cluster_id] = cluster
        
        self.clusters.update(clusters)
        
        logger.info(f"[MEMORY-CLUSTERING] Created {len(clusters)} trust clusters")
        
        return clusters
    
    def cluster_by_temporal_proximity(
        self,
        time_window_days: int = 7
    ) -> Dict[str, MemoryCluster]:
        """
        Cluster memories by temporal proximity.
        
        Groups memories created within time_window_days of each other.
        
        Args:
            time_window_days: Time window for clustering
            
        Returns:
            Dictionary of temporal clusters
        """
        logger.info(f"[MEMORY-CLUSTERING] Clustering by temporal proximity ({time_window_days}d)...")
        
        examples = self.session.query(LearningExample).order_by(
            LearningExample.created_at
        ).limit(1000).all()
        
        if not examples:
            return {}
        
        clusters = {}
        current_cluster = []
        cluster_id = 0
        last_time = None
        
        for ex in examples:
            if ex.created_at:
                if last_time is None:
                    last_time = ex.created_at
                    current_cluster = [ex]
                else:
                    days_diff = (ex.created_at - last_time).days
                    
                    if days_diff <= time_window_days:
                        current_cluster.append(ex)
                    else:
                        # Start new cluster
                        if len(current_cluster) >= self.min_cluster_size:
                            cluster = MemoryCluster(
                                cluster_id=f"temporal_{cluster_id}",
                                cluster_type="temporal",
                                memories=current_cluster,
                                centroid={"time_window_days": time_window_days}
                            )
                            clusters[cluster.cluster_id] = cluster
                            cluster_id += 1
                        
                        current_cluster = [ex]
                        last_time = ex.created_at
        
        # Add final cluster
        if len(current_cluster) >= self.min_cluster_size:
            cluster = MemoryCluster(
                cluster_id=f"temporal_{cluster_id}",
                cluster_type="temporal",
                memories=current_cluster,
                centroid={"time_window_days": time_window_days}
            )
            clusters[cluster.cluster_id] = cluster
        
        self.clusters.update(clusters)
        
        logger.info(f"[MEMORY-CLUSTERING] Created {len(clusters)} temporal clusters")
        
        return clusters
    
    def cluster_by_genesis_key(self) -> Dict[str, MemoryCluster]:
        """
        Cluster memories by Genesis Key (source).
        
        Groups memories that came from the same source.
        
        Returns:
            Dictionary of Genesis Key clusters
        """
        logger.info("[MEMORY-CLUSTERING] Clustering by Genesis Key...")
        
        examples = self.session.query(LearningExample).filter(
            LearningExample.genesis_key_id.isnot(None)
        ).limit(1000).all()
        
        genesis_clusters = defaultdict(list)
        for ex in examples:
            genesis_clusters[ex.genesis_key_id].append(ex)
        
        clusters = {}
        cluster_id = 0
        
        for genesis_key_id, memories in genesis_clusters.items():
            if len(memories) >= self.min_cluster_size:
                cluster = MemoryCluster(
                    cluster_id=f"genesis_{cluster_id}",
                    cluster_type="genesis_key",
                    memories=memories,
                    centroid={"genesis_key_id": genesis_key_id}
                )
                clusters[cluster.cluster_id] = cluster
                cluster_id += 1
        
        self.clusters.update(clusters)
        
        logger.info(f"[MEMORY-CLUSTERING] Created {len(clusters)} Genesis Key clusters")
        
        return clusters
    
    def get_cluster(self, cluster_id: str) -> Optional[MemoryCluster]:
        """Get cluster by ID."""
        return self.clusters.get(cluster_id)
    
    def get_all_clusters(self) -> Dict[str, MemoryCluster]:
        """Get all clusters."""
        return self.clusters
    
    def get_cluster_statistics(self) -> Dict[str, Any]:
        """Get statistics about all clusters."""
        if not self.clusters:
            return {
                "total_clusters": 0,
                "total_memories": 0,
                "by_type": {}
            }
        
        total_memories = sum(c.size for c in self.clusters.values())
        by_type = defaultdict(int)
        
        for cluster in self.clusters.values():
            by_type[cluster.cluster_type] += 1
        
        return {
            "total_clusters": len(self.clusters),
            "total_memories": total_memories,
            "avg_cluster_size": total_memories / len(self.clusters) if self.clusters else 0,
            "by_type": dict(by_type),
            "avg_trust": sum(c.avg_trust for c in self.clusters.values()) / len(self.clusters) if self.clusters else 0,
            "avg_priority": sum(c.avg_priority for c in self.clusters.values()) / len(self.clusters) if self.clusters else 0
        }
    
    def rebuild_all_clusters(self):
        """Rebuild all cluster types."""
        logger.info("[MEMORY-CLUSTERING] Rebuilding all clusters...")
        
        self.clusters.clear()
        
        self.cluster_by_topic()
        self.cluster_by_trust_level()
        self.cluster_by_temporal_proximity()
        self.cluster_by_genesis_key()
        
        logger.info(f"[MEMORY-CLUSTERING] Rebuilt {len(self.clusters)} clusters")


def get_memory_clustering_system(
    session: Session,
    min_cluster_size: int = 3
) -> MemoryClusteringSystem:
    """Factory function to get memory clustering system."""
    return MemoryClusteringSystem(session=session, min_cluster_size=min_cluster_size)
