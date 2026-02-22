# Notion

**File:** `api/notion.py`

## Overview

Notion Task Management API endpoints.

Provides comprehensive task management with:
- Kanban board columns (Todo, In Progress, In Review, Completed)
- Profile management with Genesis Key generation
- Full task history and versioning
- File/folder association for provenance

## Classes

- `ProfileCreateRequest`
- `ProfileUpdateRequest`
- `ProfileResponse`
- `ProfileListResponse`
- `SubtaskModel`
- `TaskCreateRequest`
- `TaskUpdateRequest`
- `TaskResponse`
- `TaskListResponse`
- `TaskHistoryResponse`
- `KanbanBoardResponse`

## Key Methods

- `get_db_session()`
- `task_to_response()`
- `profile_to_response()`
- `record_task_history()`

---
*Grace 3.1*
