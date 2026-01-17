import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import deque
import statistics
from sqlalchemy.orm import Session
from cognitive.learning_memory import LearningExample
class PerformanceMetrics:
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    """Performance metrics for Layer 1 operations."""
    operation_name: str
    count: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    latencies: deque = field(default_factory=lambda: deque(maxlen=1000))
    
    def record(self, duration: float):
        """Record a duration."""
        self.count += 1
        self.total_time += duration
        self.min_time = min(self.min_time, duration)
        self.max_time = max(self.max_time, duration)
        self.latencies.append(duration)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        if self.count == 0:
            return {
                'count': 0,
                'avg_time': 0.0,
                'min_time': 0.0,
                'max_time': 0.0,
                'p50': 0.0,
                'p95': 0.0,
                'p99': 0.0
            }
        
        sorted_latencies = sorted(self.latencies)
        n = len(sorted_latencies)
        
        return {
            'count': self.count,
            'avg_time': self.total_time / self.count,
            'min_time': self.min_time if self.min_time != float('inf') else 0.0,
            'max_time': self.max_time,
            'p50': sorted_latencies[n // 2] if n > 0 else 0.0,
            'p95': sorted_latencies[int(n * 0.95)] if n > 0 else 0.0,
            'p99': sorted_latencies[int(n * 0.99)] if n > 0 else 0.0,
            'total_time': self.total_time
        }


@dataclass
class HealthStatus:
    """Health status for Layer 1 system."""
    status: str  # healthy, degraded, unhealthy
    health_score: float  # 0-100
    issues: List[str]
    recommendations: List[str]
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'status': self.status,
            'health_score': self.health_score,
            'issues': self.issues,
            'recommendations': self.recommendations,
            'timestamp': self.timestamp.isoformat()
        }


class Layer1Monitor:
    """
    Comprehensive monitoring for Layer 1 operations.
    
    Tracks performance, health, and provides alerting.
    """
    
    def __init__(self, session: Optional[Session] = None):
        """
        Initialize Layer 1 monitor.
        
        Args:
            session: Optional database session
        """
        self.session = session
        
        # Performance metrics
        self.metrics: Dict[str, PerformanceMetrics] = {}
        
        # Health thresholds
        self.health_thresholds = {
            'trust_score_avg_min': 0.6,
            'consistency_score_avg_min': 0.5,
            'validation_coverage_min': 0.7,
            'p95_latency_max_ms': 1000.0
        }
        
        # Alerts
        self.alerts: List[Dict[str, Any]] = []
    
    def record_operation(
        self,
        operation_name: str,
        duration: float
    ):
        """Record an operation duration."""
        if operation_name not in self.metrics:
            self.metrics[operation_name] = PerformanceMetrics(operation_name=operation_name)
        
        self.metrics[operation_name].record(duration)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get all performance statistics."""
        return {
            operation: metrics.get_stats()
            for operation, metrics in self.metrics.items()
        }
    
    def check_health(self) -> HealthStatus:
        """
        Perform comprehensive health check.
        
        Returns:
            HealthStatus with health assessment
        """
        issues = []
        recommendations = []
        health_score = 100.0
        
        # 1. Check trust scores
        if self.session:
            avg_trust = self._get_average_trust_score()
            if avg_trust < self.health_thresholds['trust_score_avg_min']:
                issues.append(f"Average trust score {avg_trust:.2f} is below threshold")
                health_score -= 20
                recommendations.append("Review and improve trust scores")
        
        # 2. Check consistency scores
        if self.session:
            avg_consistency = self._get_average_consistency_score()
            if avg_consistency < self.health_thresholds['consistency_score_avg_min']:
                issues.append(f"Average consistency score {avg_consistency:.2f} is below threshold")
                health_score -= 15
                recommendations.append("Run consistency checks and resolve conflicts")
        
        # 3. Check performance
        for operation, metrics in self.metrics.items():
            stats = metrics.get_stats()
            if stats['p95'] > self.health_thresholds['p95_latency_max_ms'] / 1000.0:
                issues.append(f"{operation} p95 latency {stats['p95']*1000:.0f}ms exceeds threshold")
                health_score -= 10
                recommendations.append(f"Optimize {operation} performance")
        
        # 4. Check validation coverage
        if self.session:
            coverage = self._get_validation_coverage()
            if coverage < self.health_thresholds['validation_coverage_min']:
                issues.append(f"Validation coverage {coverage:.2%} is below threshold")
                health_score -= 10
                recommendations.append("Run validation pipeline to improve coverage")
        
        # Determine status
        if health_score >= 80:
            status = "healthy"
        elif health_score >= 60:
            status = "degraded"
        else:
            status = "unhealthy"
        
        return HealthStatus(
            status=status,
            health_score=max(0.0, health_score),
            issues=issues,
            recommendations=recommendations,
            timestamp=datetime.utcnow()
        )
    
    def _get_average_trust_score(self) -> float:
        """Get average trust score."""
        if not self.session:
            return 0.5
        
        result = self.session.query(
            __import__('sqlalchemy', fromlist=['func']).func.avg(LearningExample.trust_score)
        ).scalar()
        
        return float(result) if result else 0.5
    
    def _get_average_consistency_score(self) -> float:
        """Get average consistency score."""
        if not self.session:
            return 0.5
        
        result = self.session.query(
            __import__('sqlalchemy', fromlist=['func']).func.avg(LearningExample.consistency_score)
        ).scalar()
        
        return float(result) if result else 0.5
    
    def _get_validation_coverage(self) -> float:
        """Get validation coverage (percentage of examples validated)."""
        if not self.session:
            return 0.0
        
        total = self.session.query(LearningExample).count()
        if total == 0:
            return 0.0
        
        validated = self.session.query(LearningExample).filter(
            LearningExample.times_validated > 0
        ).count()
        
        return validated / total if total > 0 else 0.0
    
    def get_alerts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent alerts."""
        return self.alerts[-limit:]
    
    def add_alert(
        self,
        severity: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Add an alert."""
        alert = {
            'timestamp': datetime.utcnow().isoformat(),
            'severity': severity,
            'message': message,
            'metadata': metadata or {}
        }
        self.alerts.append(alert)
        
        # Keep only last 100 alerts
        if len(self.alerts) > 100:
            self.alerts = self.alerts[-100:]


# Global instance
_layer1_monitor: Optional[Layer1Monitor] = None


def get_layer1_monitor(session: Optional[Session] = None) -> Layer1Monitor:
    """Get or create global Layer 1 monitor instance."""
    global _layer1_monitor
    if _layer1_monitor is None or session is not None:
        _layer1_monitor = Layer1Monitor(session=session)
    return _layer1_monitor
