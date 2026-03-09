import os
import sys

# Add backend to PYTHONPATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from cognitive.consensus_engine import run_consensus

prompt = "As the consensus mechanism (Opus, Kimi, and Qwen), do you have full fluidity throughout the system and have access to everything you need to have access to in order to accomplish self-healing, coding, learning, and evolution? Please analyze your current capabilities, access levels, and any limitations."

print(f"Querying Consensus Engine with prompt:\n{prompt}\n")

result = run_consensus(
    prompt=prompt,
    models=["opus", "kimi", "qwen"],
    source="user"
)

print("\n" + "="*80)
print("CONSENSUS RESULT:")
print("="*80)
print(result.final_output)

print("\n" + "="*80)
print(f"Confidence: {result.confidence}")
print(f"Agreements: {len(result.agreements)}")
for a in result.agreements:
    print(f"  - {a}")
print(f"Disagreements: {len(result.disagreements)}")
for d in result.disagreements:
    print(f"  - {d}")
print("="*80)
