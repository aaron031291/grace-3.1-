# GitHub Failures Sandbox Training System

## Overview

Grace learns to fix broken code by practicing on real-world failures collected from GitHub. The system runs broken code in a sandbox, diagnoses errors, attempts fixes, and learns from the outcomes.

## System Architecture

### Components

1. **Collection System** (`scripts/collect_github_failures_enhanced.py`)
   - Collects broken code examples from GitHub
   - Multiple strategies: Gists, Issues, Repository files
   - Searches for error patterns (SyntaxError, NameError, TypeError, etc.)
   - Outputs JSON file with examples

2. **Training System** (`backend/cognitive/github_failures_sandbox_training.py`)
   - Loads failure examples
   - Runs code in isolated sandbox
   - Diagnoses errors automatically
   - Attempts fixes using Grace's coding agent
   - Tests fixes
   - Learns from outcomes

3. **Learning Integration**
   - Stores in Learning Memory
   - Creates procedural patterns for successful fixes
   - Updates Memory Mesh with experiences
   - Builds reusable fix procedures

## Training Process

For each broken code example:

1. **Run Original Code** → Capture error
2. **Diagnose Error** → Identify error type and location
3. **Generate Fix** → Use Grace's coding agent to fix
4. **Test Fix** → Run fixed code in sandbox
5. **Learn** → Store success/failure in memory systems
6. **Extract Pattern** → Create reusable fix procedure if successful

## Usage

### Collect Failures
```bash
python scripts/collect_github_failures_enhanced.py --limit 10000 --output github_failures_10000.json
```

### Train Grace
```bash
python scripts/train_on_github_failures.py --input github_failures_10000.json --output github_training_results.json
```

### Check Progress
```bash
python scripts/check_training_progress.py
```

## What Grace Learns

### Error Patterns
- Common Python errors (SyntaxError, NameError, TypeError, etc.)
- Error locations and contexts
- Error messages and their meanings

### Fix Strategies
- How to diagnose different error types
- Effective fix approaches
- When certain fixes work vs. fail

### Procedural Patterns
- Reusable fix procedures
- "How to fix SyntaxError"
- "How to fix NameError"
- "How to add missing imports"

### Code Patterns
- What works vs. what doesn't
- Common code mistakes
- Best practices for error handling

## Learning Storage

### Learning Memory
- Individual fix attempts stored as LearningExamples
- Trust scores based on success rate
- Context and outcomes preserved

### Procedural Memory
- Successful fixes create reusable procedures
- Procedures grouped by error type
- Success rates tracked per procedure

### Memory Mesh
- Episodic memory for fix experiences
- Semantic connections between similar fixes
- Pattern extraction across multiple examples

## Current Status

- **Collection**: 27 examples collected (target: 10,000)
- **Training**: Running in background
- **Learning**: Active - patterns being extracted and stored

## Future Enhancements

1. **Parallel Processing**: Process multiple examples simultaneously
2. **Incremental Learning**: Continue training as more examples collected
3. **Pattern Refinement**: Improve pattern extraction accuracy
4. **Fix Quality Metrics**: Measure fix quality beyond just "works/doesn't work"
5. **Multi-language Support**: Extend beyond Python

## Integration with MBPP

The patterns learned from GitHub failures can improve Grace's performance on MBPP:
- Better error diagnosis
- More effective fix strategies
- Reusable code patterns
- Improved code generation quality
