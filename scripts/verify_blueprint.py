import sys
from pathlib import Path

# Add project root to sys.path so backend modules can be resolved
sys.path.append(str(Path(__file__).parent.parent))

from backend.core.clarity_framework import ClarityFramework
from backend.constitutional.grace_charter import GraceCharter
from backend.models.healing_models import HealingAction

print("=== Testing Clarity Framework ===")
decision = ClarityFramework.record_decision(
    what="Testing the Clarity Log",
    why="Verification of Blueprint Component",
    who={"actor": "tester", "service": "manual"},
    where={"subsystem": "verification_script", "env": "local"},
    how={"playbook": "verify_all"},
    risk_score=0.1
)
print("Decision ID generated:", decision.id)

print("\n=== Testing Grace Charter ===")
constitution = GraceCharter.get_constitution()
print("Constitution Version:", constitution.version)
print("Number of Pillars Loaded:", len(constitution.pillars))
print("Pillar 1 Name:", constitution.pillars[0].name)
print("Risk 0.5 Acceptable?", GraceCharter.is_risk_acceptable(0.5))
print("Risk 0.8 Acceptable?", GraceCharter.is_risk_acceptable(0.8))

print("\n=== Testing HealingAction ===")
heal = HealingAction(
    trigger="High Latency",
    playbook_id="restart_api",
    risk=0.8,
    mttr_goal=60
)
print("Heal Action ID:", heal.action_id)
print("Escalation Required?", heal.is_escalation_required())

print("\n✅ All imports and models validated successfully.")
