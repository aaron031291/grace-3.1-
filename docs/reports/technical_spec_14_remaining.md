# Grace Technical Specification — 14 Remaining Items

## Priority Order (build in this sequence — each enables the next)

---

### 1. Mirror Self-Model (KEYSTONE)
**File:** `cognitive/mirror_self_modeling.py`
**Status:** Module exists but `__init__` requires a DB session. Pipeline can't instantiate it.
**What to do:**
- Fix the constructor to work without a session (lazy load)
- Implement `analyze_recent_operations()` to query genesis keys for the last 100 actions
- Build `detect_behavioral_patterns()` — group genesis keys by type, find recurring patterns (e.g. "most code generation happens in afternoon", "database healing triggers every 6 hours")
- Connect output to pipeline OODA stage — the observations should include "Grace has been doing X frequently, Y is declining"
- Store detected patterns in Magma via `store_pattern()`
**Test:** Call `MirrorSelfModelingSystem().analyze_recent_operations()` and verify it returns actual patterns from genesis key data
**Why first:** Every other system improves when Grace can see her own behavior

---

### 2. OODA Loop (Real Implementation)
**File:** `cognitive/ooda.py` + `cognitive/pipeline.py` (stage 2)
**Status:** Pipeline stage classifies prompt type and reads files. The actual `OODALoop` class in `ooda.py` has observe/orient/decide/act phases but isn't called.
**What to do:**
- Instantiate `OODALoop` in the pipeline's `_stage_ooda()`
- OBSERVE: pass project files, tech stack, recent genesis keys, mirror model patterns
- ORIENT: pass governance rules, learned patterns from Magma, episodic memory
- DECIDE: generate 2-3 approach alternatives, score by risk/complexity/alignment
- ACT: return the chosen approach with rationale
- Store the decision in Magma via `store_decision()`
**Test:** Run pipeline with a complex prompt and verify OODA produces alternatives with scored rationale, not just prompt classification
**Dependencies:** Mirror Self-Model (#1) feeds observations

---

### 3. Contradiction Detector (Embedding-Based)
**File:** `cognitive/pipeline.py` (stage 6) + `confidence_scorer/contradiction_detector.py`
**Status:** Pipeline checks language mismatch and imports. The `SemanticContradictionDetector` in confidence_scorer does embedding-based comparison but isn't called.
**What to do:**
- In pipeline `_stage_contradiction()`, instantiate `SemanticContradictionDetector`
- Pass the LLM output + RAG-retrieved context from the same project
- Compare embeddings — if output is semantically similar but logically opposite to existing knowledge, flag it
- This requires the embedding model to be loaded (needs your machine)
**Test:** Generate code that contradicts an existing file in the project, verify the detector catches it
**Dependencies:** Embedding model running, Qdrant running

---

### 4. Neural Trust Scorer (Real Neural Network)
**File:** `ml_intelligence/neural_trust_scorer.py`
**Status:** Class exists with `predict_trust()`, `update_from_outcome()`, `train_step()`. Not called from Trust Engine.
**What to do:**
- In `cognitive/trust_engine.py` `_score_chunk()`, call `NeuralTrustScorer.predict_trust()` instead of the rule-based formula
- Feed actual outcomes via `update_from_outcome()` when feedback is recorded
- Run `train_step()` periodically (idle learner or immune system cycle)
- The neural network needs training data — seed it from existing learning_examples table
**Test:** Score 10 chunks with neural scorer, verify scores differ from rule-based, verify `update_from_outcome` changes future predictions
**Dependencies:** Training data in learning_examples table

---

### 5. Ambiguity Ledger (Semantic Analysis)
**File:** `cognitive/ambiguity.py` + `cognitive/pipeline.py` (stage 3)
**Status:** Pipeline tracks knowns/unknowns as string lists. The `AmbiguityLedger` class has `add_known/inferred/assumed/unknown` with confidence levels but isn't used properly.
**What to do:**
- Instantiate `AmbiguityLedger` in the pipeline stage
- For each implicit reference found ("the database"), query RAG to check if it exists
- If found in project: `add_known()` with high confidence
- If found in KB but not project: `add_inferred()` with medium confidence
- If not found anywhere: `add_unknown()` with `blocking=True` for code generation
- If blocking unknowns exist and prompt type is "code_generation": return them to the user as questions instead of assuming
**Test:** Submit prompt "connect to the database" with no database in project. Verify ambiguity stage returns a blocking unknown and the pipeline asks for clarification instead of generating
**Dependencies:** RAG running (#3)

---

### 6. Uncertainty Quantification
**File:** `ml_intelligence/uncertainty_quantification.py`
**Status:** Has `BayesianNeuralNetwork`, `MCDropoutNetwork`, `DeepEnsemble`, `ConformalPredictor`. None called.
**What to do:**
- Choose `MCDropoutNetwork` (simplest to integrate — runs multiple forward passes with dropout)
- In the pipeline's trust post stage, run uncertainty estimation on the LLM output embedding
- Epistemic uncertainty (model doesn't know) → flag for learning
- Aleatoric uncertainty (inherent noise) → flag for human review
- Add uncertainty scores to the pipeline context output
**Test:** Generate two outputs — one on a well-known topic, one on an obscure topic. Verify epistemic uncertainty is higher for the obscure one
**Dependencies:** Embedding model, Neural Trust Scorer (#4)

---

### 7. Neuro-Symbolic Reasoner
**File:** `ml_intelligence/neuro_symbolic_reasoner.py`
**Status:** Has `reason()` and `explain_reasoning()` methods. Fuses neural retrieval with symbolic logic rules. Not called.
**What to do:**
- In the pipeline OODA orient phase, call `NeuroSymbolicReasoner.reason()` with the current context
- It should query both vector similarity (neural) and governance rules (symbolic)
- The fused result gives structured reasoning about what applies to this situation
- Store the reasoning trace in Magma for transparency
**Test:** Submit a prompt that involves a governance rule (e.g. "build a data handler" when GDPR is uploaded). Verify the reasoner surfaces the GDPR constraint alongside the code pattern
**Dependencies:** Governance rules uploaded, RAG running

---

### 8. Predictive Context Loader
**File:** `cognitive/predictive_context_loader.py`
**Status:** Has `process_query()`, `get_cached_context()`, `warmup_topics()`. Not called.
**What to do:**
- On app startup, call `warmup_topics()` with the most common prompt types from genesis key history
- In the pipeline before OODA, call `process_query()` to prefetch relevant context
- This should pre-load RAG results, Magma context, and learned patterns BEFORE the user's prompt is fully processed
- Cache results for 5 minutes
**Test:** Submit two identical prompts 2 seconds apart. Verify the second one is faster because context was cached from the first
**Dependencies:** RAG running, Magma populated

---

### 9. CodeNet Integration
**File:** `ingestion/codenet_adapter.py`
**Status:** Adapter exists with `CodeNetAdapter`, `LearningPair`, `SimilarityGroup`. Can extract error→fix pairs. Not connected to coding agent.
**What to do:**
- Download a subset of IBM's Project CodeNet dataset (Python problems)
- Run `CodeNetAdapter.load_curated_subset()` to extract learning pairs
- Run `extract_learning_signals()` to get error→accepted patterns
- Store these as learning examples in the learning_examples table
- In the pipeline generate stage, query for relevant CodeNet patterns when the prompt is about fixing errors
**Test:** Ask the coding agent to fix a common Python error. Verify it references a CodeNet pattern in its reasoning
**Dependencies:** CodeNet dataset downloaded, database running

---

### 10. Grace Agent (OODA Execution Loop)
**File:** `agent/grace_agent.py`
**Status:** Full agent with task understanding, planning, execution, learning. Uses `ExecutionBridge`. Not called from any endpoint.
**What to do:**
- Create an endpoint `POST /api/v1/agent/autonomous` that accepts a task description
- Instantiate `GraceAgent` with the execution bridge
- Run the full agent loop: understand → plan → execute → observe → learn
- Connect to governance for approval on destructive actions
- Store task results in Magma and genesis keys
**Test:** Submit "create a hello world Flask app in the test project". Verify the agent creates the files, tests them, and records the outcome
**Dependencies:** LLM running, file system access

---

### 11. Governed Bridge
**File:** `execution/governed_bridge.py`
**Status:** Wraps `ExecutionBridge` with constitutional governance checks. Not connected.
**What to do:**
- Use `GovernedExecutionBridge` instead of raw `ExecutionBridge` in the Grace Agent (#10)
- Every action the agent wants to execute goes through governance check first
- Destructive actions (delete, overwrite, deploy) require approval
- Safe actions (read, create, test) auto-execute
- Log every governance decision via genesis key
**Test:** Have the agent try to delete a file. Verify the governed bridge blocks it and routes to approval queue
**Dependencies:** Grace Agent (#10)

---

### 12. GraceOS Codegen Layer
**File:** `grace_os/layers/l6_codegen/codegen_layer.py`
**Status:** Layer 6 in the mesh architecture. Has `handle_message()` for EXECUTE_TASK and FIX_CODE. Not connected to the coding agent.
**What to do:**
- In the unified coding agent, for code generation tasks, route through the GraceOS mesh
- L6 receives a `LayerMessage` with the task, generates code, returns a `LayerResponse`
- Connect to the GraceOS message bus so other layers can coordinate
- L6 should use the cognitive pipeline internally for generation
**Test:** Send an EXECUTE_TASK message to L6 via the message bus. Verify it generates code and returns a proper response
**Dependencies:** GraceOS message bus running (tests already pass for this)

---

### 13. GraceOS Testing Layer
**File:** `grace_os/layers/l7_testing/testing_layer.py`
**Status:** Layer 7 for testing. Has handle_message() for test execution. Not connected.
**What to do:**
- After L6 generates code, automatically route to L7 for testing
- L7 runs basic validation: syntax check, import verification, lint
- If Python: run `py_compile.compile()` on generated files
- If JavaScript: run basic AST parse
- Return test results to the coding agent
- Failed tests → route back to L6 for fix → re-test (max 3 iterations)
**Test:** Generate code with a syntax error. Verify L7 catches it and L6 fixes it
**Dependencies:** GraceOS Codegen Layer (#12)

---

### 14. Continuous Background Loop
**File:** New — `cognitive/background_loop.py`
**Status:** Doesn't exist. The immune system, idle learner, and predictive context all need to run continuously but nothing starts them.
**What to do:**
- Create a background loop that starts on app startup (via FastAPI lifespan)
- Every 60 seconds: immune system scan
- Every 5 minutes (if idle): idle learner teaches one topic
- Every 10 minutes: predictive context warmup
- Every 30 minutes: mirror self-model analysis
- Every 24 hours: genesis key daily archival
- Each cycle respects TimeSense (less frequent off-hours)
- The loop is the heartbeat that makes Grace alive vs just reactive
**Test:** Start the app, wait 2 minutes, verify immune scans are running and idle learner has taught a topic
**Dependencies:** All services running on your machine

---

## Summary

| # | Item | Effort | Dependencies |
|---|---|---|---|
| 1 | Mirror Self-Model | 3-4 hours | Genesis keys in DB |
| 2 | OODA Loop | 3-4 hours | #1 |
| 3 | Contradiction Detector | 2-3 hours | Embedding model, Qdrant |
| 4 | Neural Trust Scorer | 3-4 hours | Training data in DB |
| 5 | Ambiguity Ledger | 2-3 hours | RAG running |
| 6 | Uncertainty Quantification | 3-4 hours | #4 |
| 7 | Neuro-Symbolic Reasoner | 2-3 hours | Governance rules, RAG |
| 8 | Predictive Context | 2-3 hours | RAG, Magma |
| 9 | CodeNet Integration | 3-4 hours | CodeNet dataset, DB |
| 10 | Grace Agent | 4-5 hours | LLM running |
| 11 | Governed Bridge | 2-3 hours | #10 |
| 12 | GraceOS Codegen | 3-4 hours | Message bus |
| 13 | GraceOS Testing | 3-4 hours | #12 |
| 14 | Background Loop | 2-3 hours | All services |

**Total estimated: ~40-50 hours**
**Recommended order: 1 → 2 → 5 → 3 → 4 → 6 → 7 → 8 → 9 → 10 → 11 → 12 → 13 → 14**

When all 14 are complete: Opus's rating goes from 6.5/10 to 8.5-9.0/10.
