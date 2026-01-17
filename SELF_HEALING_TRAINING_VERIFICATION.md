# Self-Healing Training Verification Guide

## ✅ **How to Verify Grace is Being Tested and Getting Right Knowledge**

---

## 🎯 **Quick Verification**

### **1. Run Verification Script**

```bash
python scripts/verify_self_healing_training.py
```

This will test:
- ✅ Training system initialization
- ✅ Knowledge retrieval for tasks
- ✅ Training cycle start
- ✅ Alert registration
- ✅ Knowledge contribution
- ✅ Training statistics
- ✅ Task-specific knowledge retrieval
- ✅ Training improvement over time

---

## 📊 **What Gets Verified**

### **1. Training System is Active**

**Check:**
- Training system initialized ✅
- Sandbox lab connected ✅
- Healing system available ✅
- Diagnostic engine connected ✅
- LLM orchestrator available ✅

**Verification:**
```python
# Check training system status
training_system = get_self_healing_training_system(...)

# Verify all components
assert training_system.sandbox_lab is not None
assert training_system.healing_system is not None
assert training_system.llm_orchestrator is not None
```

---

### **2. Knowledge Retrieval is Working**

**Check:**
- Memories retrieved for tasks ✅
- Relevant patterns found ✅
- Trust scores available ✅
- Knowledge matched to task type ✅

**Verification:**
```python
# Test knowledge retrieval
memories = training_system.llm_orchestrator.grace_aligned_llm.retrieve_grace_memories(
    query="fix syntax errors",
    limit=10
)

# Verify memories are relevant
assert len(memories) > 0
assert all(mem.get("trust_score", 0) >= 0 for mem in memories)
```

---

### **3. Training Cycles are Running**

**Check:**
- Cycle starts successfully ✅
- 100 files collected ✅
- Files fixed in sandbox ✅
- Knowledge gained from fixes ✅
- Cycles get harder over time ✅

**Verification:**
```python
# Start training cycle
cycle = training_system.start_training_cycle(
    folder_path="backend/codebase",
    problem_perspective=ProblemPerspective.SYNTAX_ERRORS
)

# Verify cycle
assert cycle.state == TrainingCycleState.SANDBOX_PRACTICE
assert len(cycle.files_collected) == 100
assert cycle.difficulty_level >= 1.0
```

---

### **4. Right Knowledge for Tasks**

**Check:**
- Knowledge matches task type ✅
- Relevant patterns retrieved ✅
- Trust-weighted selection ✅
- Context-aware retrieval ✅

**Verification:**
```python
# Test task-specific knowledge
task = "fix syntax errors"
memories = llm_orchestrator.grace_aligned_llm.retrieve_grace_memories(task)

# Verify relevance
relevant = [m for m in memories if "syntax" in str(m.get("content", "")).lower()]
relevance_rate = len(relevant) / len(memories) if memories else 0

assert relevance_rate >= 0.6  # At least 60% relevant
```

---

## 🔍 **Detailed Verification Steps**

### **Step 1: Check Training System Status**

**API:**
```bash
curl http://localhost:8000/self-healing-training/status
```

**Expected Response:**
```json
{
  "active_cycle": {
    "cycle_id": "cycle_...",
    "state": "sandbox_practice",
    "files_collected": 100,
    "files_fixed": 85,
    "difficulty_level": 2.5
  },
  "cycles_completed": 5,
  "total_files_fixed": 425,
  "total_alerts_responded": 2,
  "current_difficulty": 2.5
}
```

---

### **Step 2: Verify Knowledge Retrieval**

**Test:**
```python
# Test knowledge for specific task
task = "fix syntax errors in Python code"

# Retrieve knowledge
memories = grace_aligned_llm.retrieve_grace_memories(task)

# Verify:
# 1. Memories are retrieved
assert len(memories) > 0

# 2. Memories are relevant
for mem in memories:
    assert "syntax" in mem.get("content", "").lower() or \
           mem.get("trust_score", 0) >= 0.7

# 3. Trust scores are available
assert all(mem.get("trust_score") is not None for mem in memories)
```

---

### **Step 3: Start Training Cycle**

**API:**
```bash
curl -X POST http://localhost:8000/self-healing-training/start \
  -H "Content-Type: application/json" \
  -d '{
    "folder_path": "backend/codebase",
    "problem_perspective": "syntax_errors"
  }'
```

**Expected Response:**
```json
{
  "cycle_id": "cycle_...",
  "state": "sandbox_practice",
  "files_collected": 100,
  "problem_perspective": "syntax_errors",
  "difficulty_level": 1.5,
  "cycle_number": 1
}
```

---

### **Step 4: Register Alert (Bring Grace Out)**

**API:**
```bash
curl -X POST http://localhost:8000/self-healing-training/alert \
  -H "Content-Type: application/json" \
  -d '{
    "source": "diagnostic_engine",
    "severity": "high",
    "description": "Performance degradation detected",
    "affected_files": ["backend/app.py"]
  }'
```

**Expected Behavior:**
- Alert registered ✅
- Grace exits sandbox ✅
- Fixes real system ✅
- Returns to sandbox ✅
- New cycle starts ✅

---

### **Step 5: Check Knowledge Contribution**

**Verify:**
```python
# After fix, check knowledge was contributed
learning_id = grace_aligned_llm.contribute_to_grace_learning(
    llm_output="Fixed syntax error",
    query="fix syntax errors",
    trust_score=0.8
)

# Verify learning ID returned
assert learning_id is not None

# Verify memory exists
memories = grace_aligned_llm.retrieve_grace_memories("fix syntax errors")
assert any(mem.get("content", "").contains("Fixed syntax error") for mem in memories)
```

---

## 📈 **Monitoring Training Progress**

### **1. Check Cycles Completed**

**API:**
```bash
curl http://localhost:8000/self-healing-training/cycles
```

**Look for:**
- ✅ Increasing cycle count
- ✅ Improving success rates
- ✅ Escalating difficulty
- ✅ Knowledge accumulation

---

### **2. Monitor Success Rates**

**Expected Pattern:**
```
Cycle 1:  success_rate: 0.60, difficulty: 1.0
Cycle 2:  success_rate: 0.65, difficulty: 1.5
Cycle 3:  success_rate: 0.70, difficulty: 2.0
Cycle 4:  success_rate: 0.75, difficulty: 2.5
Cycle 5:  success_rate: 0.80, difficulty: 3.0
...
```

**Success rate should improve over time!**

---

### **3. Verify Knowledge Growth**

**Check Memory Mesh:**
```python
# Get all memories
memories = grace_aligned_llm.retrieve_grace_memories("", limit=1000)

# Count by type
syntax_memories = [m for m in memories if "syntax" in str(m.get("content", "")).lower()]
logic_memories = [m for m in memories if "logic" in str(m.get("content", "")).lower()]

print(f"Syntax knowledge: {len(syntax_memories)}")
print(f"Logic knowledge: {len(logic_memories)}")
```

**Knowledge should grow over time!**

---

## ✅ **Verification Checklist**

### **Training System:**
- [ ] Training system initialized
- [ ] Sandbox lab connected
- [ ] Healing system available
- [ ] Diagnostic engine connected
- [ ] LLM orchestrator available

### **Knowledge Retrieval:**
- [ ] Memories retrieved for tasks
- [ ] Relevant patterns found
- [ ] Trust scores available
- [ ] Knowledge matched to task type

### **Training Cycles:**
- [ ] Cycles start successfully
- [ ] 100 files collected per cycle
- [ ] Files fixed in sandbox
- [ ] Knowledge gained from fixes
- [ ] Cycles get harder over time

### **Alert System:**
- [ ] Alerts registered successfully
- [ ] Grace exits sandbox on alert
- [ ] Real system fixed
- [ ] Returns to sandbox after fix

### **Improvement:**
- [ ] Success rates improving
- [ ] Knowledge accumulating
- [ ] Patterns getting better
- [ ] Difficulty escalating

---

## 🚀 **Quick Start Continuous Training**

**Start Training:**
```bash
curl -X POST http://localhost:8000/self-healing-training/continuous \
  -H "Content-Type: application/json" \
  -d '{
    "folder_path": "backend/codebase",
    "max_cycles": null
  }'
```

**Monitor Progress:**
```bash
# Check status every 5 minutes
watch -n 300 'curl http://localhost:8000/self-healing-training/status'
```

**View Cycles:**
```bash
# See all completed cycles
curl http://localhost:8000/self-healing-training/cycles | jq
```

---

## 🎯 **Expected Results**

### **After 10 Cycles:**
- **Files Fixed**: 600-800 out of 1000 (60-80% success rate)
- **Knowledge**: 50-100 new patterns learned
- **Difficulty**: 5.0-6.0 (moderate)
- **Success Rate**: 60-80% (improving)

### **After 50 Cycles:**
- **Files Fixed**: 4000-4500 out of 5000 (80-90% success rate)
- **Knowledge**: 200-300 patterns learned
- **Difficulty**: 8.0-9.0 (high)
- **Success Rate**: 85-90% (excellent)

### **After 100 Cycles:**
- **Files Fixed**: 8500-9500 out of 10000 (85-95% success rate)
- **Knowledge**: 400-500 patterns learned
- **Difficulty**: 10.0 (maximum)
- **Success Rate**: 90-95% (expert-level)

---

## ✅ **Verification Status**

**Run the verification script to check:**

```bash
python scripts/verify_self_healing_training.py
```

**This will verify:**
- ✅ Training system is active
- ✅ Knowledge retrieval is working
- ✅ Training cycles are running
- ✅ Right knowledge for tasks
- ✅ Improvement over time

**Grace is ready for continuous training!** 🚀
