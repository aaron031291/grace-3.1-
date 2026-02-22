# Cicd Versioning

**File:** `genesis/cicd_versioning.py`

## Overview

CI/CD Pipeline Version Control
==============================
Version control for all pipeline mutations.
Tracks every change with Genesis Keys for full audit trail.

## Classes

- `MutationType`
- `PipelineVersion`
- `PipelineVersionHistory`
- `CICDVersionControl`

## Key Methods

- `record_mutation()`
- `get_version()`
- `get_history()`
- `get_all_histories()`
- `diff_versions()`
- `rollback()`
- `get_genesis_keys()`
- `export_history()`
- `get_version_control()`
- `on_pipeline_create()`
- `on_pipeline_update()`
- `on_pipeline_delete()`

## DB Tables

None

---
*Grace 3.1 Documentation*
