#!/usr/bin/env python3
"""
Check System Status - Sandbox, Self-Healing, and Coding Agent

Verifies that all systems are running and operational.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from datetime import datetime
from typing import Dict, Any, Optional


def initialize_database():
    """Initialize database connection."""
    try:
        from backend.database.connection import DatabaseConnection, DatabaseConfig, DatabaseType
        from backend.config import settings
        
        db_type = DatabaseType(settings.DATABASE_TYPE) if settings else DatabaseType.SQLITE
        db_config = DatabaseConfig(
            db_type=db_type,
            host=settings.DATABASE_HOST if settings else None,
            port=settings.DATABASE_PORT if settings else None,
            username=settings.DATABASE_USER if settings else None,
            password=settings.DATABASE_PASSWORD if settings else None,
            database=settings.DATABASE_NAME if settings else "grace",
            database_path=settings.DATABASE_PATH if settings else None,
            echo=settings.DATABASE_ECHO if settings else False,
        )
        DatabaseConnection.initialize(db_config)
        
        from backend.database.session import initialize_session_factory
        initialize_session_factory()
        
        return True
    except Exception as e:
        print(f"WARNING: Could not initialize database: {e}")
        return False


def check_sandbox_status():
    """Check if sandbox training system is running."""
    try:
        try:
            from backend.database.session import get_session
        except ImportError:
            from database.session import get_session
        from pathlib import Path
        from cognitive.multi_instance_training import get_multi_instance_training_system
        
        session = next(get_session())
        kb_path = Path("knowledge_base")
        
        # Try to get multi-instance training system
        try:
            from cognitive.self_healing_training_system import get_self_healing_training_system
            from cognitive.autonomous_sandbox_lab import get_sandbox_lab
            from cognitive.autonomous_healing_system import get_autonomous_healing, TrustLevel
            from diagnostic_machine.diagnostic_engine import get_diagnostic_engine
            from llm_orchestrator.llm_orchestrator import get_llm_orchestrator
            
            sandbox_lab = get_sandbox_lab()
            healing_system = get_autonomous_healing(session=session, trust_level=TrustLevel.MEDIUM_RISK_AUTO)
            diagnostic_engine = get_diagnostic_engine()
            llm_orchestrator = get_llm_orchestrator(session=session, knowledge_base_path=kb_path)
            
            training_system = get_self_healing_training_system(
                session=session,
                knowledge_base_path=kb_path,
                sandbox_lab=sandbox_lab,
                healing_system=healing_system,
                diagnostic_engine=diagnostic_engine,
                llm_orchestrator=llm_orchestrator
            )
            
            # Get multi-instance system
            multi_instance = get_multi_instance_training_system(
                base_training_system=training_system,
                diagnostic_engine=diagnostic_engine,
                healing_system=healing_system,
                llm_orchestrator=llm_orchestrator
            )
            
            status = multi_instance.get_instance_status()
            
            return {
                "status": "running",
                "instances": status.get("instances", {}),
                "total_instances": len(status.get("instances", {})),
                "active_instances": sum(1 for inst in status.get("instances", {}).values() if inst.get("state") == "running"),
                "details": status
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": "Could not check sandbox status"
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": "Could not initialize sandbox check"
        }


def check_self_healing_status():
    """Check if self-healing system is running."""
    try:
        try:
            from backend.database.session import get_session
        except ImportError:
            from database.session import get_session
        from cognitive.autonomous_healing_system import get_autonomous_healing, TrustLevel
        
        session = next(get_session())
        healing_system = get_autonomous_healing(
            session=session,
            trust_level=TrustLevel.MEDIUM_RISK_AUTO,
            enable_learning=True
        )
        
        # Get system status
        status = healing_system.get_system_status()
        health = healing_system.assess_system_health()
        
        return {
            "status": "running",
            "trust_level": status.get("trust_level", "unknown"),
            "learning_enabled": status.get("learning_enabled", False),
            "current_health": status.get("current_health", "unknown"),
            "anomalies_active": status.get("anomalies_active", 0),
            "health_status": health.get("health_status", "unknown"),
            "details": status
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": "Could not check self-healing status"
        }


def check_coding_agent_status():
    """Check if coding agent is running."""
    try:
        try:
            from backend.database.session import get_session
        except ImportError:
            from database.session import get_session
        from cognitive.enterprise_coding_agent import get_enterprise_coding_agent
        from cognitive.autonomous_healing_system import TrustLevel
        from pathlib import Path
        
        session = next(get_session())
        coding_agent = get_enterprise_coding_agent(
            session=session,
            repo_path=Path.cwd(),
            trust_level=TrustLevel.MEDIUM_RISK_AUTO,
            enable_learning=True,
            enable_sandbox=True
        )
        
        # Get health status
        health = coding_agent.get_health_status()
        metrics = coding_agent.get_metrics()
        
        return {
            "status": "running",
            "state": health.get("state", "unknown"),
            "learning_enabled": health.get("learning_enabled", False),
            "sandbox_available": health.get("sandbox_available", False),
            "total_tasks": metrics.total_tasks,
            "tasks_completed": metrics.tasks_completed,
            "learning_cycles": metrics.learning_cycles,
            "details": health
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": "Could not check coding agent status"
        }


def display_status():
    """Display system status."""
    print("=" * 80)
    print("GRACE SYSTEM STATUS CHECK")
    print("=" * 80)
    print()
    print(f"Checked at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Initialize database first
    print("Initializing database...")
    if not initialize_database():
        print("WARNING: Database initialization failed. Some checks may fail.")
    print()
    
    # Check Sandbox
    print("[SANDBOX TRAINING SYSTEM]")
    print("-" * 80)
    sandbox_status = check_sandbox_status()
    if sandbox_status["status"] == "running":
        print("Status: RUNNING")
        print(f"Total Instances: {sandbox_status.get('total_instances', 0)}")
        print(f"Active Instances: {sandbox_status.get('active_instances', 0)}")
        instances = sandbox_status.get("instances", {})
        if instances:
            print("\nInstance Details:")
            for inst_id, inst_data in instances.items():
                print(f"  - {inst_id}: {inst_data.get('state', 'unknown')}")
    elif sandbox_status["status"] == "error":
        print("Status: ERROR")
        print(f"Error: {sandbox_status.get('error', 'Unknown error')}")
    else:
        print("Status: UNKNOWN")
    print()
    
    # Check Self-Healing
    print("[SELF-HEALING SYSTEM]")
    print("-" * 80)
    healing_status = check_self_healing_status()
    if healing_status["status"] == "running":
        print("Status: RUNNING")
        print(f"Trust Level: {healing_status.get('trust_level', 'unknown')}")
        print(f"Learning Enabled: {healing_status.get('learning_enabled', False)}")
        print(f"Current Health: {healing_status.get('current_health', 'unknown')}")
        print(f"Health Status: {healing_status.get('health_status', 'unknown')}")
        print(f"Active Anomalies: {healing_status.get('anomalies_active', 0)}")
    elif healing_status["status"] == "error":
        print("Status: ERROR")
        print(f"Error: {healing_status.get('error', 'Unknown error')}")
    else:
        print("Status: UNKNOWN")
    print()
    
    # Check Coding Agent
    print("[CODING AGENT]")
    print("-" * 80)
    coding_status = check_coding_agent_status()
    if coding_status["status"] == "running":
        print("Status: RUNNING")
        print(f"State: {coding_status.get('state', 'unknown')}")
        print(f"Learning Enabled: {coding_status.get('learning_enabled', False)}")
        print(f"Sandbox Available: {coding_status.get('sandbox_available', False)}")
        print(f"Total Tasks: {coding_status.get('total_tasks', 0)}")
        print(f"Tasks Completed: {coding_status.get('tasks_completed', 0)}")
        print(f"Learning Cycles: {coding_status.get('learning_cycles', 0)}")
    elif coding_status["status"] == "error":
        print("Status: ERROR")
        print(f"Error: {coding_status.get('error', 'Unknown error')}")
    else:
        print("Status: UNKNOWN")
    print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    all_running = (
        sandbox_status["status"] == "running" and
        healing_status["status"] == "running" and
        coding_status["status"] == "running"
    )
    
    if all_running:
        print("ALL SYSTEMS OPERATIONAL")
        print()
        print("Sandbox: RUNNING")
        print("Self-Healing: RUNNING")
        print("Coding Agent: RUNNING")
        print()
        print("Everything is running as it should be!")
    else:
        print("SOME SYSTEMS HAVE ISSUES")
        print()
        if sandbox_status["status"] != "running":
            print("Sandbox: ISSUE")
        else:
            print("Sandbox: OK")
        
        if healing_status["status"] != "running":
            print("Self-Healing: ISSUE")
        else:
            print("Self-Healing: OK")
        
        if coding_status["status"] != "running":
            print("Coding Agent: ISSUE")
        else:
            print("Coding Agent: OK")
    
    print()
    print("=" * 80)


if __name__ == "__main__":
    display_status()
