# Kimi Brain

**File:** `cognitive/kimi_brain.py`

## Overview

Kimi Brain - READ-ONLY Intelligence Layer

Kimi is another brain. She does NOT execute anything.
She READS Grace's cognitive systems, ANALYZES problems,
and produces INSTRUCTIONS that Grace then verifies and executes.

Architecture:
    ┌──────────────────────────────────────────────────────┐
    │                    KIMI (READ-ONLY)                   │
    │                                                       │
    │  Reads:                     Produces:                │
    │  - Self-Mirroring          - Diagnosis               │
    │  - Self-Modeling           - Instructions             │
    │  - Time Sense / OODA       - Fix Recommendations     │
    │  - Self-Healing state      - Learning Priorities      │
    │  - Learning Progress       - Pattern Observations     │
    │  - Diagnostic Machine      - Architecture Suggestions │
    │  - Knowledge Base                                     │
    │                                                       │
    └───────────────────────┬──────────────────────────────┘
                            │ Instructions (read-only output)
                            ▼
    ┌──────────────────────────────────────────────────────┐
    │                 GRACE (VERIFIES & EXECUTES)           │
    │                                                       │
    │  1. Receives Kimi's instructions                     │
    │  2. Runs through OODA loop                           │
    │  3. Verifies via governance/trust                    │
    │ 

## Classes

- `InstructionType`
- `InstructionPriority`
- `KimiDiagnosis`
- `KimiInstruction`
- `KimiInstructionSet`
- `KimiBrain`

## Key Methods

- `connect_mirror()`
- `connect_diagnostics()`
- `connect_learning()`
- `connect_pattern_learner()`
- `read_system_state()`
- `diagnose()`
- `produce_instructions()`
- `get_status()`
- `get_kimi_brain()`

---
*Grace 3.1*
