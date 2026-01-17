import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
class PerformanceAlert:
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    """Performance alert."""
    severity: str  # "info", "warning", "critical"
    message: str
    timestamp: datetime
    metrics: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'severity': self.severity,
            'message': self.message,
            'timestamp': self.timestamp.isoformat(),
            'metrics': self.metrics
        }


class TimeSensePerformanceMonitor:
    """
    Monitors TimeSense performance and prediction accuracy.
    
    Detects:
    - Degrading prediction accuracy
    - Consistently slow operations
    - Stale calibration data
    - System performance issues
    """
    
    def __init__(self):
        self.alerts: List[PerformanceAlert] = []
        self.max_alerts = 100
        logger.info("[TIMESENSE-MONITOR] Initialized")
    
    def check_performance_health(self) -> Dict[str, Any]:
        """
        Check overall TimeSense performance health.
        
        Returns:
            Health status with issues and recommendations
        """
        if not TIMESENSE_AVAILABLE:
            return {
                'healthy': True,
                'status': 'not_available',
                'issues': [],
                'recommendations': []
            }
        
        try:
            engine = get_timesense_engine()
            status = engine.get_status()
            
            issues = []
            recommendations = []
            
            # Check prediction accuracy
            accuracy = status.get('prediction_accuracy', {})
            within_p95 = accuracy.get('within_p95_percent', 0)
            
            if within_p95 < 75 and accuracy.get('sample_count', 0) > 10:
                issues.append({
                    'type': 'prediction_accuracy',
                    'severity': 'warning',
                    'message': f"Only {within_p95:.1f}% of operations within p95 bounds",
                    'threshold': 75
                })
                recommendations.append(
                    "Consider recalibrating TimeSense profiles or checking for system performance issues"
                )
            
            # Check mean error
            mean_error = accuracy.get('mean_absolute_error', 0)
            if mean_error > 0.5:  # 50% average error
                issues.append({
                    'type': 'prediction_error',
                    'severity': 'critical',
                    'message': f"Operations {mean_error*100:.0f}% slower than predicted on average",
                    'threshold': 0.5
                })
                recommendations.append(
                    "Urgent: Recalibrate TimeSense immediately. System performance may have changed."
                )
            
            # Check engine status
            engine_status = status.get('engine', {})
            stable_profiles = engine_status.get('stable_profiles', 0)
            total_profiles = engine_status.get('total_profiles', 0)
            
            if total_profiles > 0:
                stability_ratio = stable_profiles / total_profiles
                if stability_ratio < 0.5:
                    issues.append({
                        'type': 'profile_stability',
                        'severity': 'warning',
                        'message': f"Only {stable_profiles}/{total_profiles} profiles are stable",
                        'threshold': 0.5
                    })
                    recommendations.append(
                        "Many profiles need recalibration. Consider running full calibration."
                    )
            
            # Check stale profiles
            stale_profiles = engine_status.get('stale_profiles', 0)
            if stale_profiles > 5:
                issues.append({
                    'type': 'stale_profiles',
                    'severity': 'info',
                    'message': f"{stale_profiles} profiles are stale",
                    'threshold': 5
                })
                recommendations.append(
                    "Consider periodic recalibration to maintain accuracy"
                )
            
            # Determine overall health
            critical_issues = [i for i in issues if i['severity'] == 'critical']
            warning_issues = [i for i in issues if i['severity'] == 'warning']
            
            if critical_issues:
                health_status = 'unhealthy'
            elif warning_issues:
                health_status = 'degraded'
            else:
                health_status = 'healthy'
            
            # Create alerts for critical/warning issues
            for issue in critical_issues + warning_issues:
                self._add_alert(
                    severity=issue['severity'],
                    message=issue['message'],
                    metrics=issue
                )
            
            return {
                'healthy': health_status == 'healthy',
                'status': health_status,
                'issues': issues,
                'recommendations': recommendations,
                'accuracy': {
                    'within_p95_percent': within_p95,
                    'mean_absolute_error': mean_error,
                    'sample_count': accuracy.get('sample_count', 0)
                },
                'engine_status': {
                    'stable_profiles': stable_profiles,
                    'total_profiles': total_profiles,
                    'stale_profiles': stale_profiles
                }
            }
        
        except Exception as e:
            logger.error(f"[TIMESENSE-MONITOR] Health check failed: {e}")
            return {
                'healthy': False,
                'status': 'error',
                'issues': [{
                    'type': 'monitor_error',
                    'severity': 'critical',
                    'message': f"Monitor error: {str(e)}"
                }],
                'recommendations': ["Check TimeSense engine status"]
            }
    
    def check_degradation(self, window_minutes: int = 60) -> Dict[str, Any]:
        """
        Check for performance degradation over a time window.
        
        Args:
            window_minutes: Time window to analyze
        
        Returns:
            Degradation analysis
        """
        if not TIMESENSE_AVAILABLE:
            return {
                'degraded': False,
                'trend': 'unknown'
            }
        
        # This would require historical data storage
        # For now, use current accuracy as indicator
        health = self.check_performance_health()
        accuracy = health.get('accuracy', {})
        
        within_p95 = accuracy.get('within_p95_percent', 100)
        
        # Consider degraded if < 80% within p95
        degraded = within_p95 < 80
        
        return {
            'degraded': degraded,
            'trend': 'improving' if within_p95 > 90 else 'stable' if within_p95 > 75 else 'degrading',
            'current_accuracy': within_p95,
            'threshold': 80
        }
    
    def check_and_trigger_calibration(self) -> Dict[str, Any]:
        """
        Auto-trigger recalibration if prediction accuracy degrades.
        
        Returns:
            Calibration trigger status
        """
        if not TIMESENSE_AVAILABLE:
            return {
                'calibration_triggered': False,
                'reason': 'TimeSense not available'
            }
        
        try:
            health = self.check_performance_health()
            
            should_recalibrate = False
            reasons = []
            
            # Check prediction accuracy
            accuracy = health.get('accuracy', {})
            within_p95 = accuracy.get('within_p95_percent', 100)
            mean_error = accuracy.get('mean_absolute_error', 0)
            
            if within_p95 < 75 and accuracy.get('sample_count', 0) > 10:
                should_recalibrate = True
                reasons.append(f"Low accuracy: {within_p95:.1f}% within p95 (threshold: 75%)")
            
            if mean_error > 0.5:
                should_recalibrate = True
                reasons.append(f"High error: {mean_error*100:.0f}% average error (threshold: 50%)")
            
            # Check stale profiles
            engine_status = health.get('engine_status', {})
            stale_profiles = engine_status.get('stale_profiles', 0)
            
            if stale_profiles > 5:
                should_recalibrate = True
                reasons.append(f"Stale profiles: {stale_profiles} profiles need recalibration")
            
            if should_recalibrate:
                logger.warning(
                    f"[TIMESENSE-MONITOR] Auto-triggering recalibration: {', '.join(reasons)}"
                )
                
                # Trigger recalibration
                engine = get_timesense_engine()
                
                # Trigger quick calibration (faster, less thorough)
                # Full calibration can be triggered manually if needed
                engine.initialize_sync(quick_calibration=True)
                
                # Log calibration trigger
                self._add_alert(
                    severity='warning',
                    message=f"Auto-triggered calibration: {', '.join(reasons)}",
                    metrics={
                        'within_p95_percent': within_p95,
                        'mean_error': mean_error,
                        'stale_profiles': stale_profiles
                    }
                )
                
                return {
                    'calibration_triggered': True,
                    'reasons': reasons,
                    'calibration_type': 'quick',
                    'health_before': health
                }
            
            return {
                'calibration_triggered': False,
                'reason': 'Accuracy within acceptable range',
                'within_p95_percent': within_p95,
                'mean_error': mean_error
            }
        
        except Exception as e:
            logger.error(f"[TIMESENSE-MONITOR] Calibration check failed: {e}")
            return {
                'calibration_triggered': False,
                'reason': f'Error: {str(e)}'
            }
    
    def get_alerts(self, severity: Optional[str] = None, limit: int = 10) -> List[PerformanceAlert]:
        """
        Get performance alerts.
        
        Args:
            severity: Filter by severity (info/warning/critical)
            limit: Maximum number of alerts to return
        
        Returns:
            List of alerts
        """
        alerts = self.alerts
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        # Return most recent
        return alerts[-limit:]
    
    def _add_alert(self, severity: str, message: str, metrics: Dict[str, Any]):
        """Add a performance alert."""
        alert = PerformanceAlert(
            severity=severity,
            message=message,
            timestamp=datetime.utcnow(),
            metrics=metrics
        )
        
        self.alerts.append(alert)
        
        # Keep only recent alerts
        if len(self.alerts) > self.max_alerts:
            self.alerts = self.alerts[-self.max_alerts:]
        
        # Log based on severity
        if severity == 'critical':
            logger.error(f"[TIMESENSE-MONITOR] {message}")
        elif severity == 'warning':
            logger.warning(f"[TIMESENSE-MONITOR] {message}")
        else:
            logger.info(f"[TIMESENSE-MONITOR] {message}")


# Global monitor instance
_performance_monitor: Optional[TimeSensePerformanceMonitor] = None


def get_performance_monitor() -> TimeSensePerformanceMonitor:
    """Get or create global performance monitor."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = TimeSensePerformanceMonitor()
    return _performance_monitor
