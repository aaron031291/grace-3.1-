# Contradiction Detector

**File:** `cognitive/contradiction_detector.py`

## Overview

Contradiction Detector - Cognitive Consistency Enforcement

Addresses Clarity Class 10 (Contradiction Detection):
- Detect logical contradictions in reasoning
- Identify drift from established patterns
- Flag conflicting outputs
- Trigger AVN (Ambiguity/Validation/Negotiation) fallback

Contradiction types:
1. Logical: Direct logical contradictions in reasoning
2. Temporal: Contradictions with previous outputs
3. Constitutional: Contradictions with core rules
4. Pattern: Drift from learned patterns
5. Confidence: Overconfident claims without support

## Classes

- `ContradictionType`
- `ContradictionSeverity`
- `AVNAction`
- `Contradiction`
- `AVNResult`
- `LintResult`
- `GraceCognitionLinter`

## Key Methods

- `to_dict()`
- `to_dict()`
- `has_critical()`
- `has_high()`
- `to_dict()`
- `update_pattern_baseline()`
- `get_stats()`
- `get_cognition_linter()`
- `reset_linter()`

---
*Grace 3.1*
