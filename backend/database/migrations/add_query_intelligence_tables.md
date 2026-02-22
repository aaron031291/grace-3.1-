# Add Query Intelligence Tables

**File:** `database/migrations/add_query_intelligence_tables.py`

## Overview

Database migration: Add query intelligence tables.

Creates tables for tracking multi-tier query handling:
- query_handling_log: Tracks tier usage and confidence scores
- knowledge_gaps: Stores identified knowledge gaps
- context_submissions: Records user-provided context

---
*Grace 3.1*
