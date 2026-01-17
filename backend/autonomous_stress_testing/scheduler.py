import sys
import os
import json
import logging
import time
import asyncio
import threading
from pathlib import Path
from datetime import datetime, UTC
from typing import Dict, List, Any, Optional
import traceback
from autonomous_stress_testing.stress_test_suite import GraceStressTestSuite, run_stress_test_suite
class StressTestScheduler:
    logger = logging.getLogger(__name__)
    """Scheduler for autonomous stress testing."""
    
    def __init__(
        self,
        interval_minutes: int = 10,
        base_url: str = "http://localhost:8000",
        enable_genesis_logging: bool = True,
        enable_diagnostic_alerts: bool = True
    ):
        self.interval_minutes = interval_minutes
        self.interval_seconds = interval_minutes * 60
        self.base_url = base_url
        self.enable_genesis_logging = enable_genesis_logging
        self.enable_diagnostic_alerts = enable_diagnostic_alerts
        
        self.running = False
        self.thread = None
        self.test_count = 0
        self.results_history: List[Dict[str, Any]] = []
        
        logger.info(f"[STRESS-SCHEDULER] Initialized with {interval_minutes} minute interval")
    
    def start(self):
        """Start the scheduler in a background thread."""
        if self.running:
            logger.warning("[STRESS-SCHEDULER] Already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        
        logger.info(f"[STRESS-SCHEDULER] Started - running every {self.interval_minutes} minutes")
    
    def stop(self):
        """Stop the scheduler."""
        if not self.running:
            return
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        
        logger.info("[STRESS-SCHEDULER] Stopped")
    
    def _run_loop(self):
        """Main scheduler loop."""
        while self.running:
            try:
                # Run stress tests
                logger.info(f"[STRESS-SCHEDULER] Running stress test suite #{self.test_count + 1}")
                results = asyncio.run(run_stress_test_suite(base_url=self.base_url))
                
                self.test_count += 1
                results["test_run_number"] = self.test_count
                self.results_history.append(results)
                
                # Log with Genesis Keys
                if self.enable_genesis_logging:
                    self._log_with_genesis(results)
                
                # Alert diagnostic engine
                if self.enable_diagnostic_alerts:
                    self._alert_diagnostic_engine(results)
                
                # Wait for next interval
                logger.info(f"[STRESS-SCHEDULER] Test #{self.test_count} complete. Next test in {self.interval_minutes} minutes")
                
                # Sleep in small increments to allow quick shutdown
                for _ in range(self.interval_seconds):
                    if not self.running:
                        break
                    time.sleep(1)
                
            except Exception as e:
                logger.error(f"[STRESS-SCHEDULER] Error in scheduler loop: {e}")
                logger.error(traceback.format_exc())
                # Continue running even if one test fails
                time.sleep(60)  # Wait 1 minute before retrying
    
    def _log_with_genesis(self, results: Dict[str, Any]):
        """Log stress test results with Genesis Keys."""
        try:
            from genesis.genesis_key_service import get_genesis_service
            from database.session import initialize_session_factory, SessionLocal
            from database.connection import DatabaseConnection
            from database.config import DatabaseConfig, DatabaseType
            from models.genesis_key_models import GenesisKeyType
            
            # Initialize database if needed
            try:
                session_factory = initialize_session_factory()
            except:
                db_config = DatabaseConfig(
                    db_type=DatabaseType.SQLITE,
                    database_path="data/grace.db"
                )
                DatabaseConnection.initialize(db_config)
                session_factory = initialize_session_factory()
            
            session = session_factory()
            
            try:
                genesis_service = get_genesis_service(session=session)
                
                # Create Genesis Key for stress test run
                summary = results.get("summary", {})
                pass_rate = summary.get("pass_rate", 0)
                issues_count = len(results.get("issues_found", []))
                
                key = genesis_service.create_key(
                    key_type=GenesisKeyType.SYSTEM_EVENT,  # Stress testing is a system event
                    what_description=f"Stress Test Run #{results.get('test_run_number', 0)}: {summary.get('passed', 0)}/{summary.get('total_tests', 0)} passed ({pass_rate:.1f}%)",
                    who_actor="stress_test_scheduler",
                    why_reason="Autonomous stress testing",
                    how_method="automated_scheduled_test",
                    context_data={
                        "test_run_number": results.get("test_run_number"),
                        "total_tests": summary.get("total_tests", 0),
                        "passed": summary.get("passed", 0),
                        "failed": summary.get("failed", 0),
                        "pass_rate": pass_rate,
                        "issues_found": issues_count,
                        "duration": results.get("total_duration", 0),
                        "results_file": results.get("results_file")
                    },
                    tags=["stress_test", "automated", f"run_{results.get('test_run_number', 0)}"]
                )
                
                logger.info(f"[STRESS-SCHEDULER] Logged test run to Genesis Key: {key.key_id}")
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"[STRESS-SCHEDULER] Failed to log with Genesis Keys: {e}")
            logger.debug(traceback.format_exc())
    
    def _alert_diagnostic_engine(self, results: Dict[str, Any]):
        """Alert both diagnostic engine AND self-healing system when issues found."""
        try:
            issues_found = results.get("issues_found", [])
            if not issues_found:
                return  # No issues, no alert needed
            
            summary = results.get("summary", {})
            pass_rate = summary.get("pass_rate", 0)
            
            # If pass rate is below 90% or issues found, alert both systems
            if pass_rate < 90 or len(issues_found) > 0:
                logger.warning(
                    f"[STRESS-SCHEDULER] Alerting diagnostic engine AND self-healing system: "
                    f"{len(issues_found)} issues found, pass rate: {pass_rate:.1f}%"
                )
                
                # Alert diagnostic engine
                self._alert_diagnostic_engine_only(results, issues_found, pass_rate)
                
                # Alert self-healing system
                self._alert_self_healing_system(results, issues_found, pass_rate)
                
                # Register new patterns with both systems for learning
                self._register_new_patterns(issues_found)
                    
        except Exception as e:
            logger.error(f"[STRESS-SCHEDULER] Error in alert system: {e}")
            logger.debug(traceback.format_exc())
    
    def _alert_diagnostic_engine_only(self, results: Dict[str, Any], issues_found: List[Dict], pass_rate: float):
        """Alert diagnostic engine with issues."""
        try:
            from diagnostic_machine.automatic_bug_fixer import AutomaticBugFixer
            from diagnostic_machine.proactive_code_scanner import ProactiveCodeScanner
            from pathlib import Path
            
            # Create issue summary
            issue_summary = {
                "source": "stress_test_scheduler",
                "test_run": results.get("test_run_number"),
                "pass_rate": pass_rate,
                "issues_count": len(issues_found),
                "issues": issues_found[:10]  # First 10 issues
            }
            
            # Save to diagnostic log file
            diagnostic_log_dir = Path("logs/diagnostic")
            diagnostic_log_dir.mkdir(parents=True, exist_ok=True)
            
            log_file = diagnostic_log_dir / f"stress_test_alert_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(issue_summary, f, indent=2, default=str)
            
            logger.info(f"[STRESS-SCHEDULER] Diagnostic alert saved to: {log_file}")
            
            # If critical issues, trigger proactive scan
            if pass_rate < 80:
                logger.warning("[STRESS-SCHEDULER] Critical issues detected - triggering proactive scan")
                try:
                    scanner = ProactiveCodeScanner(backend_dir=Path("backend"))
                    issues = scanner.scan_all()
                    
                    if issues:
                        fixer = AutomaticBugFixer(backend_dir=Path("backend"))
                        fix_results = fixer.fix_all_issues(issues)
                        
                        successful_fixes = sum(1 for f in fix_results if f.success)
                        logger.info(f"[STRESS-SCHEDULER] Proactive scan fixed {successful_fixes}/{len(fix_results)} issues")
                except Exception as e:
                    logger.error(f"[STRESS-SCHEDULER] Proactive scan failed: {e}")
            
        except ImportError:
            logger.warning("[STRESS-SCHEDULER] Diagnostic engine not available")
        except Exception as e:
            logger.error(f"[STRESS-SCHEDULER] Failed to alert diagnostic engine: {e}")
            logger.debug(traceback.format_exc())
    
    def _alert_self_healing_system(self, results: Dict[str, Any], issues_found: List[Dict], pass_rate: float):
        """Alert self-healing system with anomalies."""
        try:
            from cognitive.autonomous_healing_system import get_autonomous_healing, AnomalyType
            from database.session import initialize_session_factory, SessionLocal
            from database.connection import DatabaseConnection
            from database.config import DatabaseConfig, DatabaseType
            
            # Initialize database if needed
            try:
                session_factory = initialize_session_factory()
            except:
                db_config = DatabaseConfig(
                    db_type=DatabaseType.SQLITE,
                    database_path="data/grace.db"
                )
                DatabaseConnection.initialize(db_config)
                session_factory = initialize_session_factory()
            
            session = session_factory()
            
            try:
                healing_system = get_autonomous_healing(session=session)
                
                # Convert stress test issues to anomalies
                anomalies = self._convert_issues_to_anomalies(issues_found, results)
                
                if anomalies:
                    logger.info(f"[STRESS-SCHEDULER] Reporting {len(anomalies)} anomalies to self-healing system")
                    
                    # Add anomalies to healing system's detection queue
                    healing_system.anomalies_detected.extend(anomalies)
                    
                    # If critical issues or low pass rate, trigger immediate healing assessment
                    critical_issues = any(a.get("severity") == "critical" for a in anomalies)
                    if critical_issues or pass_rate < 70:
                        logger.warning("[STRESS-SCHEDULER] Critical anomaly detected - triggering immediate healing assessment")
                        
                        try:
                            # Run assessment (includes the anomalies we just added)
                            assessment = healing_system.assess_system_health()
                            
                            # Combine stress test anomalies with detected anomalies
                            all_anomalies = assessment.get("anomalies", []) + anomalies
                            
                            if all_anomalies:
                                # Decide healing actions for all anomalies
                                decisions = healing_system.decide_healing_actions(all_anomalies)
                                logger.info(f"[STRESS-SCHEDULER] Self-healing system decided {len(decisions)} healing actions")
                                
                                # Execute healing actions if trust allows
                                for decision in decisions:
                                    try:
                                        if decision["execution_mode"] == "autonomous":
                                            result = healing_system.execute_healing_action(decision)
                                            success = result.get("success", False) if isinstance(result, dict) else False
                                            logger.info(
                                                f"[STRESS-SCHEDULER] Executed healing action: {decision['healing_action']}, "
                                                f"success: {success}"
                                            )
                                        else:
                                            logger.info(
                                                f"[STRESS-SCHEDULER] Healing action requires approval: {decision['healing_action']}"
                                            )
                                    except Exception as e:
                                        logger.error(f"[STRESS-SCHEDULER] Failed to execute healing action: {e}")
                        except Exception as e:
                            logger.error(f"[STRESS-SCHEDULER] Failed to trigger healing assessment: {e}")
                            logger.debug(traceback.format_exc())
                
                session.commit()
                
            finally:
                session.close()
                
        except ImportError:
            logger.warning("[STRESS-SCHEDULER] Self-healing system not available")
        except Exception as e:
            logger.error(f"[STRESS-SCHEDULER] Failed to alert self-healing system: {e}")
            logger.debug(traceback.format_exc())
    
    def _convert_issues_to_anomalies(self, issues_found: List[Dict], results: Dict[str, Any]) -> List[Dict]:
        """Convert stress test issues to anomalies for self-healing system."""
        anomalies = []
        
        from cognitive.autonomous_healing_system import AnomalyType
        
        for issue in issues_found:
            # Map issue types to anomaly types
            issue_type = issue.get("issue_type", "problem").lower()
            component = issue.get("component", "unknown")
            severity = issue.get("severity", "medium")
            message = issue.get("message", "")
            
            anomaly_type = AnomalyType.PERFORMANCE_DEGRADATION  # Default
            
            # Map issue types to anomaly types
            if "error" in issue_type or "exception" in issue_type:
                if "database" in component.lower() or "db" in component.lower():
                    anomaly_type = AnomalyType.SERVICE_FAILURE
                elif "memory" in issue_type.lower() or "memory" in message.lower():
                    anomaly_type = AnomalyType.MEMORY_LEAK
                elif "performance" in issue_type.lower() or "slow" in message.lower():
                    anomaly_type = AnomalyType.PERFORMANCE_DEGRADATION
                else:
                    anomaly_type = AnomalyType.ERROR_SPIKE
            elif "performance" in issue_type or "slow" in issue_type:
                anomaly_type = AnomalyType.PERFORMANCE_DEGRADATION
            elif "memory" in issue_type or "leak" in issue_type:
                anomaly_type = AnomalyType.MEMORY_LEAK
            elif "connection" in issue_type or "timeout" in issue_type:
                anomaly_type = AnomalyType.SERVICE_FAILURE
            elif "resource" in issue_type or "exhaustion" in issue_type:
                anomaly_type = AnomalyType.RESOURCE_EXHAUSTION
            
            anomaly = {
                "type": anomaly_type,
                "severity": severity,
                "details": message,
                "component": component,
                "source": "stress_test",
                "test_run": results.get("test_run_number"),
                "timestamp": datetime.now(UTC).isoformat(),
                "issue_data": issue  # Keep original issue data for context
            }
            
            # Add service-specific info
            if "database" in component.lower() or "db" in component.lower():
                anomaly["service"] = "database"
            elif "qdrant" in component.lower():
                anomaly["service"] = "qdrant"
            elif "ollama" in component.lower():
                anomaly["service"] = "ollama"
            
            anomalies.append(anomaly)
        
        return anomalies
    
    def _register_new_patterns(self, issues_found: List[Dict]):
        """Register new patterns with both diagnostic engine and self-healing system for learning."""
        try:
            from diagnostic_machine.test_issue_integration import TestIssueIntegration
            from pathlib import Path
            
            # Create integration instance
            integration = TestIssueIntegration()
            
            # Register issues with diagnostic engine (for detection)
            integration.register_issues_with_diagnostic(issues_found)
            
            # Register issues with self-healing system (for healing)
            integration.register_issues_with_healing(issues_found)
            
            # Update automatic fixer with new fix patterns
            integration.update_automatic_fixer(issues_found)
            
            logger.info(f"[STRESS-SCHEDULER] Registered {len(issues_found)} new patterns with both systems for learning")
            
        except ImportError:
            logger.warning("[STRESS-SCHEDULER] Test issue integration not available for pattern registration")
        except Exception as e:
            logger.error(f"[STRESS-SCHEDULER] Failed to register new patterns: {e}")
            logger.debug(traceback.format_exc())
    
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        return {
            "running": self.running,
            "interval_minutes": self.interval_minutes,
            "test_count": self.test_count,
            "last_test_time": self.results_history[-1].get("end_time") if self.results_history else None,
            "total_results": len(self.results_history)
        }


# Singleton instance
_scheduler_instance: Optional[StressTestScheduler] = None


def get_stress_test_scheduler(
    interval_minutes: int = 10,
    base_url: str = "http://localhost:8000",
    enable_genesis_logging: bool = True,
    enable_diagnostic_alerts: bool = True
) -> StressTestScheduler:
    """Get or create singleton stress test scheduler."""
    global _scheduler_instance
    
    if _scheduler_instance is None:
        _scheduler_instance = StressTestScheduler(
            interval_minutes=interval_minutes,
            base_url=base_url,
            enable_genesis_logging=enable_genesis_logging,
            enable_diagnostic_alerts=enable_diagnostic_alerts
        )
    
    return _scheduler_instance


def start_stress_test_scheduler(
    interval_minutes: int = 10,
    base_url: str = "http://localhost:8000",
    enable_genesis_logging: bool = True,
    enable_diagnostic_alerts: bool = True
):
    """Start the stress test scheduler."""
    scheduler = get_stress_test_scheduler(
        interval_minutes=interval_minutes,
        base_url=base_url,
        enable_genesis_logging=enable_genesis_logging,
        enable_diagnostic_alerts=enable_diagnostic_alerts
    )
    scheduler.start()
    return scheduler


def stop_stress_test_scheduler():
    """Stop the stress test scheduler."""
    global _scheduler_instance
    
    if _scheduler_instance:
        _scheduler_instance.stop()


def main():
    """Run scheduler as standalone script."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Grace Stress Test Scheduler")
    parser.add_argument("--interval", type=int, default=10, help="Interval in minutes (default: 10)")
    parser.add_argument("--base-url", type=str, default="http://localhost:8000", help="Base URL for API tests")
    parser.add_argument("--no-genesis", action="store_true", help="Disable Genesis Key logging")
    parser.add_argument("--no-diagnostic", action="store_true", help="Disable diagnostic alerts")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f"logs/stress_test_scheduler_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log", encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger.info("=" * 80)
    logger.info("GRACE STRESS TEST SCHEDULER")
    logger.info("=" * 80)
    logger.info(f"Interval: {args.interval} minutes")
    logger.info(f"Base URL: {args.base_url}")
    logger.info(f"Genesis Logging: {not args.no_genesis}")
    logger.info(f"Diagnostic Alerts: {not args.no_diagnostic}")
    logger.info("=" * 80)
    
    # Start scheduler
    scheduler = start_stress_test_scheduler(
        interval_minutes=args.interval,
        base_url=args.base_url,
        enable_genesis_logging=not args.no_genesis,
        enable_diagnostic_alerts=not args.no_diagnostic
    )
    
    try:
        # Keep running
        while True:
            time.sleep(60)
            status = scheduler.get_status()
            logger.debug(f"[SCHEDULER] Status: {status}")
    except KeyboardInterrupt:
        logger.info("\n[SCHEDULER] Shutting down...")
        stop_stress_test_scheduler()
        logger.info("[SCHEDULER] Stopped")


if __name__ == "__main__":
    main()
