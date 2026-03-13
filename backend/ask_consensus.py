import os
import sys

# Add backend to PYTHONPATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from cognitive.consensus_engine import run_consensus

prompt = "As the consensus mechanism (Opus, Kimi, and Qwen), we are going through every file and component this weekend, checking what works and what's wrong. Before we do a 1-by-1 review, are there documents, components, orphaned logic, or redundant code that have no relevance to the actual system and can be safely deleted? Please list specific files, directories, or architectural components that are no longer relevant."

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
