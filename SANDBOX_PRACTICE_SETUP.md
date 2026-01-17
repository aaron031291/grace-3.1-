# Sandbox Practice Environment Setup

## Summary

The self-healing pipeline and coding agent have been moved back into a sandbox practice environment where they can practice together safely without affecting production systems.

## What Was Created

### 1. Sandbox Practice Script
**File**: `scripts/sandbox_practice_healing_and_coding.py`

A comprehensive sandbox environment that:
- Creates isolated directories for each practice session
- Initializes both systems in sandbox mode
- Provides practice scenarios for healing and coding
- Tracks all practice sessions with metrics
- Generates reports for review

### 2. Quick Start Script
**File**: `scripts/start_sandbox_practice.py`

Simple launcher script for quick access to practice sessions.

### 3. API Integration
**File**: `backend/api/sandbox_lab.py` (updated)

Added endpoints:
- `POST /sandbox-lab/practice/start` - Start a practice session
- `GET /sandbox-lab/practice/sessions` - List all practice sessions

### 4. Documentation
**File**: `scripts/SANDBOX_PRACTICE_README.md`

Complete documentation on using the sandbox practice environment.

## How to Use

### Quick Start

```bash
# Run practice session
python scripts/start_sandbox_practice.py
```

### Via API

```bash
# Start practice session
curl -X POST http://localhost:8000/sandbox-lab/practice/start

# List sessions
curl http://localhost:8000/sandbox-lab/practice/sessions
```

### Programmatic Usage

```python
from scripts.sandbox_practice_healing_and_coding import SandboxPracticeEnvironment

sandbox = SandboxPracticeEnvironment()
sandbox.initialize_database()
healing_system = sandbox.initialize_healing_system()
coding_agent = sandbox.initialize_coding_agent()

# Practice scenarios...
```

## Practice Scenarios Included

1. **Coding Agent - Code Generation**
   - Generate code from descriptions
   - Test code quality

2. **Self-Healing - Fix Issues**
   - Detect code issues
   - Practice healing strategies

3. **Collaboration**
   - Coding agent generates code
   - Healing agent fixes issues
   - End-to-end workflows

4. **Code Review & Fix**
   - Review generated code
   - Fix quality issues

## Key Features

- **Isolated**: Each session runs in its own directory
- **Safe**: No production impact
- **Tracked**: All sessions logged with metrics
- **Reviewable**: Reports generated for each session
- **Collaborative**: Both systems can work together

## Sandbox Structure

```
sandbox_<ID>/
├── code/           # Practice code files
├── tests/          # Test files  
├── logs/           # Session logs
└── results/        # Session results
    ├── session_<ID>.json
    └── report_<ID>.txt
```

## Configuration

The sandbox uses conservative settings:
- **Trust Level**: `LOW_RISK_AUTO` (more conservative than production)
- **Learning**: Enabled (systems learn from practice)
- **Sandbox Mode**: Enabled (prevents production changes)

## Next Steps

1. Run practice sessions regularly to improve systems
2. Review session reports to identify improvements
3. Use successful practices to propose experiments in Sandbox Lab
4. Promote validated practices through the experiment lifecycle

## Integration with Sandbox Lab

The practice environment integrates with the Autonomous Sandbox Lab:
- Practice sessions can propose experiments
- Successful practices enter sandbox testing
- Validated practices start 90-day trials
- Approved practices promote to production

## Files Created/Modified

- ✅ `scripts/sandbox_practice_healing_and_coding.py` - Main practice environment
- ✅ `scripts/start_sandbox_practice.py` - Quick launcher
- ✅ `scripts/SANDBOX_PRACTICE_README.md` - Documentation
- ✅ `backend/api/sandbox_lab.py` - Added practice endpoints
- ✅ `SANDBOX_PRACTICE_SETUP.md` - This file

## Status

✅ **Complete** - Self-healing pipeline and coding agent are now in sandbox practice mode and ready for safe testing and improvement.
