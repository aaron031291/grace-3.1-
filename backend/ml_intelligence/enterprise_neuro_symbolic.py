import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import defaultdict
import json
import gzip
from pathlib import Path
from ml_intelligence.neuro_symbolic_reasoner import NeuroSymbolicReasoner, ReasoningResult
class EnterpriseNeuroSymbolic:
    logger = logging.getLogger(__name__)
    """
    Enterprise-grade Neuro-Symbolic AI system.
    
    Features:
    - Reasoning analytics
    - Health monitoring
    - Lifecycle management
    - Reasoning clustering
    - Performance optimization
    - Weight optimization
    """
    
    def __init__(
        self,
        neuro_symbolic_reasoner: NeuroSymbolicReasoner,
        archive_dir: Optional[Path] = None,
        retention_days: int = 90
    ):
        """Initialize enterprise neuro-symbolic system."""
        self.reasoner = neuro_symbolic_reasoner
        self.retention_days = retention_days
        
        # Archive directory
        if archive_dir:
            self.archive_dir = archive_dir
        else:
            self.archive_dir = Path("backend/archived_neuro_symbolic")
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        
        # Reasoning tracking
        self._reasoning_history: List[Dict[str, Any]] = []
        self._max_history = 1000
        
        # Analytics
        self._reasoning_stats = {
            "total_reasonings": 0,
            "neural_only": 0,
            "symbolic_only": 0,
            "fused": 0,
            "by_confidence": defaultdict(int),
            "avg_neural_confidence": 0.0,
            "avg_symbolic_confidence": 0.0,
            "avg_fusion_confidence": 0.0,
            "high_confidence_count": 0
        }
        
        # Performance tracking
        self._performance_stats = {
            "avg_reasoning_time_ms": 0.0,
            "slow_reasonings": [],
            "phase_times": {
                "neural_search": 0.0,
                "symbolic_query": 0.0,
                "cross_inform": 0.0,
                "fusion": 0.0
            }
        }
        
        # Weight optimization tracking
        self._weight_stats = {
            "neural_weight": self.reasoner.neural_weight,
            "symbolic_weight": self.reasoner.symbolic_weight,
            "optimal_weights": [],
            "weight_adjustments": []
        }
        
        logger.info(
            f"[ENTERPRISE-NEURO-SYMBOLIC] Initialized: "
            f"neural_weight={self.reasoner.neural_weight:.2f}, "
            f"symbolic_weight={self.reasoner.symbolic_weight:.2f}, "
            f"retention={retention_days}d"
        )
    
    def track_reasoning(
        self,
        result: ReasoningResult,
        reasoning_time_ms: float = 0.0,
        phase_times: Optional[Dict[str, float]] = None
    ):
        """Track reasoning for analytics."""
        self._reasoning_stats["total_reasonings"] += 1
        
        # Track by type
        if len(result.neural_results) > 0 and len(result.symbolic_results) == 0:
            self._reasoning_stats["neural_only"] += 1
        elif len(result.neural_results) == 0 and len(result.symbolic_results) > 0:
            self._reasoning_stats["symbolic_only"] += 1
        else:
            self._reasoning_stats["fused"] += 1
        
        # Track confidence
        fusion_confidence = result.fusion_confidence
        confidence_bucket = "high" if fusion_confidence >= 0.7 else "medium" if fusion_confidence >= 0.4 else "low"
        self._reasoning_stats["by_confidence"][confidence_bucket] += 1
        
        if fusion_confidence >= 0.7:
            self._reasoning_stats["high_confidence_count"] += 1
        
        # Update average confidences
        total = self._reasoning_stats["total_reasonings"]
        self._reasoning_stats["avg_neural_confidence"] = (
            (self._reasoning_stats["avg_neural_confidence"] * (total - 1) + result.neural_confidence) / total
        )
        self._reasoning_stats["avg_symbolic_confidence"] = (
            (self._reasoning_stats["avg_symbolic_confidence"] * (total - 1) + result.symbolic_confidence) / total
        )
        self._reasoning_stats["avg_fusion_confidence"] = (
            (self._reasoning_stats["avg_fusion_confidence"] * (total - 1) + fusion_confidence) / total
        )
        
        # Track reasoning
        reasoning_record = {
            "query": result.query,
            "neural_results_count": len(result.neural_results),
            "symbolic_results_count": len(result.symbolic_results),
            "fused_results_count": len(result.fused_results),
            "neural_confidence": result.neural_confidence,
            "symbolic_confidence": result.symbolic_confidence,
            "fusion_confidence": fusion_confidence,
            "reasoning_time_ms": reasoning_time_ms,
            "phase_times": phase_times or {},
            "timestamp": result.timestamp.isoformat() if result.timestamp else datetime.utcnow().isoformat()
        }
        
        self._reasoning_history.append(reasoning_record)
        if len(self._reasoning_history) > self._max_history:
            self._reasoning_history.pop(0)
        
        # Track performance
        if reasoning_time_ms > 0:
            total = len(self._reasoning_history)
            current_avg = self._performance_stats["avg_reasoning_time_ms"]
            self._performance_stats["avg_reasoning_time_ms"] = (
                (current_avg * (total - 1) + reasoning_time_ms) / total
            )
            
            # Track slow reasonings (>5s)
            if reasoning_time_ms > 5000:
                self._performance_stats["slow_reasonings"].append(reasoning_record)
                if len(self._performance_stats["slow_reasonings"]) > 100:
                    self._performance_stats["slow_reasonings"].pop(0)
        
        # Track phase times
        if phase_times:
            for phase, time_ms in phase_times.items():
                if phase in self._performance_stats["phase_times"]:
                    current = self._performance_stats["phase_times"][phase]
                    count = sum(1 for r in self._reasoning_history if phase in r.get("phase_times", {}))
                    self._performance_stats["phase_times"][phase] = (
                        (current * (count - 1) + time_ms) / count if count > 0 else time_ms
                    )
    
    def optimize_weights(self) -> Dict[str, Any]:
        """
        Optimize neural-symbolic weights based on performance.
        
        Returns:
            Optimization results
        """
        logger.info("[ENTERPRISE-NEURO-SYMBOLIC] Optimizing weights...")
        
        if len(self._reasoning_history) < 10:
            return {
                "optimized": False,
                "reason": "Insufficient data (need at least 10 reasonings)"
            }
        
        # Analyze which component performs better
        neural_success = 0
        symbolic_success = 0
        fused_success = 0
        
        for reasoning in self._reasoning_history[-100:]:  # Last 100
            fusion_conf = reasoning.get("fusion_confidence", 0.0)
            neural_conf = reasoning.get("neural_confidence", 0.0)
            symbolic_conf = reasoning.get("symbolic_confidence", 0.0)
            
            if fusion_conf >= 0.7:
                fused_success += 1
            if neural_conf >= 0.7:
                neural_success += 1
            if symbolic_conf >= 0.7:
                symbolic_success += 1
        
        # Calculate optimal weights
        total = len(self._reasoning_history[-100:])
        neural_ratio = neural_success / total if total > 0 else 0.5
        symbolic_ratio = symbolic_success / total if total > 0 else 0.5
        
        # Normalize to sum to 1.0
        total_ratio = neural_ratio + symbolic_ratio
        if total_ratio > 0:
            optimal_neural = neural_ratio / total_ratio
            optimal_symbolic = symbolic_ratio / total_ratio
        else:
            optimal_neural = 0.5
            optimal_symbolic = 0.5
        
        # Store optimal weights
        self._weight_stats["optimal_weights"].append({
            "neural_weight": optimal_neural,
            "symbolic_weight": optimal_symbolic,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Keep only last 50 optimizations
        if len(self._weight_stats["optimal_weights"]) > 50:
            self._weight_stats["optimal_weights"].pop(0)
        
        # Calculate adjustment
        current_neural = self.reasoner.neural_weight
        current_symbolic = self.reasoner.symbolic_weight
        
        adjustment_needed = abs(optimal_neural - current_neural) > 0.1
        
        if adjustment_needed:
            self._weight_stats["weight_adjustments"].append({
                "from_neural": current_neural,
                "to_neural": optimal_neural,
                "from_symbolic": current_symbolic,
                "to_symbolic": optimal_symbolic,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Update weights
            self.reasoner.neural_weight = optimal_neural
            self.reasoner.symbolic_weight = optimal_symbolic
            self._weight_stats["neural_weight"] = optimal_neural
            self._weight_stats["symbolic_weight"] = optimal_symbolic
        
        logger.info(
            f"[ENTERPRISE-NEURO-SYMBOLIC] Weight optimization: "
            f"neural={optimal_neural:.2f}, symbolic={optimal_symbolic:.2f}, "
            f"adjusted={adjustment_needed}"
        )
        
        return {
            "optimized": adjustment_needed,
            "optimal_neural_weight": optimal_neural,
            "optimal_symbolic_weight": optimal_symbolic,
            "current_neural_weight": current_neural,
            "current_symbolic_weight": current_symbolic,
            "neural_success_ratio": neural_ratio,
            "symbolic_success_ratio": symbolic_ratio
        }
    
    def cluster_reasonings(self) -> Dict[str, Any]:
        """
        Cluster reasonings by type, confidence, and fusion.
        
        Returns:
            Cluster statistics
        """
        logger.info("[ENTERPRISE-NEURO-SYMBOLIC] Clustering reasonings...")
        
        # Cluster by type
        type_clusters = defaultdict(int)
        confidence_clusters = defaultdict(int)
        fusion_clusters = defaultdict(int)
        temporal_clusters = defaultdict(int)
        
        for reasoning in self._reasoning_history:
            # Type clusters
            if reasoning.get("neural_results_count", 0) > 0 and reasoning.get("symbolic_results_count", 0) == 0:
                type_clusters["neural_only"] += 1
            elif reasoning.get("neural_results_count", 0) == 0 and reasoning.get("symbolic_results_count", 0) > 0:
                type_clusters["symbolic_only"] += 1
            else:
                type_clusters["fused"] += 1
            
            # Confidence clusters
            fusion_conf = reasoning.get("fusion_confidence", 0.5)
            confidence_bucket = "high" if fusion_conf >= 0.7 else "medium" if fusion_conf >= 0.4 else "low"
            confidence_clusters[confidence_bucket] += 1
            
            # Fusion clusters (by fusion confidence)
            if fusion_conf >= 0.8:
                fusion_clusters["excellent"] += 1
            elif fusion_conf >= 0.6:
                fusion_clusters["good"] += 1
            elif fusion_conf >= 0.4:
                fusion_clusters["fair"] += 1
            else:
                fusion_clusters["poor"] += 1
            
            # Temporal clusters (by day)
            timestamp = reasoning.get("timestamp")
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp)
                    day_key = dt.strftime("%Y-%m-%d")
                    temporal_clusters[day_key] += 1
                except:
                    pass
        
        clusters = {
            "by_type": dict(type_clusters),
            "by_confidence": dict(confidence_clusters),
            "by_fusion": dict(fusion_clusters),
            "by_temporal": dict(sorted(temporal_clusters.items(), key=lambda x: x[0], reverse=True)[:30]),
            "total_clusters": (
                len(type_clusters) + len(confidence_clusters) + len(fusion_clusters)
            )
        }
        
        logger.info(
            f"[ENTERPRISE-NEURO-SYMBOLIC] Created clusters: "
            f"{len(type_clusters)} type, "
            f"{len(confidence_clusters)} confidence, "
            f"{len(fusion_clusters)} fusion"
        )
        
        return clusters
    
    def get_neuro_symbolic_health(self) -> Dict[str, Any]:
        """
        Get neuro-symbolic system health metrics.
        
        Returns:
            Health metrics
        """
        logger.info("[ENTERPRISE-NEURO-SYMBOLIC] Calculating health...")
        
        # Recent activity
        recent_reasonings = [
            r for r in self._reasoning_history
            if (datetime.utcnow() - datetime.fromisoformat(r.get("timestamp", "2000-01-01"))).days < 7
        ]
        
        # Confidence health
        avg_fusion_confidence = self._reasoning_stats["avg_fusion_confidence"]
        high_confidence_ratio = (
            self._reasoning_stats["high_confidence_count"] /
            self._reasoning_stats["total_reasonings"]
            if self._reasoning_stats["total_reasonings"] > 0 else 0.0
        )
        
        # Fusion health (how often we successfully fuse)
        fusion_ratio = (
            self._reasoning_stats["fused"] /
            self._reasoning_stats["total_reasonings"]
            if self._reasoning_stats["total_reasonings"] > 0 else 0.0
        )
        
        # Performance health
        avg_reasoning_time = self._performance_stats["avg_reasoning_time_ms"]
        performance_score = max(0.0, 1.0 - (avg_reasoning_time / 10000.0))  # Penalize if >10s
        
        # Weight balance health
        neural_weight = self.reasoner.neural_weight
        symbolic_weight = self.reasoner.symbolic_weight
        weight_balance = 1.0 - abs(neural_weight - symbolic_weight)  # Prefer balanced
        
        # Health score
        activity_ratio = len(recent_reasonings) / len(self._reasoning_history) if self._reasoning_history else 0.0
        health_score = (
            activity_ratio * 0.2 +          # Recent activity
            avg_fusion_confidence * 0.3 +    # Confidence level
            fusion_ratio * 0.2 +            # Fusion success
            performance_score * 0.2 +        # Performance
            weight_balance * 0.1            # Weight balance
        )
        
        health = {
            "total_reasonings": self._reasoning_stats["total_reasonings"],
            "recent_7d": len(recent_reasonings),
            "avg_fusion_confidence": avg_fusion_confidence,
            "high_confidence_ratio": high_confidence_ratio,
            "fusion_ratio": fusion_ratio,
            "avg_reasoning_time_ms": avg_reasoning_time,
            "neural_weight": neural_weight,
            "symbolic_weight": symbolic_weight,
            "weight_balance": weight_balance,
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
            f"[ENTERPRISE-NEURO-SYMBOLIC] Health: score={health_score:.2f} "
            f"({health['health_status']})"
        )
        
        return health
    
    def archive_old_reasonings(self) -> Dict[str, Any]:
        """
        Archive old reasonings beyond retention threshold.
        
        Returns:
            Archive statistics
        """
        logger.info(f"[ENTERPRISE-NEURO-SYMBOLIC] Archiving reasonings older than {self.retention_days} days...")
        
        cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)
        
        # Separate old and new reasonings
        old_reasonings = []
        new_reasonings = []
        
        for reasoning in self._reasoning_history:
            timestamp = reasoning.get("timestamp")
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp)
                    if dt < cutoff_date:
                        old_reasonings.append(reasoning)
                    else:
                        new_reasonings.append(reasoning)
                except:
                    new_reasonings.append(reasoning)  # Keep if can't parse
            else:
                new_reasonings.append(reasoning)
        
        archived_count = len(old_reasonings)
        
        if old_reasonings:
            # Group by month
            by_month = {}
            for reasoning in old_reasonings:
                timestamp = reasoning.get("timestamp")
                if timestamp:
                    try:
                        dt = datetime.fromisoformat(timestamp)
                        month_key = dt.strftime("%Y-%m")
                        if month_key not in by_month:
                            by_month[month_key] = []
                        by_month[month_key].append(reasoning)
                    except:
                        pass
            
            # Save compressed archives
            for month, reasonings in by_month.items():
                archive_file = self.archive_dir / f"reasonings_{month}.json.gz"
                
                with gzip.open(archive_file, 'wt', encoding='utf-8') as f:
                    json.dump({
                        "archived_at": datetime.utcnow().isoformat(),
                        "month": month,
                        "count": len(reasonings),
                        "reasonings": reasonings
                    }, f, indent=2, default=str)
        
        # Update history
        self._reasoning_history = new_reasonings
        
        logger.info(f"[ENTERPRISE-NEURO-SYMBOLIC] Archived {archived_count} reasonings")
        
        return {
            "archived_count": archived_count,
            "archive_files_created": len(by_month) if old_reasonings else 0,
            "remaining_reasonings": len(new_reasonings)
        }
    
    def get_neuro_symbolic_analytics(self) -> Dict[str, Any]:
        """
        Get comprehensive neuro-symbolic analytics.
        
        Returns:
            Complete analytics dashboard
        """
        logger.info("[ENTERPRISE-NEURO-SYMBOLIC] Generating analytics...")
        
        clusters = self.cluster_reasonings()
        health = self.get_neuro_symbolic_health()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "reasoning_statistics": {
                "total_reasonings": self._reasoning_stats["total_reasonings"],
                "neural_only": self._reasoning_stats["neural_only"],
                "symbolic_only": self._reasoning_stats["symbolic_only"],
                "fused": self._reasoning_stats["fused"],
                "by_confidence": dict(self._reasoning_stats["by_confidence"]),
                "avg_neural_confidence": self._reasoning_stats["avg_neural_confidence"],
                "avg_symbolic_confidence": self._reasoning_stats["avg_symbolic_confidence"],
                "avg_fusion_confidence": self._reasoning_stats["avg_fusion_confidence"],
                "high_confidence_ratio": (
                    self._reasoning_stats["high_confidence_count"] /
                    self._reasoning_stats["total_reasonings"]
                    if self._reasoning_stats["total_reasonings"] > 0 else 0.0
                )
            },
            "performance_statistics": {
                "avg_reasoning_time_ms": self._performance_stats["avg_reasoning_time_ms"],
                "slow_reasonings_count": len(self._performance_stats["slow_reasonings"]),
                "phase_times": self._performance_stats["phase_times"]
            },
            "weight_statistics": {
                "current_neural_weight": self._weight_stats["neural_weight"],
                "current_symbolic_weight": self._weight_stats["symbolic_weight"],
                "optimal_weights_history": self._weight_stats["optimal_weights"][-10:],  # Last 10
                "total_adjustments": len(self._weight_stats["weight_adjustments"])
            },
            "clusters": clusters,
            "health": health
        }


def get_enterprise_neuro_symbolic(
    neuro_symbolic_reasoner: NeuroSymbolicReasoner,
    archive_dir: Optional[Path] = None,
    retention_days: int = 90
) -> EnterpriseNeuroSymbolic:
    """Factory function to get enterprise neuro-symbolic system."""
    return EnterpriseNeuroSymbolic(
        neuro_symbolic_reasoner=neuro_symbolic_reasoner,
        archive_dir=archive_dir,
        retention_days=retention_days
    )
