import sys
import os
import requests

sys.path.append('c:\\Users\\aaron\\Desktop\\grace-3.1\\backend')
from settings import settings

prompt = """
We have successfully implemented the 'Continual Context Evolution' architecture in the Grace system. 
This includes:
- Shadow Execution context (__grACE_shadow/) for sandboxing LLM-generated code.
- Atomic hot-swapping into sys.modules.
- TrustGate and VVT (Vision-Voice-Text) Platinum Coins for cryptographic-style proof of verification before mutating memory or code.
- Memory Heat Circuit Breaker to drop the system into READ_ONLY mode if it modifies memory/code too rapidly.

As an AI architecture advisor, what should be the EXACT next step for the Grace architecture to achieve full autonomy, safety, and AGI-like capabilities? What new component or capability is missing now that the self-updating context loop is secure? Please give 1 clear recommendation.
"""

def query_qwen():
    print("--- Querying Qwen 3.5 (local) ---")
    try:
        # Use the actual installed model name
        url = "http://localhost:11434/api/chat"
        payload = {
            "model": "qwen3:32b",
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        }
        res = requests.post(url, json=payload, timeout=60).json()
        text = res.get("message", {}).get("content", "")
        print(text.encode("utf-8").decode("cp1252", "ignore"))
    except Exception as e:
        print(f"Failed to query Qwen: {e}")

def query_kimi():
    print("\n--- Querying Kimi (cloud) ---")
    try:
        url = "https://api.moonshot.cn/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.KIMI_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "moonshot-v1-auto",
            "messages": [{"role": "user", "content": prompt}]
        }
        res = requests.post(url, json=payload, headers=headers).json()
        text = res["choices"][0]["message"]["content"]
        print(text.encode("utf-8").decode("cp1252", "ignore"))
    except Exception as e:
        print(f"Failed to query Kimi: {e}")

if __name__ == "__main__":
    query_qwen()
    query_kimi()
