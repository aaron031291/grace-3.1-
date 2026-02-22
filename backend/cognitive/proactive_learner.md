# Proactive Learner

**File:** `cognitive/proactive_learner.py`

## Overview

Proactive Background Learning System

Grace learns automatically in the background when new training data arrives.

Key Features:
- File system monitoring for new documents
- Automatic ingestion + study when files detected
- Multi-processing for parallel learning
- Subagent architecture for autonomous operation
- Background task queue for async learning
- Progress tracking and reporting

## Classes

- `LearningTask`
- `LearningProgress`
- `FileMonitorHandler`
- `ProactiveLearningSubagent`
- `ProactiveLearningOrchestrator`

## Key Methods

- `on_created()`
- `on_modified()`
- `start()`
- `stop()`
- `get_status()`
- `start()`
- `stop()`
- `add_learning_task()`
- `get_status()`

## Database Tables

None

## Connects To

- `cognitive.active_learning_system`
- `cognitive.learning_hook`
- `database.session`
- `embedding`
- `genesis.layer1_integration`
- `ingestion.service`
- `models.database_models`
- `retrieval.retriever`

---
*Documentation for Grace 3.1*
