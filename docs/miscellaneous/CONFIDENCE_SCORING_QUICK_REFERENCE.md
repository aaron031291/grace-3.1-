# Confidence Scoring Quick Reference

## 🎯 Quick Start

### For Users/Frontend

#### Ingesting Documents

```json
POST /ingest/text
{
  "text": "Your document content...",
  "filename": "document.txt",
  "source_type": "verified_tutorial"
}
```

**source_type options:**

- `official_docs` → score multiplier: 0.95
- `academic_paper` → score multiplier: 0.90
- `verified_tutorial` → score multiplier: 0.85
- `trusted_blog` → score multiplier: 0.75
- `community_qa` → score multiplier: 0.65
- `user_generated` → score multiplier: 0.50 (default)
- `unverified` → score multiplier: 0.30

#### Retrieving with Scores

```
GET /retrieve/search?query=your%20query&limit=5
```

Response includes `confidence_score` for each chunk.

### For Developers

#### Using ConfidenceScorer Directly

```python
from confidence_scorer import ConfidenceScorer
from embedding.embedder import get_embedding_model
from vector_db.client import get_qdrant_client

# Initialize
scorer = ConfidenceScorer(
    embedding_model=get_embedding_model(),
    qdrant_client=get_qdrant_client(),
    collection_name="documents"
)

# Calculate scores
scores = scorer.calculate_confidence_score(
    text_content="Your content here",
    source_type="verified_tutorial",
    created_at=datetime.utcnow(),
)

print(f"Confidence: {scores['confidence_score']:.2f}")
print(f"Breakdown:")
print(f"  - Source: {scores['source_reliability']:.2f}")
print(f"  - Content: {scores['content_quality']:.2f}")
print(f"  - Consensus: {scores['consensus_score']:.2f}")
print(f"  - Recency: {scores['recency']:.2f}")
```

#### Accessing Scores from API Response

```python
import requests

response = requests.get("http://localhost:8000/ingest/documents/1")
doc = response.json()

print(f"Document confidence: {doc['confidence_score']:.2f}")
print(f"Source reliability: {doc['source_reliability']:.2f}")

for chunk in doc['chunks']:
    print(f"Chunk {chunk['index']}: {chunk['confidence_score']:.2f}")
```

#### Querying by Confidence Score

```python
from models.database_models import Document
from database.session import SessionLocal

db = SessionLocal()

# High confidence (reliable) documents
reliable = db.query(Document).filter(
    Document.confidence_score >= 0.7
).all()

# Low confidence (questionable) documents
questionable = db.query(Document).filter(
    Document.confidence_score < 0.5
).all()

# Sort by confidence
sorted_docs = db.query(Document).order_by(
    Document.confidence_score.desc()
).all()
```

## 📊 Scoring Breakdown

### Formula

```
confidence_score = (
    source_reliability * 0.35 +
    content_quality * 0.25 +
    consensus_score * 0.25 +
    recency * 0.10
)
```

### Typical Scores

| Scenario                            | Typical Range | Example |
| ----------------------------------- | ------------- | ------- |
| Official docs, well-written, recent | 0.80-0.95     | 0.90    |
| Academic paper, structured, cited   | 0.75-0.90     | 0.82    |
| Tutorial, code samples, recent      | 0.70-0.85     | 0.78    |
| Blog post, decent structure         | 0.60-0.75     | 0.68    |
| User-generated, minimal structure   | 0.40-0.60     | 0.50    |
| Unverified, contradictory           | 0.20-0.40     | 0.32    |

### What Improves Content Quality Score

- ✅ Length > 1000 characters (+0.2)
- ✅ Organized structure (headers, lists) (+0.1)
- ✅ Code examples, technical content (+0.1)
- ✅ Citations and references (+0.1)

### What Improves Consensus Score

- ✅ Similarity with existing knowledge
- ✅ Multiple matching chunks (higher average)
- ✅ Content aligns with domain knowledge

### What Improves Recency Score

- ✅ Created within 3 months (1.0)
- ✅ Created within 1 year (0.7)
- ✅ Less than 3 years old (0.4)

## 🗄️ Database

### New Columns in `documents` Table

```sql
- confidence_score (FLOAT)           -- Final confidence (0.0-1.0)
- source_reliability (FLOAT)         -- Source type component
- content_quality (FLOAT)            -- Content analysis component
- consensus_score (FLOAT)            -- Similarity with existing
- recency_score (FLOAT)              -- Time-based component
- confidence_metadata (TEXT)         -- JSON details
```

### New Columns in `document_chunks` Table

```sql
- confidence_score (FLOAT)           -- Chunk confidence (0.0-1.0)
- consensus_similarity_scores (TEXT) -- JSON array of similarity values
```

### Removed Column

```sql
- trust_score (FLOAT)  -- Replaced with auto-calculated confidence_score
```

## 🔄 Migration

### Run Migration

```bash
python -m backend.database.migrate_add_confidence_scoring
```

### What It Does

1. Adds all new confidence_score columns
2. Sets default value of 0.5 for existing rows
3. Removes old trust_score column
4. Creates appropriate indexes
5. Handles potential column existence gracefully

## 🛠️ API Changes

### Before

```json
POST /ingest/text
{
  "text": "...",
  "filename": "...",
  "trust_score": 0.75  ❌ REMOVED
}
```

### After

```json
POST /ingest/text
{
  "text": "...",
  "filename": "...",
  "source_type": "verified_tutorial"  ✅ NEW
}
```

### Response Changes

**GET /ingest/documents/{id}**

```json
{
  "confidence_score": 0.78, // ✅ NEW
  "source_reliability": 0.85, // ✅ NEW
  "content_quality": 0.68, // ✅ NEW
  "consensus_score": 0.72, // ✅ NEW
  "recency_score": 0.95 // ✅ NEW
  // ... other fields ...
}
```

**POST /retrieve/search**

```json
{
  "results": [
    {
      "confidence_score": 0.78, // ✅ NEW
      "chunk_id": 1,
      "text": "...",
      "score": 0.92,
      "metadata": {
        "confidence_score": 0.78, // ✅ NEW
        "document_confidence_score": 0.78 // ✅ NEW
      }
    }
  ]
}
```

## 🔍 Validation

### Check Implementation

```python
# Test that scores are calculated
from models.database_models import Document
from database.session import SessionLocal

db = SessionLocal()
doc = db.query(Document).first()

assert doc.confidence_score is not None
assert 0.0 <= doc.confidence_score <= 1.0
assert doc.source_reliability is not None
assert doc.content_quality is not None
assert doc.consensus_score is not None
assert doc.recency_score is not None

print("✅ Confidence scoring is active!")
```

### Test Score Calculation

```python
from confidence_scorer import ConfidenceScorer
from embedding.embedder import get_embedding_model

scorer = ConfidenceScorer(embedding_model=get_embedding_model())

# Test each source type
sources = ["official_docs", "academic_paper", "verified_tutorial",
           "trusted_blog", "community_qa", "user_generated", "unverified"]

for source in sources:
    score = scorer.calculate_source_reliability(source)
    print(f"{source:20} → {score:.2f}")
```

## 💡 Common Patterns

### Get Top Quality Documents

```python
from models.database_models import Document
from database.session import SessionLocal
from sqlalchemy import desc

db = SessionLocal()
top_quality = db.query(Document).filter(
    Document.status == "completed"
).order_by(desc(Document.confidence_score)).limit(10).all()
```

### Filter by Source Type Reliability

```python
# Get documents from official sources
reliable_sources = db.query(Document).filter(
    Document.source_reliability >= 0.85
).all()
```

### Analyze Consensus Patterns

```python
# Documents with high consensus (agree with existing knowledge)
consensus_high = db.query(Document).filter(
    Document.consensus_score >= 0.75
).count()

# Documents with low consensus (novel information)
consensus_low = db.query(Document).filter(
    Document.consensus_score < 0.5
).count()
```

## ⚡ Performance Tips

1. **Use Indexed Queries**: confidence_score is indexed

   ```python
   db.query(Document).filter(Document.confidence_score >= 0.7)  # Fast!
   ```

2. **Calculation Happens at Ingest Time**: Not on retrieval

   - No performance impact on search queries
   - Slight overhead on document ingestion

3. **Cache Scores**: Scores don't change after ingestion
   - Safe to cache confidence_score values
   - Only changes if document is re-ingested

## 🚨 Troubleshooting

| Problem                    | Solution                                                         |
| -------------------------- | ---------------------------------------------------------------- |
| All scores are 0.5         | Run migration, check embedding model                             |
| API error on ingest        | Check logs for embedding model errors                            |
| Missing confidence columns | Run: `python -m backend.database.migrate_add_confidence_scoring` |
| Consensus always low       | Normal for novel content, vector DB may be empty                 |
| Wrong source score         | Check source_type spelling, defaults to user_generated           |

## 📚 Related Documentation

- Full details: `CONFIDENCE_SCORING_SYSTEM.md`
- Implementation: `CONFIDENCE_SCORING_IMPLEMENTATION.md`
- Source code: `backend/confidence_scorer/confidence_scorer.py`
