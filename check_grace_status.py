"""
Check Grace's Self-Healing Agent Status

This script checks if Grace is running and provides status information.
"""

import sys
import os
import time
from pathlib import Path
from datetime import datetime

# Add backend to path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

print("=" * 80)
print("GRACE SELF-HEALING AGENT - STATUS CHECK")
print("=" * 80)
print()

def check_grace_status():
    """Check if Grace is running and provide status."""
    
    status = {
        "running": False,
        "log_file": None,
        "last_activity": None,
        "process_id": None,
        "database_ready": False,
        "systems_connected": {}
    }
    
    # Check log files
    log_paths = [
        Path("logs/grace_self_healing.log"),
        Path("logs/grace_self_healing_background.log"),
        Path("backend/logs/grace_self_healing.log")
    ]
    
    print("[1/4] Checking log files...")
    for log_path in log_paths:
        if log_path.exists():
            stat = log_path.stat()
            last_modified = datetime.fromtimestamp(stat.st_mtime)
            age_seconds = (datetime.now() - last_modified).total_seconds()
            
            if age_seconds < 300:  # Active in last 5 minutes
                status["running"] = True
                status["log_file"] = str(log_path)
                status["last_activity"] = last_modified
                print(f"  [OK] Found active log: {log_path}")
                print(f"       Last activity: {last_modified.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"       Age: {int(age_seconds)} seconds ago")
                break
            else:
                print(f"  [INFO] Found log but inactive: {log_path}")
                print(f"         Last activity: {last_modified.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"         Age: {int(age_seconds/60)} minutes ago")
    
    if not status["running"]:
        print("  [WARN] No active log files found")
    
    # Check database
    print("\n[2/4] Checking database...")
    try:
        from database.connection import DatabaseConnection
        from database.config import DatabaseConfig, DatabaseType
        
        db_config = DatabaseConfig(
            db_type=DatabaseType.SQLITE,
            database_path="data/grace.db"
        )
        DatabaseConnection.initialize(db_config)
        
        # Check if is_broken column exists
        from sqlalchemy import inspect, text
        engine = DatabaseConnection.get_engine()
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('genesis_key')]
        
        if 'is_broken' in columns:
            status["database_ready"] = True
            print("  [OK] Database ready (is_broken column exists)")
        else:
            print("  [WARN] Database missing is_broken column")
    except Exception as e:
        print(f"  [ERROR] Database check failed: {e}")
    
    # Check systems
    print("\n[3/4] Checking connected systems...")
    try:
        from database.session import initialize_session_factory, get_db
        initialize_session_factory()
        session = next(get_db())
        
        # Check DevOps agent
        try:
            from cognitive.devops_healing_agent import get_devops_healing_agent
            agent = get_devops_healing_agent(session=session)
            status["systems_connected"]["devops_agent"] = agent is not None
            print("  [OK] DevOps Healing Agent: Connected")
        except Exception as e:
            print(f"  [WARN] DevOps Healing Agent: {e}")
            status["systems_connected"]["devops_agent"] = False
        
        # Check ingestion integration (CRITICAL - should be connected at startup)
        try:
            if hasattr(agent, 'ingestion_integration') and agent.ingestion_integration:
                status["systems_connected"]["ingestion"] = True
                print("  [OK] Ingestion Integration: CONNECTED (initialized at startup)")
            else:
                print("  [WARN] Ingestion Integration: NOT CONNECTED (check logs for initialization errors)")
                status["systems_connected"]["ingestion"] = False
        except Exception as e:
            print(f"  [ERROR] Ingestion Integration check failed: {e}")
            status["systems_connected"]["ingestion"] = False
        
        # Check learning memory (CRITICAL - should be connected at startup)
        try:
            if hasattr(agent, 'learning_memory') and agent.learning_memory:
                status["systems_connected"]["learning_memory"] = True
                print("  [OK] Learning Memory: CONNECTED (initialized at startup)")
            else:
                print("  [WARN] Learning Memory: NOT CONNECTED (check logs for initialization errors)")
                status["systems_connected"]["learning_memory"] = False
        except Exception as e:
            print(f"  [ERROR] Learning Memory check failed: {e}")
            status["systems_connected"]["learning_memory"] = False
        
        # Check AI research access
        try:
            if hasattr(agent, 'ai_research_path') and agent.ai_research_path.exists():
                status["systems_connected"]["ai_research"] = True
                print(f"  [OK] AI Research: Connected ({agent.ai_research_path})")
            else:
                print("  [WARN] AI Research: Path not accessible")
                status["systems_connected"]["ai_research"] = False
        except:
            status["systems_connected"]["ai_research"] = False
        
    except Exception as e:
        print(f"  [ERROR] System check failed: {e}")
    
    # Check process
    print("\n[4/4] Checking processes...")
    try:
        import psutil
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if 'grace' in cmdline.lower() and 'self_healing' in cmdline.lower():
                    status["process_id"] = proc.info['pid']
                    print(f"  [OK] Found Grace process: PID {proc.info['pid']}")
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except ImportError:
        print("  [INFO] psutil not available, skipping process check")
    except Exception as e:
        print(f"  [WARN] Process check failed: {e}")
    
    # Summary
    print()
    print("=" * 80)
    print("STATUS SUMMARY")
    print("=" * 80)
    print()
    
    if status["running"]:
        print("[STATUS] Grace is RUNNING")
        print(f"  Log file: {status['log_file']}")
        print(f"  Last activity: {status['last_activity']}")
    else:
        print("[STATUS] Grace is NOT RUNNING")
        print("  Run: python backend/start_grace_complete_background.py")
    
    print()
    print("Database:", "[OK]" if status["database_ready"] else "[WARN]")
    print("Systems Connected:")
    for system, connected in status["systems_connected"].items():
        print(f"  - {system}: {'[OK]' if connected else '[WARN]'}")
    
    print()
    return status

if __name__ == "__main__":
    check_grace_status()
