# Testing Api

**File:** `api/testing_api.py`

## Overview

Autonomous Testing API - Self-testing with KPI and Trust Score validation.

Enables Grace to autonomously test her implementations with governance:
- Run tests against KPI thresholds
- Validate trust scores before integration
- Track all test activities with Genesis Keys
- Sandbox execution for safety

## Classes

- `TestRequest`
- `TestGenerationRequest`
- `TestValidationRequest`
- `IntegrationRequest`
- `KPICheckRequest`
- `DiagnosticReport`

## Key Methods

- `calculate_trust_score()`
- `validate_against_kpis()`

---
*Grace 3.1*
