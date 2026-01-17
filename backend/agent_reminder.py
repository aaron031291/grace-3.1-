import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import json
from system_specs import get_system_specs, SystemSpecs
class AgentReminder:
    logger = logging.getLogger(__name__)
    """
    Manages polite reminders to external coding agents about system specifications.
    
    Detects when external agents are working and provides system specs context.
    """
    
    def __init__(self, specs: Optional[SystemSpecs] = None):
        """
        Initialize agent reminder system.
        
        Args:
            specs: System specifications (defaults to loaded specs)
        """
        self.specs = specs or get_system_specs()
        self.reminder_file = Path("backend/config/agent_reminder.json")
        self.reminder_file.parent.mkdir(parents=True, exist_ok=True)
    
    def get_reminder_message(self) -> str:
        """Get polite reminder message for external agents."""
        return self.specs.get_reminder_message()
    
    def save_reminder_to_file(self):
        """Save reminder message to file for external agents to read."""
        reminder_data = {
            "timestamp": datetime.now().isoformat(),
            "message": self.get_reminder_message(),
            "specs": self.specs.to_dict()
        }
        
        with open(self.reminder_file, 'w') as f:
            json.dump(reminder_data, f, indent=2)
        
        logger.info(f"Agent reminder saved to {self.reminder_file}")
    
    def check_and_remind(self, context: Dict[str, Any]) -> Optional[str]:
        """
        Check if external agent is working and provide reminder if needed.
        
        Args:
            context: Context about current operation (e.g., file being edited, operation type)
        
        Returns:
            Reminder message if conditions are met, None otherwise
        """
        # Check if this looks like external agent activity
        is_external_agent = self._detect_external_agent(context)
        
        if is_external_agent:
            # Check if we've reminded recently (avoid spam)
            if not self._should_remind():
                return None
            
            # Save reminder to file
            self.save_reminder_to_file()
            
            # Return reminder message
            return self.get_reminder_message()
        
        return None
    
    def _detect_external_agent(self, context: Dict[str, Any]) -> bool:
        """
        Detect if external agent is likely working.
        
        Heuristics:
        - Large code changes
        - Architecture changes
        - Model recommendations
        - Resource-intensive operations
        """
        # Check for architecture/model changes
        if context.get("operation_type") in ["architecture", "model_selection", "resource_allocation"]:
            return True
        
        # Check for large code changes
        if context.get("files_changed", 0) > 5:
            return True
        
        # Check for model-related operations
        if any(keyword in str(context).lower() for keyword in ["model", "gpu", "vram", "memory", "storage"]):
            return True
        
        return False
    
    def _should_remind(self) -> bool:
        """Check if we should remind (avoid reminding too frequently)."""
        if not self.reminder_file.exists():
            return True
        
        try:
            with open(self.reminder_file, 'r') as f:
                data = json.load(f)
            
            last_reminder = datetime.fromisoformat(data.get("timestamp", "2000-01-01"))
            hours_since_reminder = (datetime.now() - last_reminder).total_seconds() / 3600
            
            # Remind at most once per hour
            return hours_since_reminder >= 1.0
            
        except Exception:
            return True
    
    def create_reminder_file(self):
        """Create reminder file in project root for easy access."""
        # Create in project root
        root_reminder = Path("GRACE_SYSTEM_SPECS.txt")
        
        with open(root_reminder, 'w') as f:
            f.write(self.get_reminder_message())
        
        logger.info(f"Reminder file created at {root_reminder}")
        
        # Also save JSON version
        self.save_reminder_to_file()


# Global instance
_agent_reminder: Optional[AgentReminder] = None


def get_agent_reminder() -> AgentReminder:
    """Get or create global agent reminder instance."""
    global _agent_reminder
    if _agent_reminder is None:
        _agent_reminder = AgentReminder()
    return _agent_reminder


def create_reminder_files():
    """Create reminder files for external agents."""
    reminder = get_agent_reminder()
    reminder.create_reminder_file()
