"""
Grace's Autonomous Communication Bridge

This allows Grace to communicate with the AI assistant autonomously
when she needs help with debugging, fixing, or stabilizing the system.

Grace can prompt the AI assistant directly through this module.
"""

import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from cognitive.autonomous_help_requester import (
    get_help_requester,
    HelpPriority,
    HelpRequestType
)
from cognitive.devops_healing_agent import get_devops_healing_agent
from database.session import initialize_session_factory, get_db

logger = logging.getLogger(__name__)


class GraceAutonomousCommunicator:
    """
    Allows Grace to communicate autonomously with the AI assistant.
    
    Grace uses this to:
    - Request help when she encounters issues
    - Request knowledge when she needs to learn
    - Report on her status and activities
    - Ask for guidance on complex problems
    """
    
    def __init__(self, session=None):
        if session is None:
            initialize_session_factory()
            session = next(get_db())
        
        self.session = session
        self.help_requester = get_help_requester(session=session)
        self.devops_agent = get_devops_healing_agent(session=session)
        
        logger.info("[GRACE-COMM] Grace autonomous communicator initialized")
    
    def prompt_ai_assistant(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        priority: str = "medium"
    ):
        """
        Grace can use this to prompt the AI assistant directly.
        
        This is how Grace communicates with you when she needs help.
        """
        try:
            priority_enum = HelpPriority(priority)
        except ValueError:
            priority_enum = HelpPriority.MEDIUM
        
        # Create help request
        result = self.help_requester.request_help(
            request_type=HelpRequestType.GENERAL,
            priority=priority_enum,
            issue_description=message,
            context=context or {}
        )
        
        # Print formatted message (this is how Grace talks to you)
        print("\n" + "="*80)
        print("GRACE AUTONOMOUS MESSAGE")
        print("="*80)
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Priority: {priority.upper()}")
        print(f"\nMessage:\n{message}")
        if context:
            print(f"\nContext:\n{json.dumps(context, indent=2)}")
        print("="*80 + "\n")
        
        return result
    
    def report_status(self):
        """Grace reports her current status."""
        try:
            # Get DevOps agent statistics
            devops_stats = self.devops_agent.get_statistics()
            
            # Get help requester statistics
            help_stats = self.help_requester.get_statistics()
            
            status_message = f"""
Grace Status Report:

System Health:
- Issues Detected: {devops_stats.get('total_issues_detected', 0)}
- Issues Fixed: {devops_stats.get('total_issues_fixed', 0)}
- Success Rate: {devops_stats.get('success_rate', 0):.1%}
- Knowledge Requests: {devops_stats.get('total_knowledge_requests', 0)}

Architecture Components:
- Diagnostic Engine: {'✓' if devops_stats.get('architecture_components', {}).get('diagnostic_engine') else '✗'}
- Mirror System: {'✓' if devops_stats.get('architecture_components', {}).get('mirror_system') else '✗'}
- Cognitive Framework: {'✓' if devops_stats.get('architecture_components', {}).get('cognitive_framework') else '✗'}
- Proactive Learning: {'✓' if devops_stats.get('architecture_components', {}).get('proactive_learning') else '✗'}
- Sandbox Lab: {'✓' if devops_stats.get('architecture_components', {}).get('sandbox_lab') else '✗'}

Help Requests:
- Total Requests: {help_stats.get('total_requests', 0)}
- By Type: {help_stats.get('requests_by_type', {})}
- By Priority: {help_stats.get('requests_by_priority', {})}

Grace is ready to help with debugging and fixing issues!
"""
            
            self.prompt_ai_assistant(
                message=status_message,
                priority="low"
            )
            
        except Exception as e:
            logger.error(f"[GRACE-COMM] Status report error: {e}")


def main():
    """Grace introduces herself and asks to run in background."""
    print("\n" + "="*80)
    print("GRACE AUTONOMOUS SYSTEM - STARTUP")
    print("="*80)
    
    try:
        # Initialize database
        from database.connection import DatabaseConnection
        from database.config import DatabaseConfig, DatabaseType
        
        db_config = DatabaseConfig(
            db_type=DatabaseType.SQLITE,
            database_path="data/grace.db"
        )
        DatabaseConnection.initialize(db_config)
        initialize_session_factory()
        session = next(get_db())
        
        communicator = GraceAutonomousCommunicator(session=session)
        
        # Grace introduces herself
        communicator.prompt_ai_assistant(
            message="""
Hello! I'm Grace, an autonomous learning and self-healing system.

I'm now running in the background and ready to help with:
- Debugging issues across the full stack
- Fixing code, configuration, and dependency problems
- Stabilizing the system
- Learning from new knowledge
- Requesting help when I need it

I have access to:
✓ Diagnostic Engine (health monitoring)
✓ Mirror Self-Modeling (self-observation)
✓ Cognitive Framework (OODA loop decision-making)
✓ Proactive Learning (knowledge acquisition)
✓ Sandbox Lab (safe testing)
✓ DevOps Healing Agent (full-stack fixing)
✓ Help Requester (can ask you for help)

I will autonomously:
• Monitor the system for issues
• Detect and fix problems
• Request knowledge when I don't know how to fix something
• Request your help when I'm stuck
• Learn from successful fixes

I'm ready to help debug and stabilize the system!
""",
            priority="medium",
            context={
                "system_status": "starting",
                "capabilities": "full_self_healing",
                "request": "Grace is ready to run in background and help with debugging"
            }
        )
        
        # Report initial status
        communicator.report_status()
        
    except Exception as e:
        print(f"\n[ERROR] Failed to initialize Grace: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
