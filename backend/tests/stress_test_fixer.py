import logging
import json
from pathlib import Path
from typing import Dict, Any, List
from sqlalchemy.orm import Session
class StressTestFixer:
    logger = logging.getLogger(__name__)
    """Automatically fixes issues found in stress tests."""
    
    def __init__(self, session: Session = None, knowledge_base_path: Path = None):
        if session is None and get_session is not None:
            try:
                self.session = next(get_session())
            except:
                self.session = None
        else:
            self.session = session
        self.kb_path = knowledge_base_path or Path("backend/knowledge_base")
        self.fixes_applied = []
        self.fixes_failed = []
        self.requires_upgrade = False
    
    def fix_all_issues(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Fix all issues found in analysis."""
        logger.info(f"Fixing {analysis.get('total_issues', 0)} issues...")
        
        # Fix critical issues
        for issue in analysis.get("critical_issues", []):
            self._fix_issue(issue)
        
        # Fix performance issues
        for issue in analysis.get("performance_issues", []):
            self._fix_issue(issue)
        
        # Fix data integrity issues
        for issue in analysis.get("data_integrity_issues", []):
            self._fix_issue(issue)
        
        # Fix resource issues
        for issue in analysis.get("resource_issues", []):
            self._fix_issue(issue)
        
        # Check if we need to upgrade systems
        if analysis.get("new_issue_types"):
            self.requires_upgrade = True
            logger.info(f"New issue types found - systems need upgrade")
        
        return {
            "fixed_count": len(self.fixes_applied),
            "failed_count": len(self.fixes_failed),
            "requires_upgrade": self.requires_upgrade,
            "fixes_applied": self.fixes_applied,
            "fixes_failed": self.fixes_failed
        }
    
    def _fix_issue(self, issue: Dict[str, Any]) -> bool:
        """Fix a single issue."""
        error = issue.get("error", "") or issue.get("issue", "")
        test_name = issue.get("test_name", "")
        
        try:
            # Health score issues
            if "health score too low" in error.lower():
                return self._fix_health_score_issue(issue)
            
            # Performance issues
            elif "performance" in error.lower() or "slow" in error.lower() or "duration" in error.lower():
                return self._fix_performance_issue(issue)
            
            # Memory issues
            elif "memory" in error.lower() and "usage" in error.lower():
                return self._fix_memory_usage_issue(issue)
            
            # CPU issues
            elif "cpu" in error.lower():
                return self._fix_cpu_issue(issue)
            
            # Data integrity issues
            elif "integrity" in error.lower() or "consistency" in error.lower():
                return self._fix_data_integrity_issue(issue)
            
            # Concurrent access issues
            elif "concurrent" in error.lower() or "success rate" in error.lower():
                return self._fix_concurrent_access_issue(issue)
            
            # Unknown issue - mark for upgrade
            else:
                logger.warning(f"Unknown issue type: {error}")
                self.requires_upgrade = True
                return False
        
        except Exception as e:
            logger.error(f"Failed to fix issue: {e}")
            self.fixes_failed.append({
                "issue": issue,
                "error": str(e)
            })
            return False
    
    def _fix_health_score_issue(self, issue: Dict[str, Any]) -> bool:
        """Fix health score issues."""
        test_name = issue.get("test_name", "")
        
        try:
            if "Memory" in test_name:
                # Run lifecycle maintenance to improve memory health
                if get_memory_lifecycle_manager is None or self.session is None:
                    return False
                lifecycle = get_memory_lifecycle_manager(self.session, self.kb_path)
                report = lifecycle.run_lifecycle_maintenance()
                
                self.fixes_applied.append({
                    "issue": issue,
                    "fix": "Ran memory lifecycle maintenance",
                    "result": report
                })
                return True
            
            elif "Librarian" in test_name:
                # Run librarian maintenance
                if get_enterprise_librarian is None or self.session is None:
                    return False
                librarian = get_enterprise_librarian(self.session, self.kb_path)
                archive_result = librarian.archive_old_documents()
                
                self.fixes_applied.append({
                    "issue": issue,
                    "fix": "Ran librarian archiving",
                    "result": archive_result
                })
                return True
            
            elif "World Model" in test_name:
                # Compress world model
                if get_enterprise_world_model is None:
                    return False
                world_model = get_enterprise_world_model(Path("backend/.genesis_world_model.json"))
                compress_result = world_model.compress_world_model()
                
                self.fixes_applied.append({
                    "issue": issue,
                    "fix": "Compressed world model",
                    "result": compress_result
                })
                return True
            
            return False
        
        except Exception as e:
            logger.error(f"Failed to fix health score issue: {e}")
            return False
    
    def _fix_performance_issue(self, issue: Dict[str, Any]) -> bool:
        """Fix performance issues."""
        try:
            # Run compression/archiving to improve performance
            if get_memory_lifecycle_manager is None or self.session is None:
                return False
            lifecycle = get_memory_lifecycle_manager(self.session, self.kb_path)
            report = lifecycle.run_lifecycle_maintenance()
            
            self.fixes_applied.append({
                "issue": issue,
                "fix": "Ran lifecycle maintenance to improve performance",
                "result": report
            })
            return True
        
        except Exception as e:
            logger.error(f"Failed to fix performance issue: {e}")
            return False
    
    def _fix_memory_usage_issue(self, issue: Dict[str, Any]) -> bool:
        """Fix memory usage issues."""
        try:
            # Run compression to reduce memory usage
            if get_memory_lifecycle_manager is None or self.session is None:
                return False
            lifecycle = get_memory_lifecycle_manager(self.session, self.kb_path)
            report = lifecycle.run_lifecycle_maintenance()
            
            self.fixes_applied.append({
                "issue": issue,
                "fix": "Ran compression to reduce memory usage",
                "result": report
            })
            return True
        
        except Exception as e:
            logger.error(f"Failed to fix memory usage issue: {e}")
            return False
    
    def _fix_cpu_issue(self, issue: Dict[str, Any]) -> bool:
        """Fix CPU usage issues."""
        # CPU issues are harder to fix automatically
        # Mark for upgrade
        self.requires_upgrade = True
        return False
    
    def _fix_data_integrity_issue(self, issue: Dict[str, Any]) -> bool:
        """Fix data integrity issues."""
        # Data integrity issues require manual review
        # Mark for upgrade
        self.requires_upgrade = True
        return False
    
    def _fix_concurrent_access_issue(self, issue: Dict[str, Any]) -> bool:
        """Fix concurrent access issues."""
        # Concurrent access issues may require code changes
        # Mark for upgrade
        self.requires_upgrade = True
        return False
