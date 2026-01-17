#!/usr/bin/env python3
"""
Check Sandbox Uptime - Self-Healing and Coding Agent

Shows how long sandbox instances have been running.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

def format_uptime(seconds):
    """Format uptime in human-readable format."""
    if seconds < 60:
        return f"{int(seconds)} seconds"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        return f"{hours} hour{'s' if hours != 1 else ''} {minutes} minute{'s' if minutes != 1 else ''}"
    else:
        days = int(seconds / 86400)
        hours = int((seconds % 86400) / 3600)
        return f"{days} day{'s' if days != 1 else ''} {hours} hour{'s' if hours != 1 else ''}"

def check_sandbox_uptime():
    """Check sandbox instance uptime."""
    try:
        from backend.database.session import get_session
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
            instances = status.get("sandbox_instances", {})
            
            print("=" * 80)
            print("SANDBOX INSTANCE UPTIME - Self-Healing & Coding Agent")
            print("=" * 80)
            print()
            print(f"Checked at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print()
            
            if not instances:
                print("No sandbox instances currently running.")
                print()
                print("Note: Sandbox instances run continuously and don't have time limits.")
                print("They will continue running until manually stopped.")
                return
            
            print(f"Active Sandbox Instances: {len(instances)}")
            print()
            
            for instance_id, instance_data in instances.items():
                instance_type = instance_data.get("type", "unknown")
                problem_perspective = instance_data.get("problem_perspective", "unknown")
                state = instance_data.get("state", "unknown")
                uptime_seconds = instance_data.get("uptime_seconds", 0)
                files_processed = instance_data.get("files_processed", 0)
                files_fixed = instance_data.get("files_fixed", 0)
                
                print(f"[{instance_id}]")
                print(f"  Type: {instance_type}")
                print(f"  Domain: {problem_perspective}")
                print(f"  State: {state}")
                print(f"  Uptime: {format_uptime(uptime_seconds)}")
                print(f"  Files Processed: {files_processed}")
                print(f"  Files Fixed: {files_fixed}")
                print()
            
            # Check for experiments in sandbox
            try:
                experiments = sandbox_lab.list_experiments(status="sandbox")
                if experiments:
                    print("=" * 80)
                    print("EXPERIMENTS IN SANDBOX")
                    print("=" * 80)
                    print()
                    print(f"Experiments in SANDBOX status: {len(experiments)}")
                    print()
                    print("Note: Experiments don't have time limits in SANDBOX.")
                    print("They move to TRIAL (90-day trial) when trust score >= 0.6")
                    print()
                    
                    for exp in experiments[:5]:  # Show first 5
                        trust_score = exp.current_trust_score
                        can_enter_trial = exp.can_enter_trial()
                        sandbox_started = exp.sandbox_started_at
                        
                        if sandbox_started:
                            sandbox_uptime = (datetime.now() - sandbox_started).total_seconds()
                            print(f"  - {exp.name or exp.experiment_id}")
                            print(f"    Trust Score: {trust_score:.2f} (need 0.6 for trial)")
                            print(f"    Time in Sandbox: {format_uptime(sandbox_uptime)}")
                            print(f"    Can Enter Trial: {'Yes' if can_enter_trial else 'No'}")
                            print()
                        else:
                            print(f"  - {exp.name or exp.experiment_id}")
                            print(f"    Trust Score: {trust_score:.2f} (need 0.6 for trial)")
                            print(f"    Can Enter Trial: {'Yes' if can_enter_trial else 'No'}")
                            print()
            except Exception as e:
                print(f"Could not check experiments: {e}")
            
            print("=" * 80)
            print("SUMMARY")
            print("=" * 80)
            print()
            print("Sandbox Training Instances:")
            print("  - Run continuously (no time limit)")
            print("  - Track uptime and performance")
            print("  - Can be stopped manually")
            print()
            print("Sandbox Lab Experiments:")
            print("  - No time limit in SANDBOX stage")
            print("  - Move to TRIAL when trust score >= 0.6")
            print("  - TRIAL stage has 90-day duration")
            print()
            
        except Exception as e:
            print(f"Error checking sandbox status: {e}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"Error initializing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_sandbox_uptime()
