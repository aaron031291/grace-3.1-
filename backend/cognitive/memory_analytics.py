import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from collections import defaultdict
class MemoryAnalytics:
    logger = logging.getLogger(__name__)
    """
    Comprehensive memory system analytics.
    
    Provides:
    - Real-time metrics
    - Performance tracking
    - Usage analytics
    - Health monitoring
    - Trend analysis
    """
    
    def __init__(
        self,
        session: Session,
        knowledge_base_path
    ):
        """Initialize memory analytics system."""
        self.session = session
        self.kb_path = knowledge_base_path
        
        # Initialize components
        self.lifecycle_manager = get_memory_lifecycle_manager(session, knowledge_base_path)
        self.relationships_graph = get_memory_relationships_graph(session)
        self.clustering_system = get_memory_clustering_system(session)
        
        logger.info("[MEMORY-ANALYTICS] Initialized")
    
    def get_real_time_metrics(self) -> Dict[str, Any]:
        """
        Get real-time memory system metrics.
        
        Returns:
            Current system metrics
        """
        logger.info("[MEMORY-ANALYTICS] Gathering real-time metrics...")
        
        # Counts
        learning_count = self.session.query(LearningExample).count()
        episodic_count = self.session.query(Episode).count()
        procedural_count = self.session.query(Procedure).count()
        pattern_count = self.session.query(LearningPattern).count()
        
        # Trust distribution
        high_trust = self.session.query(LearningExample).filter(
            LearningExample.trust_score >= 0.7
        ).count()
        
        # Recent activity (last 24 hours)
        last_24h = datetime.utcnow() - timedelta(hours=24)
        recent_learning = self.session.query(LearningExample).filter(
            LearningExample.created_at >= last_24h
        ).count()
        
        # Usage statistics
        total_references = self.session.query(
            func.sum(LearningExample.times_referenced)
        ).scalar() or 0
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_memories": learning_count + episodic_count + procedural_count + pattern_count,
            "by_type": {
                "learning_examples": learning_count,
                "episodic_memories": episodic_count,
                "procedural_memories": procedural_count,
                "patterns": pattern_count
            },
            "trust_metrics": {
                "high_trust_count": high_trust,
                "high_trust_ratio": high_trust / learning_count if learning_count > 0 else 0,
                "avg_trust": self._calculate_avg_trust()
            },
            "activity_24h": {
                "new_learning": recent_learning,
                "total_references": total_references
            },
            "system_health": self.lifecycle_manager.get_memory_health()
        }
    
    def _calculate_avg_trust(self) -> float:
        """Calculate average trust score."""
        result = self.session.query(
            func.avg(LearningExample.trust_score)
        ).scalar()
        return float(result) if result else 0.0
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics for memory system.
        
        Returns:
            Performance statistics
        """
        logger.info("[MEMORY-ANALYTICS] Gathering performance metrics...")
        
        # Query performance (estimated)
        learning_count = self.session.query(LearningExample).count()
        
        # Relationship graph metrics
        graph_stats = self.relationships_graph.get_graph_statistics()
        
        # Clustering metrics
        cluster_stats = self.clustering_system.get_cluster_statistics()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "database": {
                "total_memories": learning_count,
                "estimated_query_time_ms": self._estimate_query_time(learning_count)
            },
            "relationships": {
                "total_nodes": graph_stats["total_nodes"],
                "total_edges": graph_stats["total_edges"],
                "avg_degree": graph_stats["average_degree"]
            },
            "clustering": {
                "total_clusters": cluster_stats["total_clusters"],
                "avg_cluster_size": cluster_stats["avg_cluster_size"]
            },
            "cache_efficiency": {
                "note": "Cache stats available from MemoryMeshCache"
            }
        }
    
    def _estimate_query_time(self, memory_count: int) -> float:
        """Estimate query time based on memory count."""
        # Simple estimation: logarithmic scaling
        if memory_count < 100:
            return 10.0
        elif memory_count < 1000:
            return 20.0
        elif memory_count < 10000:
            return 50.0
        else:
            return 100.0
    
    def get_usage_patterns(
        self,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Analyze memory usage patterns.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Usage pattern analysis
        """
        logger.info(f"[MEMORY-ANALYTICS] Analyzing usage patterns ({days} days)...")
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        # Most referenced memories
        top_referenced = self.session.query(LearningExample).filter(
            LearningExample.times_referenced > 0
        ).order_by(
            LearningExample.times_referenced.desc()
        ).limit(10).all()
        
        # Most used procedures
        top_procedures = self.session.query(Procedure).filter(
            Procedure.usage_count > 0
        ).order_by(
            Procedure.usage_count.desc()
        ).limit(10).all()
        
        # Usage by type
        usage_by_type = defaultdict(int)
        for ex in self.session.query(LearningExample).filter(
            LearningExample.times_referenced > 0
        ).all():
            usage_by_type[ex.example_type] += ex.times_referenced or 0
        
        return {
            "period_days": days,
            "top_referenced_memories": [
                {
                    "id": ex.id,
                    "type": ex.example_type,
                    "references": ex.times_referenced or 0,
                    "trust_score": ex.trust_score
                }
                for ex in top_referenced
            ],
            "top_used_procedures": [
                {
                    "id": proc.id,
                    "name": proc.name,
                    "usage_count": proc.usage_count or 0,
                    "success_rate": proc.success_rate
                }
                for proc in top_procedures
            ],
            "usage_by_type": dict(usage_by_type),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_trend_analysis(
        self,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Analyze trends over time.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Trend analysis
        """
        logger.info(f"[MEMORY-ANALYTICS] Analyzing trends ({days} days)...")
        
        # Daily counts
        daily_counts = []
        for i in range(days):
            date = datetime.utcnow() - timedelta(days=i)
            start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
            
            count = self.session.query(LearningExample).filter(
                and_(
                    LearningExample.created_at >= start,
                    LearningExample.created_at < end
                )
            ).count()
            
            daily_counts.append({
                "date": start.isoformat(),
                "count": count
            })
        
        # Trust trend
        recent_trust = self.session.query(
            func.avg(LearningExample.trust_score)
        ).filter(
            LearningExample.created_at >= datetime.utcnow() - timedelta(days=7)
        ).scalar() or 0
        
        older_trust = self.session.query(
            func.avg(LearningExample.trust_score)
        ).filter(
            and_(
                LearningExample.created_at >= datetime.utcnow() - timedelta(days=30),
                LearningExample.created_at < datetime.utcnow() - timedelta(days=7)
            )
        ).scalar() or 0
        
        trust_trend = "improving" if recent_trust > older_trust else "declining" if recent_trust < older_trust else "stable"
        
        return {
            "period_days": days,
            "daily_counts": list(reversed(daily_counts)),  # Oldest first
            "trust_trend": {
                "recent_7d_avg": float(recent_trust),
                "older_23d_avg": float(older_trust),
                "trend": trust_trend,
                "change": float(recent_trust - older_trust)
            },
            "total_in_period": sum(d["count"] for d in daily_counts),
            "avg_per_day": sum(d["count"] for d in daily_counts) / days if days > 0 else 0,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_comprehensive_dashboard(self) -> Dict[str, Any]:
        """
        Get comprehensive analytics dashboard.
        
        Combines all analytics into one dashboard.
        
        Returns:
            Complete dashboard data
        """
        logger.info("[MEMORY-ANALYTICS] Generating comprehensive dashboard...")
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "real_time_metrics": self.get_real_time_metrics(),
            "performance_metrics": self.get_performance_metrics(),
            "usage_patterns": self.get_usage_patterns(),
            "trend_analysis": self.get_trend_analysis(),
            "health_status": self.lifecycle_manager.get_memory_health(),
            "relationships": self.relationships_graph.get_graph_statistics(),
            "clustering": self.clustering_system.get_cluster_statistics()
        }
    
    def get_resource_utilization(self) -> Dict[str, Any]:
        """
        Get resource utilization metrics.
        
        Returns:
            Resource usage statistics
        """
        logger.info("[MEMORY-ANALYTICS] Calculating resource utilization...")
        
        # Estimate storage
        learning_count = self.session.query(LearningExample).count()
        estimated_storage_mb = learning_count * 0.01  # ~10KB per memory (rough estimate)
        
        # Memory usage (estimated)
        estimated_memory_mb = (
            learning_count * 0.05 +  # ~50KB per memory in memory
            len(self.relationships_graph.relationships) * 0.001  # Relationship overhead
        )
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "storage": {
                "estimated_mb": estimated_storage_mb,
                "estimated_gb": estimated_storage_mb / 1024,
                "note": "Rough estimate based on memory count"
            },
            "memory": {
                "estimated_mb": estimated_memory_mb,
                "note": "In-memory structures"
            },
            "efficiency": {
                "memories_per_mb": learning_count / max(estimated_storage_mb, 0.1),
                "compression_potential": "High (lifecycle manager can compress)"
            }
        }


def get_memory_analytics(
    session: Session,
    knowledge_base_path
) -> MemoryAnalytics:
    """Factory function to get memory analytics."""
    return MemoryAnalytics(session=session, knowledge_base_path=knowledge_base_path)
