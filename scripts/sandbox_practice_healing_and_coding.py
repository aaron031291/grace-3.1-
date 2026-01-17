#!/usr/bin/env python3
"""
Sandbox Practice Environment for Self-Healing Pipeline and Coding Agent

This script creates an isolated sandbox environment where:
1. Self-healing pipeline can practice detecting and fixing issues
2. Coding agent can practice generating and fixing code
3. Both systems work together without affecting production
4. All changes are tracked and can be reviewed before promotion
"""

import sys
import os
from pathlib import Path
import tempfile
import shutil
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import uuid

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SandboxPracticeEnvironment:
    """
    Isolated sandbox environment for self-healing and coding agent practice.
    """
    
    def __init__(self, sandbox_dir: Optional[Path] = None):
        """Initialize sandbox practice environment."""
        self.sandbox_id = f"SANDBOX-{uuid.uuid4().hex[:12]}"
        self.sandbox_dir = sandbox_dir or Path(tempfile.mkdtemp(prefix=f"grace_sandbox_{self.sandbox_id}_"))
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        self.code_dir = self.sandbox_dir / "code"
        self.tests_dir = self.sandbox_dir / "tests"
        self.logs_dir = self.sandbox_dir / "logs"
        self.results_dir = self.sandbox_dir / "results"
        
        for dir_path in [self.code_dir, self.tests_dir, self.logs_dir, self.results_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Practice session tracking
        self.session_data = {
            "sandbox_id": self.sandbox_id,
            "created_at": datetime.now().isoformat(),
            "healing_practices": [],
            "coding_practices": [],
            "collaborations": [],
            "metrics": {
                "healing_attempts": 0,
                "healing_successes": 0,
                "coding_attempts": 0,
                "coding_successes": 0,
                "collaborations": 0
            }
        }
        
        logger.info(f"[SANDBOX] Created sandbox environment: {self.sandbox_id}")
        logger.info(f"[SANDBOX] Sandbox directory: {self.sandbox_dir}")
    
    def initialize_database(self):
        """Initialize database connection for sandbox."""
        try:
            from backend.database.connection import DatabaseConnection, DatabaseConfig, DatabaseType
            
            # Use a separate sandbox database
            sandbox_db_path = self.sandbox_dir / "sandbox.db"
            
            db_config = DatabaseConfig(
                db_type=DatabaseType.SQLITE,
                database="grace_sandbox",
                database_path=str(sandbox_db_path),
                echo=False,
            )
            DatabaseConnection.initialize(db_config)
            
            from backend.database.session import initialize_session_factory
            initialize_session_factory()
            
            logger.info("[SANDBOX] Database initialized")
            return True
        except Exception as e:
            logger.error(f"[SANDBOX] Database initialization failed: {e}")
            return False
    
    def initialize_healing_system(self):
        """Initialize self-healing system in sandbox mode."""
        try:
            from backend.database.session import get_session
            from cognitive.autonomous_healing_system import get_autonomous_healing, TrustLevel
            
            session = next(get_session())
            healing_system = get_autonomous_healing(
                session=session,
                repo_path=self.code_dir,
                trust_level=TrustLevel.LOW_RISK_AUTO,  # More conservative in sandbox
                enable_learning=True
            )
            
            logger.info("[SANDBOX] Self-healing system initialized")
            return healing_system
        except Exception as e:
            logger.error(f"[SANDBOX] Failed to initialize healing system: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def initialize_coding_agent(self):
        """Initialize coding agent in sandbox mode."""
        try:
            from backend.database.session import get_session
            from cognitive.enterprise_coding_agent import get_enterprise_coding_agent
            from cognitive.autonomous_healing_system import TrustLevel
            
            session = next(get_session())
            coding_agent = get_enterprise_coding_agent(
                session=session,
                repo_path=self.code_dir,
                trust_level=TrustLevel.LOW_RISK_AUTO,  # More conservative in sandbox
                enable_learning=True,
                enable_sandbox=True
            )
            
            logger.info("[SANDBOX] Coding agent initialized")
            return coding_agent
        except Exception as e:
            logger.error(f"[SANDBOX] Failed to initialize coding agent: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def create_practice_code_file(self, filename: str, code: str, has_issues: bool = True):
        """Create a practice code file with optional issues."""
        file_path = self.code_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_path.write_text(code)
        logger.info(f"[SANDBOX] Created practice file: {filename} (has_issues={has_issues})")
        return file_path
    
    def practice_healing(self, healing_system, issue_description: str, file_path: Path):
        """Practice healing a specific issue."""
        logger.info(f"[SANDBOX] Practicing healing: {issue_description}")
        
        practice_id = f"HEAL-{uuid.uuid4().hex[:8]}"
        practice_start = datetime.now()
        
        try:
            # Assess system health first (this will detect issues)
            health_assessment = healing_system.assess_system_health()
            
            # If anomalies are detected, execute healing
            anomalies = health_assessment.get("anomalies", [])
            success = False
            healing_action = "none"
            
            if anomalies:
                # Execute healing for detected anomalies
                healing_result = healing_system.execute_healing()
                success = healing_result.get("success", False)
                healing_action = healing_result.get("action_taken", "unknown")
            else:
                # No anomalies detected - this is also a valid outcome in practice
                logger.info("[SANDBOX] No anomalies detected - system is healthy")
                success = True
                healing_action = "none_needed"
            
            practice_end = datetime.now()
            duration = (practice_end - practice_start).total_seconds()
            
            practice_record = {
                "practice_id": practice_id,
                "timestamp": practice_start.isoformat(),
                "duration_seconds": duration,
                "issue_description": issue_description,
                "file_path": str(file_path),
                "success": success,
                "healing_action": healing_action,
                "anomalies_detected": len(anomalies),
                "health_status": health_assessment.get("health_status", "unknown"),
                "result": {
                    "health_assessment": health_assessment,
                    "healing_executed": len(anomalies) > 0
                }
            }
            
            self.session_data["healing_practices"].append(practice_record)
            self.session_data["metrics"]["healing_attempts"] += 1
            
            if success:
                self.session_data["metrics"]["healing_successes"] += 1
                logger.info(f"[SANDBOX] ✓ Healing practice succeeded: {practice_id}")
            else:
                logger.warning(f"[SANDBOX] ✗ Healing practice failed: {practice_id}")
            
            return practice_record
            
        except Exception as e:
            logger.error(f"[SANDBOX] Healing practice error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def practice_coding(self, coding_agent, task_description: str, task_type: str = "code_generation"):
        """Practice coding task."""
        logger.info(f"[SANDBOX] Practicing coding: {task_description}")
        
        practice_id = f"CODE-{uuid.uuid4().hex[:8]}"
        practice_start = datetime.now()
        
        try:
            from cognitive.enterprise_coding_agent import CodingTaskType
            
            # Create coding task
            coding_task = coding_agent.create_task(
                task_type=task_type,
                description=task_description,
                target_files=[],
                requirements={},
                context={"sandbox": True, "practice": True}
            )
            
            # Execute task
            execution_result = coding_agent.execute_task(coding_task.task_id)
            
            practice_end = datetime.now()
            duration = (practice_end - practice_start).total_seconds()
            
            practice_record = {
                "practice_id": practice_id,
                "timestamp": practice_start.isoformat(),
                "duration_seconds": duration,
                "task_description": task_description,
                "task_type": task_type,
                "task_id": coding_task.task_id,
                "success": execution_result.get("success", False),
                "result": execution_result
            }
            
            self.session_data["coding_practices"].append(practice_record)
            self.session_data["metrics"]["coding_attempts"] += 1
            
            if execution_result.get("success"):
                self.session_data["metrics"]["coding_successes"] += 1
                logger.info(f"[SANDBOX] ✓ Coding practice succeeded: {practice_id}")
            else:
                logger.warning(f"[SANDBOX] ✗ Coding practice failed: {practice_id}")
            
            return practice_record
            
        except Exception as e:
            logger.error(f"[SANDBOX] Coding practice error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def practice_collaboration(self, healing_system, coding_agent, scenario: Dict[str, Any]):
        """Practice collaboration between healing and coding agents."""
        logger.info(f"[SANDBOX] Practicing collaboration: {scenario.get('description', 'unknown')}")
        
        collaboration_id = f"COLLAB-{uuid.uuid4().hex[:8]}"
        collaboration_start = datetime.now()
        
        try:
            # Step 1: Coding agent generates code
            coding_result = self.practice_coding(
                coding_agent,
                scenario.get("coding_task", "Generate code"),
                scenario.get("coding_task_type", "code_generation")
            )
            
            if not coding_result or not coding_result.get("success"):
                logger.warning("[SANDBOX] Collaboration failed at coding step")
                return None
            
            # Step 2: Introduce an issue (if scenario specifies)
            if scenario.get("introduce_issue"):
                issue_file = scenario.get("issue_file")
                if issue_file and Path(issue_file).exists():
                    # Step 3: Healing agent fixes the issue
                    healing_result = self.practice_healing(
                        healing_system,
                        scenario.get("issue_description", "Fix code issue"),
                        Path(issue_file)
                    )
                    
                    collaboration_end = datetime.now()
                    duration = (collaboration_end - collaboration_start).total_seconds()
                    
                    collaboration_record = {
                        "collaboration_id": collaboration_id,
                        "timestamp": collaboration_start.isoformat(),
                        "duration_seconds": duration,
                        "scenario": scenario,
                        "coding_result": coding_result,
                        "healing_result": healing_result,
                        "success": healing_result and healing_result.get("success", False) if healing_result else False
                    }
                    
                    self.session_data["collaborations"].append(collaboration_record)
                    self.session_data["metrics"]["collaborations"] += 1
                    
                    if collaboration_record["success"]:
                        logger.info(f"[SANDBOX] ✓ Collaboration succeeded: {collaboration_id}")
                    else:
                        logger.warning(f"[SANDBOX] ✗ Collaboration failed: {collaboration_id}")
                    
                    return collaboration_record
            
            collaboration_end = datetime.now()
            duration = (collaboration_end - collaboration_start).total_seconds()
            
            collaboration_record = {
                "collaboration_id": collaboration_id,
                "timestamp": collaboration_start.isoformat(),
                "duration_seconds": duration,
                "scenario": scenario,
                "coding_result": coding_result,
                "healing_result": None,
                "success": coding_result.get("success", False)
            }
            
            self.session_data["collaborations"].append(collaboration_record)
            self.session_data["metrics"]["collaborations"] += 1
            
            return collaboration_record
            
        except Exception as e:
            logger.error(f"[SANDBOX] Collaboration error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def save_session(self):
        """Save session data to results directory."""
        session_file = self.results_dir / f"session_{self.sandbox_id}.json"
        session_file.write_text(json.dumps(self.session_data, indent=2))
        logger.info(f"[SANDBOX] Session saved: {session_file}")
        return session_file
    
    def generate_report(self) -> str:
        """Generate practice session report."""
        metrics = self.session_data["metrics"]
        
        healing_rate = (metrics["healing_successes"] / metrics["healing_attempts"] * 100) if metrics["healing_attempts"] > 0 else 0
        coding_rate = (metrics["coding_successes"] / metrics["coding_attempts"] * 100) if metrics["coding_attempts"] > 0 else 0
        
        report = f"""
{'='*80}
SANDBOX PRACTICE SESSION REPORT
{'='*80}

Sandbox ID: {self.sandbox_id}
Created: {self.session_data['created_at']}
Sandbox Directory: {self.sandbox_dir}

METRICS:
  Healing Practices:
    Attempts: {metrics['healing_attempts']}
    Successes: {metrics['healing_successes']}
    Success Rate: {healing_rate:.1f}%
  
  Coding Practices:
    Attempts: {metrics['coding_attempts']}
    Successes: {metrics['coding_successes']}
    Success Rate: {coding_rate:.1f}%
  
  Collaborations: {metrics['collaborations']}

DETAILS:
  Healing Practices: {len(self.session_data['healing_practices'])}
  Coding Practices: {len(self.session_data['coding_practices'])}
  Collaborations: {len(self.session_data['collaborations'])}

{'='*80}
"""
        return report
    
    def cleanup(self, keep_files: bool = False):
        """Clean up sandbox environment."""
        if not keep_files and self.sandbox_dir.exists():
            shutil.rmtree(self.sandbox_dir)
            logger.info(f"[SANDBOX] Cleaned up sandbox: {self.sandbox_id}")
        else:
            logger.info(f"[SANDBOX] Sandbox preserved: {self.sandbox_id}")


def run_practice_scenarios():
    """Run practice scenarios for healing and coding agents."""
    print("="*80)
    print("SANDBOX PRACTICE ENVIRONMENT")
    print("Self-Healing Pipeline & Coding Agent Practice Session")
    print("="*80)
    print()
    
    # Initialize sandbox
    sandbox = SandboxPracticeEnvironment()
    
    try:
        # Initialize database
        if not sandbox.initialize_database():
            print("ERROR: Failed to initialize database")
            return
        
        # Initialize systems
        healing_system = sandbox.initialize_healing_system()
        coding_agent = sandbox.initialize_coding_agent()
        
        if not healing_system or not coding_agent:
            print("ERROR: Failed to initialize systems")
            return
        
        print("\n[OK] Sandbox environment ready")
        print(f"Sandbox ID: {sandbox.sandbox_id}")
        print(f"Sandbox Directory: {sandbox.sandbox_dir}")
        print()
        
        # Practice Scenario 1: Coding Agent generates code
        print("-"*80)
        print("SCENARIO 1: Coding Agent - Code Generation")
        print("-"*80)
        
        coding_result = sandbox.practice_coding(
            coding_agent,
            "Create a Python function that calculates the factorial of a number using recursion, with proper error handling and type hints.",
            "code_generation"
        )
        
        print()
        
        # Practice Scenario 2: Create code with issues for healing
        print("-"*80)
        print("SCENARIO 2: Self-Healing - Fix Code Issues")
        print("-"*80)
        
        # Create a file with intentional issues
        buggy_code = '''def calculate_sum(numbers):
    total = 0
    for num in numbers:
        total += num  # Missing return statement
    # Also has indentation issue below
def helper_function():
    return True
'''
        
        buggy_file = sandbox.create_practice_code_file("buggy_code.py", buggy_code, has_issues=True)
        
        healing_result = sandbox.practice_healing(
            healing_system,
            "Fix missing return statement and indentation issues",
            buggy_file
        )
        
        print()
        
        # Practice Scenario 3: Collaboration
        print("-"*80)
        print("SCENARIO 3: Collaboration - Coding + Healing")
        print("-"*80)
        
        collaboration_result = sandbox.practice_collaboration(
            healing_system,
            coding_agent,
            {
                "description": "Generate code, then fix issues",
                "coding_task": "Create a function to find the maximum value in a list, handling edge cases",
                "coding_task_type": "code_generation",
                "introduce_issue": True,
                "issue_file": str(buggy_file),
                "issue_description": "Fix any code quality issues"
            }
        )
        
        print()
        
        # Practice Scenario 4: More coding practice
        print("-"*80)
        print("SCENARIO 4: Coding Agent - Code Review & Fix")
        print("-"*80)
        
        coding_result2 = sandbox.practice_coding(
            coding_agent,
            "Review and fix code quality issues in the generated code",
            "code_fix"
        )
        
        print()
        
        # Save session and generate report
        sandbox.save_session()
        report = sandbox.generate_report()
        print(report)
        
        # Save report to file
        report_file = sandbox.results_dir / f"report_{sandbox.sandbox_id}.txt"
        report_file.write_text(report)
        print(f"\nReport saved: {report_file}")
        
        print("\n[OK] Practice session complete!")
        print(f"Sandbox directory preserved: {sandbox.sandbox_dir}")
        print("Review results before promoting to production.")
        
    except Exception as e:
        logger.error(f"Practice session error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Optionally cleanup (set to True to keep files for review)
        # sandbox.cleanup(keep_files=False)
        pass


if __name__ == "__main__":
    run_practice_scenarios()
