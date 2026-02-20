# Governance Api

**File:** `api/governance_api.py`

## Overview

Governance API - Three Pillar Framework with Real Database Integration

Provides endpoints for:
1. Uploadable Governance Documents (industry rules, ISO compliance, standards)
2. Three Governance Pillars (Operational, Behavioral, Immutable)
3. Human-in-the-Loop Decision Review (pending, confirm, discuss, deny)
4. Rule management and KPI-driven governance

Integrates with:
- Database models for persistence
- security/governance.py GovernanceEngine for real enforcement

## Classes

- `GovernanceRuleCreate`
- `GovernanceRuleUpdate`
- `RuleToggle`
- `DecisionAction`
- `GovernanceCheckRequest`

## Key Methods

- `seed_default_rules()`
- `extract_rules_from_document()`

---
*Grace 3.1*
