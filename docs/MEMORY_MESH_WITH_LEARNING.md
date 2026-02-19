# Memory Mesh with Learning Memory Integration

## Overview

This system connects **learning memory** (with trust scores) to the **memory mesh**, creating a continuous learning feedback loop. All data in learning memory folders becomes training data with automatically calculated trust scores.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   LEARNING MEMORY (Layer 1)                      │
│                                                                  │
│  All learning data flows in with automatic trust scoring:       │
│  • User feedback                                                │
│  • System observations                                          │
│  • Corrections                                                  │
│  • Success/failure patterns                                     │
│                                                                  │
│  Trust Score = f(source, outcome, consistency, validation, age) │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│                    MEMORY MESH INTEGRATION                       │
│                                                                  │
│  High-trust examples (trust >= 0.7) flow into:                  │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Episodic    │  │  Procedural  │  │  Semantic    │          │
│  │  Memory      │  │  Memory      │  │  Network     │          │
│  │              │  │              │  │              │          │
│  │ Experiences  │  │ Learned      │  │ Knowledge    │          │
│  │ What         │  │ Skills       │  │ Facts        │          │
│  │ happened     │  │ How to do    │  │ What is true │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│                      FEEDBACK LOOP                               │
│                                                                  │
│  Outcomes feed back to update trust scores:                     │
│  • Successful use → Trust increases                             │
│  • Failed use → Trust decreases                                 │
│  • Age → Trust decays over time                                 │
│  • Validation → Trust adjusted                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Trust Scoring System

### Components of Trust Score

Trust score is calculated from 5 components:

#### 1. **Source Reliability** (40% weight)

Different sources have different inherent reliability:

```python
source_weights = {
    'user_feedback_positive': 0.9,
    'user_feedback_negative': 0.8,
    'system_observation_success': 0.85,
    'system_observation_failure': 0.9,  # Failures teach more
    'external_api_validated': 0.7,
    'external_api_unvalidated': 0.4,
    'inferred': 0.3,
    'assumed': 0.1
}
```

#### 2. **Outcome Quality** (30% weight)

How well did the actual outcome match the expected outcome?

- Perfect match: 1.0
- Partial match: 0.5-0.9
- No match: 0.0

#### 3. **Consistency** (20% weight)

Does this align with other high-trust knowledge?

- Highly consistent: 1.0
- Somewhat consistent: 0.5-0.9
- Contradictory: 0.0

#### 4. **Validation History** (10% weight)

How often has this been validated/invalidated?

```
validation_score = validated / (validated + invalidated)
```

#### 5. **Recency Weight** (multiplicative)

Exponential decay over time:

```
recency_weight = exp(-decay_rate * age_days)
Half-life: 90 days
```

### Final Trust Score Formula

```python
base_score = (
    source_reliability * 0.4 +
    outcome_quality * 0.3 +
    consistency * 0.2 +
    validation_score * 0.1
)

trust_score = base_score * recency_weight
```

## Memory Flow

### 1. Learning Data Ingestion

```python
# Example: User provides feedback
POST /learning-memory/user-feedback
{
  "interaction_id": "chat_123",
  "feedback_type": "correction",
  "correction": {
    "correct_answer": "The capital of France is Paris"
  },
  "user_id": "GU-abc123"
}

# Result:
# - Learning example created
# - Trust score: 0.9 (user feedback correction)
# - If trust >= 0.7 → Added to episodic memory
# - If trust >= 0.8 → Creates/updates procedure
```

### 2. High-Trust Data Flows to Memory Mesh

```python
# Trust >= 0.7 → Episodic Memory
if learning_example.trust_score >= 0.7:
    episode = create_episode(learning_example)
    # Episode available for recall in future decisions

# Trust >= 0.8 → Procedural Memory
if learning_example.trust_score >= 0.8:
    procedure = create_or_update_procedure(learning_example)
    # Procedure can be suggested for similar situations
```

### 3. Pattern Extraction

When 3+ similar high-trust examples exist:

```python
# Automatic pattern extraction
if similar_examples >= 3:
    pattern = extract_pattern(examples)
    # Pattern:
    # - Preconditions (when it applies)
    # - Actions (what to do)
    # - Expected outcomes (what should happen)
    # - Trust score (average of examples)
```

### 4. Feedback Loop

When learning data is used:

```python
# Update trust based on outcome
POST /learning-memory/feedback-loop/{example_id}
{
  "success": true,
  "actual_outcome": {...}
}

# Effects:
# - Trust increased if successful
# - Trust decreased if failed
# - Episodic/procedural memories updated
# - Low-trust examples (<0.5) removed from active memory
```

## API Endpoints

### Record Learning Experience

```bash
POST /learning-memory/record-experience
{
  "experience_type": "success",
  "context": {
    "goal": "configure authentication",
    "environment": "production"
  },
  "action_taken": {
    "steps": ["step 1", "step 2", "step 3"]
  },
  "outcome": {
    "success": true,
    "time_taken": 5.2
  },
  "expected_outcome": {
    "success": true
  },
  "source": "system_observation_success",
  "genesis_key_id": "GK-xyz"
}
```

**Response:**
```json
{
  "success": true,
  "learning_example_id": "LE-abc123",
  "message": "Learning experience recorded and integrated into memory mesh"
}
```

### Record User Feedback

```bash
POST /learning-memory/user-feedback
{
  "interaction_id": "chat_456",
  "feedback_type": "positive",
  "rating": 0.9,
  "feedback_text": "Great answer!",
  "user_id": "GU-user1"
}
```

**High-value learning data** - user feedback has high trust scores.

### Get Training Data

```bash
GET /learning-memory/training-data?min_trust_score=0.7&max_examples=1000
```

**Response:**
```json
{
  "success": true,
  "count": 450,
  "min_trust_score": 0.7,
  "data": [
    {
      "input": {...},
      "output": {...},
      "trust_score": 0.85,
      "source": "user_feedback_positive",
      "metadata": {
        "times_validated": 5,
        "times_invalidated": 0
      }
    },
    ...
  ]
}
```

**Use cases:**
- Fine-tuning language models
- Training classifiers
- Improving inference patterns

### Export Training Data

```bash
POST /learning-memory/export-training-data
{
  "min_trust_score": 0.8,
  "experience_type": "success",
  "export_format": "jsonl"
}
```

**Creates file:**
```
knowledge_base/exports/training_data_1673456789.jsonl
```

### Get Memory Mesh Stats

```bash
GET /learning-memory/stats
```

**Response:**
```json
{
  "success": true,
  "stats": {
    "learning_memory": {
      "total_examples": 5000,
      "high_trust_examples": 3500,
      "trust_ratio": 0.7
    },
    "episodic_memory": {
      "total_episodes": 3500,
      "linked_from_learning": 3500,
      "linkage_ratio": 1.0
    },
    "procedural_memory": {
      "total_procedures": 250,
      "high_success_procedures": 200,
      "success_ratio": 0.8
    },
    "pattern_extraction": {
      "total_patterns": 120
    }
  }
}
```

### Sync Learning Folders

```bash
POST /learning-memory/sync-folders
```

**What it does:**
- Reads all files from `knowledge_base/layer_1/learning_memory/*/`
- Ingests them into memory mesh with trust scoring
- Useful for batch import

### Feedback Loop Update

```bash
POST /learning-memory/feedback-loop/LE-abc123
{
  "success": true,
  "actual_outcome": {
    "result": "configured successfully"
  }
}
```

**Updates:**
- Learning example trust score
- Associated episodic memory
- Associated procedure success rate

### Decay Trust Scores

```bash
POST /learning-memory/decay-trust-scores
```

**Should be run daily (cron job)**

Applies time-based decay to all trust scores based on age.

## File System Structure

```
knowledge_base/
└── layer_1/
    └── learning_memory/
        ├── feedback/
        │   └── 2026-01-11/
        │       └── learning_1673456789.json
        ├── correction/
        │   └── 2026-01-11/
        │       └── learning_1673456790.json
        ├── success/
        │   └── 2026-01-11/
        │       └── learning_1673456791.json
        ├── failure/
        │   └── 2026-01-11/
        │       └── learning_1673456792.json
        └── pattern/
            └── 2026-01-11/
                └── learning_1673456793.json
```

### Example Learning File

```json
{
  "context": {
    "goal": "fix authentication error",
    "error_type": "401_unauthorized"
  },
  "action": {
    "steps": [
      "check token expiration",
      "refresh token",
      "retry request"
    ]
  },
  "outcome": {
    "success": true,
    "time_taken": 2.5
  },
  "expected_outcome": {
    "success": true
  },
  "source": "system_observation_success",
  "user_id": "GU-system",
  "genesis_key_id": "GK-fix-auth-001"
}
```

## Database Schema

### learning_examples

```sql
CREATE TABLE learning_examples (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,

    -- What was learned
    example_type TEXT NOT NULL,
    input_context TEXT NOT NULL,  -- JSON
    expected_output TEXT NOT NULL,  -- JSON
    actual_output TEXT,  -- JSON

    -- Trust scoring
    trust_score REAL DEFAULT 0.5 NOT NULL,
    source_reliability REAL DEFAULT 0.5 NOT NULL,
    outcome_quality REAL DEFAULT 0.5 NOT NULL,
    consistency_score REAL DEFAULT 0.5 NOT NULL,
    recency_weight REAL DEFAULT 1.0 NOT NULL,

    -- Provenance
    source TEXT NOT NULL,
    source_user_id TEXT,
    genesis_key_id TEXT,

    -- Learning metadata
    times_referenced INTEGER DEFAULT 0,
    times_validated INTEGER DEFAULT 0,
    times_invalidated INTEGER DEFAULT 0,
    last_used TIMESTAMP,

    -- Connections to memory mesh
    episodic_episode_id TEXT,
    procedure_id TEXT,

    -- Metadata
    metadata TEXT  -- JSON
);
```

### episodes

```sql
CREATE TABLE episodes (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP,

    -- What happened
    problem TEXT NOT NULL,
    action TEXT NOT NULL,  -- JSON
    outcome TEXT NOT NULL,  -- JSON
    predicted_outcome TEXT,  -- JSON
    prediction_error REAL DEFAULT 0.0,

    -- Trust
    trust_score REAL DEFAULT 0.5 NOT NULL,
    source TEXT NOT NULL,

    -- Links
    genesis_key_id TEXT,
    decision_id TEXT,

    -- Time
    timestamp TIMESTAMP,

    -- Similarity search
    embedding TEXT,  -- JSON array

    metadata TEXT  -- JSON
);
```

### procedures

```sql
CREATE TABLE procedures (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP,

    -- Identification
    name TEXT NOT NULL UNIQUE,
    goal TEXT NOT NULL,
    procedure_type TEXT NOT NULL,

    -- Execution
    steps TEXT NOT NULL,  -- JSON array
    preconditions TEXT NOT NULL,  -- JSON

    -- Quality
    trust_score REAL DEFAULT 0.5 NOT NULL,
    success_rate REAL DEFAULT 0.0 NOT NULL,
    usage_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,

    -- Evidence
    supporting_examples TEXT,  -- JSON array
    learned_from_episode_id TEXT,

    embedding TEXT,  -- JSON array
    metadata TEXT  -- JSON
);
```

### learning_patterns

```sql
CREATE TABLE learning_patterns (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP,

    pattern_name TEXT NOT NULL UNIQUE,
    pattern_type TEXT NOT NULL,

    -- Pattern definition
    preconditions TEXT NOT NULL,  -- JSON
    actions TEXT NOT NULL,  -- JSON
    expected_outcomes TEXT NOT NULL,  -- JSON

    -- Quality
    trust_score REAL DEFAULT 0.5 NOT NULL,
    success_rate REAL DEFAULT 0.0 NOT NULL,
    sample_size INTEGER DEFAULT 0,

    -- Evidence
    supporting_examples TEXT NOT NULL,  -- JSON array

    -- Usage
    times_applied INTEGER DEFAULT 0,
    times_succeeded INTEGER DEFAULT 0,
    times_failed INTEGER DEFAULT 0,

    linked_procedures TEXT  -- JSON array
);
```

## Migration

```bash
# Run migration to create memory mesh tables
cd backend
python database/migrate_add_memory_mesh.py
```

## Usage Examples

### Example 1: User Corrects Answer

```python
# User: "No, the capital of Australia is Canberra, not Sydney"

# 1. Record correction
response = requests.post('http://localhost:8000/learning-memory/user-feedback', json={
    "interaction_id": "chat_789",
    "feedback_type": "correction",
    "correction": {
        "question": "What is the capital of Australia?",
        "correct_answer": "Canberra"
    },
    "user_id": "GU-user1"
})

# 2. Learning example created:
# - trust_score: 0.9 (user correction)
# - Added to episodic memory
# - Next time Grace is asked, she recalls this episode

# 3. If similar corrections happen 3+ times:
# - Pattern extracted
# - Procedure created: "How to answer capital city questions"
```

### Example 2: System Learns from Success

```python
# System successfully completes a task

# 1. Record success
response = requests.post('http://localhost:8000/learning-memory/record-experience', json={
    "experience_type": "success",
    "context": {
        "goal": "optimize database query",
        "query_type": "SELECT with JOIN"
    },
    "action_taken": {
        "optimization": "add index on foreign key"
    },
    "outcome": {
        "success": true,
        "speedup": 10.5
    },
    "expected_outcome": {
        "success": true
    },
    "source": "system_observation_success"
})

# 2. Learning example created:
# - trust_score: 0.85 (system success)
# - Added to episodic and procedural memory
# - Procedure: "How to optimize queries with JOINs"

# 3. Next time similar query optimization needed:
# - Procedure suggested
# - Success rate tracked
# - Trust updated based on outcomes
```

### Example 3: Training Data Export

```python
# Get high-trust training data for fine-tuning

response = requests.get('http://localhost:8000/learning-memory/training-data', params={
    'min_trust_score': 0.8,
    'max_examples': 5000
})

training_data = response.json()['data']

# Use for:
# - Fine-tuning language model
# - Training classifier
# - Improving retrieval
```

## Benefits

### 1. **Continuous Learning**
- Grace learns from every interaction
- Trust scores ensure high-quality training data
- Feedback loops improve performance over time

### 2. **Automatic Trust Management**
- No manual data labeling needed
- Trust calculated from multiple signals
- Time decay prevents stale data

### 3. **Multi-Level Memory**
- Learning memory (raw experiences)
- Episodic memory (high-trust experiences)
- Procedural memory (learned skills)
- Patterns (extracted regularities)

### 4. **Traceable Learning**
- Every learning example linked to Genesis Key
- Full provenance tracking
- Auditable trust scores

### 5. **Selective Use**
- Only high-trust data used for training
- Low-trust data archived but not deleted
- Validation history tracked

## Maintenance

### Daily Cron Jobs

```bash
# Decay trust scores based on age
curl -X POST http://localhost:8000/learning-memory/decay-trust-scores

# Sync new learning files from file system
curl -X POST http://localhost:8000/learning-memory/sync-folders
```

### Monitoring

```bash
# Check memory mesh health
curl http://localhost:8000/learning-memory/stats
```

**Watch for:**
- Trust ratio < 0.5 (too much low-trust data)
- Linkage ratio < 0.7 (episodic memory not being populated)
- Success ratio < 0.5 (procedures not working well)

## Next Steps

1. **Run migration:** Create memory mesh tables
2. **Sync existing data:** Import learning files
3. **Start collecting:** Record feedback and outcomes
4. **Monitor trust:** Watch stats endpoint
5. **Export training data:** Use for fine-tuning

---

**The learning memory system ensures Grace continuously improves while maintaining high data quality through automatic trust scoring.**
