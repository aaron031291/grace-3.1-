# Migrate Add Librarian

**File:** `database/migrate_add_librarian.py`

## Overview

Migration script to add Librarian System tables to Grace.

This migration adds 6 new tables for the Librarian System:
- librarian_tags: Tag definitions
- document_tags: Document-tag relationships
- document_relationships: Document relationship graph
- librarian_rules: Pattern matching rules
- librarian_actions: Approval workflow queue
- librarian_audit: Complete audit trail

Run this script to enable automatic file organization and categorization.

## Classes

None

## Key Methods

- `migrate()`

---
*Grace 3.1*
