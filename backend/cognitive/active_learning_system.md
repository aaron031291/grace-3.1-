# Active Learning System

**File:** `cognitive/active_learning_system.py`

## Overview

Grace Active Learning System

Transforms passive RAG into active learning where Grace:
1. Studies training materials from AI research folder
2. Practices skills in the sandbox environment
3. Learns from successes and failures
4. Builds persistent knowledge and abilities

Architecture:
- AI Research Folder = Curriculum (what to learn)
- Cognitive Framework = How to think and learn
- Learning Memory = What has been learned
- Sandbox = Practice environment
- File Manager = Her world to interact with

## Classes

- `TrainingSession`
- `SkillLevel`
- `GraceActiveLearningSystem`

## Key Methods

- `study_topic()`
- `practice_skill()`
- `extract_learning_patterns()`
- `create_training_curriculum()`
- `get_skill_assessment()`

## Database Tables

None

## Connects To

- `cognitive.engine`
- `cognitive.learning_memory`
- `cognitive.predictive_context_loader`
- `database.session`
- `genesis.genesis_key_service`
- `retrieval.retriever`

---
*Documentation for Grace 3.1*
