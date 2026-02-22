# Cicd

**File:** `genesis/cicd.py`

## Overview

Genesis Key CI/CD Pipeline System
=================================
Self-hosted CI/CD pipeline powered by Genesis Keys.
No external dependencies - fully autonomous build/test/deploy.

Genesis Key Actions for CI/CD:
- PIPELINE_TRIGGER: Initiates a pipeline run
- PIPELINE_STAGE: Executes a pipeline stage
- PIPELINE_COMPLETE: Marks pipeline completion
- BUILD_ARTIFACT: Creates build artifacts
- TEST_EXECUTION: Runs test suites
- DEPLOYMENT: Handles deployments

## Classes

- `PipelineStatus`
- `StageType`
- `StageResult`
- `PipelineStage`
- `Pipeline`
- `PipelineRun`
- `GenesisKeyAction`
- `GenesisCICD`

## Key Methods

- `get_pipeline()`
- `get_run()`
- `list_pipelines()`
- `list_runs()`
- `register_pipeline()`
- `get_genesis_keys()`
- `get_cicd()`

## DB Tables

None

---
*Grace 3.1 Documentation*
