# Grace 3.1 Deep Architecture Guide

## System Architecture Overview

Grace is built as a layered autonomous AI system with 481 Python modules across 16 subsystems. Every action is tracked by Genesis Keys, every output is verified by HIA (Honesty, Integrity, Accountability), and every component reports health via the Handshake Protocol.

## The 4 Cognitive Layers

### Layer 1 — Message Bus
The central nervous system. All components communicate through typed messages. Components register with the Genesis# Component Registry and send heartbeats every 60 seconds. Silent deaths are detected automatically.

### Layer 2 — Interpreters
Pattern detection across all incoming data. The Diagnostic Machine's interpreter layer identifies recurring issues, error clusters, and performance degradation patterns. Magma Memory stores these patterns in its graph structure for recall.

### Layer 3 — Judgement
Decision-making using the OODA Loop (Observe, Orient, Decide, Act) with 12 invariants enforced. The Cognitive Engine evaluates alternatives, scores them by reversibility and optionality, and logs every decision for accountability.

### Layer 4 — Action
Execution layer with progressive autonomy. Actions escalate from auto-execute (low risk) to manual approval (high risk) based on trust scores. The Autonomous Engine handles events, schedules, conditions, and self-improvement needs.

## Memory Systems

### Unified Memory (6 types)
- **Episodic**: Concrete experiences — what happened, when, outcome
- **Procedural**: Learned skills — how to do things
- **Semantic**: Facts and knowledge from the knowledge base
- **Working**: Active short-term context for current task
- **Learning**: Trust-scored training examples
- **Causal**: Cause-effect relationships

### Magma Memory
Graph-based memory with 4 relation types (semantic, temporal, causal, entity). Supports RRF fusion for multi-source retrieval, causal inference via LLM, and intent-aware routing. Persists to disk every 300 seconds.

### Memory Mesh
Distributed memory with trust scores, confidence tracking, contradiction detection, and forgetting curves. Snapshots enable point-in-time recovery.

## Self-* Agent Ecosystem

Six autonomous agents in a closed-loop improvement cycle:

1. **SelfHealingAgent** — Detects anomalies, executes 8 levels of healing actions, creates playbooks from successes
2. **SelfMirrorAgent** — Observes all operations via Genesis Keys, detects behavioral patterns
3. **SelfModelAgent** — Builds statistical models of system behavior
4. **SelfLearnerAgent** — Studies training data, practices skills, tracks retention
5. **CodeAgentSelf** — Tracks code operations, creates code playbooks
6. **SelfEvolverAgent** — Orchestrates evolution, identifies bottlenecks, switches between improve/monitor/scale modes

## Three-Layer Reasoning Pipeline

### Layer 1 — Parallel Independent Reasoning
Multiple LLMs receive the same query + training data context. Each reasons independently.

### Layer 2 — Synthesis Reasoning
Each LLM receives all Layer 1 outputs. Cross-examines, challenges, and synthesizes.

### Layer 3 — Grace Verification
Checks against training data grounding, governance rules, HIA framework, and contradiction detection.

### Reasoning Router
Automatically classifies queries into tiers:
- **Tier 0**: Instant (greetings, < 1s)
- **Tier 1**: Standard (single model + RAG, 3-8s)
- **Tier 2**: Consensus (parallel models, 10-30s)
- **Tier 3**: Deep (full 3-layer, 30-180s)

## Governance & Security

### Constitutional DNA (11 Immutable Rules)
Human Centricity, Transcendence Mission, Trust Earned, Money Before Tech, Partnership Equal, Safety First, Transparency Required, Reversibility Preferred, Honesty, Integrity, Accountability.

### HIA Framework
Every LLM output is checked for fabricated sources, inflated confidence, internal data consistency, and audit trail completeness.

### TimeSense Governance
28 SLAs across 12 component categories with 3-tier violation severity (warning/critical/breach) and auto-heal triggers.

## Unified Intelligence Table
Single source of truth collecting from 18+ subsystems every 2 minutes. The Librarian audits completeness. ML/DL can run directly on this table for predictions and anomaly detection.
