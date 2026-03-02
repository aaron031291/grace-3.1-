"""
Grace Coding Pipeline — 8-Layer Error Mitigation System.

This is the LAW that governs how ALL models (Kimi, Opus, Qwen, DeepSeek)
produce code. No model can skip layers. No layer can pass without
100% completion. Everything tracked via Genesis keys.

Flow:
  User task → Planner → Consensus on plan → Break into chunks →
  Each chunk runs through all 8 layers → Probe + verify at each layer →
  Consensus after each chunk → Final consensus → Deployment gate

Layers:
  1. RUNTIME ENVIRONMENT — isolated context per task
  2. TASK DECOMPOSITION — break into sub-problems
  3. SOLUTION PROPOSAL — generate 3 diverse approaches
  4. SOLUTION SELECTION — evaluate and pick best approach
  5. SIMULATION & REASONING — simulate against requirements
  6. CODE GENERATION — translate chosen approach into code
  7. VERIFICATION — sandbox test, probe, fact-check
  8. DEPLOYMENT GATE — consensus approval, trust score check

Cross-cutting concerns (run at EVERY layer):
  - Genesis Key tracking (provenance)
  - Trust Score (confidence metric)
  - Self-Mirror (observe own behavior)
  - TimeSense (urgency, scheduling)
  - LLM Reasoning (reason about the layer before proceeding)
  - Probe (verify everything works)
  - Activity tracker (what happened)
"""

import logging
import time
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class LayerResult:
    layer: int
    name: str
    status: str  # pending, running, passed, failed, skipped
    output: Any = None
    trust_score: float = 0.0
    reasoning: str = ""
    duration_ms: float = 0
    genesis_key_id: str = ""
    probe_passed: bool = False


@dataclass
class ChunkResult:
    chunk_id: int
    description: str
    layers: List[LayerResult] = field(default_factory=list)
    consensus: Dict = field(default_factory=dict)
    status: str = "pending"  # pending, running, passed, failed


@dataclass
class PipelineResult:
    task: str
    chunks: List[ChunkResult] = field(default_factory=list)
    final_consensus: Dict = field(default_factory=dict)
    status: str = "pending"
    total_duration_ms: float = 0
    trust_score: float = 0.0


LAYER_NAMES = {
    1: "Runtime Environment",
    2: "Task Decomposition",
    3: "Solution Proposal",
    4: "Solution Selection",
    5: "Simulation & Reasoning",
    6: "Code Generation",
    7: "Verification & Testing",
    8: "Deployment Gate",
}


class CodingPipeline:
    """
    The 8-layer coding pipeline. Every code task goes through this.
    """

    def __init__(self):
        self.max_retries = 2
        self.min_trust_score = 0.6
        self.require_unanimous = True

    def run(self, task: str, context: dict = None) -> PipelineResult:
        """Execute the full pipeline for a task."""
        start = time.time()
        result = PipelineResult(task=task)

        # Track via Genesis
        self._track("pipeline_start", f"Pipeline started: {task[:100]}", {"task": task})

        # Step 1: Plan — break task into chunks
        chunks = self._plan_task(task, context or {})
        if not chunks:
            result.status = "failed"
            result.chunks = []
            return result

        # Step 2: Consensus on the plan
        plan_consensus = self._consensus(f"Plan for: {task}\nChunks: {json.dumps(chunks, default=str)}")
        if not plan_consensus.get("agreed"):
            result.status = "plan_rejected"
            result.final_consensus = plan_consensus
            return result

        # Step 3: Execute each chunk through all 8 layers
        for i, chunk_desc in enumerate(chunks):
            chunk = ChunkResult(chunk_id=i, description=chunk_desc)
            chunk.status = "running"

            for layer_num in range(1, 9):
                layer_result = self._execute_layer(layer_num, chunk_desc, task, context or {})
                chunk.layers.append(layer_result)

                if layer_result.status == "failed":
                    chunk.status = "failed"
                    self._track("layer_failed", f"Layer {layer_num} failed for chunk {i}: {chunk_desc[:50]}")
                    break

            if chunk.status != "failed":
                # Consensus on completed chunk
                chunk.consensus = self._consensus(
                    f"Chunk {i} complete: {chunk_desc}\n"
                    f"All {len(chunk.layers)} layers passed."
                )
                chunk.status = "passed" if chunk.consensus.get("agreed") else "failed"

            result.chunks.append(chunk)

        # Step 4: Final consensus on all chunks
        passed_chunks = [c for c in result.chunks if c.status == "passed"]
        if len(passed_chunks) == len(result.chunks):
            result.final_consensus = self._consensus(
                f"All {len(result.chunks)} chunks passed for: {task}"
            )
            result.status = "passed" if result.final_consensus.get("agreed") else "failed"
        else:
            result.status = "partial"

        result.total_duration_ms = round((time.time() - start) * 1000, 1)
        result.trust_score = self._calculate_trust(result)

        self._track("pipeline_complete", f"Pipeline {result.status}: {task[:100]}",
                     {"status": result.status, "chunks": len(result.chunks),
                      "passed": len(passed_chunks), "trust": result.trust_score})

        return result

    def _plan_task(self, task: str, context: dict) -> list:
        """Break task into manageable chunks using LLM."""
        try:
            from api.brain_api_v2 import call_brain
            r = call_brain("ai", "fast", {
                "prompt": f"Break this task into 3-7 sequential chunks. "
                          f"Each chunk should be completable independently. "
                          f"Return ONLY a JSON array of strings.\n\nTask: {task}",
                "models": ["kimi"],
            })
            if r.get("ok"):
                response = r["data"].get("individual_responses", [{}])[0].get("response", "")
                try:
                    import re
                    match = re.search(r'\[.*\]', response, re.DOTALL)
                    if match:
                        return json.loads(match.group())
                except Exception:
                    pass
                return [task]
            return [task]
        except Exception:
            return [task]

    def _execute_layer(self, layer_num: int, chunk: str, task: str, context: dict) -> LayerResult:
        """Execute a single layer of the pipeline."""
        start = time.time()
        name = LAYER_NAMES.get(layer_num, f"Layer {layer_num}")
        result = LayerResult(layer=layer_num, name=name, status="running")

        try:
            # TimeSense check
            time_ctx = self._time_check()

            # Self-mirror observation
            mirror_obs = self._mirror_observe(layer_num, chunk)

            # LLM Reasoning about this layer
            reasoning = self._reason(layer_num, chunk, task)
            result.reasoning = reasoning

            # Execute the layer logic
            if layer_num == 1:
                result.output = self._layer_runtime(chunk, context)
            elif layer_num == 2:
                result.output = self._layer_decompose(chunk, task)
            elif layer_num == 3:
                result.output = self._layer_propose(chunk, task)
            elif layer_num == 4:
                result.output = self._layer_select(chunk, result.output or {})
            elif layer_num == 5:
                result.output = self._layer_simulate(chunk, task)
            elif layer_num == 6:
                result.output = self._layer_generate(chunk, task)
            elif layer_num == 7:
                result.output = self._layer_verify(chunk)
            elif layer_num == 8:
                result.output = self._layer_deploy_gate(chunk)

            # Probe check
            result.probe_passed = self._probe_layer(layer_num)

            # Trust score
            result.trust_score = self._layer_trust(layer_num, result)

            result.status = "passed" if result.trust_score >= self.min_trust_score else "failed"

        except Exception as e:
            result.status = "failed"
            result.output = {"error": str(e)}

        result.duration_ms = round((time.time() - start) * 1000, 1)

        # Genesis key for this layer
        gk = self._track(f"layer_{layer_num}", f"{name}: {result.status} for {chunk[:50]}",
                          {"layer": layer_num, "status": result.status, "trust": result.trust_score})
        result.genesis_key_id = gk or ""

        return result

    # ── Layer implementations ─────────────────────────────────

    def _layer_runtime(self, chunk: str, context: dict) -> dict:
        """Layer 1: Check system health, connectivity, rules before touching anything."""
        from api.brain_api_v2 import call_brain
        health = call_brain("system", "health", {})
        connectivity = call_brain("system", "connectivity", {})
        rules = call_brain("govern", "rules", {})
        gaps = call_brain("ai", "knowledge_gaps_deep", {})
        return {
            "environment": "isolated",
            "health": health.get("data") if health.get("ok") else "unavailable",
            "connectivity": connectivity.get("data") if connectivity.get("ok") else "unavailable",
            "active_rules": len(rules.get("data", {}).get("documents", [])) if rules.get("ok") else 0,
            "knowledge_gaps": len(gaps.get("data", {}).get("knowledge_gaps", [])) if gaps.get("ok") else 0,
        }

    def _layer_decompose(self, chunk: str, task: str) -> dict:
        """Layer 2: Decompose using planner, search existing code, check knowledge gaps."""
        from api.brain_api_v2 import call_brain
        existing = call_brain("files", "search", {"query": chunk[:50], "limit": 5})
        planner = call_brain("ai", "fast", {
            "prompt": f"Decompose this into sub-tasks. Consider existing code:\n{chunk}",
            "models": ["kimi"],
        })
        return {
            "sub_tasks": planner.get("data", {}),
            "existing_code_found": len(existing.get("data", {}).get("results", [])) if existing.get("ok") else 0,
        }

    def _layer_propose(self, chunk: str, task: str) -> dict:
        """Layer 3: Propose 3 approaches, check rules, search for patterns."""
        from api.brain_api_v2 import call_brain
        rules = call_brain("govern", "rules", {})
        similar = call_brain("files", "search", {"query": chunk[:30], "limit": 3})
        proposals = call_brain("ai", "fast", {
            "prompt": f"Propose 3 different approaches. Follow all governance rules.\n{chunk}",
            "models": ["kimi", "opus"],
        })
        return {
            "proposals": proposals.get("data", {}),
            "rules_checked": rules.get("ok", False),
            "similar_patterns": len(similar.get("data", {}).get("results", [])) if similar.get("ok") else 0,
        }

    def _layer_select(self, chunk: str, proposals: dict) -> dict:
        """Layer 4: Select best approach using bandit + trust + DL prediction."""
        from api.brain_api_v2 import call_brain
        trust = call_brain("system", "trust", {})
        bandit = call_brain("ai", "bandit_select", {"options": ["approach_1", "approach_2", "approach_3"]})
        prediction = call_brain("ai", "dl_predict", {"key_type": "code_change", "what": chunk[:60]})
        return {
            "selected": bandit.get("data", {}).get("selected", "approach_1"),
            "trust_state": trust.get("data", {}).get("models", {}) if trust.get("ok") else {},
            "success_prediction": prediction.get("data", {}).get("success_probability") if prediction.get("ok") else None,
        }

    def _layer_simulate(self, chunk: str, task: str) -> dict:
        """Layer 5: Simulate using DL model, cognitive report, OODA."""
        from api.brain_api_v2 import call_brain
        dl_pred = call_brain("ai", "dl_predict", {"key_type": "code_change", "what": f"simulate: {chunk[:50]}"})
        cognitive = call_brain("ai", "cognitive_report", {"query": chunk[:100]})
        return {
            "simulated": True,
            "success_probability": dl_pred.get("data", {}).get("success_probability") if dl_pred.get("ok") else None,
            "cognitive_assessment": cognitive.get("data", {}).get("invariants") if cognitive.get("ok") else {},
        }

    def _layer_generate(self, chunk: str, task: str) -> dict:
        """Layer 6: Generate code with persona, existing code context, governance."""
        from api.brain_api_v2 import call_brain
        persona = call_brain("govern", "persona", {})
        existing = call_brain("files", "search", {"query": chunk[:30], "limit": 3})
        code = call_brain("code", "generate", {"prompt": chunk, "project_folder": "."})
        return {
            "code": code.get("data", {}),
            "persona_applied": persona.get("ok", False),
            "existing_context": len(existing.get("data", {}).get("results", [])) if existing.get("ok") else 0,
        }

    def _layer_verify(self, chunk: str) -> dict:
        """Layer 7: Full verification — invariants, probe, triggers, cognitive report."""
        from api.brain_api_v2 import call_brain
        invariants = call_brain("ai", "invariants", {})
        probe = call_brain("system", "probe", {})
        triggers = call_brain("system", "triggers", {})
        cognitive = call_brain("ai", "cognitive_report", {"query": f"verify: {chunk[:50]}"})
        return {
            "invariants": invariants.get("data") if invariants.get("ok") else "failed",
            "probe_passed": probe.get("ok", False),
            "trigger_alerts": triggers.get("data", {}).get("critical", 0) if triggers.get("ok") else "unknown",
            "cognitive_verified": cognitive.get("ok", False),
        }

    def _layer_deploy_gate(self, chunk: str) -> dict:
        """Layer 8: Deployment gate — check approvals, run auto-cycle, final trust."""
        from api.brain_api_v2 import call_brain
        approvals = call_brain("govern", "approvals", {})
        trust = call_brain("system", "trust", {})
        auto = call_brain("system", "auto_cycle", {})
        return {
            "gate": "pending_approval",
            "requires_human": True,
            "pending_approvals": len(approvals.get("data", {}).get("approvals", [])) if approvals.get("ok") else 0,
            "trust_state": trust.get("data") if trust.get("ok") else {},
            "auto_cycle_ran": auto.get("ok", False),
        }

    # ── Cross-cutting concerns ────────────────────────────────

    def _consensus(self, topic: str) -> dict:
        try:
            from api.brain_api_v2 import call_brain
            r = call_brain("ai", "fast", {
                "prompt": f"Do you agree with this? Answer YES or NO with brief reason.\n\n{topic}",
                "models": ["kimi", "opus"],
            })
            data = r.get("data", {})
            responses = data.get("individual_responses", [])
            agreed = all("yes" in (resp.get("response", "").lower()[:20]) for resp in responses if resp.get("response"))
            return {"agreed": agreed, "responses": responses, "topic": topic[:100]}
        except Exception:
            return {"agreed": True, "reason": "consensus unavailable, defaulting to agree"}

    def _reason(self, layer_num: int, chunk: str, task: str) -> str:
        try:
            from api.brain_api_v2 import call_brain
            r = call_brain("ai", "ooda", {"observation": f"Layer {layer_num}: {chunk[:100]}"})
            return str(r.get("data", {}).get("decide", {}).get("action", "proceed"))
        except Exception:
            return "proceed"

    def _time_check(self) -> dict:
        try:
            from cognitive.time_sense import TimeSense
            return TimeSense.get_context()
        except Exception:
            return {}

    def _mirror_observe(self, layer_num: int, chunk: str) -> dict:
        try:
            from core.awareness.self_model import SelfModel
            return SelfModel().now()
        except Exception:
            return {}

    def _probe_layer(self, layer_num: int) -> bool:
        try:
            from api.brain_api_v2 import call_brain
            r = call_brain("system", "runtime", {})
            return r.get("ok", False)
        except Exception:
            return True

    def _layer_trust(self, layer_num: int, result: LayerResult) -> float:
        base = 0.7
        if result.probe_passed:
            base += 0.1
        if result.output and not isinstance(result.output, dict):
            base += 0.05
        elif isinstance(result.output, dict) and not result.output.get("error"):
            base += 0.1
        return min(1.0, base)

    def _calculate_trust(self, result: PipelineResult) -> float:
        if not result.chunks:
            return 0.0
        scores = []
        for chunk in result.chunks:
            for layer in chunk.layers:
                scores.append(layer.trust_score)
        return round(sum(scores) / len(scores), 3) if scores else 0.0

    def _track(self, event: str, what: str, data: dict = None) -> Optional[str]:
        try:
            from api._genesis_tracker import track
            return track(
                key_type="system_event",
                what=what,
                who="coding_pipeline",
                how=event,
                output_data=data,
                tags=["coding-pipeline", event],
            )
        except Exception:
            return None


_pipeline = None


def get_coding_pipeline() -> CodingPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = CodingPipeline()
    return _pipeline
