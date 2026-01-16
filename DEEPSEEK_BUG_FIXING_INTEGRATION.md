# DeepSeek AI Integration for Automatic Bug Fixing

## Overview

The automatic bug fixing system now uses **DeepSeek AI** for intelligent, context-aware code fixes. This makes the self-healing system significantly smarter and able to handle complex issues that pattern-based fixes cannot.

## How It Works

### Two-Tier Fixing Strategy

1. **Pattern-Based Fixes (Fast)**
   - Tries pattern matching first for common issues
   - Fast, deterministic, no LLM calls
   - Handles: syntax errors, simple code quality issues

2. **DeepSeek AI Fixes (Intelligent)**
   - Falls back to DeepSeek when pattern-based fails
   - Context-aware understanding of code
   - Handles: complex issues, project-specific patterns

### DeepSeek Integration

```python
from diagnostic_machine.automatic_bug_fixer import get_automatic_fixer

# Create fixer with DeepSeek enabled (default)
fixer = get_automatic_fixer(use_deepseek=True)

# Fix issues - DeepSeek will be used automatically when needed
fixes = fixer.fix_all_issues(issues)
```

## What DeepSeek Can Fix

### Complex Syntax Errors
- Multi-line syntax issues
- Context-dependent errors
- Nested structure problems

### Code Quality Issues
- Mutable default arguments (with proper context)
- Complex refactoring needs
- Project-specific patterns

### Import Errors
- Missing dependencies
- Circular import resolution
- Path resolution issues

### Security Vulnerabilities
- Context-aware security fixes
- Best practice enforcement
- Project-specific security patterns

## DeepSeek Configuration

### Model Selection
- **Primary**: `deepseek-coder:33b-instruct` (best for code fixes)
- **Fallback**: `deepseek-coder:6.7b-instruct` (faster, smaller)
- **Reasoning**: `deepseek-r1:70b` (for complex analysis)

### Parameters
- **Temperature**: 0.2 (low for deterministic fixes)
- **Max Tokens**: 500 (limit response size)
- **Timeout**: 30 seconds

## Example Usage

### Automatic (Default)
```python
# DeepSeek is used automatically when pattern-based fixes fail
fixer = get_automatic_fixer()
result = fixer.fix_issue(issue)
```

### Manual Control
```python
# Disable DeepSeek (pattern-based only)
fixer = get_automatic_fixer(use_deepseek=False)

# Enable DeepSeek explicitly
fixer = get_automatic_fixer(use_deepseek=True)
```

## Benefits

1. **Context Awareness**: Understands code structure and patterns
2. **Intelligent Fixes**: Goes beyond simple pattern matching
3. **Project-Specific**: Adapts to your codebase conventions
4. **Fallback Safety**: Pattern-based fixes first, AI as backup
5. **Explanation**: Provides explanations for fixes

## Requirements

1. **Ollama Installed**: `ollama serve`
2. **DeepSeek Models**: 
   ```bash
   ollama pull deepseek-coder:33b-instruct
   # Or smaller model:
   ollama pull deepseek-coder:6.7b-instruct
   ```
3. **LLM Orchestrator**: Already integrated in Grace

## Performance

- **Pattern-Based**: < 1ms per fix
- **DeepSeek Fix**: ~2-5 seconds per fix
- **Fallback**: Only uses DeepSeek when pattern-based fails

## Safety Features

1. **Backups**: All fixes create backups (even AI fixes)
2. **Rollback**: Can restore from backups
3. **Verification**: Pattern-based fixes verified before AI
4. **Timeout**: 30-second timeout prevents hanging
5. **Error Handling**: Falls back gracefully if DeepSeek unavailable

## Status

✅ **COMPLETE** - DeepSeek AI integrated into automatic bug fixing system

The system now intelligently fixes bugs using AI when pattern-based methods aren't sufficient!
