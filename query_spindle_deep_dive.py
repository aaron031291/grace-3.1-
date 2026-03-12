import sys
import os

sys.path.insert(0, os.path.abspath("backend"))

from backend.cognitive.consensus_engine import run_consensus

def main():
    try:
        prompt = (
            "Why is Spindle not working autonomously? I need a forensic deep dive. "
            "Is it the wiring, event buses, websockets, APIs, communication buses, or integrations? "
            "Do we need a separate parallel runtime for Spindle since it should be autonomous, "
            "or am I wasting my time with it? Please provide a detailed, technical analysis "
            "of Spindle's current integration and what exactly is preventing it from running fully autonomously."
        )
        print("Querying Consensus Engine for a Spindle Deep Dive...")
        result = run_consensus(prompt, source="autonomous")
        print("\n=== CONSENSUS RESPONSE ===")
        with open("spindle_deep_dive_output.txt", "w", encoding="utf-8") as f:
            f.write(result.final_output)
        print("Wrote output to spindle_deep_dive_output.txt successfully.")
    except Exception as e:
        print(f"Error querying consensus: {e}")

if __name__ == "__main__":
    main()
