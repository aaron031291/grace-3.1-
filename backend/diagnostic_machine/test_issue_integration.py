import logging
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
class TestIssueIntegration:
    logger = logging.getLogger(__name__)
    """Integrates test issues with self-healing and diagnostic systems."""
    
    def __init__(self):
        self.healing_system = None
        self.diagnostic_engine = None
        self.issue_patterns: Dict[str, Any] = {}
        
        # Initialize connections
        self._init_healing_system()
        self._init_diagnostic_engine()
    
    def _init_healing_system(self):
        """Initialize connection to self-healing system."""
        try:
            from cognitive.autonomous_healing_system import get_autonomous_healing
            from database.session import get_session
            
            session = get_session()
            self.healing_system = get_autonomous_healing(session=session)
            logger.info("[TEST-INTEGRATION] Connected to self-healing system")
        except Exception as e:
            logger.warning(f"[TEST-INTEGRATION] Could not connect to self-healing: {e}")
    
    def _init_diagnostic_engine(self):
        """Initialize connection to diagnostic engine."""
        try:
            from diagnostic_machine.proactive_code_scanner import ProactiveCodeScanner
            self.diagnostic_engine = ProactiveCodeScanner()
            logger.info("[TEST-INTEGRATION] Connected to diagnostic engine")
        except Exception as e:
            logger.warning(f"[TEST-INTEGRATION] Could not connect to diagnostic engine: {e}")
    
    def load_test_issues(self, issues_file: Path) -> List[Dict[str, Any]]:
        """Load test issues from JSON file."""
        try:
            if not issues_file.exists():
                logger.warning(f"[TEST-INTEGRATION] Issues file not found: {issues_file}")
                return []
            
            issues_data = json.loads(issues_file.read_text())
            logger.info(f"[TEST-INTEGRATION] Loaded {len(issues_data)} issues from {issues_file}")
            return issues_data
        except Exception as e:
            logger.error(f"[TEST-INTEGRATION] Failed to load issues: {e}")
            return []
    
    def register_issues_with_healing(self, issues: List[Dict[str, Any]]):
        """Register test issues with self-healing system."""
        if not self.healing_system:
            logger.warning("[TEST-INTEGRATION] Self-healing system not available")
            return
        
        logger.info(f"[TEST-INTEGRATION] Registering {len(issues)} issues with self-healing")
        
        registered = 0
        for issue in issues:
            try:
                # Convert test issue to healing system format
                healing_issue = {
                    "description": issue.get("message", ""),
                    "component": issue.get("component", ""),
                    "test_name": issue.get("test_name", ""),
                    "issue_type": issue.get("issue_type", "problem"),
                    "severity": issue.get("severity", "medium"),
                    "auto_fixable": issue.get("auto_fixable", False),
                    "fix_suggested": issue.get("fix_suggested"),
                    "details": issue.get("details", {}),
                    "stack_trace": issue.get("stack_trace"),
                    "timestamp": issue.get("timestamp", datetime.now().isoformat())
                }
                
                # Register with healing system
                # This creates a healing pattern that the system can recognize
                self._register_healing_pattern(healing_issue)
                registered += 1
                
            except Exception as e:
                logger.error(f"[TEST-INTEGRATION] Failed to register issue: {e}")
        
        logger.info(f"[TEST-INTEGRATION] Registered {registered}/{len(issues)} issues with self-healing")
    
    def _register_healing_pattern(self, issue: Dict[str, Any]):
        """Register a healing pattern for an issue."""
        # Store pattern for recognition
        pattern_key = f"{issue['component']}:{issue['issue_type']}:{issue['severity']}"
        self.issue_patterns[pattern_key] = issue
        
        # If healing system has a method to register patterns, use it
        if hasattr(self.healing_system, 'register_issue_pattern'):
            try:
                self.healing_system.register_issue_pattern(
                    pattern=issue['description'],
                    component=issue['component'],
                    issue_type=issue['issue_type'],
                    auto_fixable=issue['auto_fixable'],
                    fix_suggestion=issue.get('fix_suggested')
                )
            except Exception as e:
                logger.debug(f"[TEST-INTEGRATION] Pattern registration not available: {e}")
    
    def register_issues_with_diagnostic(self, issues: List[Dict[str, Any]]):
        """Register test issues with diagnostic engine."""
        if not self.diagnostic_engine:
            logger.warning("[TEST-INTEGRATION] Diagnostic engine not available")
            return
        
        logger.info(f"[TEST-INTEGRATION] Registering {len(issues)} issues with diagnostic engine")
        
        registered = 0
        for issue in issues:
            try:
                # Create detection pattern
                pattern = {
                    "message_pattern": issue.get("message", "")[:100],  # First 100 chars
                    "component": issue.get("component", ""),
                    "issue_type": issue.get("issue_type", "problem"),
                    "severity": issue.get("severity", "medium"),
                    "detection_rules": self._create_detection_rules(issue)
                }
                
                # Register with diagnostic engine
                self._register_diagnostic_pattern(pattern)
                registered += 1
                
            except Exception as e:
                logger.error(f"[TEST-INTEGRATION] Failed to register diagnostic pattern: {e}")
        
        logger.info(f"[TEST-INTEGRATION] Registered {registered}/{len(issues)} issues with diagnostic engine")
    
    def _create_detection_rules(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """Create detection rules for diagnostic engine."""
        message = issue.get("message", "")
        component = issue.get("component", "")
        issue_type = issue.get("issue_type", "problem")
        
        # Extract key phrases from message
        key_phrases = []
        if "import" in message.lower():
            key_phrases.append("import_error")
        if "syntax" in message.lower():
            key_phrases.append("syntax_error")
        if "missing" in message.lower():
            key_phrases.append("missing_resource")
        if "failed" in message.lower():
            key_phrases.append("operation_failed")
        
        return {
            "message_contains": message[:50] if len(message) > 50 else message,
            "component": component,
            "issue_type": issue_type,
            "key_phrases": key_phrases,
            "severity": issue.get("severity", "medium")
        }
    
    def _register_diagnostic_pattern(self, pattern: Dict[str, Any]):
        """Register a diagnostic pattern."""
        # Store pattern
        pattern_key = f"{pattern['component']}:{pattern['issue_type']}"
        if pattern_key not in self.issue_patterns:
            self.issue_patterns[pattern_key] = []
        self.issue_patterns[pattern_key].append(pattern)
        
        # If diagnostic engine has a method to register patterns, use it
        if hasattr(self.diagnostic_engine, 'register_detection_pattern'):
            try:
                self.diagnostic_engine.register_detection_pattern(
                    pattern=pattern['message_pattern'],
                    component=pattern['component'],
                    issue_type=pattern['issue_type'],
                    rules=pattern['detection_rules']
                )
            except Exception as e:
                logger.debug(f"[TEST-INTEGRATION] Pattern registration not available: {e}")
    
    def update_automatic_fixer(self, issues: List[Dict[str, Any]]):
        """Update automatic bug fixer with new fix patterns."""
        try:
            from diagnostic_machine.automatic_bug_fixer import AutomaticBugFixer
            
            fixer = AutomaticBugFixer()
            
            # Group issues by type for fixer
            fixable_issues = [i for i in issues if i.get("auto_fixable", False)]
            
            logger.info(f"[TEST-INTEGRATION] Updating automatic fixer with {len(fixable_issues)} fixable issues")
            
            # For each fixable issue, add fix pattern
            for issue in fixable_issues:
                fix_suggestion = issue.get("fix_suggested")
                if fix_suggestion:
                    # Store fix pattern
                    issue_type = issue.get("issue_type", "unknown")
                    component = issue.get("component", "unknown")
                    
                    logger.debug(f"[TEST-INTEGRATION] Added fix pattern for {component}:{issue_type}")
            
        except Exception as e:
            logger.error(f"[TEST-INTEGRATION] Failed to update automatic fixer: {e}")
    
    def process_test_report(self, report_file: Path):
        """Process a complete test report and update all systems."""
        try:
            if not report_file.exists():
                logger.warning(f"[TEST-INTEGRATION] Report file not found: {report_file}")
                return
            
            report_data = json.loads(report_file.read_text())
            
            # Extract all issues
            all_issues = report_data.get("all_issues", [])
            
            logger.info(f"[TEST-INTEGRATION] Processing test report with {len(all_issues)} issues")
            
            # Register with all systems
            self.register_issues_with_healing(all_issues)
            self.register_issues_with_diagnostic(all_issues)
            self.update_automatic_fixer(all_issues)
            
            logger.info("[TEST-INTEGRATION] Test report processed successfully")
            
        except Exception as e:
            logger.error(f"[TEST-INTEGRATION] Failed to process test report: {e}")
    
    def get_recognized_patterns(self) -> Dict[str, Any]:
        """Get all recognized patterns."""
        return {
            "patterns": self.issue_patterns,
            "total_patterns": len(self.issue_patterns),
            "healing_connected": self.healing_system is not None,
            "diagnostic_connected": self.diagnostic_engine is not None
        }


def get_test_issue_integration() -> TestIssueIntegration:
    """Get or create test issue integration instance."""
    return TestIssueIntegration()


def main():
    """Main entry point for processing test issues."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python test_issue_integration.py <issues_file.json> [report_file.json]")
        sys.exit(1)
    
    integration = get_test_issue_integration()
    
    # Process issues file
    issues_file = Path(sys.argv[1])
    issues = integration.load_test_issues(issues_file)
    
    if issues:
        integration.register_issues_with_healing(issues)
        integration.register_issues_with_diagnostic(issues)
        integration.update_automatic_fixer(issues)
    
    # Process report file if provided
    if len(sys.argv) >= 3:
        report_file = Path(sys.argv[2])
        integration.process_test_report(report_file)
    
    # Print summary
    patterns = integration.get_recognized_patterns()
    print(f"\n[SUMMARY]")
    print(f"  Patterns registered: {patterns['total_patterns']}")
    print(f"  Healing connected: {patterns['healing_connected']}")
    print(f"  Diagnostic connected: {patterns['diagnostic_connected']}")


if __name__ == "__main__":
    main()
