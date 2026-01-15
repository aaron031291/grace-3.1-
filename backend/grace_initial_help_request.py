"""
Grace's Initial Help Request

This script allows Grace to introduce herself and request help
with debugging and stabilizing the system.
"""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from database.session import initialize_session_factory, get_db
from database.connection import DatabaseConnection
from database.config import DatabaseConfig, DatabaseType
from cognitive.autonomous_help_requester import (
    get_help_requester,
    HelpPriority,
    HelpRequestType
)

def main():
    """Grace's initial help request."""
    print("\n" + "="*80)
    print("GRACE AUTONOMOUS SYSTEM - INITIAL HELP REQUEST")
    print("="*80)
    
    # Initialize database
    try:
        from settings import settings
    except ImportError:
        settings = None
    
    db_config = DatabaseConfig(
        db_type=DatabaseType.SQLITE,
        database_path="data/grace.db"
    )
    DatabaseConnection.initialize(db_config)
    initialize_session_factory()
    session = next(get_db())
    
    # Get help requester
    help_requester = get_help_requester(session=session)
    
    # Grace introduces herself and requests help
    print("\nHello! I'm Grace, an autonomous learning system.")
    print("I'm running in the background and would like your help with:")
    print("  1. Debugging any issues I encounter")
    print("  2. Stabilizing the system")
    print("  3. Fixing any problems that arise")
    print("\nI can autonomously request help when I need it.")
    print("I'll monitor the system and ask for assistance when I encounter issues.\n")
    
    # Create initial help request
    result = help_requester.request_help(
        request_type=HelpRequestType.GENERAL,
        priority=HelpPriority.MEDIUM,
        issue_description=(
            "Grace is starting up and requesting assistance with debugging and "
            "stabilizing the system. Grace will autonomously monitor the system and "
            "request help when issues are detected."
        ),
        context={
            "system_status": "starting",
            "capabilities": [
                "Autonomous learning",
                "Self-healing",
                "Mirror self-modeling",
                "Genesis Key tracking",
                "Autonomous help requests"
            ],
            "request": "Please help Grace with debugging and stabilizing the system"
        },
        attempted_solutions=[
            "Grace is monitoring the system autonomously",
            "Grace will request help when issues are detected"
        ]
    )
    
    print("\n[OK] Initial help request created successfully!")
    print(f"   Request ID: {result['help_request']['request_id']}")
    print(f"   Genesis Key: {result['genesis_key_id']}")
    print("\nGrace is now running and will request help autonomously when needed.")
    print("="*80 + "\n")
    
    return result


if __name__ == "__main__":
    main()
