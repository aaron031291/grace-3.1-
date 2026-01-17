# Launcher NLP Error Processing

## Overview

The launcher now processes all errors through Natural Language Processing (NLP) to provide user-friendly explanations and actionable solutions. This makes technical errors more understandable and helps users resolve issues faster.

## Features

### 1. **Intelligent Error Analysis**
- Converts technical error messages into clear, non-technical explanations
- Identifies root causes and provides context
- Assesses error severity (low/medium/high/critical)

### 2. **Actionable Solutions**
- Provides 2-3 suggested solutions for each error
- Solutions are prioritized and specific to the error type
- Includes troubleshooting steps

### 3. **Multi-Mode Processing**
- **LLM Processing** (if backend available): Uses GRACE's LLM orchestrator for intelligent error analysis
- **Rule-Based Processing** (fallback): Uses pattern matching for common error types
- **HTTP API** (if backend running): Calls backend LLM API for error processing

### 4. **Graceful Degradation**
- Falls back to rule-based processing if LLM is unavailable
- Never blocks launcher startup
- Always provides some form of error explanation

## How It Works

### Error Processing Flow

```
1. Error Occurs
   ↓
2. Capture Error + Context
   ↓
3. Try LLM Processing (if available)
   ├─ Direct orchestrator (if in same process)
   ├─ HTTP API (if backend running)
   └─ Fallback to rule-based
   ↓
4. Display NLP Explanation
   ├─ What Happened (clear explanation)
   ├─ Suggested Solutions (2-3 actionable steps)
   └─ Technical Details (for debugging)
```

### Example Output

**Before (Technical):**
```
RuntimeError: Backend process died during startup (exit code: 1)
Last output: [ERROR] ModuleNotFoundError: No module named 'uvicorn'
```

**After (NLP Processed):**
```
📝 What Happened:
   A required Python module is missing, preventing the backend from starting.

💡 Suggested Solutions:
   1. Install missing dependencies: pip install uvicorn
   2. Run setup script to install all requirements
   3. Check Python environment and virtual environment activation

🔍 Technical Details:
   Error Type: RuntimeError
   Original Error: Backend process died during startup (exit code: 1)
   Severity: HIGH
```

## Supported Error Types

The NLP processor recognizes and provides specific explanations for:

- **Port Conflicts**: Port already in use
- **File Not Found**: Missing files or directories
- **Permission Errors**: Access denied issues
- **Connection Errors**: Service connectivity problems
- **Process Failures**: Unexpected process termination
- **Version Mismatches**: Component version conflicts
- **Generic Errors**: Fallback for unknown errors

## Integration Points

### Launcher Integration

Errors are processed at these key points:

1. **Launch Sequence Errors** (`launch()` method)
   - Setup validation failures
   - Backend startup failures
   - Health check failures
   - Version handshake failures

2. **Backend Process Errors** (`wait_for_backend()` method)
   - Process death during startup
   - Timeout errors
   - Health check failures

3. **General Exceptions** (all exception handlers)
   - Any unhandled exception during launch

## Configuration

### Initialization

```python
from launcher.nlp_error_processor import get_nlp_error_processor

# Initialize with LLM support (default)
nlp_processor = get_nlp_error_processor(
    use_llm=True,
    backend_url="http://localhost:8000"
)

# Rule-based only (no LLM)
nlp_processor = get_nlp_error_processor(use_llm=False)
```

### Processing Errors

```python
error_info = nlp_processor.process_error(
    error=exception,
    context={
        "root_path": "/path/to/grace",
        "backend_port": 8000,
        "processes": ["backend"]
    }
)

# Access results
explanation = error_info['nlp_explanation']
solutions = error_info['suggested_solutions']
severity = error_info['severity']
```

## Backend API Integration

If the backend is running, the launcher can use the LLM orchestrator API:

**Endpoint:** `POST /llm/task`

**Request:**
```json
{
  "prompt": "Analyze this launcher error...",
  "task_type": "general",
  "require_verification": false,
  "require_consensus": false,
  "enable_learning": false
}
```

**Response:**
```json
{
  "content": "EXPLANATION: ...\nSOLUTIONS:\n1. ...\n2. ...\nSEVERITY: high"
}
```

## Rule-Based Patterns

When LLM is unavailable, the processor uses pattern matching:

- **Port errors**: Detects "port", "already", "in use"
- **File errors**: Detects "not found", "missing", "file"
- **Permission errors**: Detects "permission", "denied"
- **Connection errors**: Detects "connection", "connect"
- **Process errors**: Detects "process", "died", "exited"
- **Version errors**: Detects "version", "mismatch"

## Benefits

1. **Better User Experience**: Clear, actionable error messages
2. **Faster Troubleshooting**: Immediate solutions provided
3. **Reduced Support Burden**: Users can self-resolve common issues
4. **Intelligent Analysis**: LLM provides context-aware explanations
5. **Always Available**: Rule-based fallback ensures explanations are always provided

## Future Enhancements

- **Learning from Errors**: Track common errors and improve solutions
- **Error Categories**: Group similar errors for better analysis
- **Solution Success Tracking**: Learn which solutions work best
- **Interactive Troubleshooting**: Step-by-step guided resolution
- **Error Prevention**: Proactive checks to prevent common errors

## Files

- `launcher/nlp_error_processor.py`: Core NLP error processing logic
- `launcher/launcher.py`: Integration with launcher error handlers

## Testing

To test NLP error processing:

1. **Trigger an error** (e.g., missing file, port conflict)
2. **Observe NLP output** in launcher console
3. **Verify solutions** are actionable and relevant
4. **Check fallback** by disabling backend (should use rule-based)

## Notes

- NLP processing is non-blocking and never prevents launcher startup
- LLM processing requires backend to be running (may not be available during startup)
- Rule-based processing is always available as fallback
- All original error information is preserved for debugging
