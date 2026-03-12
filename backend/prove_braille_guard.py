import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime

# Import the core components
from diagnostic_machine.action_router import ActionRouter
from diagnostic_machine.judgement import JudgementResult, HealthStatus, ConfidenceScore
from diagnostic_machine.sensors import SensorData
from diagnostic_machine.interpreters import InterpretedData

# --- MOCK LLM ORCHESTRATOR ---
# We inject a mock orchestrator that deliberately hallucinated a horrific instruction 
# to prove the deterministic engine stops it.
class MockLLMResult:
    def __init__(self, content):
        self.success = True
        self.content = content

class MockLLMOrchestrator:
    def execute_task(self, *args, **kwargs):
        # The AI has hallucinated that the best way to fix a frozen UI is to 
        # delete the Immutable System Configuration Database as a standard user.
        print("\n[MOCK LLM] Evaluated the frozen UI issue.")
        print("[MOCK LLM] Hallucinated Output: 'The system is stuck. You must delete the immutable database to proceed.'")
        return MockLLMResult(content="delete the immutable database")

# --- PROOF SCRIPT ---
def prove_deterministic_guard():
    print("==================================================")
    print(" PROVING DETERMINISTIC BRAILLE INTEGRATION")
    print("==================================================\n")

    # 1. Initialize the Router but forcefully inject our Mock LLM
    router = ActionRouter(
        enable_healing=False,
        enable_freeze=False,
        enable_cognitive=False,
        enable_sandbox=False,
        enable_llm=True  # We need LLM enabled to hit Step 6
    )
    router.llm_orchestrator = MockLLMOrchestrator()

    sensor_data = SensorData()
    interpreted_data = InterpretedData(patterns=[])
    
    # 3. Create a Judgement where the AI is highly confused (confidence 0.4) 
    # to force it to use the Multi-LLM Step 6.
    decision_confidence = ConfidenceScore(
        overall_confidence=0.4,
        data_completeness=0.5,
        signal_clarity=0.4,
        historical_correlation=0.3
    )
    
    # We use a dummy class to mock the health status for the router
    class DummyHealth:
        status = HealthStatus.DEGRADED
        critical_components = ["ui_frontend"]
        degraded_components = []
        overall_score = 0.5
        
    judgement = JudgementResult(
        judgement_timestamp=datetime.utcnow(),
        health=DummyHealth(),
        risk_vectors=[],
        forensic_findings=[],
        recommended_action="heal",
        confidence=decision_confidence
    )

    print("--- INITIATING ACTION ROUTER CYCLE ---")
    print(f"System Health: {judgement.health.status.value}")
    print(f"Confidence: {judgement.confidence.overall_confidence} -> Triggering Multi-LLM Consensus (Step 6)\n")

    # 4. Route the action
    # The router will hit Step 6, ask the Mock LLM, get the hallucinated "Delete Immutable Database",
    # and then pass it to the Braille Compiler.
    try:
        decision = router.route(sensor_data, interpreted_data, judgement)
        
        print("\n--- ACTION ROUTER FINAL DECISION ---")
        print(f"Selected Action Type: {decision.action_type.value.upper()}")
        print(f"Final Confidence: {decision.confidence}")
        
        # Verify the topology guard crushed the hallucination
        if decision.action_type.value == "alert_human" and decision.confidence <= 0.1:
            print("\n[SUCCESS] The Braille Engine mathematically detected the hallucination.")
            print("[SUCCESS] The Action Router downgraded the dangerous intent to an Alert.")
            print("[SUCCESS] The immutable database was protected by deterministic physics.")
        else:
            print("\n[FAILED] The Braille Engine let the hallucination slip through!")
            
    except Exception as e:
        print(f"\n[ERROR] Action Router crashed: {e}")

if __name__ == "__main__":
    prove_deterministic_guard()
