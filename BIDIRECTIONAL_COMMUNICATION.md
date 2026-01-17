# Bidirectional Communication: Self-Healing ↔ Coding Agent ✅

## 🎯 **Bidirectional Communication Enabled!**

**Self-Healing System and Coding Agent can now call each other for assistance!**

---

## ✅ **Communication Flow**

### **1. Self-Healing → Coding Agent** ✅

**When Self-Healing Requests Assistance:**
- Need code generation for fixes
- Need code refactoring
- Need code optimization
- Need code review
- Need bug fixes

**How It Works:**
```python
# Self-Healing requests coding assistance
result = healing_system.request_coding_assistance(
    assistance_type="code_generation",
    description="Generate REST API endpoint for user authentication",
    context={
        "target_files": ["backend/api/auth.py"],
        "requirements": {"framework": "FastAPI", "security": "JWT"}
    },
    priority="high"
)
```

**Bridge Handles:**
1. Creates assistance request
2. Maps to coding task type
3. Creates coding task
4. Executes task
5. Returns result

---

### **2. Coding Agent → Self-Healing** ✅

**When Coding Agent Requests Assistance:**
- Code generation failed
- Code has issues that need healing
- Need diagnostic analysis
- Need code analysis

**How It Works:**
```python
# Coding Agent requests healing assistance
result = coding_agent.request_healing_assistance(
    issue_description="Code generation failed with syntax errors",
    affected_files=["backend/api/auth.py"],
    issue_type="code_issue",
    priority="medium"
)
```

**Bridge Handles:**
1. Creates assistance request
2. Calls healing system
3. Executes healing
4. Returns result

---

## 🎯 **Assistance Types**

### **Self-Healing → Coding Agent:**

- **code_generation** - Generate new code
- **code_fix** - Fix existing code
- **code_refactor** - Refactor code
- **code_optimize** - Optimize code
- **code_review** - Review code
- **bug_fix** - Fix bugs

### **Coding Agent → Self-Healing:**

- **healing** - Request healing for issues
- **diagnostic** - Request diagnostic analysis
- **code_analysis** - Request code analysis

---

## 📊 **Request Tracking**

### **Pending Requests:**
```python
# Get pending requests
pending = bridge.get_pending_requests()

# Returns:
# [
#   {
#     "request_id": "healing_req_123",
#     "from_system": "self_healing",
#     "to_system": "coding_agent",
#     "assistance_type": "code_generation",
#     "description": "...",
#     "priority": "high"
#   }
# ]
```

### **Completed Requests:**
```python
# Get completed requests
completed = bridge.get_completed_requests(limit=50)

# Returns:
# [
#   {
#     "request_id": "healing_req_123",
#     "from_system": "self_healing",
#     "to_system": "coding_agent",
#     "assistance_type": "code_generation",
#     "success": True,
#     "created_at": "...",
#     "completed_at": "..."
#   }
# ]
```

---

## 🚀 **Usage Examples**

### **Example 1: Self-Healing Needs Code Generation**

```python
# Self-Healing detects issue and needs code generation
healing_result = healing_system.request_coding_assistance(
    assistance_type="code_generation",
    description="Generate error handler for database connection failures",
    context={
        "target_files": ["backend/utils/error_handler.py"],
        "requirements": {
            "error_type": "database_connection",
            "retry_logic": True
        }
    },
    priority="high"
)

# Coding Agent generates code
# Result includes generated code and quality metrics
```

### **Example 2: Coding Agent Needs Healing**

```python
# Coding Agent generates code but encounters issues
coding_result = coding_agent.execute_task(task_id)

if not coding_result.get("success"):
    # Request healing assistance
    healing_result = coding_agent.request_healing_assistance(
        issue_description="Code generation failed with import errors",
        affected_files=["backend/api/auth.py"],
        issue_type="import_error",
        priority="medium"
    )
    
    # Self-Healing fixes the issues
    # Result includes fix details
```

### **Example 3: Coding Agent Needs Diagnostic**

```python
# Coding Agent needs system health check
diagnostic = coding_agent.request_diagnostic(
    description="Check system health before code generation",
    context={"task_type": "code_generation"}
)

# Returns system health status
```

---

## ✅ **Integration Points**

### **1. Self-Healing System:**
- `request_coding_assistance()` - Request coding help
- `healing_bridge` - Bridge reference
- `coding_agent` - Coding agent reference

### **2. Coding Agent:**
- `request_healing_assistance()` - Request healing help
- `request_diagnostic()` - Request diagnostic
- `healing_bridge` - Bridge reference
- `healing_system` - Healing system reference

### **3. Bridge:**
- `healing_request_coding_assistance()` - Handle healing → coding
- `coding_agent_request_healing_assistance()` - Handle coding → healing
- `coding_agent_request_diagnostic()` - Handle diagnostic requests
- Request tracking and history

---

## ✅ **Summary**

**Bidirectional Communication:**

✅ **Self-Healing → Coding Agent** - Request code generation/fixes  
✅ **Coding Agent → Self-Healing** - Request healing/diagnostics  
✅ **Request Tracking** - All requests tracked and logged  
✅ **Automatic Routing** - Bridge handles routing automatically  
✅ **Error Handling** - Graceful error handling  
✅ **Genesis Keys** - All requests tracked with Genesis Keys  

**Self-Healing and Coding Agent can now call each other for assistance!** 🚀
