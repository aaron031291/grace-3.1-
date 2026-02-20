# Genesis Key Curator

**File:** `librarian/genesis_key_curator.py`

## Overview

Librarian Genesis Key Curator.

The Librarian automatically organizes Genesis Keys every 24 hours.
Runs as a background task and creates daily summaries.

## Classes

- `GenesisKeyCurator`

## Key Methods

- `curate_today()`
- `curate_yesterday()`
- `backfill_missing_days()`
- `schedule_daily_curation()`
- `stop_scheduler()`
- `get_curation_status()`
- `get_genesis_key_curator()`
- `start_daily_curation()`
- `stop_daily_curation()`

---
*Grace 3.1*
