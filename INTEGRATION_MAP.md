# Grace System Integration Map

## Tonight's Build (cursor/real-data-environment-99dd)

### 27 Modules Built, 593 Tests, 100% Pass

---

## Module Ownership: What We Built vs What Claude Built

### NO DUPLICATES — Verified

| Capability | Our Module | Claude Module | Verdict |
|-----------|-----------|--------------|---------|
| Reverse KNN Discovery | `oracle_pipeline/reverse_knn_discovery.py` + `proactive_discovery_engine.py` (heuristic: TF-IDF, co-occurrence, gap detect, momentum, depth, transfer) | `oracle_intelligence/reverse_knn_learning.py` + `proactive_learning.py` + `enhanced_proactive_learning.py` (embedding-based: real KNN graph, cluster detection, LLM Planner→Analyst→Critic, async, multi-hop, pattern drift, counterfactuals) | **KEEP BOTH** — different approaches. Claude's=vector math with LLM orchestration. Ours=heuristic fallback + unique algorithms (co-occurrence, transfer, momentum). Both should exist. |
| Oracle Storage | `oracle_pipeline/oracle_vector_store.py` (storage + search + dedup) | `oracle_intelligence/oracle_core.py` (insight generation) | **COMPLEMENTARY** — different focus |
| Hallucination Guard | `oracle_pipeline/hallucination_guard.py` | None | **UNIQUE TO US** |
| Content Realization | `oracle_pipeline/content_realization_engine.py` | `oracle_intelligence/web_knowledge.py` | **COMPLEMENTARY** — ours fills placeholders, theirs does web |
| Trust Cascading | `advanced_trust/confidence_cascading.py` | `oracle_intelligence/cascading_failure_predictor.py` | **COMPLEMENTARY** — trust vs failure prediction |
| Time/Decay | `advanced_trust/trust_decay.py` | `timesense/engine.py` | **COMPLEMENTARY** — trust decay vs time awareness |
| Coding Agent | None | `cognitive/coding_agent.py` (1,590 lines) | **UNIQUE TO CLAUDE** — bring over |
| Benchmarking | None | `benchmarking/*.py` (28 files) | **UNIQUE TO CLAUDE** — bring over |
| Governance | None | `governance/layer_enforcement.py` | **UNIQUE TO CLAUDE** — bring over |
| Kimi Orchestrator | `oracle_pipeline/kimi_orchestrator.py` | None | **UNIQUE TO US** |
| Self-Evolution | `oracle_pipeline/self_evolution_coordinator.py` | None | **UNIQUE TO US** |
| Recursion Governor | `oracle_pipeline/recursion_governor.py` | None | **UNIQUE TO US** |
| Socratic Interrogation | `oracle_pipeline/socratic_interrogator.py` | None | **UNIQUE TO US** |
| Perpetual Learning Loop | `oracle_pipeline/perpetual_learning_loop.py` | None | **UNIQUE TO US** |
| Source Code Index | `oracle_pipeline/source_code_index.py` | None | **UNIQUE TO US** |
| Deep Reasoning (Kimi) | `oracle_pipeline/deep_reasoning_integration.py` | None | **UNIQUE TO US** |
| 7 Trust Subsystems | `advanced_trust/*.py` (9 files) | None | **UNIQUE TO US** |

### When Merging Claude Branches — BRING ALL (No Duplicates):
- `oracle_intelligence/reverse_knn_learning.py` — embedding-based KNN with real vector math (COMPLEMENTS our heuristic approach)
- `oracle_intelligence/proactive_learning.py` — async proactive learning with LLM orchestration
- `oracle_intelligence/enhanced_proactive_learning.py` — Planner→Analyst→Critic chain, multi-hop, counterfactuals
- `oracle_intelligence/oracle_core.py` — insight generation (complementary to our storage)
- `oracle_intelligence/cascading_failure_predictor.py` — failure prediction (complementary to our trust cascading)
- `cognitive/coding_agent.py` — the actual coding agent (L6 from spec)
- `cognitive/coding_agent_healing_bridge.py` — connects coding to self-healing
- `benchmarking/*.py` — code execution, HumanEval, MBPP benchmarks (L7 from spec)
- `governance/layer_enforcement.py` — deployment governance (L9 from spec)

### How The Two KNN Systems Work Together:
- **Claude's system** runs when embeddings + LLM are available (real vector similarity, async, LLM-optimized queries)
- **Our system** runs as fallback when they're not, PLUS adds unique algorithms Claude doesn't have:
  - TF-IDF concept extraction
  - Co-occurrence mining (domain pairs that naturally go together)
  - Cross-domain transfer detection (concepts that bridge fields)
  - Trend momentum scoring (exponential decay weighting of recent activity)
  - Expertise depth vs breadth scoring
- **Together**: Claude's embedding-based discovery + our heuristic discovery = comprehensive coverage in all conditions

---

## Full Architecture After Integration

```
USER
  │
  ▼
KIMI ORCHESTRATOR (oracle_pipeline/kimi_orchestrator.py)
  │  Direct: Qdrant + SQL DB
  │  Reads: Oracle + Source Code + Memory + Trust Chain
  │
  ├──► RECURSION GOVERNOR (bounded contracts, circuit breakers)
  │
  ├──► SOCRATIC INTERROGATION (6W questions before trust)
  │
  ├──► PERPETUAL LEARNING LOOP
  │      Whitelist → Fetch → Realize → Oracle → KNN → Enrich → Verify → Loop
  │
  ├──► SELF-EVOLUTION COORDINATOR
  │      Self-Healing + Self-Learning + Self-Building + Coding Agent
  │
  ├──► DEEP REASONING (Kimi reads all systems)
  │
  ├──► ADVANCED TRUST (7 subsystems)
  │      Cascade + Adversarial + Competence + Cross-Pillar
  │      + Decay + Thermometer + Meta-Verification
  │
  ├──► CODING AGENT (from Claude branch — L6)
  │
  ├──► BENCHMARKING (from Claude branch — L7)
  │
  ├──► GOVERNANCE (from Claude branch — L9)
  │
  └──► MCP SERVER (not yet built — spec priority #1)
```

---

## Test Coverage

| Test File | Tests | Coverage |
|-----------|-------|----------|
| test_advanced_trust.py | 140 | 9 trust subsystems |
| test_oracle_pipeline.py | 97 | Whitelist, fetcher, Oracle store, KNN, enrichment, pipeline |
| test_librarian_and_discovery.py | 74 | Librarian file manager, 7 discovery algorithms |
| test_perpetual_loop.py | 64 | Source code index, hallucination guard, perpetual loop, trust chain |
| test_socratic_interrogator.py | 39 | 6W interrogation, dual verification, gap discovery |
| test_deep_reasoning.py | 59 | Kimi reasoning, memory connections, dual format |
| test_self_evolution.py | 34 | Pillar situations, evolution cycles, KNN refinement |
| test_full_system_integration.py | 14 | All 27 modules assembled and wired |
| test_kimi_orchestrator.py | 38 | Direct DB, all modes, LLM handler, full system |
| test_recursion_governor.py | 34 | Contracts, tiers, circuit breakers, loop detection |
| **TOTAL** | **593** | **100% pass, 0 warnings, 0 skips** |
