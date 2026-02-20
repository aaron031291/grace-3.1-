# Cognitive Integration

**File:** `diagnostic_machine/cognitive_integration.py`

## Overview

Cognitive Framework Integration for Diagnostic Machine

Connects diagnostic insights to GRACE's cognitive systems:
- Learning Memory: Store diagnostic patterns as learning examples
- Memory Mesh: Index patterns for retrieval
- Decision Log: Log all diagnostic decisions for observability
- Procedural Memory: Extract reusable diagnostic procedures

This closes the learning loop: diagnostics inform learning,
learning improves diagnostics.

## Classes

- `DiagnosticInsightType`
- `DiagnosticInsight`
- `DiagnosticProcedure`
- `LearningMemoryIntegration`
- `DecisionLogIntegration`
- `MemoryMeshIntegration`
- `ProceduralMemoryIntegration`
- `CognitiveIntegrationManager`

## Key Methods

- `store_pattern_insight()`
- `store_healing_insight()`
- `store_anomaly_insight()`
- `store_forensic_insight()`
- `log_diagnostic_decision()`
- `log_healing_decision()`
- `log_freeze_decision()`
- `store_diagnostic_pattern()`
- `retrieve_similar_patterns()`
- `extract_procedure_from_pattern()`
- `process_diagnostic_cycle()`
- `retrieve_relevant_knowledge()`
- `get_cognitive_manager()`

---
*Grace 3.1*
