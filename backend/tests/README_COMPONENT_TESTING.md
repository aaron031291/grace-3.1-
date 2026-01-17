# Comprehensive Component Testing with Self-Healing

This system tests all 400+ components in GRACE, logs bugs/problems, and automatically sends them to the self-healing system for fixing.

## Overview

The comprehensive component tester:
1. **Tests all components** - Imports, validates, and checks every component
2. **Logs bugs** - Creates detailed bug reports with context
3. **Creates Genesis Keys** - Tracks every issue with Genesis Keys
4. **Triggers self-healing** - Automatically sends issues to the autonomous healing system
5. **Generates reports** - Comprehensive test reports with healing summaries

## Quick Start

### Command Line

```bash
# Test all components with self-healing enabled
python -m tests.comprehensive_component_tester

# Test with custom trust level
python -m tests.comprehensive_component_tester --trust-level 5

# Test only specific category
python -m tests.comprehensive_component_tester --category api

# Disable self-healing (only test and log)
python -m tests.comprehensive_component_tester --no-healing
```

### Using Scripts

**Windows:**
```bash
run_component_tests.bat
```

**Linux/Mac:**
```bash
chmod +x run_component_tests.sh
./run_component_tests.sh
```

### API Endpoint

```bash
# Start test in background
curl -X POST http://localhost:8000/component-testing/test-all \
  -H "Content-Type: application/json" \
  -d '{
    "enable_healing": true,
    "trust_level": 3,
    "background": true
  }'

# Check test status
curl http://localhost:8000/component-testing/status/{test_id}

# Get test report
curl http://localhost:8000/component-testing/reports/{report_id}
```

## How It Works

### 1. Component Discovery

The tester automatically discovers all components from:
- `backend/api/` - API endpoints
- `backend/cognitive/` - Cognitive systems
- `backend/genesis/` - Genesis system
- `backend/llm_orchestrator/` - LLM orchestration
- And 20+ more categories

### 2. Component Testing

For each component, the tester:
- **Import Test** - Verifies the module can be imported
- **Discovery** - Finds classes and functions
- **Issue Detection** - Checks for syntax errors, missing imports, etc.
- **Basic Validation** - Tries to instantiate main classes

### 3. Bug Logging

When issues are found:
- **Genesis Key Created** - Every bug gets a Genesis Key for tracking
- **Detailed Context** - Error messages, tracebacks, file paths
- **Issue Classification** - Severity levels (critical, medium, low)

### 4. Self-Healing Integration

The healing system:
- **Assesses Health** - Detects anomalies from Genesis Keys
- **Decides Actions** - Chooses appropriate healing actions
- **Executes Healing** - Automatically fixes issues based on trust level
- **Learns** - Updates trust scores from healing outcomes

## Trust Levels

The trust level determines what healing actions can be auto-executed:

- **0 - MANUAL_ONLY** - No autonomous actions
- **1 - SUGGEST_ONLY** - Suggest actions, require approval
- **2 - LOW_RISK_AUTO** - Auto-execute low-risk actions only
- **3 - MEDIUM_RISK_AUTO** (default) - Auto-execute medium-risk actions
- **4 - HIGH_RISK_AUTO** - Auto-execute high-risk actions
- **5-9** - Increasing levels of autonomy

## Test Report

The test report includes:

```json
{
  "test_suite": "comprehensive_component_test",
  "summary": {
    "total_components": 400,
    "passed": 350,
    "failed": 30,
    "errors": 20,
    "success_rate": 87.5
  },
  "healing_summary": {
    "total_issues_found": 50,
    "genesis_keys_created": 50,
    "healing_triggered": 45,
    "healing_successful": 40
  },
  "results": [...]
}
```

## Component Categories

Available categories for targeted testing:

- `api` - API endpoints
- `cognitive` - Cognitive systems
- `genesis` - Genesis system
- `llm_orchestrator` - LLM orchestration
- `retrieval` - Retrieval system
- `ingestion` - Ingestion system
- `file_manager` - File management
- `librarian` - Librarian system
- `ml_intelligence` - ML Intelligence
- `layer1` - Layer 1 system
- `layer2` - Layer 2 system
- `diagnostic_machine` - Diagnostic machine
- `timesense` - TimeSense system
- And more...

## Healing Actions

The healing system can automatically:

1. **BUFFER_CLEAR** - Clear buffers (very safe)
2. **CACHE_FLUSH** - Flush caches (safe)
3. **CONNECTION_RESET** - Reset connections (generally safe)
4. **DATABASE_TABLE_CREATE** - Create missing tables (safe)
5. **PROCESS_RESTART** - Restart process (moderate risk)
6. **SERVICE_RESTART** - Restart service (moderate-high risk)
7. **STATE_ROLLBACK** - Rollback state (high risk)
8. **ISOLATION** - Isolate component (high risk)
9. **EMERGENCY_SHUTDOWN** - Emergency shutdown (very high risk)

## Integration with Other Systems

The component tester integrates with:

- **Genesis Keys** - Universal tracking
- **Autonomous Healing System** - Automatic fixing
- **Diagnostic Machine** - Health monitoring
- **Learning Memory** - Pattern detection
- **Telemetry** - System metrics

## Example Output

```
╔══════════════════════════════════════════════════════════════╗
║         GRACE COMPREHENSIVE COMPONENT TEST REPORT            ║
╚══════════════════════════════════════════════════════════════╝

Test Suite: comprehensive_component_test
Duration: 45.23 seconds

SUMMARY:
  Total Components: 400
  ✓ Passed: 350
  ✗ Failed: 30
  ⚠ Errors: 20
  Success Rate: 87.50%

HEALING SUMMARY:
  Total Issues Found: 50
  Genesis Keys Created: 50
  Healing Actions Triggered: 45
  Healing Successful: 40
```

## Best Practices

1. **Run regularly** - Test components after major changes
2. **Start with low trust** - Use trust level 2-3 initially
3. **Review healing actions** - Check what was auto-fixed
4. **Monitor Genesis Keys** - Track all issues via Genesis Keys
5. **Use categories** - Test specific categories during development

## Troubleshooting

### Import Errors

If components fail to import:
- Check Python path
- Verify dependencies are installed
- Check for circular imports

### Healing Not Triggered

If healing isn't triggered:
- Check trust level (may be too low)
- Verify Genesis Keys are being created
- Check healing system logs

### Timeout Issues

If tests timeout:
- Increase `test_timeout_seconds`
- Test specific categories instead of all
- Check for hanging imports

## API Endpoints

- `POST /component-testing/test-all` - Start comprehensive test
- `GET /component-testing/status/{test_id}` - Get test status
- `GET /component-testing/categories` - List categories
- `GET /component-testing/reports` - List all reports
- `GET /component-testing/reports/{report_id}` - Get specific report

## Files

- `comprehensive_component_tester.py` - Main tester implementation
- `run_component_tests.py` - Quick runner script
- `component_testing_api.py` - API endpoints
- `component_test_report_*.json` - Test reports
