# Grace Librarian System - Setup & Usage Guide

## Overview

The Grace Librarian System provides automatic file management for your knowledge base with:
- **Hybrid Categorization**: Rule-based patterns + AI content analysis
- **Flat Tag System**: Multiple tags per document with confidence scores
- **Relationship Detection**: Automatic discovery of similar/related/version documents
- **Tiered Permissions**: Auto-execution for safe actions, approval queue for sensitive operations
- **Complete Audit Trail**: All actions logged with rollback capability

## Quick Start

### 1. Verify Installation

Run the test script to verify all components are working:

```bash
cd backend
python test_librarian_integration.py
```

You should see:
```
[OK] ALL TESTS PASSED - Librarian system is working!
```

### 2. Check Database Tables

The following tables should exist:
- `librarian_tags` - Tag definitions
- `document_tags` - Document-tag assignments
- `document_relationships` - Document relationships
- `librarian_rules` - Categorization rules
- `librarian_actions` - Approval workflow queue
- `librarian_audit` - Complete audit trail

### 3. Verify Default Rules

40 default rules are seeded automatically:
- 22 extension-based rules (PDF, Python, JavaScript, etc.)
- 8 path-based rules (AI Research, Systems Thinking, etc.)
- 10 filename-based rules (README, LICENSE, test files, etc.)

Check with:
```python
from database.session import initialize_session_factory
from librarian.rule_categorizer import RuleBasedCategorizer

SessionLocal = initialize_session_factory()
db = SessionLocal()
categorizer = RuleBasedCategorizer(db)
stats = categorizer.get_rule_statistics()
print(f"Total rules: {stats['total_rules']}")
```

### 4. Configuration

All settings are in [backend/settings.py](backend/settings.py):

```python
# Librarian Configuration (defaults shown)
LIBRARIAN_AUTO_PROCESS = True              # Auto-process uploads
LIBRARIAN_USE_AI = True                    # Enable AI analysis
LIBRARIAN_DETECT_RELATIONSHIPS = True      # Enable relationship detection
LIBRARIAN_AI_CONFIDENCE_THRESHOLD = 0.6    # Min confidence for AI tags
LIBRARIAN_SIMILARITY_THRESHOLD = 0.7       # Min similarity for relationships
LIBRARIAN_MAX_RELATIONSHIP_CANDIDATES = 20 # Max candidates to check
LIBRARIAN_AI_MODEL = "mistral:7b"          # LLM model for AI analysis
```

You can override these in [backend/.env](backend/.env):

```bash
LIBRARIAN_AUTO_PROCESS=true
LIBRARIAN_USE_AI=true
LIBRARIAN_DETECT_RELATIONSHIPS=true
LIBRARIAN_AI_CONFIDENCE_THRESHOLD=0.6
LIBRARIAN_SIMILARITY_THRESHOLD=0.7
LIBRARIAN_AI_MODEL=mistral:7b
```

## How It Works

### Automatic Processing Pipeline

When you upload a file, the librarian automatically:

1. **Rule-Based Categorization**
   - Matches file against 40+ pattern rules
   - Assigns tags based on extension, filename, path, MIME type
   - High confidence (0.95) for rule-based tags

2. **AI Content Analysis** (if enabled and needed)
   - Analyzes document content using LLM
   - Suggests category, tags, topics
   - Only runs if: no rules matched OR fewer than 3 tags assigned
   - Confidence threshold: 0.6 (configurable)

3. **Tag Assignment**
   - Combines rule-based + AI tags
   - Removes duplicates
   - Tracks confidence and source (rule/ai/user)

4. **Relationship Detection** (if enabled)
   - Embedding similarity (threshold: 0.7)
   - Version pattern detection (v1, v2, draft, final)
   - Citation detection (filename appears in content)
   - Duplicate detection (similarity > 0.95)

5. **Auto-Execution**
   - Safe actions (tags, metadata, indexing) execute immediately
   - Sensitive actions (folder creation, deletion) go to approval queue

### Example: Upload a PDF

```python
# Upload a PDF file
POST /files/upload
{
  "file": research_paper.pdf,
  "folder_path": "research/ai",
  "ingest": "true"
}

# Librarian automatically processes:
# 1. Rules matched: "PDF Documents", "AI Research Folder"
# 2. Tags assigned: "pdf", "document", "AI", "research"
# 3. AI analysis (if needed): adds "machine-learning", "neural-networks"
# 4. Relationships: finds 3 similar documents
# 5. All actions auto-executed (safe operations)
```

## Usage Examples

### Tag Management

```python
from database.session import initialize_session_factory
from librarian.tag_manager import TagManager

SessionLocal = initialize_session_factory()
db = SessionLocal()
tag_manager = TagManager(db)

# Create a tag
tag = tag_manager.get_or_create_tag(
    name="important",
    description="High-priority documents",
    category="priority",
    color="#FF0000"
)

# Assign tags to a document
tag_manager.assign_tags(
    document_id=123,
    tag_names=["important", "urgent"],
    assigned_by="user",
    confidence=1.0
)

# Search documents by tags
results = tag_manager.search_documents_by_tags(
    tag_names=["important", "AI"],
    match_all=False,  # OR search
    limit=50
)

# Get tag statistics
stats = tag_manager.get_tag_statistics()
print(f"Total tags: {stats['total_tags']}")
print(f"Most used: {stats['most_used']}")
```

### Rule Management

```python
from librarian.rule_categorizer import RuleBasedCategorizer

categorizer = RuleBasedCategorizer(db)

# Create a custom rule
rule = categorizer.create_rule(
    name="Machine Learning Papers",
    pattern_type="content",
    pattern_value=r"(neural network|deep learning|transformer)",
    action_type="assign_tag",
    action_params={"tag_names": ["ml", "deep-learning"]},
    priority=10
)

# Test rule against existing documents
matches = categorizer.test_rule_against_documents(rule.id, limit=100)
print(f"Rule would match {len(matches)} documents")

# Get rule statistics
stats = categorizer.get_rule_statistics()
print(f"Total rules: {stats['total_rules']}")
print(f"Most effective: {stats['most_effective']}")
```

### AI Analysis

```python
from librarian.ai_analyzer import AIContentAnalyzer
from ollama_client.client import get_ollama_client

analyzer = AIContentAnalyzer(db, get_ollama_client())

# Analyze a document
result = analyzer.analyze_document(document_id=123)
print(f"Category: {result['category']}")
print(f"Tags: {result['tags']}")
print(f"Topics: {result['topics']}")
print(f"Confidence: {result['confidence']}")

# Suggest tags for a query
tags = analyzer.suggest_tags_for_query(
    "Paper about neural networks and transformers",
    max_tags=5
)
print(f"Suggested tags: {tags}")

# Compare two documents
comparison = analyzer.compare_documents(doc_id_1=123, doc_id_2=456)
print(f"Similarity: {comparison['similarity_score']}")
print(f"Relationship: {comparison['relationship_type']}")
```

### Relationship Management

```python
from librarian.relationship_manager import RelationshipManager
from embedding.embedder import get_embedding_model
from vector_db.client import get_qdrant_client

rel_manager = RelationshipManager(
    db,
    get_embedding_model(),
    get_qdrant_client()
)

# Detect relationships for a document
relationships = rel_manager.detect_relationships(
    document_id=123,
    max_candidates=20,
    similarity_threshold=0.7
)
print(f"Found {len(relationships)} relationships")

# Get document relationships
rels = rel_manager.get_document_relationships(document_id=123)
print(f"Outgoing: {len(rels['outgoing'])}")
print(f"Incoming: {len(rels['incoming'])}")

# Get dependency graph
graph = rel_manager.get_dependency_graph(
    document_id=123,
    max_depth=3
)
print(f"Graph has {len(graph['nodes'])} nodes, {len(graph['edges'])} edges")
```

### Complete Pipeline

```python
from librarian.engine import LibrarianEngine
from embedding.embedder import get_embedding_model
from ollama_client.client import get_ollama_client
from vector_db.client import get_qdrant_client
from settings import settings

# Create librarian engine
librarian = LibrarianEngine(
    db_session=db,
    embedding_model=get_embedding_model(),
    ollama_client=get_ollama_client(),
    vector_db_client=get_qdrant_client(),
    ai_model_name=settings.LIBRARIAN_AI_MODEL,
    use_ai=settings.LIBRARIAN_USE_AI,
    detect_relationships=settings.LIBRARIAN_DETECT_RELATIONSHIPS,
    ai_confidence_threshold=settings.LIBRARIAN_AI_CONFIDENCE_THRESHOLD,
    similarity_threshold=settings.LIBRARIAN_SIMILARITY_THRESHOLD
)

# Process a single document
result = librarian.process_document(document_id=123)
print(f"Status: {result['status']}")
print(f"Tags assigned: {result['tags_assigned']}")
print(f"Relationships: {result['relationships_detected']}")
print(f"Rules matched: {result['rules_matched']}")

# Process batch
results = librarian.process_batch(document_ids=[1, 2, 3, 4, 5])
successful = [r for r in results if r['status'] == 'success']
print(f"Processed {len(successful)}/{len(results)} documents")

# Reprocess all documents (useful after adding new rules)
summary = librarian.reprocess_all_documents(
    use_ai=False,  # Rules only (fast)
    detect_relationships=True,
    batch_size=10,
    limit=100  # Limit to 100 documents
)
print(f"Processed: {summary['documents_processed']}")
print(f"Tags assigned: {summary['total_tags_assigned']}")
print(f"Relationships: {summary['total_relationships_detected']}")

# Get system statistics
stats = librarian.get_system_statistics()
print(f"Total tags: {stats['tags']['total_tags']}")
print(f"Active rules: {stats['rules']['total_rules']}")
print(f"AI available: {stats['ai_available']}")

# Health check
health = librarian.health_check()
print(f"Overall status: {health['overall_status']}")
```

## Approval Workflow

### Permission Tiers

**Auto-Executed (permission_tier = "auto"):**
- assign_tag
- update_metadata
- reindex
- detect_relationship
- calculate_confidence
- extract_content

**Requires Approval (permission_tier = "approval_required"):**
- create_folder
- delete_file
- move_file
- rename_file
- delete_folder
- modify_system_file

### Working with Approval Queue

```python
from librarian.approval_workflow import ApprovalWorkflow

workflow = ApprovalWorkflow(db)

# Get pending actions
pending = workflow.get_pending_actions(permission_tier="approval_required")
print(f"{len(pending)} actions awaiting approval")

for action in pending:
    print(f"Action {action.id}: {action.action_type}")
    print(f"  Document: {action.document_id}")
    print(f"  Reason: {action.reason}")
    print(f"  Confidence: {action.confidence}")

# Approve an action
workflow.approve_action(
    action_id=5,
    reviewed_by="user@example.com",
    notes="Looks good, proceed"
)

# Reject an action
workflow.reject_action(
    action_id=6,
    reviewed_by="user@example.com",
    reason="Incorrect categorization"
)

# Batch approve
workflow.batch_approve(
    action_ids=[7, 8, 9],
    reviewed_by="admin@example.com"
)

# Auto-approve high-confidence safe actions
count = workflow.auto_approve_safe_actions(min_confidence=0.9)
print(f"Auto-approved {count} high-confidence actions")

# Get statistics
stats = workflow.get_action_statistics()
print(f"Pending: {stats['by_status']['pending']}")
print(f"Approved: {stats['by_status']['approved']}")
print(f"Auto-tier: {stats['by_tier']['auto']}")
```

## Integration with File Upload

The librarian is automatically integrated with the file upload endpoint.

When you upload a file via `/files/upload` or `/files/upload-multiple` with `ingest=true`:

1. File is saved to knowledge_base
2. Text is extracted and ingested into vector database
3. **Librarian automatically processes the document** (async, non-blocking)
4. Processing happens in background - upload completes immediately

Check the logs to see librarian activity:

```bash
[LIBRARIAN] Starting automatic processing for document 123
[LIBRARIAN] ✓ Processed document 123: 5 tags, 3 relationships, rules matched: ['PDF Documents', 'AI Research Folder']
```

## Troubleshooting

### No AI Analysis Happening

Check if Ollama is running and model exists:

```python
from librarian.ai_analyzer import AIContentAnalyzer
from ollama_client.client import get_ollama_client

analyzer = AIContentAnalyzer(db, get_ollama_client())
print(f"AI available: {analyzer.is_available()}")

info = analyzer.get_model_info()
print(info)
```

If not available:
1. Start Ollama: `ollama serve`
2. Pull model: `ollama pull mistral:7b`
3. Check settings: `LIBRARIAN_AI_MODEL=mistral:7b`

### No Relationships Detected

Relationships require:
1. Embedding model loaded
2. Qdrant vector database running
3. Documents already ingested with embeddings

Check:
```python
from librarian.relationship_manager import RelationshipManager

rel_manager = RelationshipManager(db, get_embedding_model(), get_qdrant_client())

# Should not raise errors
try:
    rels = rel_manager.detect_relationships(document_id=123)
    print(f"Detected {len(rels)} relationships")
except Exception as e:
    print(f"Error: {e}")
```

### Rules Not Matching

Check rule patterns:

```python
from librarian.rule_categorizer import RuleBasedCategorizer

categorizer = RuleBasedCategorizer(db)

# Test specific document
matches = categorizer.categorize_document(document_id=123)
print(f"Matched {len(matches)} rules:")
for match in matches:
    print(f"  - {match['rule_name']}")
```

If no matches, rules may need adjustment or new rules created.

### Disable Features

Temporarily disable features via settings:

```python
# In .env file
LIBRARIAN_AUTO_PROCESS=false  # Disable automatic processing
LIBRARIAN_USE_AI=false        # Disable AI analysis
LIBRARIAN_DETECT_RELATIONSHIPS=false  # Disable relationship detection
```

Or per-request:

```python
result = librarian.process_document(
    document_id=123,
    use_ai=False,  # Override setting
    detect_relationships=False  # Override setting
)
```

## Advanced Features

### Custom Rule Types

Create rules for content patterns:

```python
# Content-based rule (requires text search)
rule = categorizer.create_rule(
    name="Security Papers",
    pattern_type="content",
    pattern_value=r"(security|cryptography|encryption)",
    action_type="assign_tag",
    action_params={"tag_names": ["security", "cryptography"]},
    priority=5
)
```

### Tag Categories

Organize tags by category:

```python
tag_manager.get_or_create_tag("critical", category="priority", color="#FF0000")
tag_manager.get_or_create_tag("high", category="priority", color="#FFA500")
tag_manager.get_or_create_tag("medium", category="priority", color="#FFFF00")
tag_manager.get_or_create_tag("low", category="priority", color="#00FF00")

# Get all priority tags
stats = tag_manager.get_tag_statistics()
priority_count = stats['by_category'].get('priority', 0)
print(f"Priority tags: {priority_count}")
```

### Relationship Types

Supported relationship types:
- `citation` - Source cites target
- `prerequisite` - Source requires target
- `related` - General relationship
- `version` - Version sequence
- `supersedes` - Replaces previous version
- `part_of` - Component relationship
- `duplicate` - High similarity

Create custom relationships:

```python
rel_manager.create_relationship(
    source_id=123,
    target_id=456,
    type="prerequisite",
    confidence=0.95,
    strength=0.8,
    metadata={"reason": "References concepts from target"}
)
```

### Audit Trail

All actions are logged:

```python
from models.librarian_models import LibrarianAudit

# Get audit log for a document
audit_entries = db.query(LibrarianAudit).filter(
    LibrarianAudit.document_id == 123
).order_by(LibrarianAudit.created_at.desc()).all()

for entry in audit_entries:
    print(f"{entry.created_at}: {entry.action_type}")
    print(f"  Status: {entry.status}")
    print(f"  Details: {entry.action_details}")
```

## Performance Tips

1. **Batch Processing**: Use `process_batch()` instead of individual calls
2. **Disable AI for Bulk**: Set `use_ai=False` when reprocessing large document sets
3. **Adjust Thresholds**: Lower similarity threshold (0.6) to find more relationships
4. **Rule Priority**: Higher priority rules execute first, set strategically
5. **Cache Rules**: Rules are cached for 60s, frequent matches are fast

## Summary

The Grace Librarian System provides comprehensive, automatic file management:

- ✓ All librarian tables created
- ✓ 40 default rules seeded
- ✓ Tag management working
- ✓ Rule categorization ready
- ✓ AI analysis integrated
- ✓ Relationship detection ready
- ✓ Approval workflow functional
- ✓ Automatic processing on file upload
- ✓ Complete audit trail
- ✓ Test script verified

The system is ready to automatically organize, categorize, and index all files in your Grace knowledge base!
