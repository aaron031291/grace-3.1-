"""Start Grace's autonomous learning system directly."""

import sys
sys.path.insert(0, 'backend')

from cognitive.learning_subagent_system import LearningOrchestrator
from genesis.autonomous_triggers import get_genesis_trigger_pipeline
from database.session import initialize_session_factory
from settings import KNOWLEDGE_BASE_PATH
from pathlib import Path

print("[STARTUP] Starting Grace's Autonomous Learning System...")

# Initialize session
session_factory = initialize_session_factory()
session = session_factory()

# Create orchestrator
print("[STARTUP] Creating Learning Orchestrator (8 processes)...")
orchestrator = LearningOrchestrator(
    knowledge_base_path=KNOWLEDGE_BASE_PATH,
    num_study_agents=3,
    num_practice_agents=2
)

# Connect trigger pipeline
print("[STARTUP] Connecting Genesis Key Trigger Pipeline...")
trigger_pipeline = get_genesis_trigger_pipeline(
    session=session,
    knowledge_base_path=Path(KNOWLEDGE_BASE_PATH),
    orchestrator=orchestrator
)

# Start the system
print("[STARTUP] Starting all subagents...")
orchestrator.start()

print("\n✅✅✅ GRACE IS NOW AUTONOMOUSLY LEARNING! ✅✅✅\n")
print("System Status:")
status = orchestrator.get_status()
for key, value in status.items():
    print(f"  {key}: {value}")

print("\nTrigger Pipeline Status:")
trigger_status = trigger_pipeline.get_status()
for key, value in trigger_status.items():
    print(f"  {key}: {value}")

print("\n[RUNNING] Grace is learning autonomously in the background.")
print("[RUNNING] Add files to backend/knowledge_base/ and Grace will learn automatically!")
print("\n[PRESS CTRL+C TO STOP]")

try:
    import time
    while True:
        time.sleep(10)
        # Print status every 10 seconds
        status = orchestrator.get_status()
        print(f"\r[STATUS] Tasks: {status.get('total_tasks_completed', 0)} completed, "
              f"Queues: Study={status.get('study_queue_size', 0)}, "
              f"Practice={status.get('practice_queue_size', 0)}   ", end='')
except KeyboardInterrupt:
    print("\n\n[SHUTDOWN] Stopping Grace...")
    orchestrator.stop()
    print("[SHUTDOWN] Grace stopped gracefully.")
