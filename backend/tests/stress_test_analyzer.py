import json
import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
class StressTestAnalyzer:
    logger = logging.getLogger(__name__)
    """Analyzes stress test results and identifies issues."""
    
    def __init__(self):
        self.test_log_path = TEST_LOG_PATH
    
    def analyze_test_results(self) -> Dict[str, Any]:
        """Analyze all test results and identify issues."""
        if not self.test_log_path.exists():
            logger.warning("No test log file found")
            return {
                "critical_issues": [],
                "warnings": [],
                "new_issue_types": [],
                "performance_issues": [],
                "data_integrity_issues": [],
                "resource_issues": []
            }
        
        with open(self.test_log_path, 'r') as f:
            all_results = json.load(f)
        
        # Filter to recent results (last 24 hours)
        recent_results = [
            r for r in all_results
            if self._is_recent(r.get("timestamp", ""))
        ]
        
        # Analyze
        critical_issues = []
        warnings = []
        performance_issues = []
        data_integrity_issues = []
        resource_issues = []
        new_issue_types = []
        
        # Known issue patterns
        known_patterns = {
            "memory_health_low": "Memory health score below threshold",
            "performance_degradation": "Performance metrics below expected",
            "data_inconsistency": "Data integrity checks failed",
            "resource_exhaustion": "Resource usage exceeds limits",
            "concurrent_access_failure": "Concurrent operations failing",
            "lifecycle_management_slow": "Lifecycle operations taking too long"
        }
        
        for result in recent_results:
            # Check for errors
            if result.get("errors"):
                for error in result["errors"]:
                    issue = {
                        "test_name": result.get("test_name", "Unknown"),
                        "perspective": result.get("perspective", "Unknown"),
                        "error": error,
                        "timestamp": result.get("timestamp"),
                        "metrics": result.get("metrics", {})
                    }
                    
                    # Classify issue
                    if "health score too low" in error.lower():
                        critical_issues.append(issue)
                    elif "performance" in error.lower() or "duration" in error.lower():
                        performance_issues.append(issue)
                    elif "integrity" in error.lower() or "consistency" in error.lower():
                        data_integrity_issues.append(issue)
                    elif "memory" in error.lower() or "cpu" in error.lower() or "storage" in error.lower():
                        resource_issues.append(issue)
                    else:
                        critical_issues.append(issue)
                    
                    # Check if this is a new issue type
                    issue_type = self._classify_issue_type(error)
                    if issue_type not in known_patterns:
                        new_issue_types.append({
                            "issue_type": issue_type,
                            "error": error,
                            "test_name": result.get("test_name"),
                            "first_seen": result.get("timestamp")
                        })
            
            # Check for warnings
            if result.get("warnings"):
                for warning in result["warnings"]:
                    warnings.append({
                        "test_name": result.get("test_name", "Unknown"),
                        "perspective": result.get("perspective", "Unknown"),
                        "warning": warning,
                        "timestamp": result.get("timestamp"),
                        "metrics": result.get("metrics", {})
                    })
            
            # Check metrics for issues
            metrics = result.get("metrics", {})
            
            # Performance issues
            if "duration_ms" in metrics and metrics["duration_ms"] > 10000:
                performance_issues.append({
                    "test_name": result.get("test_name"),
                    "issue": f"Test took too long: {metrics['duration_ms']:.1f}ms",
                    "timestamp": result.get("timestamp")
                })
            
            # Resource issues
            if "memory_mb" in metrics and metrics["memory_mb"] > 2000:
                resource_issues.append({
                    "test_name": result.get("test_name"),
                    "issue": f"High memory usage: {metrics['memory_mb']:.1f} MB",
                    "timestamp": result.get("timestamp")
                })
            
            if "cpu_percent" in metrics and metrics["cpu_percent"] > 80:
                resource_issues.append({
                    "test_name": result.get("test_name"),
                    "issue": f"High CPU usage: {metrics['cpu_percent']:.1f}%",
                    "timestamp": result.get("timestamp")
                })
        
        return {
            "critical_issues": critical_issues,
            "warnings": warnings,
            "performance_issues": performance_issues,
            "data_integrity_issues": data_integrity_issues,
            "resource_issues": resource_issues,
            "new_issue_types": new_issue_types,
            "total_issues": len(critical_issues) + len(performance_issues) + len(data_integrity_issues) + len(resource_issues),
            "analysis_timestamp": datetime.utcnow().isoformat()
        }
    
    def _is_recent(self, timestamp_str: str, hours: int = 24) -> bool:
        """Check if timestamp is within last N hours."""
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            now = datetime.utcnow()
            diff = (now - timestamp.replace(tzinfo=None)).total_seconds() / 3600
            return diff <= hours
        except:
            return True  # If we can't parse, assume recent
    
    def _classify_issue_type(self, error: str) -> str:
        """Classify issue type from error message."""
        error_lower = error.lower()
        
        if "health" in error_lower:
            return "health_degradation"
        elif "performance" in error_lower or "slow" in error_lower or "duration" in error_lower:
            return "performance_degradation"
        elif "memory" in error_lower:
            return "memory_issue"
        elif "cpu" in error_lower:
            return "cpu_issue"
        elif "storage" in error_lower or "disk" in error_lower:
            return "storage_issue"
        elif "integrity" in error_lower or "consistency" in error_lower:
            return "data_integrity"
        elif "concurrent" in error_lower or "thread" in error_lower:
            return "concurrency_issue"
        elif "connection" in error_lower or "database" in error_lower:
            return "connection_issue"
        elif "timeout" in error_lower:
            return "timeout_issue"
        else:
            return "unknown_issue"


if __name__ == "__main__":
    analyzer = StressTestAnalyzer()
    analysis = analyzer.analyze_test_results()
    print(json.dumps(analysis, indent=2, default=str))
