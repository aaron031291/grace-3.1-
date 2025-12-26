# Confidence Scoring - Verification Checklist

Use this checklist to verify that the confidence scoring system is properly implemented and functional.

## 📋 Pre-Deployment Checks

### Code Files Exist

- [ ] `backend/confidence_scorer/__init__.py` exists
- [ ] `backend/confidence_scorer/confidence_scorer.py` exists (~400 lines)
- [ ] `backend/database/migrate_add_confidence_scoring.py` exists
- [ ] All modified files have been updated

### Python Imports Work

```bash
cd /home/umer/Public/projects/grace_3/backend
python -c "from confidence_scorer import ConfidenceScorer; print('✓ ConfidenceScorer imports correctly')"
```

- [ ] ConfidenceScorer imports without error
- [ ] No circular import issues

### Models Updated

```bash
python -c "from models.database_models import Document; print(Document.__table__.columns.keys())"
```

- [ ] Document model has `confidence_score` column
- [ ] Document model has `source_reliability` column
- [ ] Document model has `content_quality` column
- [ ] Document model has `consensus_score` column
- [ ] Document model has `recency_score` column
- [ ] Document model has `confidence_metadata` column
- [ ] Document model does NOT have `trust_score` column (removed)
- [ ] DocumentChunk model has `confidence_score` column
- [ ] DocumentChunk model has `consensus_similarity_scores` column

## 🗄️ Database Migration

### Run Migration

```bash
cd /home/umer/Public/projects/grace_3
python -m backend.database.migrate_add_confidence_scoring
```

Check for success messages:

- [ ] Script completes without errors
- [ ] See message: "Migration completed at [timestamp]"
- [ ] New columns added to documents table
- [ ] New columns added to document_chunks table
- [ ] Old trust_score column removed (or warning if already removed)

### Verify Database Schema

```sql
-- For PostgreSQL
SELECT column_name, data_type FROM information_schema.columns
WHERE table_name = 'documents' AND column_name LIKE '%confidence%';

-- For SQLite
PRAGMA table_info(documents);
```

- [ ] confidence_score column exists (FLOAT)
- [ ] source_reliability column exists (FLOAT)
- [ ] content_quality column exists (FLOAT)
- [ ] consensus_score column exists (FLOAT)
- [ ] recency_score column exists (FLOAT)
- [ ] confidence_metadata column exists (TEXT)

```sql
-- Check document_chunks table
SELECT column_name FROM information_schema.columns
WHERE table_name = 'document_chunks' AND column_name LIKE '%confidence%';
```

- [ ] confidence_score column exists (FLOAT)
- [ ] consensus_similarity_scores column exists (TEXT)

## 🚀 API Endpoint Tests

### Start Backend Service

```bash
cd /home/umer/Public/projects/grace_3/backend
python app.py
```

- [ ] Backend starts without errors
- [ ] No import errors
- [ ] Service listens on port 8000

### Test Text Ingestion with source_type

**Request:**

```bash
curl -X POST http://localhost:8000/ingest/text \
  -H "Content-Type: application/json" \
  -d '{
    "text": "This is a test tutorial about Python loops. Loops are essential...",
    "filename": "test_tutorial.txt",
    "source_type": "verified_tutorial"
  }'
```

**Response should contain:**

- [ ] `success: true`
- [ ] `document_id` (e.g., 1)
- [ ] `message` with success text

### Test Document Info Endpoint

**Request:**

```bash
curl http://localhost:8000/ingest/documents/1
```

**Response should contain:**

- [ ] `confidence_score` (number between 0-1)
- [ ] `source_reliability` (should be 0.85 for verified_tutorial)
- [ ] `content_quality` (number between 0-1)
- [ ] `consensus_score` (number between 0-1)
- [ ] `recency_score` (number between 0-1)
- [ ] `chunks` array with chunk-level `confidence_score`
- [ ] Each chunk has `consensus_similarities` array

### Test File Upload with source_type

**Request:**

```bash
# Create test file
echo "This is an official Python documentation example..." > test.txt

curl -X POST http://localhost:8000/ingest/file \
  -F "file=@test.txt" \
  -F "source=upload" \
  -F "source_type=official_docs"
```

**Response should contain:**

- [ ] `success: true`
- [ ] `document_id`

### Test List Documents

**Request:**

```bash
curl "http://localhost:8000/ingest/documents?limit=10"
```

**Response should contain:**

- [ ] `documents` array
- [ ] Each document has `confidence_score` field
- [ ] No `trust_score` field

### Test Retrieval with Confidence

**Request:**

```bash
curl "http://localhost:8000/retrieve/search?query=Python%20tutorial&limit=5"
```

**Response should contain:**

- [ ] `results` array with chunks
- [ ] Each chunk has `confidence_score` field
- [ ] Each chunk has `score` field (similarity score)
- [ ] Metadata includes `confidence_score`
- [ ] Metadata includes `document_confidence_score`

## 🧪 Functional Tests

### Test Source Type Affects Score

```bash
# Create three documents with different source types

# Official docs
curl -X POST http://localhost:8000/ingest/text \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Official Python documentation: loops are control flow structures",
    "filename": "official.txt",
    "source_type": "official_docs"
  }'

# User generated
curl -X POST http://localhost:8000/ingest/text \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Official Python documentation: loops are control flow structures",
    "filename": "user.txt",
    "source_type": "user_generated"
  }'

# Unverified
curl -X POST http://localhost:8000/ingest/text \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Official Python documentation: loops are control flow structures",
    "filename": "unverified.txt",
    "source_type": "unverified"
  }'
```

**Verification:**

```python
from models.database_models import Document
from database.session import SessionLocal

db = SessionLocal()

official = db.query(Document).filter(Document.filename == "official.txt").first()
user = db.query(Document).filter(Document.filename == "user.txt").first()
unverified = db.query(Document).filter(Document.filename == "unverified.txt").first()

print(f"Official docs: {official.confidence_score:.2f}")  # Should be highest
print(f"User generated: {user.confidence_score:.2f}")      # Should be middle
print(f"Unverified: {unverified.confidence_score:.2f}")    # Should be lowest

# They should all have same text but different scores due to source_type
assert official.confidence_score > user.confidence_score > unverified.confidence_score
print("✓ Source type correctly affects confidence score")
```

- [ ] Official docs has highest score
- [ ] User generated has medium score
- [ ] Unverified has lowest score
- [ ] Difference is due to source_reliability component

### Test Content Quality Affects Score

```python
from models.database_models import Document
from database.session import SessionLocal

db = SessionLocal()

# Should have been created above
short = db.query(Document).filter(Document.filename == "short.txt").first()  # Short text
long = db.query(Document).filter(Document.filename == "long.txt").first()    # Long text with structure

if short and long:
    print(f"Short content: {short.content_quality:.2f}")
    print(f"Long content: {long.content_quality:.2f}")
    assert long.content_quality > short.content_quality
    print("✓ Content quality correctly affects confidence score")
```

- [ ] Well-structured content has higher content_quality
- [ ] Short, minimal content has lower content_quality

### Test Recency Affects Score

```python
from models.database_models import Document
from database.session import SessionLocal
from datetime import datetime, timedelta

db = SessionLocal()

# Inspect a document
doc = db.query(Document).first()
age_days = (datetime.utcnow() - doc.created_at).days

print(f"Document age: {age_days} days")
print(f"Recency score: {doc.recency_score:.2f}")

if age_days < 90:
    assert doc.recency_score == 1.0, f"Expected 1.0, got {doc.recency_score}"
    print("✓ Recent content has recency_score = 1.0")
```

- [ ] Newly created documents have recency_score = 1.0

## 🔒 Backward Compatibility

### Verify trust_score Parameter Removed

```bash
curl -X POST http://localhost:8000/ingest/text \
  -H "Content-Type: application/json" \
  -d '{
    "text": "test",
    "filename": "test.txt",
    "trust_score": 0.75
  }'
```

- [ ] Request is accepted (trust_score is ignored)
- [ ] OR request is rejected with clear error message
- [ ] Document is created successfully regardless

### Verify Default source_type Works

```bash
curl -X POST http://localhost:8000/ingest/text \
  -H "Content-Type: application/json" \
  -d '{
    "text": "test content",
    "filename": "test.txt"
  }'
```

- [ ] Request succeeds
- [ ] Document created with source_reliability = 0.50 (user_generated default)

## 📊 Monitoring & Verification

### Check Database Contains Scores

```python
from models.database_models import Document, DocumentChunk
from database.session import SessionLocal

db = SessionLocal()

# Check documents
docs_with_scores = db.query(Document).filter(
    Document.confidence_score != None
).count()

print(f"Documents with confidence scores: {docs_with_scores}")
assert docs_with_scores > 0, "No documents have confidence scores!"

# Check chunks
chunks_with_scores = db.query(DocumentChunk).filter(
    DocumentChunk.confidence_score != None
).count()

print(f"Chunks with confidence scores: {chunks_with_scores}")
assert chunks_with_scores > 0, "No chunks have confidence scores!"

print("✓ Database contains confidence scores")
```

- [ ] Documents have confidence_score values
- [ ] DocumentChunks have confidence_score values
- [ ] Scores are between 0.0 and 1.0

### Verify Consensus Calculation

```python
from models.database_models import DocumentChunk
from database.session import SessionLocal
import json

db = SessionLocal()

# Check if any chunks have consensus similarity scores
chunk = db.query(DocumentChunk).first()

if chunk and chunk.consensus_similarity_scores:
    similarities = json.loads(chunk.consensus_similarity_scores)
    print(f"Consensus similarity scores: {similarities}")

    # They should be numbers between 0 and 1
    assert all(isinstance(s, (int, float)) for s in similarities)
    assert all(0.0 <= s <= 1.0 for s in similarities)
    print("✓ Consensus scores are properly formatted")
else:
    print("Note: First chunk may not have consensus matches (expected for new content)")
```

- [ ] Chunk consensus_similarity_scores is valid JSON array
- [ ] All similarity values are between 0 and 1

## 📝 Logging Check

### Review Application Logs

```bash
# Look for confidence scoring messages
grep -i "confidence" /var/log/grace_backend.log  # Adjust path as needed
grep -i "consensus" /var/log/grace_backend.log
```

Should see messages like:

- ✓ "Created document record: ... confidence_score=0.xxx"
- ✓ "Calculated confidence scores for X chunks"
- ✓ "Average: X.XXX, Min: X.XXX, Max: X.XXX"

- [ ] Logs show confidence score calculations
- [ ] No errors related to confidence_scorer import
- [ ] Chunk processing logs show statistics

## 🎯 Final Verification

### Run Complete Test Suite

```python
#!/usr/bin/env python
"""Complete verification of confidence scoring system"""

from models.database_models import Document, DocumentChunk
from database.session import SessionLocal
from confidence_scorer import ConfidenceScorer
import json

print("🔍 Confidence Scoring System Verification\n")

# 1. Check imports
print("1. Checking imports...")
try:
    scorer = ConfidenceScorer()
    print("   ✓ ConfidenceScorer imports successfully")
except Exception as e:
    print(f"   ✗ Failed to import ConfidenceScorer: {e}")
    exit(1)

# 2. Check database schema
print("\n2. Checking database schema...")
db = SessionLocal()

doc = db.query(Document).first()
if not doc:
    print("   ⚠ No documents found in database")
else:
    required_fields = [
        'confidence_score', 'source_reliability', 'content_quality',
        'consensus_score', 'recency_score', 'confidence_metadata'
    ]

    for field in required_fields:
        if hasattr(doc, field):
            value = getattr(doc, field)
            print(f"   ✓ {field}: {value}")
        else:
            print(f"   ✗ Missing field: {field}")
            exit(1)

# 3. Check scoring components
print("\n3. Checking score components...")
if doc:
    print(f"   Overall confidence: {doc.confidence_score:.2f}")
    print(f"   - Source reliability: {doc.source_reliability:.2f}")
    print(f"   - Content quality: {doc.content_quality:.2f}")
    print(f"   - Consensus: {doc.consensus_score:.2f}")
    print(f"   - Recency: {doc.recency_score:.2f}")

    # Verify formula: score should be weighted sum of components
    calculated = (
        doc.source_reliability * 0.35 +
        doc.content_quality * 0.25 +
        doc.consensus_score * 0.25 +
        doc.recency_score * 0.10
    )
    print(f"   Calculated from formula: {calculated:.2f}")

    if abs(doc.confidence_score - calculated) < 0.01:
        print("   ✓ Score formula verified")
    else:
        print("   ✗ Score formula mismatch!")

# 4. Check chunks
print("\n4. Checking chunks...")
chunk = db.query(DocumentChunk).first()
if chunk:
    print(f"   ✓ Chunk confidence_score: {chunk.confidence_score:.2f}")
    if chunk.consensus_similarity_scores:
        sims = json.loads(chunk.consensus_similarity_scores)
        print(f"   ✓ Consensus similarities: {len(sims)} values")

print("\n✅ Verification Complete!")
print("\nIf all checks passed, the confidence scoring system is operational.")
```

- [ ] All required fields present
- [ ] Scores are valid numbers between 0-1
- [ ] Formula verification passes
- [ ] Chunks have scores

## 🚀 Deployment Sign-Off

When all checks pass:

- [ ] System is ready for production deployment
- [ ] No manual trust_score assignment allowed
- [ ] Confidence scores automatically calculated
- [ ] Retrieval includes confidence metrics
- [ ] Database properly migrated
- [ ] Backward compatibility verified

**Date Completed**: ******\_******

**Verified By**: ******\_******

**Notes**: **************************************\_**************************************

---

---

**System Status**: ✅ **CONFIDENCE SCORING OPERATIONAL**
