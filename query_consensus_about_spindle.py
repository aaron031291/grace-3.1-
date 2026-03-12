import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath("backend"))

from backend.cognitive.consensus_engine import run_consensus

def main():
    try:
        prompt = (
            "Spindle is successfully generating code to fix errors (e.g., 'def patch_grace_launcher(): ...'), "
            "but it just writes this function to the sandbox and never actually *executes* the function "
            "to perform the fix on the real files. "
            "Also, we want the Self-Healing system to run fully autonomously in the background without the user pushing a button. "
            "How do we solve these two issues in the Grace architecture?"
        )
        print("Querying Consensus Engine...")
        # run_consensus is apparently synchronous
        result = run_consensus(prompt, source="autonomous")
        print("\n=== CONSENSUS RESPONSE ===")
        print(result.final_output)
    except Exception as e:
        print(f"Error querying consensus: {e}")

if __name__ == "__main__":
    main()
