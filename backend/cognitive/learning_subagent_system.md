# Learning Subagent System

**File:** `cognitive/learning_subagent_system.py`

## Overview

Multi-Process Learning Subagent System

Complete autonomous learning architecture running as independent processes.

Architecture:
- Master Process: Orchestrates learning subagents
- Study Subagents: Autonomous concept extraction (multi-process)
- Practice Subagents: Skill execution and validation (multi-process)
- Mirror Subagent: Self-reflection and gap identification (dedicated process)
- Trust Scorer Subagent: Continuous trust score updates (dedicated process)
- Predictive Context Subagent: Pre-fetching and caching (dedicated process)

All subagents run independently in background with IPC via queues.

## Classes

- `TaskType`
- `MessageType`
- `LearningTask`
- `Message`
- `NullRetriever`
- `BaseSubagent`
- `StudySubagent`
- `PracticeSubagent`
- `MirrorSubagent`
- `LearningOrchestrator`

## Key Methods

- `to_dict()`
- `from_dict()`
- `to_dict()`
- `from_dict()`
- `retrieve()`
- `start()`
- `stop()`
- `start()`
- `stop()`
- `submit_study_task()`
- `submit_practice_task()`
- `get_status()`

---
*Grace 3.1*
