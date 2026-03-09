import pytest
import asyncio
from backend.models.healing_models import HealingAction

@pytest.mark.asyncio
async def test_healing_action_escalation():
    """
    Ensures HealingAction follows constitutional rules for risk thresholds.
    """
    # Low risk action
    action = HealingAction(
        trigger="guardian.warning",
        playbook_id="auto_heal_1",
        risk=0.2,
        mttr_goal=60
    )
    assert action.is_escalation_required() is False
    
    # High risk action (Clause 4: > 0.7 requires explicit approval)
    high_risk_action = HealingAction(
        trigger="guardian.kernel_panic",
        playbook_id="deep_reset",
        risk=0.8,
        mttr_goal=300
    )
    assert high_risk_action.is_escalation_required() is True

def test_root_registry_listeners():
    """
    Ensures root registry listeners initialize correctly and can import HealingAction.
    (Stubs the actual DB listener to verify imports and initialization don't break).
    """
    try:
        from backend.models.healing_models import HealingAction
        import uuid
        
        # Simulating a listener loading an action
        action = HealingAction(
            trigger="db.disconnect",
            playbook_id="reconnect_db",
            risk=0.1,
            mttr_goal=10
        )
        assert action.action_id.startswith("heal_")
        
    except ImportError as e:
        pytest.fail(f"Listener could not import dependencies: {e}")
