# Training Data Source Registry

**File:** `cognitive/training_data_sources.py`

## Purpose

Registry of 46 external data sources for knowledge acquisition

## Overview

Training Data Source Registry

Defines all external data sources Grace can learn from.
The Oracle and training pipeline use this to discover, fetch,
and ingest knowledge from GitHub repos, APIs, and websites.

Each source has:
- URL and access method (git clone, API, scrape)
- Trust score (how reliable the source is)
- Category (what domain it covers)
- Priority (what order to ingest)
- Auto-refresh interval (how often to re-check)

## Classes

- `SourceType`
- `SourceCategory`
- `DataSource`
- `TrainingDataSourceRegistry`

## Key Methods

- `get_by_priority()`
- `get_by_category()`
- `get_by_type()`
- `get_github_repos()`
- `get_apis()`
- `get_websites()`
- `get_unfetched()`
- `get_stale()`
- `mark_fetched()`
- `get_stats()`
- `to_dict()`
- `get_training_source_registry()`

## Database Tables

None (no DB tables)

## Dataclasses

- `DataSource`

## Connects To

Self-contained

## How It Works

This module is part of Grace 3.1's autonomous intelligence system.
See the source code docstring and inline comments for detailed logic.

---
*Auto-generated documentation for Grace 3.1 rocketdev branch*
