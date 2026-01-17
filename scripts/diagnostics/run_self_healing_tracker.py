#!/usr/bin/env python3
"""
Self-Healing Capability Tracker
Runs the self-healing system and tracks what fixes it can perform.
"""

import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime, UTC
from typing import Dict, List, Any, Optional

# Add backend to path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

# Setup logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / f"self_healing_tracker_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class SelfHealingTracker:
    """Tracks self-healing system capabilities and fixes."""
    
    def __init__(self):
        self.healing_system = None
        self.capabilities: Dict[str, Any] = {}
        self.fixes_performed: List[Dict[str, Any]] = []
        self.fixes_available: List[Dict[str, Any]] = []
        
    def initialize_healing_system(self):
        """Initialize the self-healing system."""
        try:
            from cognitive.autonomous_healing_system import (
                get_autonomous_healing,
                HealingAction,
                TrustLevel,
                HealthStatus,
                AnomalyType
            )
            from database.session import get_session, initialize_session_factory
            from database.connection import DatabaseConnection
            from database.config import DatabaseConfig, DatabaseType
            
            # Initialize database
            db_config = DatabaseConfig(
                db_type=DatabaseType.SQLITE,
                database_path="data/grace.db"
            )
            DatabaseConnection.initialize(db_config)
            initialize_session_factory()
            session = get_session()
            
            # Get healing system
            self.healing_system = get_autonomous_healing(
                session=session,
                repo_path=Path("backend"),
                trust_level=TrustLevel.MEDIUM_RISK_AUTO,
                enable_learning=True
            )
            
            logger.info("[TRACKER] Self-healing system initialized")
            return True
            
        except Exception as e:
            logger.error(f"[TRACKER] Failed to initialize healing system: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def track_capabilities(self):
        """Track what the self-healing system can do."""
        if not self.healing_system:
            logger.error("[TRACKER] Healing system not initialized")
            return
        
        logger.info("=" * 80)
        logger.info("TRACKING SELF-HEALING CAPABILITIES")
        logger.info("=" * 80)
        
        # Track healing actions
        self._track_healing_actions()
        
        # Track health assessment
        self._track_health_assessment()
        
        # Track anomaly detection
        self._track_anomaly_detection()
        
        # Track trust levels
        self._track_trust_levels()
        
        # Track automatic fixer capabilities
        self._track_automatic_fixer()
        
        # Save capabilities
        self._save_capabilities()
    
    def _track_healing_actions(self):
        """Track available healing actions."""
        logger.info("\n[TRACKING] Healing Actions")
        logger.info("-" * 80)
        
        from cognitive.autonomous_healing_system import HealingAction
        
        actions = []
        for action in HealingAction:
            action_info = {
                "action": action.value,
                "name": action.name,
                "description": self._get_action_description(action),
                "trust_score": self.healing_system.trust_scores.get(action, 0.0),
                "can_auto_execute": self._can_auto_execute(action),
                "risk_level": self._get_risk_level(action)
            }
            actions.append(action_info)
            
            logger.info(f"  {action.value}:")
            logger.info(f"    Trust Score: {action_info['trust_score']:.2f}")
            logger.info(f"    Auto-Execute: {action_info['can_auto_execute']}")
            logger.info(f"    Risk Level: {action_info['risk_level']}")
        
        self.capabilities["healing_actions"] = actions
        self.fixes_available.extend(actions)
    
    def _get_action_description(self, action) -> str:
        """Get description for healing action."""
        from cognitive.autonomous_healing_system import HealingAction
        
        descriptions = {
            HealingAction.BUFFER_CLEAR: "Clear system buffers to free memory",
            HealingAction.CACHE_FLUSH: "Flush caches to resolve stale data",
            HealingAction.CONNECTION_RESET: "Reset network/database connections",
            HealingAction.PROCESS_RESTART: "Restart a specific process",
            HealingAction.SERVICE_RESTART: "Restart a service",
            HealingAction.STATE_ROLLBACK: "Rollback to a known good state",
            HealingAction.ISOLATION: "Isolate affected component",
            HealingAction.EMERGENCY_SHUTDOWN: "Emergency shutdown of system"
        }
        return descriptions.get(action, "Unknown action")
    
    def _can_auto_execute(self, action) -> bool:
        """Check if action can be auto-executed."""
        try:
            from cognitive.autonomous_healing_system import HealingAction
            
            trust_score = self.healing_system.trust_scores.get(action, 0.0)
            trust_level = self.healing_system.trust_level.value
            
            # Map actions to required trust levels
            required_levels = {
                HealingAction.BUFFER_CLEAR: 2,  # LOW_RISK_AUTO
                HealingAction.CACHE_FLUSH: 2,
                HealingAction.CONNECTION_RESET: 3,  # MEDIUM_RISK_AUTO
                HealingAction.PROCESS_RESTART: 3,
                HealingAction.SERVICE_RESTART: 4,  # HIGH_RISK_AUTO
                HealingAction.STATE_ROLLBACK: 4,
                HealingAction.ISOLATION: 5,  # CRITICAL_AUTO
                HealingAction.EMERGENCY_SHUTDOWN: 5
            }
            
            required = required_levels.get(action, 5)
            return trust_level >= required and trust_score > 0.3
        except:
            return False
    
    def _get_risk_level(self, action) -> str:
        """Get risk level for action."""
        from cognitive.autonomous_healing_system import HealingAction
        
        risk_levels = {
            HealingAction.BUFFER_CLEAR: "LOW",
            HealingAction.CACHE_FLUSH: "LOW",
            HealingAction.CONNECTION_RESET: "MEDIUM",
            HealingAction.PROCESS_RESTART: "MEDIUM",
            HealingAction.SERVICE_RESTART: "HIGH",
            HealingAction.STATE_ROLLBACK: "HIGH",
            HealingAction.ISOLATION: "CRITICAL",
            HealingAction.EMERGENCY_SHUTDOWN: "CRITICAL"
        }
        return risk_levels.get(action, "UNKNOWN")
    
    def _track_health_assessment(self):
        """Track health assessment capabilities."""
        logger.info("\n[TRACKING] Health Assessment")
        logger.info("-" * 80)
        
        try:
            assessment = self.healing_system.assess_system_health()
            
            health_info = {
                "health_status": assessment.get("health_status", "unknown"),
                "anomalies_detected": assessment.get("anomalies_detected", 0),
                "metrics": assessment.get("metrics", {}),
                "thresholds": self.healing_system.thresholds
            }
            
            self.capabilities["health_assessment"] = health_info
            
            logger.info(f"  Current Health: {health_info['health_status']}")
            logger.info(f"  Anomalies Detected: {health_info['anomalies_detected']}")
            logger.info(f"  Thresholds:")
            for key, value in health_info['thresholds'].items():
                logger.info(f"    {key}: {value}")
                
        except Exception as e:
            logger.error(f"  Failed to assess health: {e}")
            self.capabilities["health_assessment"] = {"error": str(e)}
    
    def _track_anomaly_detection(self):
        """Track anomaly detection capabilities."""
        logger.info("\n[TRACKING] Anomaly Detection")
        logger.info("-" * 80)
        
        from cognitive.autonomous_healing_system import AnomalyType
        
        anomalies = []
        for anomaly_type in AnomalyType:
            anomaly_info = {
                "type": anomaly_type.value,
                "name": anomaly_type.name,
                "can_detect": True,
                "healing_action": self._get_healing_action_for_anomaly(anomaly_type)
            }
            anomalies.append(anomaly_info)
            logger.info(f"  {anomaly_type.value}: {anomaly_info['healing_action']}")
        
        self.capabilities["anomaly_detection"] = anomalies
    
    def _get_healing_action_for_anomaly(self, anomaly_type) -> str:
        """Get healing action for anomaly type."""
        from cognitive.autonomous_healing_system import AnomalyType
        
        mappings = {
            AnomalyType.ERROR_SPIKE: "PROCESS_RESTART",
            AnomalyType.MEMORY_LEAK: "BUFFER_CLEAR",
            AnomalyType.PERFORMANCE_DEGRADATION: "CACHE_FLUSH",
            AnomalyType.RESPONSE_TIMEOUT: "CONNECTION_RESET",
            AnomalyType.DATA_INCONSISTENCY: "STATE_ROLLBACK",
            AnomalyType.SECURITY_BREACH: "ISOLATION",
            AnomalyType.RESOURCE_EXHAUSTION: "SERVICE_RESTART"
        }
        return mappings.get(anomaly_type, "BUFFER_CLEAR")
    
    def _track_trust_levels(self):
        """Track trust levels and scores."""
        logger.info("\n[TRACKING] Trust Levels")
        logger.info("-" * 80)
        
        from cognitive.autonomous_healing_system import TrustLevel
        
        trust_info = {
            "current_trust_level": self.healing_system.trust_level.name,
            "current_trust_value": self.healing_system.trust_level.value,
            "action_trust_scores": {}
        }
        
        for action, score in self.healing_system.trust_scores.items():
            trust_info["action_trust_scores"][action.value] = score
            logger.info(f"  {action.value}: {score:.2f}")
        
        self.capabilities["trust_levels"] = trust_info
    
    def _track_automatic_fixer(self):
        """Track automatic bug fixer capabilities."""
        logger.info("\n[TRACKING] Automatic Bug Fixer")
        logger.info("-" * 80)
        
        try:
            from diagnostic_machine.automatic_bug_fixer import AutomaticBugFixer
            
            fixer = AutomaticBugFixer()
            
            fixer_capabilities = {
                "available": True,
                "can_fix": [
                    "syntax_error",
                    "import_error",
                    "missing_file",
                    "code_quality"
                ],
                "uses_deepseek": fixer.use_deepseek,
                "creates_backups": fixer.create_backups
            }
            
            self.capabilities["automatic_fixer"] = fixer_capabilities
            
            logger.info("  Available: Yes")
            logger.info(f"  Can Fix: {', '.join(fixer_capabilities['can_fix'])}")
            logger.info(f"  Uses DeepSeek: {fixer_capabilities['uses_deepseek']}")
            logger.info(f"  Creates Backups: {fixer_capabilities['creates_backups']}")
            
        except Exception as e:
            logger.warning(f"  Automatic fixer not available: {e}")
            self.capabilities["automatic_fixer"] = {"available": False, "error": str(e)}
    
    def run_healing_cycle(self):
        """Run a healing cycle and track what it does."""
        if not self.healing_system:
            logger.error("[TRACKER] Healing system not initialized")
            return
        
        logger.info("\n" + "=" * 80)
        logger.info("RUNNING HEALING CYCLE")
        logger.info("=" * 80)
        
        try:
            cycle_result = self.healing_system.run_monitoring_cycle()
            
            fix_result = {
                "timestamp": datetime.now(UTC).isoformat(),
                "health_status": cycle_result.get("health_status", "unknown"),
                "anomalies_detected": cycle_result.get("anomalies_detected", 0),
                "decisions_made": cycle_result.get("decisions_made", 0),
                "actions_executed": cycle_result.get("actions_executed", 0),
                "awaiting_approval": cycle_result.get("awaiting_approval", 0),
                "failures": cycle_result.get("failures", 0),
                "decisions": cycle_result.get("decisions", []),
                "results": cycle_result.get("results", {})
            }
            
            self.fixes_performed.append(fix_result)
            
            logger.info(f"Health Status: {fix_result['health_status']}")
            logger.info(f"Anomalies Detected: {fix_result['anomalies_detected']}")
            logger.info(f"Decisions Made: {fix_result['decisions_made']}")
            logger.info(f"Actions Executed: {fix_result['actions_executed']}")
            logger.info(f"Awaiting Approval: {fix_result['awaiting_approval']}")
            logger.info(f"Failures: {fix_result['failures']}")
            
            if fix_result['decisions']:
                logger.info("\nDecisions:")
                for decision in fix_result['decisions']:
                    logger.info(f"  - {decision.get('healing_action', 'unknown')}: {decision.get('reason', 'N/A')}")
            
            if fix_result['results'].get('executed'):
                logger.info("\nExecuted Actions:")
                for action in fix_result['results']['executed']:
                    logger.info(f"  - {action.get('action', 'unknown')}: {action.get('result', 'N/A')}")
            
            return fix_result
            
        except Exception as e:
            logger.error(f"Failed to run healing cycle: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _save_capabilities(self):
        """Save capabilities to file."""
        capabilities_file = Path(f"self_healing_capabilities_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        # Convert enums to strings
        def convert_value(v):
            if hasattr(v, 'value'):
                return v.value
            elif isinstance(v, dict):
                return {k: convert_value(val) for k, val in v.items()}
            elif isinstance(v, list):
                return [convert_value(item) for item in v]
            return v
        
        capabilities_dict = convert_value(self.capabilities)
        
        capabilities_dict["summary"] = {
            "total_healing_actions": len(self.capabilities.get("healing_actions", [])),
            "total_anomaly_types": len(self.capabilities.get("anomaly_detection", [])),
            "auto_fixer_available": self.capabilities.get("automatic_fixer", {}).get("available", False),
            "timestamp": datetime.now(UTC).isoformat()
        }
        
        capabilities_file.write_text(json.dumps(capabilities_dict, indent=2, default=str))
        logger.info(f"\n[TRACKER] Saved capabilities to {capabilities_file}")
    
    def save_fixes_report(self):
        """Save fixes report."""
        if not self.fixes_performed:
            logger.info("[TRACKER] No fixes performed to report")
            return
        
        report_file = Path(f"self_healing_fixes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        report = {
            "timestamp": datetime.now(UTC).isoformat(),
            "total_cycles": len(self.fixes_performed),
            "total_actions_executed": sum(f.get("actions_executed", 0) for f in self.fixes_performed),
            "total_anomalies_detected": sum(f.get("anomalies_detected", 0) for f in self.fixes_performed),
            "fixes_performed": self.fixes_performed,
            "fixes_available": self.fixes_available
        }
        
        report_file.write_text(json.dumps(report, indent=2, default=str))
        logger.info(f"[TRACKER] Saved fixes report to {report_file}")
    
    def print_summary(self):
        """Print summary of capabilities."""
        logger.info("\n" + "=" * 80)
        logger.info("SELF-HEALING CAPABILITIES SUMMARY")
        logger.info("=" * 80)
        
        logger.info(f"\nHealing Actions Available: {len(self.capabilities.get('healing_actions', []))}")
        for action in self.capabilities.get('healing_actions', []):
            auto = "[YES]" if action.get('can_auto_execute') else "[NO]"
            logger.info(f"  {auto} {action['action']} (Trust: {action['trust_score']:.2f}, Risk: {action['risk_level']})")
        
        logger.info(f"\nAnomaly Types Detected: {len(self.capabilities.get('anomaly_detection', []))}")
        for anomaly in self.capabilities.get('anomaly_detection', []):
            logger.info(f"  - {anomaly['type']} -> {anomaly['healing_action']}")
        
        auto_fixer = self.capabilities.get('automatic_fixer', {})
        if auto_fixer.get('available'):
            logger.info(f"\nAutomatic Fixer: Available")
            logger.info(f"  Can Fix: {', '.join(auto_fixer.get('can_fix', []))}")
        else:
            logger.info(f"\nAutomatic Fixer: Not Available")
        
        logger.info(f"\nFixes Performed: {len(self.fixes_performed)}")
        if self.fixes_performed:
            total_actions = sum(f.get("actions_executed", 0) for f in self.fixes_performed)
            logger.info(f"  Total Actions Executed: {total_actions}")
        
        logger.info("=" * 80)


def main():
    """Main entry point."""
    logger.info("=" * 80)
    logger.info("SELF-HEALING CAPABILITY TRACKER")
    logger.info("=" * 80)
    
    tracker = SelfHealingTracker()
    
    # Initialize
    if not tracker.initialize_healing_system():
        logger.error("Failed to initialize healing system")
        return 1
    
    # Track capabilities
    tracker.track_capabilities()
    
    # Run healing cycle
    tracker.run_healing_cycle()
    
    # Print summary
    tracker.print_summary()
    
    # Save reports
    tracker.save_fixes_report()
    
    logger.info("\n[TRACKER] Tracking complete!")
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
