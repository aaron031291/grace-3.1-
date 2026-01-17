# Sandbox Practice Environment

## Overview

The Sandbox Practice Environment provides an isolated testing environment where the **Self-Healing Pipeline** and **Coding Agent** can practice together without affecting production systems.

## Features

- **Isolated Environment**: Each practice session runs in a separate sandbox directory
- **Safe Testing**: All changes are contained and can be reviewed before promotion
- **Collaboration**: Self-healing and coding agents can work together on scenarios
- **Tracking**: All practice sessions are tracked with metrics and reports
- **No Production Impact**: Changes never affect production code or databases

## Quick Start

### Option 1: Command Line Script

```bash
# Run a practice session
python scripts/start_sandbox_practice.py

# Or run the full script directly
python scripts/sandbox_practice_healing_and_coding.py
```

### Option 2: API Endpoint

```bash
# Start a practice session via API
curl -X POST http://localhost:8000/sandbox-lab/practice/start

# List all practice sessions
curl http://localhost:8000/sandbox-lab/practice/sessions
```

## Practice Scenarios

The sandbox environment includes several built-in practice scenarios:

1. **Coding Agent - Code Generation**
   - Practice generating code from descriptions
   - Test code quality and correctness
   - Learn from feedback

2. **Self-Healing - Fix Code Issues**
   - Practice detecting code issues
   - Test healing strategies
   - Validate fixes

3. **Collaboration - Coding + Healing**
   - Coding agent generates code
   - Self-healing agent fixes issues
   - Test end-to-end workflows

4. **Code Review & Fix**
   - Practice code review
   - Identify and fix quality issues
   - Improve code standards

## Sandbox Structure

Each sandbox session creates:

```
sandbox_<ID>/
├── code/           # Practice code files
├── tests/          # Test files
├── logs/           # Session logs
└── results/        # Session results and reports
    ├── session_<ID>.json
    └── report_<ID>.txt
```

## Session Data

Each practice session tracks:

- **Healing Practices**: Attempts, successes, failure reasons
- **Coding Practices**: Tasks, code generated, quality scores
- **Collaborations**: Joint efforts between systems
- **Metrics**: Success rates, durations, improvements

## Reviewing Results

After a practice session:

1. Check the session JSON file: `results/session_<ID>.json`
2. Review the report: `results/report_<ID>.txt`
3. Examine generated code: `code/` directory
4. Review logs: `logs/` directory

## Promoting to Production

Before promoting sandbox improvements:

1. Review all practice session results
2. Validate code quality and correctness
3. Test in staging environment
4. Use the Sandbox Lab API to promote experiments

## Configuration

The sandbox uses conservative settings by default:

- **Trust Level**: `LOW_RISK_AUTO` (more conservative than production)
- **Learning**: Enabled (systems learn from practice)
- **Sandbox Mode**: Enabled (prevents production changes)

## API Endpoints

### Start Practice Session
```http
POST /sandbox-lab/practice/start
```

### List Practice Sessions
```http
GET /sandbox-lab/practice/sessions
```

## Example Usage

```python
from scripts.sandbox_practice_healing_and_coding import SandboxPracticeEnvironment

# Create sandbox
sandbox = SandboxPracticeEnvironment()

# Initialize systems
sandbox.initialize_database()
healing_system = sandbox.initialize_healing_system()
coding_agent = sandbox.initialize_coding_agent()

# Practice coding
result = sandbox.practice_coding(
    coding_agent,
    "Create a function to calculate fibonacci numbers",
    "code_generation"
)

# Practice healing
healing_result = sandbox.practice_healing(
    healing_system,
    "Fix missing return statement",
    Path("code/buggy_file.py")
)

# Save and review
sandbox.save_session()
print(sandbox.generate_report())
```

## Best Practices

1. **Regular Practice**: Run practice sessions regularly to improve systems
2. **Review Results**: Always review session reports before promoting
3. **Iterative Improvement**: Use practice feedback to refine systems
4. **Collaboration**: Test collaboration scenarios to improve integration
5. **Clean Up**: Remove old sandbox directories periodically

## Troubleshooting

### Database Initialization Fails
- Check database permissions
- Ensure SQLite is available
- Verify database path is writable

### Systems Fail to Initialize
- Check dependencies are installed
- Verify database connection
- Review logs for specific errors

### Practice Scenarios Fail
- Check code directory permissions
- Verify file paths are correct
- Review error logs in `logs/` directory

## Integration with Sandbox Lab

The practice environment integrates with the Autonomous Sandbox Lab:

- Practice sessions can propose experiments
- Successful practices can enter sandbox testing
- Validated practices can start 90-day trials
- Approved practices can promote to production

## See Also

- [Sandbox Lab API Documentation](../backend/api/sandbox_lab.py)
- [Self-Healing System](../backend/cognitive/autonomous_healing_system.py)
- [Coding Agent](../backend/cognitive/enterprise_coding_agent.py)
- [Autonomous Sandbox Lab](../backend/cognitive/autonomous_sandbox_lab.py)
