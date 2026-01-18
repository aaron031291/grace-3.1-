import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set
from collections import defaultdict, deque
from dataclasses import asdict
import json
import gzip
from pathlib import Path
from layer1.message_bus import Layer1MessageBus, Message, MessageType, ComponentType
logger = logging.getLogger(__name__)

class EnterpriseMessageBus:
    """
    Enterprise-grade Layer 1 Message Bus.
    
    Features:
    - Message analytics
    - Health monitoring
    - Lifecycle management
    - Message clustering
    - Performance optimization
    """
    
    def __init__(
        self,
        message_bus: Layer1MessageBus,
        archive_dir: Optional[Path] = None,
        retention_days: int = 30
    ):
        """Initialize enterprise message bus."""
        self.message_bus = message_bus
        self.retention_days = retention_days
        
        # Archive directory
        if archive_dir:
            self.archive_dir = archive_dir
        else:
            self.archive_dir = Path("backend/archived_messages")
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        
        # Analytics
        self._message_stats = {
            "total_messages": 0,
            "by_type": defaultdict(int),
            "by_component": defaultdict(int),
            "by_topic": defaultdict(int),
            "avg_priority": 0.0,
            "high_priority_count": 0,
            "autonomous_actions": 0
        }
        
        # Performance tracking
        self._performance_stats = {
            "avg_processing_time_ms": 0.0,
            "slow_messages": [],
            "cache_hits": 0,
            "cache_misses": 0
        }
        
        logger.info(
            f"[ENTERPRISE-MESSAGE-BUS] Initialized: "
            f"retention={retention_days}d"
        )
    
    def track_message(self, message: Message, processing_time_ms: float = 0.0):
        """Track message for analytics."""
        self._message_stats["total_messages"] += 1
        self._message_stats["by_type"][message.message_type.value] += 1
        self._message_stats["by_component"][message.from_component.value] += 1
        self._message_stats["by_topic"][message.topic] += 1
        
        # Update average priority
        total = self._message_stats["total_messages"]
        current_avg = self._message_stats["avg_priority"]
        self._message_stats["avg_priority"] = (
            (current_avg * (total - 1) + message.priority) / total
        )
        
        if message.priority >= 8:
            self._message_stats["high_priority_count"] += 1
        
        # Track performance
        if processing_time_ms > 0:
            total_processed = sum(1 for _ in self._performance_stats["slow_messages"]) + 1
            current_avg = self._performance_stats["avg_processing_time_ms"]
            self._performance_stats["avg_processing_time_ms"] = (
                (current_avg * (total_processed - 1) + processing_time_ms) / total_processed
            )
            
            # Track slow messages (>100ms)
            if processing_time_ms > 100:
                self._performance_stats["slow_messages"].append({
                    "message_id": message.message_id,
                    "topic": message.topic,
                    "processing_time_ms": processing_time_ms,
                    "timestamp": message.timestamp.isoformat()
                })
                # Keep only last 100 slow messages
                if len(self._performance_stats["slow_messages"]) > 100:
                    self._performance_stats["slow_messages"].pop(0)
    
    def cluster_messages(self) -> Dict[str, Any]:
        """
        Cluster messages by topic, component, and priority.
        
        Returns:
            Cluster statistics
        """
        logger.info("[ENTERPRISE-MESSAGE-BUS] Clustering messages...")
        
        history = self.message_bus._message_history
        
        # Cluster by topic
        topic_clusters = defaultdict(int)
        component_clusters = defaultdict(int)
        priority_clusters = defaultdict(int)
        temporal_clusters = defaultdict(int)
        
        for msg in history:
            topic_clusters[msg.topic] += 1
            component_clusters[msg.from_component.value] += 1
            
            # Priority clusters
            if msg.priority >= 8:
                priority_clusters["high"] += 1
            elif msg.priority >= 5:
                priority_clusters["medium"] += 1
            else:
                priority_clusters["low"] += 1
            
            # Temporal clusters (by hour)
            hour_key = msg.timestamp.strftime("%Y-%m-%d-%H")
            temporal_clusters[hour_key] += 1
        
        clusters = {
            "by_topic": dict(sorted(topic_clusters.items(), key=lambda x: x[1], reverse=True)[:20]),
            "by_component": dict(component_clusters),
            "by_priority": dict(priority_clusters),
            "by_temporal": dict(sorted(temporal_clusters.items(), key=lambda x: x[0], reverse=True)[:24]),
            "total_clusters": (
                len(topic_clusters) + len(component_clusters) + len(priority_clusters)
            )
        }
        
        logger.info(
            f"[ENTERPRISE-MESSAGE-BUS] Created clusters: "
            f"{len(topic_clusters)} topic, "
            f"{len(component_clusters)} component, "
            f"{len(priority_clusters)} priority"
        )
        
        return clusters
    
    def get_message_bus_health(self) -> Dict[str, Any]:
        """
        Get message bus health metrics.
        
        Returns:
            Health metrics
        """
        logger.info("[ENTERPRISE-MESSAGE-BUS] Calculating health...")
        
        stats = self.message_bus.get_stats()
        history = self.message_bus._message_history
        
        # Recent activity
        recent_messages = [
            msg for msg in history
            if (datetime.utcnow() - msg.timestamp).total_seconds() < 3600
        ]
        
        # Component health
        registered_components = len(self.message_bus._registered_components)
        active_components = len(set(msg.from_component for msg in recent_messages))
        
        # Performance health
        avg_processing = self._performance_stats["avg_processing_time_ms"]
        slow_message_ratio = (
            len(self._performance_stats["slow_messages"]) / len(history)
            if history else 0.0
        )
        
        # Health score
        activity_ratio = len(recent_messages) / len(history) if history else 0.0
        component_ratio = active_components / registered_components if registered_components > 0 else 0.0
        performance_score = max(0.0, 1.0 - (avg_processing / 1000.0))  # Penalize if >1s
        
        health_score = (
            activity_ratio * 0.4 +        # Recent activity
            component_ratio * 0.3 +        # Component engagement
            performance_score * 0.3        # Performance
        )
        
        health = {
            "total_messages": len(history),
            "recent_1h": len(recent_messages),
            "registered_components": registered_components,
            "active_components": active_components,
            "autonomous_actions": stats.get("autonomous_actions_triggered", 0),
            "avg_processing_time_ms": avg_processing,
            "slow_message_ratio": slow_message_ratio,
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
            f"[ENTERPRISE-MESSAGE-BUS] Health: score={health_score:.2f} "
            f"({health['health_status']})"
        )
        
        return health
    
    def archive_old_messages(self) -> Dict[str, Any]:
        """
        Archive old messages beyond retention threshold.
        
        Returns:
            Archive statistics
        """
        logger.info(f"[ENTERPRISE-MESSAGE-BUS] Archiving messages older than {self.retention_days} days...")
        
        cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)
        history = self.message_bus._message_history
        
        # Separate old and new messages
        old_messages = [msg for msg in history if msg.timestamp < cutoff_date]
        new_messages = [msg for msg in history if msg.timestamp >= cutoff_date]
        
        archived_count = len(old_messages)
        
        if old_messages:
            # Group by day
            by_day = {}
            for msg in old_messages:
                day_key = msg.timestamp.strftime("%Y-%m-%d")
                if day_key not in by_day:
                    by_day[day_key] = []
                by_day[day_key].append(asdict(msg))
            
            # Save compressed archives
            for day, messages in by_day.items():
                archive_file = self.archive_dir / f"messages_{day}.json.gz"
                
                with gzip.open(archive_file, 'wt', encoding='utf-8') as f:
                    json.dump({
                        "archived_at": datetime.utcnow().isoformat(),
                        "day": day,
                        "count": len(messages),
                        "messages": messages
                    }, f, indent=2, default=str)
        
        # Update message bus history
        self.message_bus._message_history = new_messages
        
        logger.info(f"[ENTERPRISE-MESSAGE-BUS] Archived {archived_count} messages")
        
        return {
            "archived_count": archived_count,
            "archive_files_created": len(by_day) if old_messages else 0,
            "remaining_messages": len(new_messages)
        }
    
    def get_message_bus_analytics(self) -> Dict[str, Any]:
        """
        Get comprehensive message bus analytics.
        
        Returns:
            Complete analytics dashboard
        """
        logger.info("[ENTERPRISE-MESSAGE-BUS] Generating analytics...")
        
        clusters = self.cluster_messages()
        health = self.get_message_bus_health()
        stats = self.message_bus.get_stats()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "message_statistics": {
                "total_messages": self._message_stats["total_messages"],
                "by_type": dict(self._message_stats["by_type"]),
                "by_component": dict(self._message_stats["by_component"]),
                "by_topic": dict(sorted(
                    self._message_stats["by_topic"].items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:20]),
                "avg_priority": self._message_stats["avg_priority"],
                "high_priority_count": self._message_stats["high_priority_count"]
            },
            "performance_statistics": {
                "avg_processing_time_ms": self._performance_stats["avg_processing_time_ms"],
                "slow_messages_count": len(self._performance_stats["slow_messages"]),
                "cache_hit_rate": (
                    self._performance_stats["cache_hits"] /
                    (self._performance_stats["cache_hits"] + self._performance_stats["cache_misses"])
                    if (self._performance_stats["cache_hits"] + self._performance_stats["cache_misses"]) > 0 else 0.0
                )
            },
            "clusters": clusters,
            "health": health,
            "bus_statistics": stats
        }


def get_enterprise_message_bus(
    message_bus: Layer1MessageBus,
    archive_dir: Optional[Path] = None,
    retention_days: int = 30
) -> EnterpriseMessageBus:
    """Factory function to get enterprise message bus."""
    return EnterpriseMessageBus(
        message_bus=message_bus,
        archive_dir=archive_dir,
        retention_days=retention_days
    )
