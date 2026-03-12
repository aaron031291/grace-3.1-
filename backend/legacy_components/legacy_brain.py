import logging

logger = logging.getLogger(__name__)

class LegacyBrain:
    def __init__(self):
        # Genesis Key Injection
        from cognitive.genesis_key import genesis_key
        self.brain_key = genesis_key.mint(component="legacy_brain_module")
        logger.info(f"[LEGACY-BRAIN] Securely instantiated with Genesis Key: {self.brain_key}")

    def execute_legacy_heuristic(self, input_data: dict) -> dict:
        """
        An old heuristic rules engine running prior to Qwen integration.
        Now tracked via the Genesis Key.
        """
        logger.info(f"[LEGACY-BRAIN] Running heuristic tracking via key: {self.brain_key}")
        # Simulate processing
        return {"decision": "heuristic_approve", "confidence": 0.45, "genesis_key": self.brain_key}
