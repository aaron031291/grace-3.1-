# Governance

**File:** `security/governance.py`

## Overview

Grace Governance - Constitutional AI Framework

Layer-1 + Layer-2 runtime-wired governance system integrating with:
- Layer1 Message Bus for component coordination
- Cognitive Enforcer for OODA invariants
- Genesis Keys for audit trails
- Security Config for policy settings
- KPI Tracker for metrics-driven governance
- Telemetry for uptime and SLA enforcement

Constitutional DNA provides immutable rules that cannot be overridden.
Policy Engine provides runtime-configurable governance checks.
Metrics Engine tracks KPIs for governance decisions.

## Classes

- `ConstitutionalRule`
- `ConstitutionalRuleMeta`
- `AutonomyTier`
- `AutonomyTierConfig`
- `SLATier`
- `SLAConfig`
- `ActionCategory`
- `ActionTrustRequirement`
- `CapabilityProgress`
- `ApprovalRecord`
- `ViolationEscalation`
- `TrustDecayConfig`
- `QuarantinedResource`
- `ComplianceStandard`
- `ComplianceRequirement`
- `MetricSample`
- `GovernanceKPI`
- `GovernanceMetrics`
- `GovernanceContext`
- `GovernanceViolation`
- `GovernanceDecision`
- `PolicyRule`
- `GovernanceEngine`
- `GovernanceConnector`

## Key Methods

- `record_latency()`
- `record_operation()`
- `record_learning_event()`
- `record_confidence()`
- `record_hallucination()`
- `update_component_health()`
- `update_trust_score()`
- `record_sla_violation()`
- `check_kpi_health()`
- `get_all_kpi_health()`
- `check_compliance()`
- `get_dashboard_data()`
- `check_constitutional_rules()`
- `add_policy_rule()`
- `remove_policy_rule()`
- `check_policy_rules()`
- `check_autonomy_tier()`
- `set_autonomy_tier()`
- `adjust_trust_score()`
- `assign_sla()`
- `check_sla_compliance()`
- `get_component_sla_status()`
- `check_all_compliance()`
- `enforce_learning_standards()`
- `check_capability()`

## Database Tables

None

## Connects To

- `security.config`

---
*Documentation for Grace 3.1*
