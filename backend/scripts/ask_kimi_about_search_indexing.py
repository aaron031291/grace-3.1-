#!/usr/bin/env python3
"""
Ask the Kimi API about the search indexing / self-documenting system we're building.

Run from backend: python scripts/ask_kimi_about_search_indexing.py

Requires KIMI_API_KEY (and optionally KIMI_MODEL) in .env. Uses Grace's consensus
engine to send the question to Kimi and print the response.
"""

import sys
from pathlib import Path

backend = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend))

from dotenv import load_dotenv
load_dotenv(backend / ".env")

SUMMARY = """
We're building a queryable search/indexing layer for Grace so devs can ask in plain language:

1. **Ask tab (UI)** — Devs type questions; POST /brain/ask routes to the best brain+action.
2. **Architecture compass exposed** — system actions: architecture_explain(component), architecture_find(capability), architecture_connected(from, to), architecture_diagnose(), architecture_map(). So "what does pipeline do?", "trace path from X to Y", "what can handle code review?" return real data.
3. **Embedding + schema + graphs + brains** — system actions: embedding_config, brain_directory, models_summary, schema_info (DB + Qdrant), graphs_info (component graph, qdrant, magma). So "what embedding model?", "list APIs", "schema/databases", "graphs" all work.
4. **Neighbor-by-neighbor fallback** — When NLP routing confidence is low (<0.25), we add nearest_actions: top actions by keyword overlap so the UI can show "Did you mean: ...?" instead of a weak match.

All of this is keyword-based routing plus the existing Architecture Compass (live component graph). No vector search over the index yet.
"""

PROMPT = (
    "We're building the search/indexing system described below. "
    "As an external reviewer (Kimi), what should we consider or improve? "
    "Focus on: gaps for dev onboarding, missing queries, whether neighbor-by-neighbor is enough, "
    "and any risks or simplifications you'd suggest.\n\n"
    + SUMMARY
)


def main():
    print("Asking Kimi about the search indexing we're building...")
    print("(Requires KIMI_API_KEY in .env)\n")

    try:
        from cognitive.consensus_engine import run_consensus, _check_model_available
    except ImportError as e:
        print(f"Import error: {e}")
        print("Run from backend: python scripts/ask_kimi_about_search_indexing.py")
        return 1

    if not _check_model_available("kimi"):
        print("Kimi is not available (missing KIMI_API_KEY or check _check_model_available).")
        return 1

    r = run_consensus(
        prompt=PROMPT,
        models=["kimi"],
        system_prompt="You are reviewing a technical design for a self-documenting AI system. Be concise and practical.",
        source="ask_kimi_script",
    )
    print("--- Kimi's response ---")
    print(r.final_output)
    print("---")
    if getattr(r, "models_used", None):
        print("Models used:", r.models_used)
    return 0


if __name__ == "__main__":
    sys.exit(main())
