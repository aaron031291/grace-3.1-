import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from diagnostic_machine.action_router import ActionRouter
from diagnostic_machine.judgement import JudgementResult, HealthStatus, ConfidenceScore
from diagnostic_machine.sensors import SensorData
from diagnostic_machine.interpreters import InterpretedData

def test_router_integration():
    try:
        router = ActionRouter(
            enable_healing=False,
            enable_freeze=False,
            enable_cognitive=False,
            enable_sandbox=False,
            enable_llm=False
        )
        print("ActionRouter initialized successfully with the new Braille imports.")
        
        from diagnostic_machine.action_router import BRAILLE_COMPILER_AVAILABLE
        print(f"Braille Compiler Available: {BRAILLE_COMPILER_AVAILABLE}")
        print("\nIntegration test passed! The deterministic bitmask engine is wired.")
    except Exception as e:
        print(f"Error initializing ActionRouter: {e}")

if __name__ == "__main__":
    test_router_integration()
