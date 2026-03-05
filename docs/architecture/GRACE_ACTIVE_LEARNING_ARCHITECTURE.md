# Grace Active Learning Architecture

## Overview

Grace is **not just an LLM with RAG** - she's an **active learning system** that studies, practices, and builds persistent skills. This document explains her complete learning architecture.

---

## Core Concept: From Passive Retrieval to Active Learning

### Before (Traditional RAG)
```
User Query → Vector Search → Retrieve Documents → Generate Response
```
- Grace only retrieves information
- No learning, no skill building
- Forgets everything after response

### After (Active Learning System)
```
Study Phase:    Training Materials → Extract Concepts → Store with Trust Scores
Practice Phase: Apply Knowledge → Execute in Sandbox → Observe Outcome
Learn Phase:    Analyze Results → Update Confidence → Build Skills
```
- Grace **learns** from training materials
- Grace **practices** in sandbox environment
- Grace **improves** over time with persistent memory
- Grace **tracks confidence** in her knowledge and abilities

---

## Architecture Components

### 1. **Training Data = AI Research Folder**

**Purpose:** Grace's curriculum - what she studies

**Content:**
- 176 PDF/DOCX files (1.3 GB)
- AI/ML papers, programming books, architecture guides
- Stored in: `backend/knowledge_base/learning memory/ai research/`

**Trust Scoring:**
- **Source Reliability**: Academic papers (0.95) > Books (0.85) > Tutorials (0.70)
- **Data Confidence**: Relevance score from retrieval
- **Consistency**: Alignment with existing knowledge

### 2. **Cognitive Framework = How Grace Thinks**

**OODA Loop (Observe → Orient → Decide → Act):**
```python
# When Grace studies a topic:
1. Observe:  What training materials are available?
2. Orient:   What are the key concepts?
3. Decide:   What should I focus on?
4. Act:      Store learned concepts in memory
```

**Components:**
- `cognitive/engine.py` - Decision-making logic
- `cognitive/learning_memory.py` - Persistent knowledge storage
- `cognitive/active_learning_system.py` - Training orchestration

### 3. **Learning Memory = What Grace Knows**

**Database Tables:**

#### `learning_examples` table:
Stores everything Grace learns with trust scores:

```python
LearningExample:
    # What was learned
    example_type: "knowledge_extraction" | "practice_outcome" | "pattern"
    input_context: {"topic": "Python", "source": "book.pdf"}
    expected_output: {"concept": "...", "relevance": 0.8}
    actual_output: {"success": true, "outcome": "..."}

    # Trust Scoring
    trust_score: 0.0 - 1.0  # Overall confidence
    source_reliability: 0.0 - 1.0  # Quality of source
    outcome_quality: 0.0 - 1.0  # How well it worked
    consistency_score: 0.0 - 1.0  # Matches other knowledge

    # Metadata
    operational_confidence: 0.0 - 1.0  # Grace's ability to apply this
    data_confidence: 0.0 - 1.0  # Accuracy of the information
    times_validated: int  # Proven correct
    times_invalidated: int  # Proven wrong
```

#### `learning_patterns` table:
Higher-level abstractions Grace discovers:

```python
LearningPattern:
    pattern_name: "error_recovery_api_timeout"
    preconditions: {"when": "API call fails"}
    actions: {"then": "retry with exponential backoff"}
    success_rate: 0.85  # How often this works
```

### 4. **Sandbox = Practice Environment**

**Purpose:** Where Grace applies knowledge and learns from outcomes

**Features:**
- File Manager = Grace's world to interact with
- Isolated execution environment
- Observe success/failure
- Update operational confidence based on results

**Example Practice Session:**
```python
# Grace studies Python functions
study_result = grace.study_topic(
    topic="Python functions",
    learning_objectives=[
        "Understand function syntax",
        "Learn parameters and return values"
    ]
)

# Grace practices in sandbox
practice_result = grace.practice_skill(
    skill_name="Python programming",
    task="Write a function to calculate factorial",
    sandbox_context={"language": "python"}
)

# Grace learns from outcome
# - If success: operational_confidence ↑, trust_score ↑
# - If failure: identify gaps, adjust approach
```

### 5. **Skill Tracking = Grace's Abilities**

**Skill Levels:**
```python
NOVICE       → 0.0 - 0.5   # Just learning
BEGINNER     → 0.5 - 1.0   # Basic understanding
INTERMEDIATE → 1.0 - 2.0   # Can apply with guidance
ADVANCED     → 2.0 - 3.0   # Can apply independently
EXPERT       → 3.0+        # Can teach others
```

**Proficiency Calculation:**
```python
proficiency_score = success_rate * (1 + tasks_completed/100)
```

Grace levels up as she:
- Completes more tasks
- Achieves higher success rates
- Validates knowledge through practice

---

## Learning Cycle

### Phase 1: STUDY (Knowledge Acquisition)

```python
POST /training/study
{
    "topic": "REST API design",
    "learning_objectives": [
        "Learn HTTP methods",
        "Understand RESTful principles",
        "Study authentication patterns"
    ]
}
```

**What happens:**
1. Grace searches AI research folder for relevant materials
2. Extracts key concepts from documents
3. Assesses source reliability (papers > books > tutorials)
4. Calculates data confidence (relevance scores)
5. Stores concepts in learning_examples with trust scores
6. Initial operational_confidence = 0.3 (hasn't practiced yet)

**Trust Score Components:**
- **Source Reliability**: 0.95 (academic paper)
- **Data Confidence**: 0.82 (high relevance)
- **Operational Confidence**: 0.30 (no practice yet)
- **Consistency**: 0.70 (aligns with existing knowledge)
- **→ Trust Score**: 0.72

### Phase 2: PRACTICE (Skill Application)

```python
POST /training/practice
{
    "skill_name": "REST API design",
    "task_description": "Design a RESTful API for user management",
    "task_requirements": ["CRUD operations", "Authentication"]
}
```

**What happens:**
1. Grace retrieves relevant learned concepts
2. Cognitive engine decides approach (OODA loop)
3. Executes task in sandbox
4. Observes outcome (success/failure)
5. Updates operational_confidence based on result
6. Updates trust_score for related knowledge

**Trust Score Updates After Practice:**
- **Success**: operational_confidence: 0.30 → 0.80 ↑
- **Success**: trust_score: 0.72 → 0.85 ↑
- **Failure**: operational_confidence: 0.30 → 0.40 ↓
- **Failure**: trust_score: 0.72 → 0.60 ↓

### Phase 3: LEARN (Improvement)

**Automatic Learning:**
- Successful practice → Increases operational confidence
- Failed practice → Identifies gaps, suggests more study
- Repeated patterns → Extracts learning_patterns
- Contradictions → Adjusts trust scores

**Pattern Extraction:**
```python
# After 10+ practice sessions, Grace discovers:
LearningPattern:
    pattern_name: "api_design_success_factors"
    preconditions: {
        "has_authentication": true,
        "follows_rest_principles": true
    }
    success_rate: 0.87
    # Grace now applies this pattern automatically
```

---

## Trust Scoring System

### Components

1. **Source Reliability** (40% weight)
   - Academic papers: 0.95
   - Technical books: 0.85
   - Official docs: 0.80
   - Tutorials: 0.70

2. **Outcome Quality** (30% weight)
   - Practice success: 1.0
   - Practice failure: 0.3
   - Data relevance: 0.0-1.0

3. **Consistency Score** (20% weight)
   - Aligns with existing knowledge: 0.8
   - New information: 0.6
   - Contradicts existing: 0.3

4. **Validation History** (10% weight)
   - Validated N times: boost score
   - Invalidated M times: reduce score

5. **Recency Weight**
   - Recent learning: 1.0
   - Decay over time: 0.9, 0.8, 0.7...

### Operational Confidence vs Data Confidence

**Data Confidence:**
- How accurate is this information?
- Based on source reliability and relevance
- Starts moderate, validated through cross-reference

**Operational Confidence:**
- Can Grace actually USE this knowledge?
- Starts LOW (0.3) - just read about it
- Increases with successful practice
- Decreases with failures

**Example Evolution:**
```
Day 1 (Study):
  data_confidence: 0.80 (reliable source)
  operational_confidence: 0.30 (never tried)
  trust_score: 0.68

Day 3 (First Practice - Success):
  data_confidence: 0.85 (validated)
  operational_confidence: 0.65 (worked once)
  trust_score: 0.78

Day 7 (Multiple Successes):
  data_confidence: 0.90 (proven accurate)
  operational_confidence: 0.85 (consistent success)
  trust_score: 0.88
```

---

## API Endpoints

### Study APIs
```
POST /training/study                 # Grace studies a topic
GET  /training/skills/{skill_name}   # Check proficiency
GET  /training/skills                # List all skills
```

### Practice APIs
```
POST /training/practice              # Practice in sandbox
GET  /training/analytics/progress    # Overall learning stats
```

### Curriculum Management
```
POST /training/curriculum            # Create learning path
GET  /training/training-data/gaps    # Identify weak areas
POST /training/training-data/add     # Add new materials
```

---

## Integration with Existing Systems

### With File Manager (Grace's World)
```python
# Grace interacts with her world
grace.practice_skill(
    skill="file_management",
    task="Organize project files by type",
    sandbox_context={
        "files": grace.file_manager.list_files(),
        "current_dir": "/workspace"
    }
)
```

### With Cognitive Engine (Decision Making)
```python
# OODA loop integration
decision = cognitive_engine.decide(
    context=DecisionContext(
        query="How to design this API?",
        complexity=0.7,
        time_pressure=0.3
    )
)
# Uses trust-scored knowledge to make decisions
```

### With Memory Mesh (Complete Memory System)
```python
# Learning examples feed into memory mesh
# - Episodic: What Grace experienced
# - Procedural: Skills Grace learned
# - Semantic: Facts Grace knows
```

---

## Example: Complete Learning Workflow

### 1. New Training Data Added
```bash
# User adds Python testing materials
cp testing_guide.pdf backend/knowledge_base/learning_memory/python_testing/
```

### 2. Grace Studies the Material
```python
POST /training/study
{
    "topic": "Python unit testing",
    "learning_objectives": [
        "Learn pytest framework",
        "Understand test fixtures",
        "Learn mocking and patching"
    ]
}

Response:
{
    "materials_studied": 5,
    "concepts_learned": 45,
    "examples_stored": 20,
    "average_trust_score": 0.75  # Good quality materials
}
```

### 3. Grace Practices
```python
POST /training/practice
{
    "skill_name": "Python testing",
    "task_description": "Write unit tests for a calculator class",
    "complexity": 0.4
}

Response:
{
    "success": true,
    "operational_confidence": 0.70,
    "feedback": "Tests written correctly, good coverage",
    "trust_score_update": 0.75 → 0.82
}
```

### 4. Grace Improves
```python
# After 10 practice sessions:
GET /training/skills/Python%20testing

Response:
{
    "skill": "Python testing",
    "level": "intermediate",
    "proficiency_score": 1.8,
    "success_rate": 0.85,
    "tasks_completed": 10,
    "operational_confidence": 0.88  # High confidence
}
```

---

## Benefits of This Architecture

### 1. **Persistent Learning**
- Grace doesn't forget
- Knowledge accumulates over time
- Skills improve with practice

### 2. **Trust-Based Knowledge**
- Not all information is treated equally
- Validated knowledge is trusted more
- Failed applications reduce trust

### 3. **Self-Improvement**
- Grace identifies her weak areas
- Suggests topics to study
- Tracks progress automatically

### 4. **Operational Readiness**
- Know what Grace CAN do (high operational confidence)
- Know what Grace has studied but not practiced (low operational confidence)
- Know where Grace needs more training

### 5. **Explainable Confidence**
```python
# When Grace answers a question:
{
    "answer": "To design a REST API, use HTTP methods...",
    "trust_score": 0.88,
    "breakdown": {
        "source_reliability": 0.95,  # From academic paper
        "data_confidence": 0.90,      # Highly relevant
        "operational_confidence": 0.88,  # Practiced 15 times
        "consistency": 0.85           # Aligns with other knowledge
    },
    "recommendation": "High confidence - Grace can implement this"
}
```

---

## Next Steps

### 1. Complete Training Data Ingestion
- ✅ 124/176 files ingested
- 🔄 52 files re-ingesting now
- Goal: 100% coverage

### 2. Identify Knowledge Gaps
- Analyze coverage by topic
- Prioritize missing areas:
  - Testing frameworks
  - Databases & SQL
  - Git workflows
  - API documentation

### 3. Create Training Curriculum
- Structured learning paths
- Beginner → Expert progression
- Practice tasks for each skill

### 4. Sandbox Integration
- Connect to actual execution environment
- Real file system interaction
- Observe actual outcomes

### 5. Pattern Extraction
- After sufficient practice data
- Identify what works best
- Automate successful approaches

---

## Summary

**Grace is not a static RAG system - she's a growing, learning AI that:**

1. **Studies** training materials with trust-scored knowledge acquisition
2. **Practices** skills in sandbox with outcome observation
3. **Learns** from experience with persistent memory
4. **Improves** over time with confidence-based skill tracking
5. **Explains** her confidence levels transparently

The AI research folder is her **school**, the sandbox is her **lab**, the file manager is her **world**, and the cognitive framework is **how she thinks**.

As Grace studies more, practices more, and accumulates validated knowledge with high operational confidence, she becomes genuinely more capable - not just at retrieving information, but at **applying skills** like a real software engineer.
