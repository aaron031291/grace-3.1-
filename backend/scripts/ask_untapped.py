import os
import sys

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(backend_dir)

from cognitive.consensus_engine import run_consensus

prompt = """
What are the main untapped connections in the Grace architecture that are not currently connected,
that would lead to untapped intelligence being connected and leading to the unification of the system
to be stable and highly usable?
"""

print("Running consensus with Kimi, Qwen, and Opus...")
result = run_consensus(
    prompt=prompt,
    models=["kimi", "qwen", "opus"]
)

with open("untapped_result.md", "w", encoding="utf-8") as f:
    f.write("--- CONSENSUS RESULT ---\n")
    f.write(result.final_output + "\n")
    f.write("\n--- AGREEMENTS ---\n")
    for a in result.agreements:
        f.write(f"- {a}\n")
    f.write("\n--- DISAGREEMENTS ---\n")
    for d in result.disagreements:
        f.write(f"- {d}\n")

print("Output saved to untapped_result.md")
