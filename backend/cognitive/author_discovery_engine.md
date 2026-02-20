# Author Discovery Engine

**File:** `cognitive/author_discovery_engine.py`

## Purpose

Discovers more works by highest-trust authors

## Overview

Author Discovery Engine

Takes the highest-trust books in the knowledge base and automatically
discovers more works by those authors + related authors.

The logic:
1. Rank all ingested books by trust score
2. Extract author names from the top-trust books
3. Search GitHub, Google Scholar, and web for more works by those authors
4. Discover co-authors, cited works, and recommended reads
5. Generate acquisition recommendations ranked by predicted trust
6. Feed recommendations to the Oracle for tracking

This creates a virtuous cycle:
  High-trust book → Author identified → More works found →
  Ingested → KNN expands → New connections discovered → Repeat

Authors in our highest-trust books:
- Richard Bird & Jeremy Gibbons (Cambridge) — Algorithm Design
- Andrew Hunt & David Thomas — Pragmatic Programmer
- Bass, Clements & Kazman (CMU SEI) — Software Architecture
- Martin Fowler — Refactoring
- Scott Chacon — Pro Git

## Classes

- `AuthorProfile`
- `AcquisitionRecommendation`
- `AuthorDiscoveryEngine`

## Key Methods

- `get_top_authors()`
- `get_missing_works()`
- `generate_search_queries()`
- `search_for_author()`
- `get_report()`
- `get_author_discovery_engine()`

## Database Tables

None (no DB tables)

## Dataclasses

- `AuthorProfile`
- `AcquisitionRecommendation`

## Connects To

- `cognitive.learning_hook`

## How It Works

This module is part of Grace 3.1's autonomous intelligence system.
See the source code docstring and inline comments for detailed logic.

---
*Auto-generated documentation for Grace 3.1 rocketdev branch*
