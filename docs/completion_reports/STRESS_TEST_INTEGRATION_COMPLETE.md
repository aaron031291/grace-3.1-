# Stress Test Integration with Diagnostic Engine and Self-Healing System

## Overview

The stress test scheduler now alerts **both** the diagnostic engine AND the self-healing system when new problems are detected. Both systems learn from these problems and upgrade their capabilities to detect and fix them in the future.

## Integration Complete ✅

### What Was Changed

**File:** `backend/autonomous_stress_testing/scheduler.py`

### Key Features

1. **Dual Alert System**
   - When stress tests find issues, both diagnostic engine AND self-healing system are alerted
   - Issues are converted to appropriate formats for each system
   - Both systems can learn from the same problems

2. **Issue-to-Anomaly Conversion**
   - Stress test issues are converted to anomalies for self-healing system
   - Anomaly types are intelligently mapped:
     - `error`/`exception` → `ERROR_SPIKE`, `SERVICE_FAILURE`, `MEMORY_LEAK`, or `PERFORMANCE_DEGRADATION`
     - `performance`/`slow` → `PERFORMANCE_DEGRADATION`
     - `memory`/`leak` → `MEMORY_LEAK`
     - `connection`/`timeout` → `SERVICE_FAILURE`
     - `resource`/`exhaustion` → `RESOURCE_EXHAUSTION`

3. **Pattern Registration for Learning**
   - New patterns are registered with diagnostic engine for detection
   - New patterns are registered with self-healing system for healing
   - Automatic bug fixer is updated with new fix patterns
   - Both systems learn from stress test results

4. **Immediate Response for Critical Issues**
   - If pass rate < 70% or critical severity issues detected:
     - Self-healing system immediately assesses health
     - Healing actions are decided and executed autonomously (if trust allows)
     - Diagnostic engine triggers proactive scan and fixes

## Alert Flow

```
Stress Test Finds Issues
    ↓
Convert Issues to Anomalies
    ↓
┌─────────────────────────────┬─────────────────────────────┐
│   Diagnostic Engine         │   Self-Healing System       │
│   - Save to log file        │   - Add to anomaly queue    │
│   - Trigger proactive scan  │   - Assess system health    │
│   - Fix issues if critical  │   - Decide healing actions  │
│   - Register patterns       │   - Execute if trusted      │
│                             │   - Register patterns       │
└─────────────────────────────┴─────────────────────────────┘
    ↓
Register New Patterns
    ↓
Both Systems Learn & Upgrade
```

## Methods Added

### `_alert_diagnostic_engine(self, results)`
- Main alert method that coordinates both systems
- Routes to diagnostic engine and self-healing system
- Registers new patterns for learning

### `_alert_diagnostic_engine_only(self, results, issues_found, pass_rate)`
- Alerts diagnostic engine
- Saves issue summary to log file
- Triggers proactive scan if critical (pass rate < 80%)

### `_alert_self_healing_system(self, results, issues_found, pass_rate)`
- Alerts self-healing system
- Converts issues to anomalies
- Triggers immediate healing assessment if critical (pass rate < 70%)

### `_convert_issues_to_anomalies(self, issues_found, results)`
- Converts stress test issues to self-healing anomalies
- Maps issue types to anomaly types
- Preserves original issue data for context

### `_register_new_patterns(self, issues_found)`
- Registers patterns with diagnostic engine for detection
- Registers patterns with self-healing system for healing
- Updates automatic bug fixer with new fix patterns

## Learning & Upgrading

### Diagnostic Engine Learning
- New detection patterns are registered via `TestIssueIntegration`
- Patterns include message patterns, component info, and detection rules
- Diagnostic engine can now detect similar issues in future scans

### Self-Healing System Learning
- New healing patterns are registered via `TestIssueIntegration`
- System learns which healing actions work for which anomalies
- Trust scores are updated based on healing outcomes
- System improves its decision-making over time

### Automatic Bug Fixer Learning
- New fix patterns are added via `TestIssueIntegration`
- Fixer learns how to fix similar issues automatically
- Patterns include fix suggestions and auto-fixability flags

## Example Flow

1. **Stress Test Run**
   ```
   Test #42: 12/15 tests passed (80% pass rate)
   Issues Found: 3
     - Database connection timeout
     - Memory leak in cache
     - Slow API response
   ```

2. **Alert Diagnostic Engine**
   ```
   [STRESS-SCHEDULER] Alerting diagnostic engine: 3 issues found, pass rate: 80.0%
   - Saved alert to logs/diagnostic/stress_test_alert_20250116_203402.json
   - Triggering proactive scan (pass rate < 80%)
   - Proactive scan fixed 1/3 issues
   ```

3. **Alert Self-Healing System**
   ```
   [STRESS-SCHEDULER] Reporting 3 anomalies to self-healing system
   - Converting issues to anomalies:
     * Database connection timeout → SERVICE_FAILURE (database)
     * Memory leak in cache → MEMORY_LEAK
     * Slow API response → PERFORMANCE_DEGRADATION
   - Triggering immediate healing assessment (pass rate < 80%)
   - Self-healing system decided 2 healing actions
   - Executed healing action: CONNECTION_RESET, success: True
   - Executed healing action: CACHE_FLUSH, success: True
   ```

4. **Register New Patterns**
   ```
   [STRESS-SCHEDULER] Registered 3 new patterns with both systems for learning
   - Diagnostic engine can now detect similar issues
   - Self-healing system can now heal similar anomalies
   - Automatic bug fixer can now fix similar issues
   ```

## Benefits

1. **Proactive Detection**
   - Diagnostic engine learns to detect similar issues before they become critical
   - Patterns are registered so future scans catch them early

2. **Autonomous Healing**
   - Self-healing system learns which actions work for which anomalies
   - System becomes more effective at healing over time
   - Trust scores improve as healing actions succeed

3. **Continuous Improvement**
   - Both systems upgrade their capabilities automatically
   - Each stress test run makes the system smarter
   - Problems are fixed faster in future runs

4. **Unified Response**
   - Diagnostic engine fixes code-level issues
   - Self-healing system fixes runtime issues
   - Both work together to keep Grace healthy

## Configuration

The integration is enabled by default when stress test scheduler runs:

```python
# In backend/app.py
start_stress_test_scheduler(
    interval_minutes=10,
    enable_genesis_logging=True,
    enable_diagnostic_alerts=True  # Enables both systems
)
```

## Status

✅ **Complete** - Stress tests now alert both systems and enable learning/upgrading

## Next Steps

The system will now:
1. Run stress tests every 10 minutes
2. Alert both systems when issues are found
3. Register new patterns for learning
4. Continuously improve detection and healing capabilities

No further action needed - the system is fully autonomous! 🚀
