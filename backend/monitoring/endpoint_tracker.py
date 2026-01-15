"""
API Endpoint Health Tracker

Tracks health metrics for all API endpoints:
- Response times
- Error rates
- Request counts
- Endpoint availability
"""

import time
import logging
from typing import Dict, Any, Optional, List
from collections import defaultdict, deque
from datetime import datetime, UTC
from threading import Lock

logger = logging.getLogger(__name__)


class EndpointHealthTracker:
    """Track health of all API endpoints."""
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.endpoint_metrics: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "response_times": deque(maxlen=max_history),
            "error_codes": defaultdict(int),
            "last_request_time": None,
            "last_error_time": None,
            "avg_response_time_ms": 0.0,
            "max_response_time_ms": 0.0,
            "min_response_time_ms": float('inf'),
            "error_rate": 0.0
        })
        self.lock = Lock()
    
    def track_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        duration_ms: float
    ):
        """Track an API request."""
        key = f"{method} {endpoint}"
        
        with self.lock:
            metrics = self.endpoint_metrics[key]
            metrics["total_requests"] += 1
            metrics["last_request_time"] = datetime.now(UTC).isoformat()
            
            # Track response time
            metrics["response_times"].append(duration_ms)
            metrics["avg_response_time_ms"] = sum(metrics["response_times"]) / len(metrics["response_times"])
            metrics["max_response_time_ms"] = max(metrics["max_response_time_ms"], duration_ms)
            metrics["min_response_time_ms"] = min(metrics["min_response_time_ms"], duration_ms)
            
            # Track success/failure
            if status_code < 400:
                metrics["successful_requests"] += 1
            else:
                metrics["failed_requests"] += 1
                metrics["error_codes"][status_code] += 1
                metrics["last_error_time"] = datetime.now(UTC).isoformat()
                metrics["error_rate"] = metrics["failed_requests"] / metrics["total_requests"]
    
    def get_unhealthy_endpoints(self, threshold_error_rate: float = 0.1, threshold_response_time_ms: float = 5000) -> List[Dict[str, Any]]:
        """Get endpoints with health issues."""
        unhealthy = []
        
        with self.lock:
            for endpoint, metrics in self.endpoint_metrics.items():
                issues = []
                
                # Check error rate
                if metrics["error_rate"] > threshold_error_rate:
                    issues.append({
                        "type": "high_error_rate",
                        "severity": "high" if metrics["error_rate"] > 0.2 else "medium",
                        "error_rate": metrics["error_rate"],
                        "failed_requests": metrics["failed_requests"],
                        "total_requests": metrics["total_requests"]
                    })
                
                # Check response time
                if metrics["avg_response_time_ms"] > threshold_response_time_ms:
                    issues.append({
                        "type": "slow_response",
                        "severity": "high" if metrics["avg_response_time_ms"] > 10000 else "medium",
                        "avg_time_ms": metrics["avg_response_time_ms"],
                        "max_time_ms": metrics["max_response_time_ms"]
                    })
                
                # Check if endpoint hasn't been called recently (stale)
                if metrics["last_request_time"]:
                    last_request = datetime.fromisoformat(metrics["last_request_time"].replace('Z', '+00:00'))
                    hours_since_last = (datetime.now(UTC) - last_request).total_seconds() / 3600
                    if hours_since_last > 24 and metrics["total_requests"] > 0:
                        issues.append({
                            "type": "stale_endpoint",
                            "severity": "low",
                            "hours_since_last": hours_since_last
                        })
                
                if issues:
                    unhealthy.append({
                        "endpoint": endpoint,
                        "issues": issues,
                        "metrics": {
                            "total_requests": metrics["total_requests"],
                            "error_rate": metrics["error_rate"],
                            "avg_response_time_ms": metrics["avg_response_time_ms"],
                            "last_request_time": metrics["last_request_time"]
                        }
                    })
        
        return unhealthy
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all endpoint metrics."""
        with self.lock:
            return dict(self.endpoint_metrics)
    
    def get_endpoint_health(self, endpoint: str, method: str = "GET") -> Dict[str, Any]:
        """Get health for a specific endpoint."""
        key = f"{method} {endpoint}"
        
        with self.lock:
            if key not in self.endpoint_metrics:
                return {"status": "unknown", "message": "No requests tracked"}
            
            metrics = self.endpoint_metrics[key]
            
            # Determine health status
            if metrics["error_rate"] > 0.2 or metrics["avg_response_time_ms"] > 10000:
                status = "unhealthy"
            elif metrics["error_rate"] > 0.1 or metrics["avg_response_time_ms"] > 5000:
                status = "degraded"
            else:
                status = "healthy"
            
            return {
                "status": status,
                "metrics": dict(metrics)
            }


# Global tracker instance
_endpoint_tracker: Optional[EndpointHealthTracker] = None


def get_endpoint_tracker() -> EndpointHealthTracker:
    """Get or create global endpoint tracker."""
    global _endpoint_tracker
    if _endpoint_tracker is None:
        _endpoint_tracker = EndpointHealthTracker()
    return _endpoint_tracker
