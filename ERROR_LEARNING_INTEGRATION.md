# Error Learning Integration Guide

## 🔄 **Overview**

Grace now automatically feeds all errors into the self-healing and learning pipeline. When errors occur, they are:

1. **Tracked** with Genesis Keys (full error context)
2. **Fed to Learning Memory** (for pattern recognition)
3. **Triggered for Self-Healing** (automatic fixes)
4. **Stored for Future Learning** (improve next time)

---

## 🚀 **How It Works**

### **Automatic Error Capture**

Errors are automatically captured at these locations:

1. **LLM Orchestrator Initialization** - MultiLLMClient, RepositoryAccessLayer, ConfidenceScorer failures
2. **Memory Retrieval** - Memory Mesh, RAG, LLM Orchestrator memory retrieval failures
3. **Code Analysis** - Code analyzer errors
4. **Diagnostic Analysis** - Diagnostic engine errors
5. **TimeSense Estimation** - Time estimation errors
6. **Ollama Integration** - Connection errors, 500 errors, HTTP errors
7. **API Errors** - Chat message errors, etc.

### **Error Learning Flow**

```
Error Occurs
    ↓
Record Error (Genesis Key)
    ↓
Feed to Learning Memory
    ↓
Trigger Self-Healing (if high severity)
    ↓
Store for Pattern Recognition
    ↓
Future: System learns from pattern
    ↓
Next Time: Better handling/prevention
```

---

## 📋 **What Gets Recorded**

### **Error Information Captured**

- **Error Type**: Exception class name
- **Error Message**: Exception message
- **Error Traceback**: Full stack trace
- **Component**: Where error occurred
- **Context**: What was happening (location, reason, method)
- **Severity**: low, medium, high, critical
- **Timestamp**: When error occurred

### **Example Error Record**

```python
{
    "error_type": "ConnectionError",
    "error_message": "Failed to connect to Ollama service",
    "component": "ollama_client.connection_error",
    "context": {
        "location": "ollama_client.connection_error",
        "reason": "Ollama API error: connection_error",
        "method": "generate_response",
        "base_url": "http://localhost:11434"
    },
    "severity": "high",
    "timestamp": "2024-01-15T10:30:00Z"
}
```

---

## 🔧 **Integration Points**

### **1. LLM Orchestrator**

**Location:** `backend/llm_orchestrator/llm_orchestrator.py`

**Errors Captured:**
- MultiLLMClient initialization failures
- RepositoryAccessLayer initialization failures
- ConfidenceScorer initialization failures

**Example:**
```python
except Exception as e:
    logger.warning(f"[LLM ORCHESTRATOR] MultiLLMClient initialization failed: {e}")
    self._record_error_for_learning(e, "multi_llm_initialization", session)
```

### **2. Enterprise Coding Agent**

**Location:** `backend/cognitive/enterprise_coding_agent.py`

**Errors Captured:**
- Memory Mesh retrieval errors
- RAG retrieval errors
- LLM Orchestrator memory retrieval errors
- Code analysis errors
- Diagnostic analysis errors
- TimeSense estimation errors

**Example:**
```python
except Exception as e:
    logger.warning(f"[CODING-AGENT] Memory Mesh retrieval error: {e}")
    self._record_error_for_learning(e, "memory_mesh_retrieval", "observe_phase")
```

### **3. Ollama Client**

**Location:** `backend/ollama_client/client.py`

**Errors Captured:**
- Connection errors
- 500 server errors
- HTTP errors
- Request failures

**Example:**
```python
except requests.ConnectionError as e:
    error = ConnectionError(f"Failed to connect...")
    self._record_ollama_error_for_learning(error, "connection_error")
    raise error
```

---

## 🎯 **Self-Healing Triggers**

### **Automatic Healing**

When errors are recorded with **high** or **critical** severity, the self-healing system is automatically triggered:

```python
if severity in ["high", "critical"]:
    # Trigger healing cycle
    healing_result = healing_system.run_monitoring_cycle()
```

### **Healing Actions**

The self-healing system may:
- Reconnect to services
- Reload configurations
- Clear caches
- Restart components
- Fix code issues (if CODE_FIX action available)

---

## 📊 **Learning from Errors**

### **Pattern Recognition**

Errors are stored in Learning Memory and analyzed for patterns:

- **Common Error Types**: Which errors occur most frequently
- **Error Context**: When/where errors occur
- **Error Sequences**: Which errors lead to other errors
- **Recovery Patterns**: What fixes work for which errors

### **Future Improvements**

Based on error patterns, Grace can:

1. **Prevent Errors**: Avoid known error conditions
2. **Better Error Handling**: Improve error recovery
3. **Proactive Fixes**: Fix issues before they cause errors
4. **Pattern Matching**: Recognize similar errors and apply known fixes

---

## 💻 **Using Error Learning Integration**

### **Manual Error Recording**

You can manually record errors:

```python
from cognitive.error_learning_integration import get_error_learning_integration

error_learning = get_error_learning_integration(session=session)

try:
    # Some operation that might fail
    result = risky_operation()
except Exception as e:
    # Record error for learning
    error_learning.record_error(
        error=e,
        context={
            "location": "my_component.operation",
            "reason": "Operation failed",
            "method": "risky_operation"
        },
        component="my_component",
        severity="medium"
    )
    raise  # Re-raise if needed
```

### **Recording Warnings**

For lower-severity issues:

```python
error_learning.record_warning(
    warning_message="Service degraded but still functional",
    context={"location": "service.check", "reason": "High latency"},
    component="service_monitor"
)
```

---

## 🔍 **Viewing Learned Errors**

### **Query Learning Memory**

```python
from cognitive.learning_memory import LearningMemoryManager

learning_manager = LearningMemoryManager(session=session)

# Get error patterns
error_patterns = learning_manager.find_similar_examples(
    example_type="error_occurred",
    min_trust=0.7,
    limit=10
)
```

### **Check Genesis Keys**

```python
from genesis.genesis_key_service import get_genesis_service

genesis_service = get_genesis_service(session=session)

# Get recent errors
recent_errors = session.query(GenesisKey).filter(
    GenesisKey.is_error == True
).order_by(
    GenesisKey.when_timestamp.desc()
).limit(10).all()
```

---

## 📝 **Best Practices**

1. **Record All Errors** - Let the system learn from everything
2. **Provide Context** - Include location, reason, method in context
3. **Set Appropriate Severity** - Helps prioritize healing actions
4. **Don't Fail on Recording** - Error learning shouldn't break operations
5. **Monitor Learning** - Check what patterns are being learned

---

## 🔗 **Related Files**

- `backend/cognitive/error_learning_integration.py` - Error learning integration
- `backend/genesis/genesis_key_service.py` - Genesis Key creation
- `backend/cognitive/learning_memory.py` - Learning Memory system
- `backend/cognitive/autonomous_healing_system.py` - Self-healing system
- `backend/genesis/autonomous_triggers.py` - Autonomous trigger pipeline

---

**Last Updated:** Current Session  
**Status:** Error learning integration complete - all errors automatically fed to self-healing pipeline
