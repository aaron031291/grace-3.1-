import requests
import json
import logging

logger = logging.getLogger(__name__)

GRACE_API_URL = "http://localhost:8000/brain"

def send(message: str):
    """
    Send an event or notification to Grace.
    Used by IDE triggers (like on_save) to update Grace's context passively.
    """
    try:
        payload = {
            "action": "live", 
            "payload": {"event": message}
        }
        requests.post(f"{GRACE_API_URL}/tasks", json=payload, timeout=3)
    except Exception as e:
        logger.warning(f"Failed to send event to Grace API: {e}")

def process(user_input: str) -> dict:
    """
    Send a natural language command to Grace.
    Grace's brain handles the deterministic translations internally.
    
    Returns standard IDE bridge format: {"files": [...], "code": "..."}
    """
    try:
        payload = {
            "action": "generate",
            "payload": {
                "prompt": user_input,
                "use_pipeline": True
            }
        }
        res = requests.post(f"{GRACE_API_URL}/code", json=payload, timeout=120)
        
        if res.status_code == 200:
            data = res.json()
            if data.get("ok"):
                # Extract the generated code context from the brain API response
                result_data = data.get("data", {})
                
                # Format to match the expected IDE response standard
                return {
                    "files": result_data.get("files", []),
                    "code": result_data.get("code", "Done.")
                }
            else:
                return {"error": data.get("error")}
        return {"error": f"HTTP {res.status_code}"}
    except Exception as e:
        logger.error(f"Failed to process command via Grace API: {e}")
        return {"error": str(e)}
