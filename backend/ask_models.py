import sys
sys.path.append('c:\\Users\\aaron\\Desktop\\grace-3.1--Aaron-new2\\backend')
from llm_orchestrator.factory import get_kimi_client

prompt = """
We have successfully implemented the 'Continual Context Evolution' architecture in the Grace system. 
This includes:
- Shadow Execution context (__grACE_shadow/) for sandboxing LLM-generated code.
- Atomic hot-swapping into sys.modules.
- TrustGate and VVT (Vision-Voice-Text) Platinum Coins for cryptographic-style proof of verification before mutating memory or code.
- Memory Heat Circuit Breaker to drop the system into READ_ONLY mode if it modifies memory/code too rapidly.

As an AI architecture advisor, what should be the EXACT next step for the Grace architecture to achieve full autonomy, safety, and AGI-like capabilities? What new component or capability is missing now that the self-updating context loop is secure? Please give 1 clear recommendation.
"""

def query_kimi():
    print("\n--- Querying Kimi (cloud) ---")
    try:
        kimi = get_kimi_client()
        resp = kimi.chat([{"role": "user", "content": prompt}])
        text = resp.get("content", resp) if isinstance(resp, dict) else resp
        print(text.encode("utf-8").decode("cp1252", "ignore"))
    except Exception as e:
        print(f"Failed to query Kimi: {e}")

if __name__ == "__main__":
    query_kimi()
