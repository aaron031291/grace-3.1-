import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import defaultdict
from dataclasses import asdict
import json
import gzip
from pathlib import Path
from cognitive.engine import CognitiveEngine, DecisionContext
class EnterpriseCognitiveEngine:
    logger = logging.getLogger(__name__)
    """
    Enterprise-grade Layer 2 Cognitive Engine.
    
    Features:
    - Decision analytics
    - Health monitoring
    - Lifecycle management
    - Decision clustering
    - Performance optimization
    """
    
    def __init__(
        self,
        cognitive_engine: CognitiveEngine,
        archive_dir: Optional[Path] = None,
        retention_days: int = 90
    ):
        """Initialize enterprise cognitive engine."""
        self.cognitive_engine = cognitive_engine
        self.retention_days = retention_days
        
        # Archive directory
        if archive_dir:
            self.archive_dir = archive_dir
        else:
            self.archive_dir = Path("backend/archived_decisions")
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        
        # Decision tracking
        self._decision_history: List[Dict[str, Any]] = []
        self._max_history = 1000
        
        # Analytics
        self._decision_stats = {
            "total_decisions": 0,
            "by_type": defaultdict(int),
            "by_outcome": defaultdict(int),
            "by_scope": defaultdict(int),
            "avg_confidence": 0.0,
            "successful_decisions": 0,
            "failed_decisions": 0
        }
        
        # Performance tracking
        self._performance_stats = {
            "avg_decision_time_ms": 0.0,
            "slow_decisions": [],
            "ooda_loop_times": {
                "observe": 0.0,
                "orient": 0.0,
                "decide": 0.0,
                "act": 0.0
            }
        }
        
        logger.info(
            f"[ENTERPRISE-COGNITIVE-ENGINE] Initialized: "
            f"retention={retention_days}d"
        )
    
    def track_decision(
        self,
        context: DecisionContext,
        outcome: str = "unknown",
        decision_time_ms: float = 0.0,
        ooda_times: Optional[Dict[str, float]] = None
    ):
        """Track decision for analytics."""
        self._decision_stats["total_decisions"] += 1
        
        # Track by scope
        self._decision_stats["by_scope"][context.impact_scope] += 1
        
        # Track by outcome
        self._decision_stats["by_outcome"][outcome] += 1
        if outcome == "success":
            self._decision_stats["successful_decisions"] += 1
        elif outcome == "failed":
            self._decision_stats["failed_decisions"] += 1
        
        # Track decision
        decision_record = {
            "decision_id": context.decision_id,
            "problem_statement": context.problem_statement,
            "impact_scope": context.impact_scope,
            "is_reversible": context.is_reversible,
            "requires_determinism": context.requires_determinism,
            "outcome": outcome,
            "decision_time_ms": decision_time_ms,
            "timestamp": context.created_at.isoformat(),
            "ooda_times": ooda_times or {}
        }
        
        self._decision_history.append(decision_record)
        if len(self._decision_history) > self._max_history:
            self._decision_history.pop(0)
        
        # Track performance
        if decision_time_ms > 0:
            total = len(self._decision_history)
            current_avg = self._performance_stats["avg_decision_time_ms"]
            self._performance_stats["avg_decision_time_ms"] = (
                (current_avg * (total - 1) + decision_time_ms) / total
            )
            
            # Track slow decisions (>5s)
            if decision_time_ms > 5000:
                self._performance_stats["slow_decisions"].append(decision_record)
                if len(self._performance_stats["slow_decisions"]) > 100:
                    self._performance_stats["slow_decisions"].pop(0)
        
        # Track OODA loop times
        if ooda_times:
            for phase, time_ms in ooda_times.items():
                if phase in self._performance_stats["ooda_loop_times"]:
                    current = self._performance_stats["ooda_loop_times"][phase]
                    count = sum(1 for d in self._decision_history if phase in d.get("ooda_times", {}))
                    self._performance_stats["ooda_loop_times"][phase] = (
                        (current * (count - 1) + time_ms) / count if count > 0 else time_ms
                    )
    
    def cluster_decisions(self) -> Dict[str, Any]:
        """
        Cluster decisions by type, outcome, and scope.
        
        Returns:
            Cluster statistics
        """
        logger.info("[ENTERPRISE-COGNITIVE-ENGINE] Clustering decisions...")
        
        # Cluster by scope
        scope_clusters = defaultdict(int)
        outcome_clusters = defaultdict(int)
        reversibility_clusters = defaultdict(int)
        temporal_clusters = defaultdict(int)
        
        for decision in self._decision_history:
            scope_clusters[decision.get("impact_scope", "unknown")] += 1
            outcome_clusters[decision.get("outcome", "unknown")] += 1
            reversibility_clusters[str(decision.get("is_reversible", True))] += 1
            
            # Temporal clusters (by day)
            timestamp = decision.get("timestamp")
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp)
                    day_key = dt.strftime("%Y-%m-%d")
                    temporal_clusters[day_key] += 1
                except:
                    pass
        
        clusters = {
            "by_scope": dict(scope_clusters),
            "by_outcome": dict(outcome_clusters),
            "by_reversibility": dict(reversibility_clusters),
            "by_temporal": dict(sorted(temporal_clusters.items(), key=lambda x: x[0], reverse=True)[:30]),
            "total_clusters": (
                len(scope_clusters) + len(outcome_clusters) + len(reversibility_clusters)
            )
        }
        
        logger.info(
            f"[ENTERPRISE-COGNITIVE-ENGINE] Created clusters: "
            f"{len(scope_clusters)} scope, "
            f"{len(outcome_clusters)} outcome, "
            f"{len(reversibility_clusters)} reversibility"
        )
        
        return clusters
    
    def get_cognitive_engine_health(self) -> Dict[str, Any]:
        """
        Get cognitive engine health metrics.
        
        Returns:
            Health metrics
        """
        logger.info("[ENTERPRISE-COGNITIVE-ENGINE] Calculating health...")
        
        # Recent activity
        recent_decisions = [
            d for d in self._decision_history
            if (datetime.utcnow() - datetime.fromisoformat(d.get("timestamp", "2000-01-01"))).days < 7
        ]
        
        # Success rate
        total = self._decision_stats["total_decisions"]
        success_rate = (
            self._decision_stats["successful_decisions"] / total
            if total > 0 else 0.0
        )
        
        # Performance health
        avg_decision_time = self._performance_stats["avg_decision_time_ms"]
        performance_score = max(0.0, 1.0 - (avg_decision_time / 10000.0))  # Penalize if >10s
        
        # Health score
        activity_ratio = len(recent_decisions) / total if total > 0 else 0.0
        health_score = (
            activity_ratio * 0.3 +      # Recent activity
            success_rate * 0.4 +        # Success rate
            performance_score * 0.3     # Performance
        )
        
        health = {
            "total_decisions": total,
            "recent_7d": len(recent_decisions),
            "success_rate": success_rate,
            "avg_decision_time_ms": avg_decision_time,
            "ooda_loop_times": self._performance_stats["ooda_loop_times"],
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
            f"[ENTERPRISE-COGNITIVE-ENGINE] Health: score={health_score:.2f} "
            f"({health['health_status']})"
        )
        
        return health
    
    def archive_old_decisions(self) -> Dict[str, Any]:
        """
        Archive old decisions beyond retention threshold.
        
        Returns:
            Archive statistics
        """
        logger.info(f"[ENTERPRISE-COGNITIVE-ENGINE] Archiving decisions older than {self.retention_days} days...")
        
        cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)
        
        # Separate old and new decisions
        old_decisions = []
        new_decisions = []
        
        for decision in self._decision_history:
            timestamp = decision.get("timestamp")
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp)
                    if dt < cutoff_date:
                        old_decisions.append(decision)
                    else:
                        new_decisions.append(decision)
                except:
                    new_decisions.append(decision)  # Keep if can't parse
            else:
                new_decisions.append(decision)
        
        archived_count = len(old_decisions)
        
        if old_decisions:
            # Group by month
            by_month = {}
            for decision in old_decisions:
                timestamp = decision.get("timestamp")
                if timestamp:
                    try:
                        dt = datetime.fromisoformat(timestamp)
                        month_key = dt.strftime("%Y-%m")
                        if month_key not in by_month:
                            by_month[month_key] = []
                        by_month[month_key].append(decision)
                    except:
                        pass
            
            # Save compressed archives
            for month, decisions in by_month.items():
                archive_file = self.archive_dir / f"decisions_{month}.json.gz"
                
                with gzip.open(archive_file, 'wt', encoding='utf-8') as f:
                    json.dump({
                        "archived_at": datetime.utcnow().isoformat(),
                        "month": month,
                        "count": len(decisions),
                        "decisions": decisions
                    }, f, indent=2, default=str)
        
        # Update history
        self._decision_history = new_decisions
        
        logger.info(f"[ENTERPRISE-COGNITIVE-ENGINE] Archived {archived_count} decisions")
        
        return {
            "archived_count": archived_count,
            "archive_files_created": len(by_month) if old_decisions else 0,
            "remaining_decisions": len(new_decisions)
        }
    
    def get_cognitive_engine_analytics(self) -> Dict[str, Any]:
        """
        Get comprehensive cognitive engine analytics.
        
        Returns:
            Complete analytics dashboard
        """
        logger.info("[ENTERPRISE-COGNITIVE-ENGINE] Generating analytics...")
        
        clusters = self.cluster_decisions()
        health = self.get_cognitive_engine_health()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "decision_statistics": {
                "total_decisions": self._decision_stats["total_decisions"],
                "by_scope": dict(self._decision_stats["by_scope"]),
                "by_outcome": dict(self._decision_stats["by_outcome"]),
                "success_rate": (
                    self._decision_stats["successful_decisions"] /
                    self._decision_stats["total_decisions"]
                    if self._decision_stats["total_decisions"] > 0 else 0.0
                )
            },
            "performance_statistics": {
                "avg_decision_time_ms": self._performance_stats["avg_decision_time_ms"],
                "slow_decisions_count": len(self._performance_stats["slow_decisions"]),
                "ooda_loop_times": self._performance_stats["ooda_loop_times"]
            },
            "clusters": clusters,
            "health": health
        }


def get_enterprise_cognitive_engine(
    cognitive_engine: CognitiveEngine,
    archive_dir: Optional[Path] = None,
    retention_days: int = 90
) -> EnterpriseCognitiveEngine:
    """Factory function to get enterprise cognitive engine."""
    return EnterpriseCognitiveEngine(
        cognitive_engine=cognitive_engine,
        archive_dir=archive_dir,
        retention_days=retention_days
    )
