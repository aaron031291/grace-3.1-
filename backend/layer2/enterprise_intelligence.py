import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import defaultdict
import json
import gzip
from pathlib import Path

logger = logging.getLogger(__name__)


class EnterpriseLayer2Intelligence:
    """
    Enterprise-grade Layer 2 Intelligence.
    
    Features:
    - Intelligence analytics
    - Health monitoring
    - Lifecycle management
    - Performance optimization
    """
    
    def __init__(
        self,
        layer2_intelligence,
        archive_dir: Optional[Path] = None,
        retention_days: int = 90
    ):
        """Initialize enterprise Layer 2 Intelligence."""
        self.layer2 = layer2_intelligence
        self.retention_days = retention_days
        
        # Archive directory
        if archive_dir:
            self.archive_dir = archive_dir
        else:
            self.archive_dir = Path("backend/archived_layer2_intelligence")
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        
        # Intelligence tracking
        self._intelligence_history: List[Dict[str, Any]] = []
        self._max_history = 1000
        
        # Analytics
        self._intelligence_stats = {
            "total_cycles": 0,
            "total_decisions": 0,
            "total_insights": 0,
            "by_intent": defaultdict(int),
            "by_confidence": defaultdict(int),
            "avg_confidence": 0.0,
            "high_confidence_count": 0
        }
        
        # Performance tracking
        self._performance_stats = {
            "avg_cycle_time_ms": 0.0,
            "slow_cycles": [],
            "phase_times": {
                "observe": 0.0,
                "orient": 0.0,
                "decide": 0.0,
                "act": 0.0
            }
        }
        
        logger.info(
            f"[ENTERPRISE-LAYER2-INTELLIGENCE] Initialized: "
            f"retention={retention_days}d"
        )
    
    def track_cycle(
        self,
        intent: str,
        decision: Dict[str, Any],
        confidence: float,
        cycle_time_ms: float = 0.0,
        phase_times: Optional[Dict[str, float]] = None
    ):
        """Track cognitive cycle for analytics."""
        self._intelligence_stats["total_cycles"] += 1
        self._intelligence_stats["total_decisions"] += 1
        self._intelligence_stats["by_intent"][intent] += 1
        
        # Track confidence
        confidence_bucket = "high" if confidence >= 0.7 else "medium" if confidence >= 0.4 else "low"
        self._intelligence_stats["by_confidence"][confidence_bucket] += 1
        
        if confidence >= 0.7:
            self._intelligence_stats["high_confidence_count"] += 1
        
        # Update average confidence
        total = self._intelligence_stats["total_cycles"]
        current_avg = self._intelligence_stats["avg_confidence"]
        self._intelligence_stats["avg_confidence"] = (
            (current_avg * (total - 1) + confidence) / total
        )
        
        # Track cycle
        cycle_record = {
            "intent": intent,
            "decision": decision,
            "confidence": confidence,
            "cycle_time_ms": cycle_time_ms,
            "phase_times": phase_times or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self._intelligence_history.append(cycle_record)
        if len(self._intelligence_history) > self._max_history:
            self._intelligence_history.pop(0)
        
        # Track performance
        if cycle_time_ms > 0:
            total = len(self._intelligence_history)
            current_avg = self._performance_stats["avg_cycle_time_ms"]
            self._performance_stats["avg_cycle_time_ms"] = (
                (current_avg * (total - 1) + cycle_time_ms) / total
            )
            
            # Track slow cycles (>10s)
            if cycle_time_ms > 10000:
                self._performance_stats["slow_cycles"].append(cycle_record)
                if len(self._performance_stats["slow_cycles"]) > 100:
                    self._performance_stats["slow_cycles"].pop(0)
        
        # Track phase times
        if phase_times:
            for phase, time_ms in phase_times.items():
                if phase in self._performance_stats["phase_times"]:
                    current = self._performance_stats["phase_times"][phase]
                    count = sum(1 for c in self._intelligence_history if phase in c.get("phase_times", {}))
                    self._performance_stats["phase_times"][phase] = (
                        (current * (count - 1) + time_ms) / count if count > 0 else time_ms
                    )
    
    def track_insight(self):
        """Track insight generation."""
        self._intelligence_stats["total_insights"] += 1
    
    def cluster_intelligence(self) -> Dict[str, Any]:
        """
        Cluster intelligence by intent, confidence, and temporal.
        
        Returns:
            Cluster statistics
        """
        logger.info("[ENTERPRISE-LAYER2-INTELLIGENCE] Clustering intelligence...")
        
        # Cluster by intent
        intent_clusters = defaultdict(int)
        confidence_clusters = defaultdict(int)
        temporal_clusters = defaultdict(int)
        
        for cycle in self._intelligence_history:
            intent_clusters[cycle.get("intent", "unknown")] += 1
            
            confidence = cycle.get("confidence", 0.5)
            confidence_bucket = "high" if confidence >= 0.7 else "medium" if confidence >= 0.4 else "low"
            confidence_clusters[confidence_bucket] += 1
            
            # Temporal clusters (by day)
            timestamp = cycle.get("timestamp")
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp)
                    day_key = dt.strftime("%Y-%m-%d")
                    temporal_clusters[day_key] += 1
                except:
                    pass
        
        clusters = {
            "by_intent": dict(sorted(intent_clusters.items(), key=lambda x: x[1], reverse=True)[:20]),
            "by_confidence": dict(confidence_clusters),
            "by_temporal": dict(sorted(temporal_clusters.items(), key=lambda x: x[0], reverse=True)[:30]),
            "total_clusters": (
                len(intent_clusters) + len(confidence_clusters)
            )
        }
        
        logger.info(
            f"[ENTERPRISE-LAYER2-INTELLIGENCE] Created clusters: "
            f"{len(intent_clusters)} intent, "
            f"{len(confidence_clusters)} confidence"
        )
        
        return clusters
    
    def compress_context_memory(self) -> Dict[str, Any]:
        """
        Compress old context memory.
        
        Returns:
            Compression statistics
        """
        logger.info("[ENTERPRISE-LAYER2-INTELLIGENCE] Compressing context memory...")
        
        if not hasattr(self.layer2, '_context_memory'):
            return {"compressed_count": 0, "space_saved_bytes": 0}
        
        context_memory = self.layer2._context_memory
        original_size = len(json.dumps(context_memory))
        
        # Keep only recent contexts
        cutoff_date = datetime.utcnow() - timedelta(days=7)
        compressed_memory = []
        
        for ctx in context_memory:
            timestamp = ctx.get("timestamp")
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp)
                    if dt >= cutoff_date:
                        compressed_memory.append(ctx)
                except:
                    compressed_memory.append(ctx)  # Keep if can't parse
            else:
                compressed_memory.append(ctx)
        
        # Update context memory
        self.layer2._context_memory = compressed_memory[-self.layer2._max_context:]
        
        compressed_size = len(json.dumps(self.layer2._context_memory))
        space_saved = original_size - compressed_size
        
        logger.info(
            f"[ENTERPRISE-LAYER2-INTELLIGENCE] Compressed context memory, "
            f"saved ~{space_saved / 1024:.2f} KB"
        )
        
        return {
            "compressed_count": len(context_memory) - len(self.layer2._context_memory),
            "space_saved_bytes": space_saved
        }
    
    def get_intelligence_health(self) -> Dict[str, Any]:
        """
        Get intelligence health metrics.
        
        Returns:
            Health metrics
        """
        logger.info("[ENTERPRISE-LAYER2-INTELLIGENCE] Calculating health...")
        
        # Recent activity
        recent_cycles = [
            c for c in self._intelligence_history
            if (datetime.utcnow() - datetime.fromisoformat(c.get("timestamp", "2000-01-01"))).days < 7
        ]
        
        # Confidence health
        avg_confidence = self._intelligence_stats["avg_confidence"]
        high_confidence_ratio = (
            self._intelligence_stats["high_confidence_count"] /
            self._intelligence_stats["total_cycles"]
            if self._intelligence_stats["total_cycles"] > 0 else 0.0
        )
        
        # Performance health
        avg_cycle_time = self._performance_stats["avg_cycle_time_ms"]
        performance_score = max(0.0, 1.0 - (avg_cycle_time / 30000.0))  # Penalize if >30s
        
        # Health score
        activity_ratio = len(recent_cycles) / len(self._intelligence_history) if self._intelligence_history else 0.0
        health_score = (
            activity_ratio * 0.3 +          # Recent activity
            avg_confidence * 0.4 +         # Confidence level
            performance_score * 0.3        # Performance
        )
        
        health = {
            "total_cycles": self._intelligence_stats["total_cycles"],
            "total_insights": self._intelligence_stats["total_insights"],
            "recent_7d": len(recent_cycles),
            "avg_confidence": avg_confidence,
            "high_confidence_ratio": high_confidence_ratio,
            "avg_cycle_time_ms": avg_cycle_time,
            "phase_times": self._performance_stats["phase_times"],
            "health_score": health_score,
            "health_status": (
                "excellent" if health_score >= 0.8 else
                "good" if health_score >= 0.6 else
                "fair" if health_score >= 0.4 else
                "poor"
            ),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(
            f"[ENTERPRISE-LAYER2-INTELLIGENCE] Health: score={health_score:.2f} "
            f"({health['health_status']})"
        )
        
        return health
    
    def archive_old_intelligence(self) -> Dict[str, Any]:
        """
        Archive old intelligence beyond retention threshold.
        
        Returns:
            Archive statistics
        """
        logger.info(f"[ENTERPRISE-LAYER2-INTELLIGENCE] Archiving intelligence older than {self.retention_days} days...")
        
        cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)
        
        # Separate old and new intelligence
        old_intelligence = []
        new_intelligence = []
        
        for cycle in self._intelligence_history:
            timestamp = cycle.get("timestamp")
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp)
                    if dt < cutoff_date:
                        old_intelligence.append(cycle)
                    else:
                        new_intelligence.append(cycle)
                except:
                    new_intelligence.append(cycle)  # Keep if can't parse
            else:
                new_intelligence.append(cycle)
        
        archived_count = len(old_intelligence)
        
        if old_intelligence:
            # Group by month
            by_month = {}
            for cycle in old_intelligence:
                timestamp = cycle.get("timestamp")
                if timestamp:
                    try:
                        dt = datetime.fromisoformat(timestamp)
                        month_key = dt.strftime("%Y-%m")
                        if month_key not in by_month:
                            by_month[month_key] = []
                        by_month[month_key].append(cycle)
                    except:
                        pass
            
            # Save compressed archives
            for month, cycles in by_month.items():
                archive_file = self.archive_dir / f"intelligence_{month}.json.gz"
                
                with gzip.open(archive_file, 'wt', encoding='utf-8') as f:
                    json.dump({
                        "archived_at": datetime.utcnow().isoformat(),
                        "month": month,
                        "count": len(cycles),
                        "cycles": cycles
                    }, f, indent=2, default=str)
        
        # Update history
        self._intelligence_history = new_intelligence
        
        logger.info(f"[ENTERPRISE-LAYER2-INTELLIGENCE] Archived {archived_count} cycles")
        
        return {
            "archived_count": archived_count,
            "archive_files_created": len(by_month) if old_intelligence else 0,
            "remaining_cycles": len(new_intelligence)
        }
    
    def get_intelligence_analytics(self) -> Dict[str, Any]:
        """
        Get comprehensive intelligence analytics.
        
        Returns:
            Complete analytics dashboard
        """
        logger.info("[ENTERPRISE-LAYER2-INTELLIGENCE] Generating analytics...")
        
        clusters = self.cluster_intelligence()
        health = self.get_intelligence_health()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "intelligence_statistics": {
                "total_cycles": self._intelligence_stats["total_cycles"],
                "total_decisions": self._intelligence_stats["total_decisions"],
                "total_insights": self._intelligence_stats["total_insights"],
                "by_intent": dict(sorted(
                    self._intelligence_stats["by_intent"].items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:20]),
                "by_confidence": dict(self._intelligence_stats["by_confidence"]),
                "avg_confidence": self._intelligence_stats["avg_confidence"],
                "high_confidence_ratio": (
                    self._intelligence_stats["high_confidence_count"] /
                    self._intelligence_stats["total_cycles"]
                    if self._intelligence_stats["total_cycles"] > 0 else 0.0
                )
            },
            "performance_statistics": {
                "avg_cycle_time_ms": self._performance_stats["avg_cycle_time_ms"],
                "slow_cycles_count": len(self._performance_stats["slow_cycles"]),
                "phase_times": self._performance_stats["phase_times"]
            },
            "clusters": clusters,
            "health": health
        }


def get_enterprise_layer2_intelligence(
    layer2_intelligence,
    archive_dir: Optional[Path] = None,
    retention_days: int = 90
) -> EnterpriseLayer2Intelligence:
    """Factory function to get enterprise Layer 2 Intelligence."""
    return EnterpriseLayer2Intelligence(
        layer2_intelligence=layer2_intelligence,
        archive_dir=archive_dir,
        retention_days=retention_days
    )
