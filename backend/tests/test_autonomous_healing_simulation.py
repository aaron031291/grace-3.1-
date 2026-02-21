"""Simulation mode sanity checks for AutonomousHealingSystem."""

from pathlib import Path

from cognitive.autonomous_healing_system import (
    AutonomousHealingSystem,
    HealingAction,
    TrustLevel,
)


def test_simulation_mode_stubbed_actions():
    system = AutonomousHealingSystem(
        session=None,
        repo_path=Path("."),
        trust_level=TrustLevel.MEDIUM_RISK_AUTO,
        enable_learning=False,
        simulation_mode=True,
    )

    anomaly = {"type": HealingAction.CACHE_FLUSH, "evidence": ["FILE-123"]}
    actions = [
        HealingAction.BUFFER_CLEAR,
        HealingAction.CACHE_FLUSH,
        HealingAction.CONNECTION_RESET,
        HealingAction.PROCESS_RESTART,
        HealingAction.SERVICE_RESTART,
        HealingAction.STATE_ROLLBACK,
        HealingAction.ISOLATION,
        HealingAction.EMERGENCY_SHUTDOWN,
    ]

    for action in actions:
        result = system._execute_action(action.value, anomaly, user_id="test-user")
        assert result["status"] == "simulated"
        assert result["mode"] == "simulate"
        assert result["action"] == action.value


if __name__ == "__main__":
    test_simulation_mode_stubbed_actions()
    print("OK")
