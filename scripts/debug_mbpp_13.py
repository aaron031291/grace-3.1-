#!/usr/bin/env python3
"""Debug script for mbpp_13 problem."""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from backend.database.connection import DatabaseConnection, DatabaseConfig, DatabaseType
from backend.database.session import initialize_session_factory, get_session
from backend.cognitive.enterprise_coding_agent import get_enterprise_coding_agent, CodingTaskType
from backend.cognitive.autonomous_healing_system import TrustLevel
from backend.benchmarking.mbpp_expanded_sample import MBPP_EXPANDED_PROBLEMS

# Initialize database
db_config = DatabaseConfig(
    db_type=DatabaseType.SQLITE,
    database="grace",
    database_path=str(project_root / "data" / "grace.db"),
    echo=False,
)
DatabaseConnection.initialize(db_config)
initialize_session_factory()

# Initialize coding agent
session = next(get_session())
coding_agent = get_enterprise_coding_agent(
    session=session,
    repo_path=Path.cwd(),
    trust_level=TrustLevel.MEDIUM_RISK_AUTO,
    enable_learning=True,
    enable_sandbox=True
)

# Get mbpp_13 problem
problem = MBPP_EXPANDED_PROBLEMS[8]  # mbpp_13
print("Problem:", problem["text"])
print()

# Create task
task = coding_agent.create_task(
    task_type=CodingTaskType.CODE_GENERATION,
    description=problem["text"]
)

# Execute task
execution_result = coding_agent.execute_task(task.task_id)

if execution_result.get("success"):
    generation = execution_result.get("result", {}).get("generation")
    if generation:
        code = generation.code_after if hasattr(generation, 'code_after') else str(generation)
        print("Generated Code:")
        print("=" * 80)
        print(code)
        print("=" * 80)
        print()
        print("Expected Code:")
        print("=" * 80)
        print(problem["code"])
        print("=" * 80)
    else:
        print("No generation found")
else:
    print("Task execution failed:", execution_result.get("error"))
