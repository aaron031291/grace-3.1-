# Multi-file Semantic Refactoring - IMPLEMENTED ✅

## Overview

The semantic refactoring engine has been fully implemented, completing the #2 gap in the self-healing capabilities:

| # | Feature | Status |
|---|---------|--------|
| 1 | Plan → Patch → Validate → Rollback | ✅ Already Implemented |
| 2 | **Multi-file semantic refactoring** | ✅ **NOW IMPLEMENTED** |
| 3 | Proactive drift detection | ✅ Already Implemented |
| 4 | Outcome-based learning | ✅ Already Implemented |
| 5 | CI/CD pre-commit healing | ✅ Already Implemented |
| 6 | Runtime healing recipes | ✅ Already Implemented |
| 7 | Healing SLO metrics | ✅ Already Implemented |

## New Files Created

### 1. `backend/cognitive/semantic_refactoring_engine.py`
The core engine providing:
- **SymbolFinder**: AST-based symbol reference discovery
- **ImportAnalyzer**: Analyzes import statements for module moves
- **SemanticRefactoringEngine**: Main engine with:
  - `find_symbol_references()` - Find all references to a symbol
  - `plan_rename_symbol()` - Create a rename plan
  - `plan_move_module()` - Create a module move plan
  - `execute_plan()` - Execute with validation and rollback
  - `rollback_plan()` - Rollback a completed plan

### 2. `backend/api/semantic_refactoring_api.py`
REST API endpoints:
- `POST /api/refactoring/rename` - Rename symbols across codebase
- `POST /api/refactoring/move-module` - Move modules with import updates
- `POST /api/refactoring/find-references` - Find all symbol references
- `GET /api/refactoring/plans` - List all refactoring plans
- `GET /api/refactoring/plans/{plan_id}` - Get plan status
- `POST /api/refactoring/plans/{plan_id}/execute` - Execute a plan
- `POST /api/refactoring/plans/{plan_id}/rollback` - Rollback a plan

### 3. `backend/tests/test_semantic_refactoring.py`
Comprehensive test suite covering:
- Symbol reference finding
- Rename planning and execution
- Module move planning
- Dry run vs actual execution
- Rollback functionality

## Integration with Self-Healing

### New Healing Action
Added `SEMANTIC_REFACTOR` to `HealingAction` enum in `autonomous_healing_system.py`:
```python
class HealingAction(str, Enum):
    ...
    SEMANTIC_REFACTOR = "semantic_refactor"  # Level 3: Multi-file symbol rename/move
```

### Trust Score
Configured with trust score of 0.70 (multi-file changes with validation):
```python
HealingAction.SEMANTIC_REFACTOR: 0.70,  # Multi-file refactoring with validation
```

### Execution Handler
The `_execute_semantic_refactor()` method handles:
- Symbol renames across the codebase
- Module moves with automatic import updates
- Genesis Key creation for audit trail
- Automatic rollback on validation failure

## Usage Examples

### 1. Rename a Symbol (API)
```bash
curl -X POST http://localhost:8000/api/refactoring/rename \
  -H "Content-Type: application/json" \
  -d '{
    "old_name": "helper_function",
    "new_name": "utility_function",
    "symbol_type": "function",
    "dry_run": false
  }'
```

### 2. Move a Module (API)
```bash
curl -X POST http://localhost:8000/api/refactoring/move-module \
  -H "Content-Type: application/json" \
  -d '{
    "source_module": "cognitive.old_module",
    "target_module": "cognitive.utils.new_module",
    "dry_run": true
  }'
```

### 3. Find References (API)
```bash
curl -X POST http://localhost:8000/api/refactoring/find-references \
  -H "Content-Type: application/json" \
  -d '{
    "symbol_name": "MyClass",
    "symbol_type": "class"
  }'
```

### 4. Via Self-Healing System
```python
from cognitive.autonomous_healing_system import AutonomousHealingSystem, HealingAction

healing_system = AutonomousHealingSystem(session)

# Trigger semantic refactor via anomaly
anomaly = {
    "refactor_type": "rename",
    "old_name": "deprecated_function",
    "new_name": "new_function",
    "symbol_type": "function",
    "reason": "API deprecation fix"
}

result = healing_system._execute_semantic_refactor(anomaly, "system")
```

## Features

### Safety Mechanisms
1. **Backup Creation**: All affected files are backed up before modifications
2. **Syntax Validation**: Patches are validated via AST before application
3. **Validation Pipeline**: Integrates with HealingValidationPipeline
4. **Automatic Rollback**: Restores files on validation failure
5. **Dry Run Mode**: Test changes without applying

### Capabilities
- ✅ Rename functions across all files
- ✅ Rename classes with import updates
- ✅ Rename methods within class scope
- ✅ Move modules to new locations
- ✅ Update all import statements automatically
- ✅ Handle relative and absolute imports
- ✅ Preserve code formatting
- ✅ Track changes with Genesis Keys

### Limitations
- Does not support renaming local variables (would need scope analysis)
- String-based references (e.g., in docstrings) are not updated
- Does not support cross-language refactoring

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    REST API Layer                            │
│  semantic_refactoring_api.py                                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              SemanticRefactoringEngine                       │
│  semantic_refactoring_engine.py                             │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ SymbolFinder │  │ImportAnalyzer│  │ RefactoringPlan  │   │
│  │ (AST-based)  │  │              │  │                  │   │
│  └──────────────┘  └──────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│            HealingValidationPipeline                         │
│  healing_validation_pipeline.py                             │
│                                                              │
│  Plan → Patch → Validate → Rollback                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│            AutonomousHealingSystem                           │
│  autonomous_healing_system.py                               │
│                                                              │
│  SEMANTIC_REFACTOR action handler                           │
└─────────────────────────────────────────────────────────────┘
```

## Summary

All 7 self-healing capabilities are now fully implemented:

1. ✅ **Plan → Patch → Validate → Rollback** - Full validation pipeline
2. ✅ **Multi-file semantic refactoring** - NEW: Symbol rename, module moves
3. ✅ **Proactive drift detection** - Scheduled scans, healing queue
4. ✅ **Outcome-based learning** - Fix success tracking, pattern reuse
5. ✅ **CI/CD pre-commit healing** - Auto-fix on commit
6. ✅ **Runtime healing recipes** - Circuit breakers, canary rollbacks
7. ✅ **Healing SLO metrics** - MTTR, success rate tracking
