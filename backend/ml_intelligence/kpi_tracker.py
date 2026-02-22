"""
KPI Tracking System - Component Performance Metrics

Tracks Key Performance Indicators (KPIs) for all components, aggregating
performance data into operational health signals that feed into trust scores.

Key Features:
- Action frequency tracking (every action increments KPI)
- Component-level KPI aggregation
- KPI-to-trust score conversion
- System-wide trust aggregation
- Time-windowed metrics (recent vs. historical)

Classes:
- `KPI`
- `ComponentKPIs`
- `KPITracker`

Key Methods:
- `increment()`
- `get_kpi()`
- `increment_kpi()`
- `get_trust_score()`
- `get_recent_kpi()`
- `to_dict()`
- `register_component()`
- `increment_kpi()`
- `get_component_kpis()`
- `get_component_trust_score()`
- `get_system_trust_score()`
- `get_health_signal()`
- `get_system_health()`
- `to_dict()`
- `get_kpi_tracker()`
- `reset_kpi_tracker()`

Connects To:
Self-contained
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


@dataclass
class KPI:
    """Key Performance Indicator for a component."""
    component_name: str
    metric_name: str
    value: float
    count: int = 1
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def increment(self, value: float = 1.0, metadata: Optional[Dict[str, Any]] = None):
        """Increment KPI value."""
        self.count += 1
        self.value += value
        self.timestamp = datetime.now()
        if metadata:
            self.metadata.update(metadata)


@dataclass
class ComponentKPIs:
    """All KPIs for a single component."""
    component_name: str
    kpis: Dict[str, KPI] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def get_kpi(self, metric_name: str) -> KPI:
        """Get or create KPI for metric."""
        if metric_name not in self.kpis:
            self.kpis[metric_name] = KPI(
                component_name=self.component_name,
                metric_name=metric_name,
                value=0.0,
                count=0,
            )
        return self.kpis[metric_name]
    
    def increment_kpi(self, metric_name: str, value: float = 1.0, metadata: Optional[Dict[str, Any]] = None):
        """Increment a KPI."""
        kpi = self.get_kpi(metric_name)
        kpi.increment(value, metadata)
        self.updated_at = datetime.now()
    
    def get_trust_score(self, metric_weights: Optional[Dict[str, float]] = None) -> float:
        """
        Convert KPIs to trust score.
        
        Higher frequency and consistency = higher trust.
        
        Args:
            metric_weights: Optional weights for different metrics
            
        Returns:
            Trust score (0-1)
        """
        if not self.kpis:
            return 0.5  # Default neutral trust
        
        if metric_weights is None:
            # Default: equal weights
            metric_weights = {name: 1.0 for name in self.kpis.keys()}
        
        total_weight = sum(metric_weights.values())
        if total_weight == 0:
            return 0.5
        
        # Calculate weighted average
        weighted_sum = 0.0
        for metric_name, kpi in self.kpis.items():
            weight = metric_weights.get(metric_name, 1.0)
            
            # Normalize value (assuming higher is better)
            # Use count as proxy for consistency
            # Normalize: count / (count + 1) approaches 1.0
            normalized = min(kpi.count / (kpi.count + 10), 1.0)  # Smooth normalization
            
            weighted_sum += weight * normalized
        
        trust_score = weighted_sum / total_weight
        
        # Ensure bounds
        return max(0.0, min(1.0, trust_score))
    
    def get_recent_kpi(self, metric_name: str, time_window: timedelta = timedelta(hours=24)) -> Optional[KPI]:
        """Get KPI if updated within time window."""
        if metric_name not in self.kpis:
            return None
        
        kpi = self.kpis[metric_name]
        if datetime.now() - kpi.timestamp > time_window:
            return None
        
        return kpi
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "component_name": self.component_name,
            "kpis": {
                name: {
                    "value": kpi.value,
                    "count": kpi.count,
                    "timestamp": kpi.timestamp.isoformat(),
                    "metadata": kpi.metadata,
                }
                for name, kpi in self.kpis.items()
            },
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "trust_score": self.get_trust_score(),
        }


class KPITracker:
    """
    Tracks KPIs for all components.
    
    Translates component performance metrics into trust scores.
    """
    
    def __init__(self):
        """Initialize KPI tracker."""
        self.components: Dict[str, ComponentKPIs] = {}
        self.metric_weights: Dict[str, Dict[str, float]] = {}  # Component -> Metric -> Weight
        logger.info("[KPI-TRACKER] Initialized")
    
    def register_component(self, component_name: str, metric_weights: Optional[Dict[str, float]] = None):
        """
        Register a component for KPI tracking.
        
        Args:
            component_name: Name of component
            metric_weights: Optional weights for metrics
        """
        if component_name not in self.components:
            self.components[component_name] = ComponentKPIs(component_name=component_name)
            logger.debug(f"[KPI-TRACKER] Registered component: {component_name}")
        
        if metric_weights:
            self.metric_weights[component_name] = metric_weights
    
    def increment_kpi(
        self,
        component_name: str,
        metric_name: str,
        value: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Increment a KPI for a component.
        
        Every time a component does its job, this ticks up.
        
        Args:
            component_name: Name of component
            metric_name: Name of metric (e.g., "requests_handled", "successes")
            value: Value to increment by
            metadata: Optional metadata
        """
        if component_name not in self.components:
            self.register_component(component_name)
        
        self.components[component_name].increment_kpi(metric_name, value, metadata)
        logger.debug(f"[KPI-TRACKER] {component_name}.{metric_name} += {value} (total: {self.components[component_name].get_kpi(metric_name).count})")
    
    def get_component_kpis(self, component_name: str) -> Optional[ComponentKPIs]:
        """Get KPIs for a component."""
        return self.components.get(component_name)
    
    def get_component_trust_score(self, component_name: str) -> float:
        """
        Get trust score for a component based on KPIs.
        
        Args:
            component_name: Name of component
            
        Returns:
            Trust score (0-1)
        """
        if component_name not in self.components:
            return 0.5  # Default neutral trust
        
        component = self.components[component_name]
        weights = self.metric_weights.get(component_name)
        return component.get_trust_score(weights)
    
    def get_system_trust_score(self, component_weights: Optional[Dict[str, float]] = None) -> float:
        """
        Calculate system-wide trust score from all component trust scores.
        
        All component-level trust scores roll up into system-wide trust.
        
        Args:
            component_weights: Optional weights for components
            
        Returns:
            System-wide trust score (0-1)
        """
        if not self.components:
            return 0.5  # Default neutral trust
        
        if component_weights is None:
            # Default: equal weights
            component_weights = {name: 1.0 for name in self.components.keys()}
        
        total_weight = sum(component_weights.values())
        if total_weight == 0:
            return 0.5
        
        # Calculate weighted average of component trust scores
        weighted_sum = 0.0
        for component_name, component in self.components.items():
            weight = component_weights.get(component_name, 1.0)
            component_trust = component.get_trust_score(self.metric_weights.get(component_name))
            weighted_sum += weight * component_trust
        
        system_trust = weighted_sum / total_weight
        
        # Ensure bounds
        return max(0.0, min(1.0, system_trust))
    
    def get_health_signal(self, component_name: str) -> Dict[str, Any]:
        """
        Get operational health signal for a component.
        
        Aggregates KPIs into health signal.
        
        Args:
            component_name: Name of component
            
        Returns:
            Health signal dictionary
        """
        component = self.get_component_kpis(component_name)
        if not component:
            return {
                "component_name": component_name,
                "status": "unknown",
                "trust_score": 0.5,
                "kpi_count": 0,
            }
        
        trust_score = component.get_trust_score(self.metric_weights.get(component_name))
        
        # Determine status based on trust score
        if trust_score >= 0.8:
            status = "excellent"
        elif trust_score >= 0.6:
            status = "good"
        elif trust_score >= 0.4:
            status = "fair"
        else:
            status = "poor"
        
        return {
            "component_name": component_name,
            "status": status,
            "trust_score": trust_score,
            "kpi_count": len(component.kpis),
            "total_actions": sum(kpi.count for kpi in component.kpis.values()),
            "updated_at": component.updated_at.isoformat(),
        }
    
    def get_system_health(self) -> Dict[str, Any]:
        """
        Get system-wide operational health.
        
        Returns:
            System health dictionary
        """
        system_trust = self.get_system_trust_score()
        
        component_health = {}
        for component_name in self.components.keys():
            component_health[component_name] = self.get_health_signal(component_name)
        
        # Determine overall status
        if system_trust >= 0.8:
            status = "excellent"
        elif system_trust >= 0.6:
            status = "good"
        elif system_trust >= 0.4:
            status = "fair"
        else:
            status = "poor"
        
        return {
            "system_trust_score": system_trust,
            "status": status,
            "component_count": len(self.components),
            "components": component_health,
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert tracker to dictionary."""
        return {
            "components": {
                name: component.to_dict()
                for name, component in self.components.items()
            },
            "system_trust_score": self.get_system_trust_score(),
            "system_health": self.get_system_health(),
        }


# Singleton instance
_kpi_tracker: Optional[KPITracker] = None


def get_kpi_tracker() -> KPITracker:
    """Get global KPI tracker instance."""
    global _kpi_tracker
    if _kpi_tracker is None:
        _kpi_tracker = KPITracker()
    return _kpi_tracker


def reset_kpi_tracker():
    """Reset global KPI tracker (for testing)."""
    global _kpi_tracker
    _kpi_tracker = None
