# Comprehensive Component Testing Guide

This guide explains how to use the comprehensive E2E and stress testing system for all Grace components.

## Overview

The comprehensive testing system:
1. **Tests all individual components** with E2E and stress tests
2. **Logs all issues** (problems, warnings, skips, failures) to JSON files
3. **Updates self-healing system** to recognize and fix logged issues
4. **Updates diagnostic engine** to recognize logged issues

## Quick Start

### Run All Tests

```bash
python run_comprehensive_testing.py
```

This will:
- Discover all components in the backend
- Run E2E tests on each component
- Run stress tests on each component
- Log all issues to `test_issues_YYYYMMDD_HHMMSS.json`
- Generate a test report in `test_report_YYYYMMDD_HHMMSS.json`
- Update self-healing and diagnostic systems with found issues

## Files Created

### Test Issues File
- **Location**: `test_issues_YYYYMMDD_HHMMSS.json`
- **Content**: All issues found during testing (problems, warnings, skips, failures)
- **Format**: JSON array of issue objects

### Test Report File
- **Location**: `test_report_YYYYMMDD_HHMMSS.json`
- **Content**: Complete test report with statistics and component results
- **Format**: JSON object with summary and detailed results

### Log Files
- **Location**: `logs/component_testing_YYYYMMDD_HHMMSS.log`
- **Content**: Detailed execution logs

## Issue Types

The system categorizes issues into:

1. **Problems**: Non-critical issues that should be addressed
2. **Warnings**: Potential issues that may cause problems
3. **Skips**: Tests that were skipped (e.g., missing dependencies)
4. **Failures**: Critical issues that cause tests to fail

## Issue Severity Levels

- **CRITICAL**: System-breaking issues
- **HIGH**: Major issues that affect functionality
- **MEDIUM**: Moderate issues
- **LOW**: Minor issues
- **INFO**: Informational issues

## Integration with Self-Healing

The testing system automatically updates the self-healing system with:
- Issue patterns for recognition
- Auto-fixable issues
- Fix suggestions
- Component-specific healing patterns

## Integration with Diagnostic Engine

The testing system automatically updates the diagnostic engine with:
- Detection patterns
- Component-specific rules
- Issue type classifications
- Severity mappings

## Manual Integration

If you want to manually process test issues:

```python
from diagnostic_machine.test_issue_integration import get_test_issue_integration

integration = get_test_issue_integration()

# Load issues from file
issues = integration.load_test_issues(Path("test_issues_20250115_120000.json"))

# Register with systems
integration.register_issues_with_healing(issues)
integration.register_issues_with_diagnostic(issues)
integration.update_automatic_fixer(issues)
```

Or use the command line:

```bash
python -m backend.diagnostic_machine.test_issue_integration test_issues_20250115_120000.json test_report_20250115_120000.json
```

## Component Discovery

The system automatically discovers components in:
- `backend/database`
- `backend/embedding`
- `backend/vector_db`
- `backend/retrieval`
- `backend/ingestion`
- `backend/layer1`
- `backend/cognitive`
- `backend/genesis`
- `backend/llm_orchestrator`
- `backend/ml_intelligence`
- `backend/diagnostic_machine`
- `backend/file_manager`
- `backend/librarian`
- `backend/telemetry`
- `backend/security`
- `backend/version_control`

## Test Types

### E2E Tests
- Module import tests
- Class instantiation tests
- Basic method tests
- Dependency checks
- Structure validation

### Stress Tests
- Concurrent access tests
- Memory usage tests
- Error handling tests
- Performance tests

## Understanding Test Results

### Component Test Result

Each component gets:
- **Status**: PASSED, FAILED, WARNING, SKIPPED
- **Duration**: Time taken to test
- **Issues**: List of all issues found
- **Counts**: Number of passed/failed/skipped/warning tests

### Test Report Summary

The report includes:
- Total components tested
- Components passed/failed/skipped
- Total issues by type (problems, warnings, skips, failures)
- Issues by severity
- Duration and timestamps

## Troubleshooting

### Tests Fail to Run

1. Check that backend components are accessible
2. Verify database connection if needed
3. Check log files for detailed error messages

### Integration Fails

1. Verify self-healing system is initialized
2. Check diagnostic engine is available
3. Review integration logs for specific errors

### No Issues Found

This could mean:
- All components are working correctly
- Tests are not comprehensive enough
- Component discovery failed

## Extending the System

### Add New Test Types

Edit `comprehensive_component_testing.py` and add new test methods to `ComponentTester`:

```python
def _test_custom_functionality(self, component: Dict, module: Any) -> Optional[TestIssue]:
    """Test custom functionality."""
    # Your test logic here
    return None  # or return TestIssue if issue found
```

### Add New Components

Components are automatically discovered from the backend directory. To add a new component:

1. Create the component directory in `backend/`
2. Add it to the `discover_components()` method if needed
3. Run tests - it will be automatically included

### Custom Issue Detection

Modify the test methods to detect specific issues:

```python
def _test_custom_issue(self, component: Dict, module: Any) -> Optional[TestIssue]:
    """Detect custom issues."""
    # Check for specific conditions
    if some_condition:
        return TestIssue(
            component=component['name'],
            test_name="custom_test",
            issue_type="problem",
            severity=IssueSeverity.MEDIUM,
            message="Custom issue detected",
            auto_fixable=True,
            fix_suggested="Suggested fix here"
        )
    return None
```

## Best Practices

1. **Run tests regularly** to catch issues early
2. **Review test reports** to understand system health
3. **Fix auto-fixable issues** first
4. **Monitor integration status** to ensure systems are updated
5. **Keep test issues file** for historical tracking

## Example Output

```
================================================================================
COMPREHENSIVE COMPONENT TESTING
================================================================================
[DISCOVERY] Found 16 components to test

================================================================================
Testing component: database
================================================================================
[E2E] Testing component: database
[STRESS] Testing component: database
...

================================================================================
TEST SUMMARY
================================================================================
Duration: 45.23 seconds
Components tested: 16
Components passed: 14
Components failed: 1
Components skipped: 1

Issues:
  Problems: 5
  Warnings: 12
  Skips: 3
  Failures: 2
================================================================================
```

## Next Steps

After running tests:

1. Review the test report JSON file
2. Check the issues file for detailed problem descriptions
3. Verify that self-healing and diagnostic systems were updated
4. Fix critical and high-severity issues
5. Re-run tests to verify fixes

## Support

For issues or questions:
- Check log files in `logs/`
- Review test report JSON files
- Check integration status in the summary output
