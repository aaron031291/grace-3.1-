# Multi-Tier Query Handling - Quick Start Guide

## Running the Database Migration

The migration script is ready but needs to be run with the correct Python path.

### Option 1: Using PYTHONPATH (Recommended)

```bash
cd /home/zair/Documents/grace/test/grace-3.1-/backend
PYTHONPATH=/home/zair/Documents/grace/test/grace-3.1-/backend python database/migrations/add_query_intelligence_tables.py
```

### Option 2: From Python Interactive Shell

```bash
cd /home/zair/Documents/grace/test/grace-3.1-/backend
python
```

Then in Python:
```python
import sys
sys.path.insert(0, '/home/zair/Documents/grace/test/grace-3.1-/backend')

from database.migrations.add_query_intelligence_tables import upgrade
upgrade()
```

### Option 3: Add to Migration Runner

Add to `backend/run_all_migrations.py`:

```python
from database.migrations.add_query_intelligence_tables import upgrade as query_intelligence_upgrade

# In the migration list:
migrations = [
    # ... existing migrations ...
    ("Query Intelligence Tables", query_intelligence_upgrade),
]
```

Then run:
```bash
cd backend
python run_all_migrations.py
```

---

## Verifying the Migration

### Check Tables Exist

```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('query_handling_log', 'knowledge_gaps', 'context_submissions');
```

### View Table Structure

```sql
\d query_handling_log
\d knowledge_gaps
\d context_submissions
```

---

## Testing the System

### 1. Start Grace Backend

```bash
cd /home/zair/Documents/grace/test/grace-3.1-/backend
source venv/bin/activate
python app.py
```

### 2. Test Tier 1 (VectorDB Success)

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "What is the Genesis Key system?"}
    ]
  }'
```

**Expected Response**:
- `tier`: "VECTORDB"
- `confidence`: > 0.7
- `sources`: Array of chunks
- `warnings`: null

### 3. Test Tier 2 (Model Knowledge)

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "What is Python programming language?"}
    ]
  }'
```

**Expected Response**:
- `tier`: "MODEL_KNOWLEDGE"
- `confidence`: 0.6-0.8
- `sources`: []
- `warnings`: ["This answer is based on the AI model's general knowledge..."]

### 4. Test Tier 3 (Context Request)

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "How do I deploy this project?"}
    ]
  }'
```

**Expected Response**:
- `tier`: "USER_CONTEXT"
- `confidence`: 0.0
- `knowledge_gaps`: Array of gaps with specific questions
- Message requesting context

### 5. Submit Context

```bash
curl -X POST http://localhost:8000/api/context/submit \
  -H "Content-Type: application/json" \
  -d '{
    "query_id": "q_abc123",
    "contexts": [
      {
        "gap_id": "gap_001",
        "value": "AWS with Docker containers"
      }
    ]
  }'
```

### 6. View Context Stats

```bash
curl http://localhost:8000/api/context/stats
```

---

## Files Created

### Core Implementation
1. `backend/database/migrations/add_query_intelligence_tables.py`
2. `backend/models/query_intelligence_models.py`
3. `backend/retrieval/query_intelligence.py`
4. `backend/retrieval/multi_tier_integration.py`
5. `backend/api/context_api.py`

### Modified
1. `backend/app.py` - ChatResponse model and /chat endpoint

### Documentation
1. `implementation_plan.md`
2. `task.md`
3. `status_tracker.md`
4. `walkthrough.md`
5. `QUICK_START.md` (this file)

---

## Troubleshooting

### Import Error: "No module named 'database'"

**Solution**: Set PYTHONPATH before running:
```bash
PYTHONPATH=/home/zair/Documents/grace/test/grace-3.1-/backend python database/migrations/add_query_intelligence_tables.py
```

### Migration Already Run

If tables already exist, the migration will skip creation (uses `CREATE TABLE IF NOT EXISTS`).

### Testing Without Migration

The system will work but won't log to database. Logs will appear in console only.

---

## Next Steps

1. ✅ Run database migration
2. ✅ Test all three tiers
3. ⏳ Create unit tests
4. ⏳ Build metrics dashboard
5. ⏳ Optimize performance
