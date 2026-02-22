# Knowledge Base Organizer

**File:** `librarian/knowledge_organizer.py`

## Purpose

Auto-organizes knowledge base into 18 domain folders

## Overview

Knowledge Base Organizer

Auto-organizes the knowledge base into domain folders.
The librarian categorizes every ingested document and places it
into the correct domain directory.

Structure:
  knowledge_base/
    algorithms/
      Algorithm_Design_With_Haskell.pdf
      Intro_Algorithms_Data_Structures.txt
    architecture/
      Software_Architecture_in_Practice.txt
      Patterns_for_API_Design.pdf
    security/
      OWASP_Cheat_Sheets.md
      Cyber_Security_SOAR.txt
    ...

Each domain folder has a _manifest.json with:
- Document list with Genesis keys
- Trust scores per document
- Total coverage score
- Last updated timestamp

The frontend can browse this like a file manager and upload
documents directly to specific domain folders.

## Classes

- `KnowledgeOrganizer`

## Key Methods

- `classify_document()`
- `organize_file()`
- `organize_all()`
- `get_domain_structure()`
- `get_coverage_report()`
- `get_knowledge_organizer()`

## Database Tables

None (no DB tables)

## Dataclasses

None

## Connects To

Self-contained

## How It Works

This module is part of Grace 3.1's autonomous intelligence system.
See the source code docstring and inline comments for detailed logic.

---
*Auto-generated documentation for Grace 3.1 rocketdev branch*
