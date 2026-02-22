# Relationship Manager

**File:** `librarian/relationship_manager.py`

## Overview

RelationshipManager - Document Relationship Detection and Management

Automatically detects and manages relationships between documents including:
- Similarity-based relationships (related content)
- Version relationships (v1, v2, draft, final)
- Citation relationships (references)
- Duplicate detection

Builds a knowledge graph of document relationships.

## Classes

- `RelationshipManager`

## Key Methods

- `detect_relationships()`
- `create_relationship()`
- `save_detected_relationships()`
- `get_document_relationships()`
- `get_dependency_graph()`
- `delete_relationship()`

---
*Grace 3.1*
