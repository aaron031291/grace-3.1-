import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from collections import defaultdict
class EnterpriseLayer1Connectors:
    logger = logging.getLogger(__name__)
    """
    Enterprise-grade unified analytics for Layer 1 connectors.
    
    Features:
    - Unified connector analytics
    - Health monitoring
    - Performance tracking
    """
    
    def __init__(self):
        """Initialize enterprise connectors analytics."""
        # Connector tracking
        self._connector_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "total_actions": 0,
            "total_requests": 0,
            "total_events": 0,
            "successful_actions": 0,
            "failed_actions": 0,
            "avg_response_time_ms": 0.0,
            "last_activity": None
        })
        
        logger.info("[ENTERPRISE-LAYER1-CONNECTORS] Initialized")
    
    def track_connector_action(
        self,
        connector_name: str,
        action_type: str,
        success: bool,
        response_time_ms: float = 0.0
    ):
        """Track connector action."""
        stats = self._connector_stats[connector_name]
        stats["total_actions"] += 1
        
        if action_type == "request":
            stats["total_requests"] += 1
        elif action_type == "event":
            stats["total_events"] += 1
        
        if success:
            stats["successful_actions"] += 1
        else:
            stats["failed_actions"] += 1
        
        # Update average response time
        if response_time_ms > 0:
            total = stats["total_actions"]
            current_avg = stats["avg_response_time_ms"]
            stats["avg_response_time_ms"] = (
                (current_avg * (total - 1) + response_time_ms) / total
            )
        
        stats["last_activity"] = datetime.utcnow().isoformat()
    
    def get_connector_health(self, connector_name: str) -> Dict[str, Any]:
        """
        Get health for specific connector.
        
        Returns:
            Health metrics
        """
        stats = self._connector_stats[connector_name]
        
        total = stats["total_actions"]
        success_rate = (
            stats["successful_actions"] / total
            if total > 0 else 0.0
        )
        
        # Performance score
        avg_time = stats["avg_response_time_ms"]
        performance_score = max(0.0, 1.0 - (avg_time / 5000.0))  # Penalize if >5s
        
        # Activity score
        last_activity = stats["last_activity"]
        if last_activity:
            try:
                dt = datetime.fromisoformat(last_activity)
                hours_since = (datetime.utcnow() - dt).total_seconds() / 3600
                activity_score = max(0.0, 1.0 - (hours_since / 24.0))  # Penalize if >24h
            except:
                activity_score = 0.5
        else:
            activity_score = 0.0
        
        health_score = (
            success_rate * 0.4 +        # Success rate
            performance_score * 0.3 +   # Performance
            activity_score * 0.3        # Activity
        )
        
        return {
            "connector_name": connector_name,
            "total_actions": total,
            "success_rate": success_rate,
            "avg_response_time_ms": avg_time,
            "last_activity": last_activity,
            "health_score": health_score,
            "health_status": (
                "excellent" if health_score >= 0.8 else
                "good" if health_score >= 0.6 else
                "fair" if health_score >= 0.4 else
                "poor"
            )
        }
    
    def get_all_connectors_health(self) -> Dict[str, Any]:
        """
        Get health for all connectors.
        
        Returns:
            Health metrics for all connectors
        """
        connectors_health = {}
        
        for connector_name in self._connector_stats.keys():
            connectors_health[connector_name] = self.get_connector_health(connector_name)
        
        # Overall health
        if connectors_health:
            avg_health = sum(h["health_score"] for h in connectors_health.values()) / len(connectors_health)
        else:
            avg_health = 0.0
        
        return {
            "connectors": connectors_health,
            "overall_health_score": avg_health,
            "overall_health_status": (
                "excellent" if avg_health >= 0.8 else
                "good" if avg_health >= 0.6 else
                "fair" if avg_health >= 0.4 else
                "poor"
            ),
            "total_connectors": len(connectors_health),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_connectors_analytics(self) -> Dict[str, Any]:
        """
        Get comprehensive connectors analytics.
        
        Returns:
            Complete analytics dashboard
        """
        logger.info("[ENTERPRISE-LAYER1-CONNECTORS] Generating analytics...")
        
        health = self.get_all_connectors_health()
        
        # Top connectors by activity
        top_connectors = sorted(
            [
                {
                    "name": name,
                    "total_actions": stats["total_actions"],
                    "success_rate": (
                        stats["successful_actions"] / stats["total_actions"]
                        if stats["total_actions"] > 0 else 0.0
                    )
                }
                for name, stats in self._connector_stats.items()
            ],
            key=lambda x: x["total_actions"],
            reverse=True
        )[:10]
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "connector_statistics": {
                "total_connectors": len(self._connector_stats),
                "top_connectors": top_connectors,
                "total_actions": sum(s["total_actions"] for s in self._connector_stats.values()),
                "total_requests": sum(s["total_requests"] for s in self._connector_stats.values()),
                "total_events": sum(s["total_events"] for s in self._connector_stats.values())
            },
            "health": health
        }


def get_enterprise_layer1_connectors() -> EnterpriseLayer1Connectors:
    """Factory function to get enterprise Layer 1 connectors analytics."""
    return EnterpriseLayer1Connectors()
