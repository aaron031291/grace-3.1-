# GRACE LLM Alignment - Quick Start Guide

**Status:** ✅ Phase 1 Implemented - GRACE System Prompts Active

---

## ✅ What's Been Done

### 1. GRACE System Prompts Created
- **File**: `backend/llm_orchestrator/grace_system_prompts.py`
- **Status**: ✅ Complete
- **Impact**: All LLM interactions now receive GRACE architecture context

### 2. LLM Orchestrator Enhanced
- **File**: `backend/llm_orchestrator/llm_orchestrator.py`
- **Status**: ✅ Complete
- **Changes**:
  - GRACE system prompts automatically injected
  - GRACE context enhancement added
  - Code-aware prompts for code tasks

---

## 🎯 Immediate Benefits

**All LLM interactions now:**
1. ✅ Understand GRACE's architecture (Genesis Keys, Layer 1, Learning Memory)
2. ✅ Reference actual code files when discussing code
3. ✅ Consider trust scores from Layer 1
4. ✅ Follow OODA loop for reasoning tasks
5. ✅ Use GRACE terminology consistently

---

## 🚀 Next Steps (Priority Order)

### Step 1: Activate Autonomous Fine-Tuning (HIGH PRIORITY)

**Goal**: Automatically fine-tune models when enough high-trust examples accumulate.

**Action**:
```python
# In backend/llm_orchestrator/llm_orchestrator.py __init__
self.autonomous_trigger = get_autonomous_fine_tuning_trigger(
    auto_approve=False,  # Keep user approval for safety
    min_examples_for_trigger=500,
    min_trust_score=0.8
)
self.autonomous_trigger.start_monitoring()
```

**Result**: Models will automatically improve as GRACE learns.

---

### Step 2: Generate GRACE Training Data (HIGH PRIORITY)

**Goal**: Create training dataset from GRACE's codebase and documentation.

**Action**: Create `backend/llm_orchestrator/grace_training_data_generator.py`:

```python
from pathlib import Path
import json

class GRACETrainingDataGenerator:
    def generate_from_documentation(self):
        """Convert all .md files to Q&A format."""
        examples = []
        for md_file in Path(".").rglob("*.md"):
            content = md_file.read_text()
            # Parse sections as Q&A
            # ... implementation
        return examples
    
    def generate_from_codebase(self):
        """Extract code patterns as training examples."""
        examples = []
        for py_file in Path("backend").rglob("*.py"):
            # Extract docstrings, function descriptions
            # ... implementation
        return examples

# Generate dataset
generator = GRACETrainingDataGenerator()
dataset = generator.generate_from_documentation()
dataset += generator.generate_from_codebase()

# Save
with open("grace_training_data.json", "w") as f:
    json.dump(dataset, f, indent=2)
```

**Result**: Training data ready for fine-tuning.

---

### Step 3: Run First Fine-Tuning Job (MEDIUM PRIORITY)

**Goal**: Fine-tune a model on GRACE-specific data.

**Action**:
```python
from llm_orchestrator.fine_tuning import get_fine_tuning_system

fine_tuning = get_fine_tuning_system()

# Prepare dataset
dataset = fine_tuning.prepare_dataset(
    task_type="general",
    dataset_name="grace_architecture_v1",
    min_trust_score=0.8,
    num_examples=1000  # Start with subset
)

# Request approval
approval = fine_tuning.request_fine_tuning_approval(
    dataset=dataset,
    base_model="qwen2.5:7b-instruct",
    target_model_name="grace-aligned-v1",
    method=FineTuningMethod.QLORA
)

# Approve and start (after reviewing)
fine_tuning.approve_and_start_fine_tuning(
    job_id=approval.job_id,
    user_id="GU-user123",
    dry_run=False
)
```

**Result**: GRACE-aligned model ready to use.

---

### Step 4: Enhance Learning Example Retrieval (MEDIUM PRIORITY)

**Goal**: Actually retrieve learning examples for context injection.

**Action**: Update `backend/llm_orchestrator/llm_orchestrator.py`:

```python
# Replace placeholder learning example retrieval
if self.learning_memory and task_request.enable_learning:
    try:
        # Extract topic from prompt
        topic = self._extract_topic(enhanced_prompt)
        
        # Query learning memory
        learning_examples = self.learning_memory.get_examples_by_topic(
            topic=topic,
            min_trust_score=0.8,
            limit=3
        )
    except Exception as e:
        logger.warning(f"Could not retrieve learning examples: {e}")
        learning_examples = None
```

**Result**: LLMs get relevant high-trust examples in context.

---

### Step 5: Track Model Performance (LOW PRIORITY)

**Goal**: Know which models work best for GRACE tasks.

**Action**: Add performance tracking:

```python
# After LLM response
if result.success:
    self._track_model_performance(
        model=result.model_used,
        task_type=task_request.task_type,
        trust_score=result.trust_score,
        user_feedback=None  # Would come from user
    )
```

**Result**: Data-driven model selection.

---

## 📊 Testing Alignment

### Test 1: GRACE Architecture Understanding

```python
response = orchestrator.execute_task(
    prompt="How does GRACE assign Genesis Keys?",
    task_type=TaskType.GENERAL
)

# Check if response:
assert "Genesis Key" in response.content
assert "Layer 1" in response.content or "Layer 1" in response.content.lower()
assert response.trust_score > 0.7
```

### Test 2: Code Generation Alignment

```python
response = orchestrator.execute_task(
    prompt="Create a function that assigns Genesis Keys",
    task_type=TaskType.CODE_GENERATION
)

# Check if response:
assert "Genesis Key" in response.content
assert "Layer 1" in response.content or "layer1" in response.content.lower()
assert "backend/" in response.content  # References actual code paths
```

### Test 3: Reasoning with OODA

```python
response = orchestrator.execute_task(
    prompt="How should I design a new feature in GRACE?",
    task_type=TaskType.REASONING
)

# Check if response mentions:
# - OODA loop (Observe, Orient, Decide, Act)
# - Trust scores
# - Genesis Keys
# - Layer 1 integration
```

---

## 🎯 Success Metrics

### Alignment Metrics
- **GRACE Architecture Questions**: % answered correctly (target: 90%+)
- **Genesis Key References**: % of responses that mention Genesis Keys appropriately (target: 80%+)
- **Code File References**: % of code responses that reference actual files (target: 70%+)

### Intelligence Metrics
- **Trust Scores**: Average trust score for LLM responses (target: 0.8+)
- **Verification Pass Rate**: % passing hallucination checks (target: 95%+)
- **User Feedback**: Average user rating (target: 4.5/5.0+)

---

## 📝 Summary

**✅ Completed:**
- GRACE system prompts created and integrated
- All LLM interactions now GRACE-aware

**🚀 Next Steps:**
1. Activate autonomous fine-tuning
2. Generate GRACE training data
3. Run first fine-tuning job
4. Enhance learning example retrieval
5. Track model performance

**🎯 Goal:**
Make LLMs understand GRACE's architecture, follow GRACE's patterns, and continuously improve through fine-tuning.

---

## 🔧 Quick Commands

### Test GRACE Alignment
```bash
# Start GRACE
python launch_grace.py

# Test via API
curl -X POST "http://localhost:8000/llm/task" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "How does GRACE assign Genesis Keys?",
    "task_type": "general"
  }'
```

### Check System Prompts
```python
from llm_orchestrator.grace_system_prompts import get_grace_system_prompt

# See what prompts are being used
print(get_grace_system_prompt(task_type="code", include_code=True))
```

---

**Status**: Phase 1 Complete ✅ | Ready for Phase 2 (Fine-Tuning) 🚀
