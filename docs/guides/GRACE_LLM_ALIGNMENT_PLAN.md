# GRACE LLM Alignment & Intelligence Enhancement Plan

**Goal:** Make LLMs more GRACE-aligned, intelligent, and all-around better for GRACE's specific needs.

---

## 🎯 Current State

### ✅ Current LLM Stack (2026)

**Primary Models (Ollama-based):**

1. **Code Generation Models:**
   - **DeepSeek-Coder-V2** (16B/33B) - Best for code generation, debugging, explanation
   - **Qwen2.5-Coder** (7B-32B) - Code understanding, generation, review
   - **CodeQwen1.5** (7B) - Fast code queries

2. **Reasoning Models:**
   - **Qwen2.5** (72B) - Strong reasoning, planning, cognitive framework following
   - **DeepSeek-R1** (7B-70B) - Chain-of-thought reasoning
   - **Llama 3.3** (70B) - General reasoning and tasks

3. **Fast Query Models:**
   - **Mistral-Small** (22B) - Fast inference, quick validation
   - **Gemma 2** (9B-27B) - Efficient validation tasks
   - **Mixtral-8x7b** - Multi-expert model

4. **Default Model:**
   - **Mistral:7b** - Default fallback model

**Embedding Model:**
   - **Qwen 4B** - Text embeddings for RAG system

**Model Selection Logic:**
   - Automatic model discovery from Ollama
   - Task-based routing (code → code models, reasoning → reasoning models)
   - Priority-based selection (higher priority = preferred)
   - Fallback to `mistral:7b` if preferred models unavailable
   - Context window awareness (larger context for RAG tasks)

### ✅ What's Already Built

1. **Multi-LLM Client** (`backend/llm_orchestrator/multi_llm_client.py`)
   - Automatic model discovery from Ollama
   - Task-based model selection (code, reasoning, general)
   - Fallback model support
   - Response caching with TTL
   - Rate limiting and retry logic
   - Model performance statistics

2. **Fine-Tuning System** (`backend/llm_orchestrator/fine_tuning.py`)
   - Supports LoRA, QLoRA, full fine-tuning
   - User approval workflow
   - Training metrics tracking

3. **Autonomous Fine-Tuning Trigger** (`backend/llm_orchestrator/autonomous_fine_tuning_trigger.py`)
   - Monitors learning examples
   - Triggers fine-tuning when thresholds met
   - Evaluates benefits using LLMs

4. **Proactive Code Intelligence** (`backend/llm_orchestrator/proactive_code_intelligence.py`)
   - Monitors code changes
   - Provides code context to LLMs
   - Learns from code patterns

5. **Learning Integration** (`backend/llm_orchestrator/learning_integration.py`)
   - Integrates with learning memory
   - Records high-trust examples
   - Feeds outcomes back to system

6. **Hallucination Mitigation** (`backend/llm_orchestrator/hallucination_guard.py`)
   - 5-layer verification pipeline
   - Repository grounding
   - Cross-model consensus

7. **Cognitive Enforcer** (`backend/llm_orchestrator/cognitive_enforcer.py`)
   - Enforces 12 OODA invariants
   - Safety-critical task validation
   - Trust score integration

8. **Repository Access** (`backend/llm_orchestrator/repo_access.py`)
   - Read-only access to all GRACE systems
   - Code search and retrieval
   - Documentation access

9. **LLM Collaboration** (`backend/llm_orchestrator/llm_collaboration.py`)
   - Inter-LLM debate and consensus
   - Multi-model validation
   - Delegation patterns

10. **Model Registry** (`backend/llm_orchestrator/multi_llm_client.py`)
    - Optimized for GRACE Memory System
    - Automatic model discovery
    - Task-based model selection
    - Performance statistics tracking

---

## 🌐 Web Learning System (NEW)

**Status:** Proposed - See `GRACE_WEB_LEARNING_SYSTEM.md` for full details

**Recommendation:** YES, LLMs should have web access for learning, but it must be:
- Integrated with GRACE's architecture (Layer 1, Genesis Keys, trust scoring)
- Safe and controlled (whitelist, rate limiting, content filtering)
- Trust-scored (source reliability, content quality)
- Stored in learning memory (high-trust content becomes knowledge)
- Tracked with Genesis Keys (complete audit trail)

**Benefits:**
- Learn current information
- Verify facts against authoritative sources
- Fill knowledge gaps
- Stay up-to-date with technologies

---

## 🚀 What Needs to Happen

### Phase 1: GRACE-Specific System Prompts (IMMEDIATE)

**Problem:** LLMs don't understand GRACE's architecture, Genesis Keys, Layer 1, etc.

**Solution:** Create GRACE-aware system prompts that are always injected.

**Action Items:**

1. **Create GRACE System Prompt Library** (`backend/llm_orchestrator/grace_system_prompts.py`)
   ```python
   GRACE_ARCHITECTURE_PROMPT = """
   You are GRACE (Generalized Reasoning and Cognitive Engine), a neuro-symbolic AI system.
   
   Key Components:
   - Genesis Keys: Universal tracking for all operations
   - Layer 1: Trust & Truth Foundation (OODA loop + 12 invariants)
   - Learning Memory: Trust-scored knowledge base
   - RAG System: Document retrieval
   - Code Intelligence: Source code awareness
   
   When responding:
   - Always reference Genesis Keys when tracking operations
   - Consider trust scores from Layer 1
   - Ground responses in learning memory when possible
   - Reference actual code files when discussing code
   - Follow OODA loop: Observe → Orient → Decide → Act
   """
   ```

2. **Enhance Multi-LLM Client** to always prepend GRACE context
   - Modify `multi_llm_client.py` to inject GRACE prompts
   - Add task-specific GRACE context (e.g., code tasks get codebase context)

3. **Create GRACE Context Builder** (`backend/llm_orchestrator/grace_context_builder.py`)
   - Builds context from:
     - Genesis Keys (related operations)
     - Layer 1 trust scores
     - Learning memory examples
     - Code repository state
     - Recent interactions

---

### Phase 2: GRACE-Specific Training Data Generation (HIGH PRIORITY)

**Problem:** LLMs aren't trained on GRACE-specific patterns, architecture, workflows.

**Solution:** Generate training datasets from GRACE's knowledge base and interactions.

**Action Items:**

1. **Create GRACE Training Data Generator** (`backend/llm_orchestrator/grace_training_data_generator.py`)
   ```python
   class GRACETrainingDataGenerator:
       """Generates training data from GRACE's knowledge."""
       
       def generate_from_codebase(self):
           """Extract code patterns, docstrings, comments as training examples."""
           
       def generate_from_documentation(self):
           """Convert GRACE docs to Q&A format."""
           
       def generate_from_interactions(self):
           """Use high-trust LLM interactions as training examples."""
           
       def generate_from_learning_memory(self):
           """Convert learning examples to training format."""
   ```

2. **Extract Training Examples From:**
   - **Codebase**: Function docstrings, class descriptions, code comments
   - **Documentation**: All `.md` files converted to Q&A pairs
   - **High-Trust Interactions**: LLM responses with trust > 0.8
   - **Learning Memory**: Trust-scored learning examples
   - **Genesis Key Patterns**: Common operation patterns

3. **Format as Training Data:**
   ```json
   {
     "instruction": "How does GRACE assign Genesis Keys?",
     "input": "",
     "output": "GRACE assigns Genesis Keys through Layer 1 integration. Every operation flows through the cognitive engine (OODA loop + 12 invariants), which creates a Genesis Key with metadata including operation type, user ID, timestamp, and trust score.",
     "context": "genesis_keys.md, layer1_integration.py"
   }
   ```

---

### Phase 3: Continuous Fine-Tuning Pipeline (HIGH PRIORITY)

**Problem:** Fine-tuning exists but isn't actively running or optimized for GRACE.

**Solution:** Activate and enhance the autonomous fine-tuning system.

**Action Items:**

1. **Activate Autonomous Fine-Tuning Trigger**
   ```python
   # In llm_orchestrator.py initialization
   autonomous_trigger = get_autonomous_fine_tuning_trigger(
       auto_approve=False,  # Keep user approval for safety
       min_examples_for_trigger=500,
       min_trust_score=0.8
   )
   autonomous_trigger.start_monitoring()
   ```

2. **Create GRACE-Specific Fine-Tuning Jobs**
   - **Code Generation**: Fine-tune on GRACE codebase patterns
   - **Reasoning**: Fine-tune on GRACE's OODA loop reasoning
   - **Documentation**: Fine-tune on GRACE architecture understanding
   - **Multi-Modal**: Fine-tune on GRACE's multimodal workflows

3. **Enhance Fine-Tuning with GRACE Context**
   - Include Genesis Key patterns in training
   - Include Layer 1 trust scoring examples
   - Include code intelligence examples
   - Include learning memory patterns

---

### Phase 4: Enhanced Context Injection (MEDIUM PRIORITY)

**Problem:** LLMs don't always have relevant GRACE context in prompts.

**Solution:** Always inject relevant GRACE context automatically.

**Action Items:**

1. **Create Context Injection System** (`backend/llm_orchestrator/grace_context_injection.py`)
   ```python
   class GRACEContextInjector:
       """Injects GRACE context into all LLM prompts."""
       
       def inject_for_task(self, task_type, prompt):
           """Inject relevant context based on task type."""
           context = []
           
           # Always include:
           context.append(self.get_grace_architecture_context())
           
           # Task-specific:
           if task_type == TaskType.CODE_GENERATION:
               context.append(self.get_codebase_context(prompt))
               context.append(self.get_genesis_key_patterns())
           
           if task_type == TaskType.REASONING:
               context.append(self.get_ooda_loop_context())
               context.append(self.get_trust_scoring_context())
           
           return self.build_prompt(context, prompt)
   ```

2. **Context Sources:**
   - **Genesis Keys**: Related operations and patterns
   - **Layer 1**: Trust scores, OODA decisions
   - **Learning Memory**: High-trust examples
   - **Codebase**: Relevant code files
   - **Documentation**: GRACE architecture docs
   - **Recent Interactions**: Similar past queries

---

### Phase 5: GRACE-Specific Model Selection (MEDIUM PRIORITY)

**Problem:** Model selection doesn't consider GRACE-specific needs.

**Solution:** Enhance model selection with GRACE-aware logic.

**Action Items:**

1. **Create GRACE Model Selector** (`backend/llm_orchestrator/grace_model_selector.py`)
   ```python
   class GRACEModelSelector:
       """Selects models optimized for GRACE tasks."""
       
       def select_for_grace_task(self, task_type, context):
           """Select model considering GRACE-specific factors."""
           
           # For code tasks, prefer models fine-tuned on GRACE codebase
           if task_type == TaskType.CODE_GENERATION:
               if self.has_grace_finetuned_model():
                   return "grace-coder-v1"
           
           # For reasoning, prefer models that understand OODA
           if task_type == TaskType.REASONING:
               return self.select_reasoning_model()
           
           # Default to best available
           return self.select_default_model()
   ```

2. **Track Model Performance for GRACE Tasks**
   - Which models perform best for GRACE-specific tasks?
   - Track success rates, trust scores, user feedback
   - Automatically prefer better-performing models

---

### Phase 6: Learning from GRACE Interactions (HIGH PRIORITY)

**Problem:** LLMs don't learn from successful GRACE interactions.

**Solution:** Capture and learn from high-quality interactions.

**Action Items:**

1. **Enhance Learning Integration** to capture more examples
   ```python
   # In llm_orchestrator.py after successful task
   if result.trust_score > 0.8 and result.confidence_score > 0.8:
       learning_integration.record_llm_interaction(
           prompt=task_request.prompt,
           response=result.content,
           trust_score=result.trust_score,
           context={
               "genesis_key_id": result.genesis_key_id,
               "task_type": task_request.task_type,
               "model_used": result.model_used
           }
       )
   ```

2. **Create Interaction Quality Scorer**
   - Score interactions based on:
     - Trust score
     - User feedback
     - Verification results
     - Follow-up success
   - Only learn from high-quality examples

3. **Automatic Training Data Generation**
   - Periodically convert high-quality interactions to training data
   - Format for fine-tuning
   - Trigger fine-tuning when enough examples accumulate

---

### Phase 7: GRACE Architecture Understanding (HIGH PRIORITY)

**Problem:** LLMs don't deeply understand GRACE's architecture.

**Solution:** Train/fine-tune on GRACE architecture documentation.

**Action Items:**

1. **Create GRACE Architecture Training Dataset**
   - Convert all `.md` documentation to training format
   - Create Q&A pairs about GRACE architecture
   - Include code examples from GRACE codebase

2. **Fine-Tune on GRACE Documentation**
   ```python
   # Generate dataset from docs
   dataset = grace_training_data_generator.generate_from_documentation()
   
   # Fine-tune model
   fine_tuning_system.prepare_dataset(
       task_type="general",
       dataset_name="grace_architecture_v1",
       examples=dataset
   )
   ```

3. **Test Architecture Understanding**
   - Create test questions about GRACE
   - Verify LLMs can answer correctly
   - Iterate until understanding is good

---

### Phase 8: Proactive Learning Enhancement (MEDIUM PRIORITY)

**Problem:** Proactive code intelligence exists but could be more aggressive.

**Solution:** Enhance proactive learning to be more active.

**Action Items:**

1. **Enhance Code Intelligence Monitoring**
   - Monitor more file types
   - Analyze code patterns more deeply
   - Extract more learning opportunities

2. **Create Code Pattern Learning**
   ```python
   # When code changes detected
   code_analysis = proactive_code_intelligence.analyze_code_change(file_path)
   
   # Extract learning opportunities
   learning_examples = code_analysis.extract_learning_examples()
   
   # Record in learning memory
   for example in learning_examples:
       learning_memory.record_example(example, trust_score=0.85)
   ```

3. **Automatic Code Documentation Generation**
   - LLMs generate documentation for new code
   - Learn from code patterns
   - Build code knowledge base

---

## 📋 Implementation Checklist

### Immediate (Week 1)
- [ ] Create GRACE system prompt library
- [ ] Enhance multi-LLM client to inject GRACE prompts
- [ ] Create GRACE context builder
- [ ] Test with sample queries

### Short-term (Weeks 2-4)
- [ ] Create GRACE training data generator
- [ ] Generate initial training dataset from codebase/docs
- [ ] Activate autonomous fine-tuning trigger
- [ ] Run first fine-tuning job on GRACE data

### Medium-term (Months 2-3)
- [ ] Enhance context injection system
- [ ] Create GRACE model selector
- [ ] Track model performance for GRACE tasks
- [ ] Iterate on fine-tuning based on results

### Long-term (Months 4-6)
- [ ] Continuous learning from interactions
- [ ] Proactive learning enhancements
- [ ] Architecture understanding improvements
- [ ] Performance optimization

---

## 🎯 Success Metrics

### Alignment Metrics
- **GRACE Architecture Understanding**: % of questions about GRACE answered correctly
- **Genesis Key Awareness**: % of responses that reference Genesis Keys appropriately
- **Layer 1 Integration**: % of responses that consider trust scores

### Intelligence Metrics
- **Code Generation Quality**: Trust scores for code generation tasks
- **Reasoning Quality**: OODA loop adherence in reasoning tasks
- **Context Relevance**: Relevance of injected context

### Performance Metrics
- **Response Quality**: User feedback scores
- **Trust Scores**: Average trust scores for LLM responses
- **Verification Pass Rate**: % of responses passing hallucination checks

---

## 🔧 Technical Implementation

### 1. GRACE System Prompt Library

Create `backend/llm_orchestrator/grace_system_prompts.py`:

```python
GRACE_BASE_PROMPT = """
You are GRACE (Generalized Reasoning and Cognitive Engine), a neuro-symbolic AI system.

Core Architecture:
- Genesis Keys: Universal tracking for all operations (format: GK-{type}-{timestamp}-{hash})
- Layer 1: Trust & Truth Foundation with OODA loop (Observe → Orient → Decide → Act)
- Learning Memory: Trust-scored knowledge base (trust scores 0.0-1.0)
- RAG System: Document retrieval from vector database
- Code Intelligence: Source code awareness and analysis

When responding:
1. Always consider trust scores from Layer 1
2. Reference Genesis Keys when tracking operations
3. Ground responses in learning memory when possible
4. Reference actual code files when discussing code
5. Follow OODA loop for reasoning tasks
6. Consider 12 OODA invariants for safety-critical tasks
"""

GRACE_CODE_PROMPT = """
You have read-only access to GRACE's source code repository.

When generating code:
- Follow GRACE's code patterns and conventions
- Reference existing functions/classes when relevant
- Consider Genesis Key tracking for operations
- Include trust scoring where appropriate
- Follow Layer 1 integration patterns
"""

GRACE_REASONING_PROMPT = """
For reasoning tasks, follow GRACE's OODA loop:

1. OBSERVE: What information is available?
   - Learning memory examples
   - Trust scores
   - Related Genesis Keys
   - Code context

2. ORIENT: What are the constraints and context?
   - Layer 1 trust requirements
   - Safety constraints
   - Available resources

3. DECIDE: What is the best approach?
   - Consider multiple options
   - Evaluate trust implications
   - Minimize blast radius

4. ACT: Execute decision
   - Track with Genesis Key
   - Update trust scores
   - Learn from outcome
"""
```

### 2. GRACE Training Data Generator

Create `backend/llm_orchestrator/grace_training_data_generator.py`:

```python
class GRACETrainingDataGenerator:
    """Generates training data from GRACE's knowledge."""
    
    def generate_from_codebase(self) -> List[Dict]:
        """Extract code patterns as training examples."""
        examples = []
        
        # Find all Python files
        for py_file in Path("backend").rglob("*.py"):
            # Extract docstrings
            docstrings = self.extract_docstrings(py_file)
            
            # Extract function/class descriptions
            descriptions = self.extract_descriptions(py_file)
            
            # Create Q&A pairs
            for doc in docstrings:
                examples.append({
                    "instruction": f"What does this code do? {py_file.name}",
                    "input": doc["code"],
                    "output": doc["description"],
                    "context": str(py_file)
                })
        
        return examples
    
    def generate_from_documentation(self) -> List[Dict]:
        """Convert GRACE docs to Q&A format."""
        examples = []
        
        for md_file in Path(".").rglob("*.md"):
            content = md_file.read_text()
            
            # Extract sections as Q&A
            sections = self.parse_markdown_sections(content)
            
            for section in sections:
                examples.append({
                    "instruction": section["title"],
                    "input": "",
                    "output": section["content"],
                    "context": str(md_file)
                })
        
        return examples
```

### 3. Enhanced Context Injection

Modify `backend/llm_orchestrator/llm_orchestrator.py`:

```python
def _enhance_prompt_with_grace_context(
    self,
    prompt: str,
    task_type: TaskType,
    task_request: LLMTaskRequest
) -> str:
    """Enhance prompt with GRACE-specific context."""
    
    context_parts = []
    
    # Base GRACE context
    context_parts.append(GRACE_BASE_PROMPT)
    
    # Task-specific context
    if task_type == TaskType.CODE_GENERATION:
        context_parts.append(GRACE_CODE_PROMPT)
        # Add relevant code files
        if self.repo_access:
            relevant_files = self.repo_access.search_code(
                pattern=extract_keywords(prompt),
                max_results=5
            )
            context_parts.append(f"Relevant code files: {relevant_files}")
    
    if task_type == TaskType.REASONING:
        context_parts.append(GRACE_REASONING_PROMPT)
        # Add relevant learning examples
        if self.learning_memory:
            examples = self.learning_memory.get_high_trust_examples(
                topic=extract_topic(prompt),
                min_trust=0.8,
                limit=3
            )
            context_parts.append(f"Relevant learning examples: {examples}")
    
    # Build enhanced prompt
    enhanced_prompt = "\n\n".join(context_parts) + "\n\nUser Query: " + prompt
    
    return enhanced_prompt
```

---

## 🚀 Quick Start

### Step 1: Install Current LLM Models
```bash
# Code generation models (recommended)
ollama pull deepseek-coder:33b-instruct
ollama pull qwen2.5-coder:32b-instruct
ollama pull codeqwen:7b

# Reasoning models
ollama pull qwen2.5:72b-instruct
ollama pull deepseek-r1:70b
ollama pull llama3.3:70b-instruct

# Fast query models
ollama pull mistral-small:22b
ollama pull gemma2:27b-instruct

# Default fallback
ollama pull mistral:7b

# Verify installation
curl http://localhost:8000/llm/models
```

### Step 2: Create GRACE System Prompts
```bash
# Create the file
touch backend/llm_orchestrator/grace_system_prompts.py
# Implement prompts (see Technical Implementation above)
```

### Step 3: Generate Initial Training Data
```python
from llm_orchestrator.grace_training_data_generator import GRACETrainingDataGenerator

generator = GRACETrainingDataGenerator()
dataset = generator.generate_from_documentation()
dataset += generator.generate_from_codebase()

# Save dataset
import json
with open("grace_training_data.json", "w") as f:
    json.dump(dataset, f, indent=2)
```

### Step 4: Activate Fine-Tuning
```python
from llm_orchestrator.fine_tuning import get_fine_tuning_system
from llm_orchestrator.autonomous_fine_tuning_trigger import get_autonomous_fine_tuning_trigger

# Start monitoring
trigger = get_autonomous_fine_tuning_trigger()
trigger.start_monitoring()
```

### Step 5: Test Alignment
```python
# Test with GRACE-specific questions
response = orchestrator.execute_task(
    prompt="How does GRACE assign Genesis Keys?",
    task_type=TaskType.GENERAL
)

# Check if response references Genesis Keys, Layer 1, etc.
assert "Genesis Key" in response.content
assert "Layer 1" in response.content
```

---

## 📊 Expected Improvements

After implementing this plan:

1. **Alignment**: LLMs will understand GRACE architecture (90%+ accuracy on GRACE questions)
2. **Intelligence**: Better code generation following GRACE patterns
3. **Context Awareness**: Always have relevant GRACE context
4. **Learning**: Continuously improve from interactions
5. **Performance**: Higher trust scores, better user feedback

---

## ✅ Summary

To make LLMs more GRACE-aligned and intelligent:

1. **Immediate**: Add GRACE system prompts to all LLM interactions
2. **Short-term**: Generate training data from GRACE codebase/docs and fine-tune
3. **Medium-term**: Enhance context injection and model selection
4. **Long-term**: Continuous learning from interactions

**Key Principle**: Every LLM interaction should be aware of GRACE's architecture, use GRACE's context, and learn from GRACE's patterns.
