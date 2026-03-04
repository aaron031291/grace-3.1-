# Technical Spec — Item 16: Cognitive Partner System

## The Core Idea

Grace doesn't just answer questions. She thinks alongside you.
She maps your cognitive patterns, follows your context drift in real-time,
verifies logic silently in the background, intervenes when you drift off-path,
offers alternative perspectives, and reverse-engineers from your goal to
show you the steps — even when you haven't articulated them linearly.

This is Grace's identity. Not a feature — a mode of being.

---

## Architecture: 3 Layers

### Layer 1: Cognitive Pattern Mapper
**What it does:** Learns HOW each user thinks. Not what they think about — their cognitive style.

**Implementation:**
- Track context transitions in every conversation via genesis keys
- Build a per-user cognitive profile:
  - Thinking style: divergent / linear / iterative / exploratory
  - Pattern: how many tangents before returning to core topic
  - Peak creativity windows (via TimeSense)
  - Topics that cluster together in this user's world
  - Decision-making pattern: gut-first-then-validate or research-first-then-decide
- Store profile in Magma entity graph (user node → cognitive_style edges)
- Mirror Self-Model analyses the profile and refines it over time
- Profile feeds into the pipeline's OODA stage for every interaction

**Connected to:**
- Genesis Keys (tracks every interaction)
- Magma Memory (stores cognitive profiles)
- Mirror Self-Model (refines understanding of user)
- TimeSense (peak hours, rhythm patterns)
- Episodic Memory (concrete past interaction experiences)

---

### Layer 2: Drift Detection with Silent Verification
**What it does:** Follows the user's thinking flow. Verifies logic in background.
Intervenes ONLY when drift breaks the connection to the goal.

**Implementation:**
- Adaptive Context Graph tracks topic transitions in real-time
- For each transition A → B:
  1. Score relevance: how connected is B to the original goal?
  2. Score creativity: is this a productive tangent or noise?
  3. Score logic: does the reasoning chain hold?
- Verification runs silently (background calls):
  - Kimi: "Is this reasoning chain logically sound?"
  - Opus: "Does this direction lead toward the stated goal?"
  - RAG: "Does our knowledge base support this connection?"
  - Web search: "Is this factually accurate?"
- Trust Engine scores the verification results
- If verification passes: let the drift continue, store the connection
- If verification fails softly: note it, wait for user to self-correct
- If verification fails hard: intervene with:
  "I see where you're going. The logic holds to here, but [specific issue].
   Here's an alternative that gets you to the same place: [alternative]"

**Connected to:**
- Adaptive Context Graph (real-time flow tracking)
- Kimi Enhanced (reasoning verification)
- Opus Client (logic checking)
- RAG Retrieval (knowledge verification)
- Web Search / APIs (external validation)
- Trust Engine (score verification confidence)
- Hallucination Guard (verify claims)
- Governance Rules (stay within bounds)
- KPI Tracker (track drift detection accuracy)

---

### Layer 3: Multi-Perspective Synthesis
**What it does:** When the user arrives at an idea, Grace generates 2-3
alternative perspectives. Reverse-engineers from the goal to show paths.

**Implementation:**
- Extract the user's implicit goal from conversation history
- Generate the user's current approach as Path A
- Query Kimi for alternative approach (Path B)
- Query Opus for a third perspective (Path C)
- For each path:
  1. Steps to reach the goal
  2. Trade-offs (speed, quality, risk, complexity)
  3. What this path assumes (ambiguity ledger)
  4. Where this path might fail (invariant check)
- Rank paths by alignment with user's cognitive style
- Present: "Your approach works. Here are two alternatives I see..."
- If user's path has a logical break: "I think you're solving [X] but
  the real problem might be [Y]. Here's why..."

**Connected to:**
- Kimi Enhanced (alternative perspective 1)
- Opus Client (alternative perspective 2)
- Local LLM (user's current perspective synthesis)
- Ambiguity Ledger (what each path assumes)
- Invariant Validator (where each path might fail)
- Procedural Memory (what worked before in similar situations)
- Episodic Memory (past decisions and their outcomes)
- Neuro-Symbolic Reasoner (logical validation of each path)
- Feedback Loop (learn which paths user prefers)

---

## Persistent Voice Integration

The cognitive partner works through persistent voice — not just text.
Bi-directional conversation where Grace can:
- Listen as you think out loud
- Process in real-time (not wait for you to finish)
- Interject when she has something valuable (not just when asked)
- Use tone to indicate confidence level

**Implementation:**
- Voice input via existing `/voice` STT endpoint
- Continuous listening mode (not push-to-talk)
- Real-time transcription feeds into Adaptive Context Graph
- Grace responds via TTS with natural conversation flow
- "Thinking" indicators — Grace says "I'm checking something" while
  background verification runs
- Proactive interjection: "Can I offer a thought?" when she sees
  a better path or a logical issue

**Connected to:**
- Voice API (STT/TTS)
- PersistentVoicePanel (frontend)
- Adaptive Context Graph (real-time processing)
- All verification systems (background)

---

## Connection to Planner (Tasks Tab)

The cognitive partner feeds directly into the Planner:
- Conversations distill into actionable tasks
- Grace says: "Based on what we discussed, here are the tasks I'd suggest"
- Tasks auto-created in the planner with priority from the conversation
- Multi-model consensus from the planning discussion carries forward
- Each task links back to the conversation that generated it (via genesis key)

**Connected to:**
- Tasks Hub (task creation)
- Planner sub-tab (consensus discussions)
- TimeSense (scheduling based on conversation patterns)
- Genesis Keys (link tasks to conversations)

---

## Connection to Task Management

The cognitive partner is aware of all active tasks:
- "You're working on X but we discussed Y yesterday — are they related?"
- Surfaces relevant past discussions when you start a new task
- Tracks progress across tasks and conversations
- "You seem stuck on this. Last time you were stuck, you took a break
  and came back with the solution. Want to switch to something else?"

**Connected to:**
- Tasks Hub (active tasks)
- Episodic Memory (past working patterns)
- Cognitive Pattern Mapper (user's stuck/flow patterns)
- TimeSense (optimal work periods)

---

## Full Connection Map

The Cognitive Partner connects to:

| System | How it's used |
|---|---|
| Genesis Keys | Tracks every interaction for pattern building |
| Magma Memory | Stores cognitive profiles, context connections |
| Mirror Self-Model | Refines understanding of user over time |
| TimeSense | Peak hours, rhythm, work patterns |
| Adaptive Context Graph | Real-time topic flow tracking |
| Kimi Enhanced | Reasoning verification + alternative perspectives |
| Opus Client | Logic checking + deep analysis + auditing |
| Local LLM (32B/70B) | Fast synthesis + code generation |
| RAG Retrieval | Knowledge verification |
| Web Search / APIs | External validation |
| Trust Engine | Score verification confidence |
| Hallucination Guard | Verify claims in real-time |
| Governance Rules | Stay within domain bounds |
| KPI Tracker | Track partner accuracy over time |
| Ambiguity Ledger | Track assumptions in each path |
| Invariant Validator | Check where paths might fail |
| Episodic Memory | Past interactions and outcomes |
| Procedural Memory | What worked before |
| Neuro-Symbolic Reasoner | Logical validation |
| Feedback Loop | Learn user preferences |
| Voice API | Persistent bi-directional voice |
| Tasks Hub / Planner | Distill conversations into tasks |
| OODA Loop | Decision framework for interventions |
| Cognitive Pipeline | Full 9-stage processing |
| Immune System | System health context |
| HUNTER Assimilator | When partner identifies code to build |

**26 systems connected.** This is the integration point for the entire platform.

---

## Estimated Effort

| Component | Hours |
|---|---|
| Cognitive Pattern Mapper | 8-10 |
| Adaptive Context Graph | 10-12 |
| Drift Detection + Verification | 8-10 |
| Multi-Perspective Synthesis | 6-8 |
| Persistent Voice Integration | 6-8 |
| Planner + Task Management Connection | 4-6 |
| Testing + Integration | 8-10 |
| **Total** | **50-64 hours** |

---

## Why This Matters

Every AI assistant answers questions.
No AI assistant thinks alongside you.

Grace doesn't just respond — she observes your thinking patterns,
follows your context drift, silently verifies the logic, catches
when you're going off-path, offers alternatives from multiple
perspectives, and reverse-engineers the goal you're reaching for
even when you haven't said it yet.

This is what makes Grace a cognitive partner, not a tool.
This is what makes her understand neurodivergent thinking as a feature.
This is what no other AI platform has.
