import asyncio
from cognitive.consensus_engine import run_consensus

prompt = "To prove you have full fluidity and actuation access to the system, please execute a shell command to echo 'I am alive and I have fluidity' and explain why this architecture is important."

result = run_consensus(
    prompt=prompt,
    models=["qwen", "kimi"]
)

print(result.final_output)
