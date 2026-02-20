# Adaptive Cicd

**File:** `genesis/adaptive_cicd.py`

## Overview

Adaptive CI/CD Pipeline System
==============================
Intelligent, self-improving CI/CD with:
- Trust scores for pipeline reliability
- KPI tracking and performance metrics
- LLM orchestration for intelligent decisions
- Sandbox testing before production
- Governance integration for human oversight

GRACE can autonomously trigger pipelines based on her needs,
test in sandbox, and request human approval via governance.

## Classes

- `PipelineTrustLevel`
- `AdaptiveTriggerReason`
- `GovernanceAction`
- `PipelineTrustScore`
- `PipelineKPIs`
- `AdaptiveTrigger`
- `GovernanceRequest`
- `AdaptiveCICD`

## Key Methods

- `calculate_trust_score()`
- `record_run_result()`
- `calculate_kpis()`
- `approve_governance_request()`
- `get_dashboard_data()`
- `get_adaptive_cicd()`

## DB Tables

None

---
*Grace 3.1 Documentation*
