# Approval Workflow

**File:** `librarian/approval_workflow.py`

## Overview

ApprovalWorkflow - Permission Management and Approval Queue

Manages tiered permission system for librarian actions:
- Auto-commit: Safe actions (tagging, metadata, indexing)
- Approval required: Sensitive actions (folder creation, deletion, moves)

Provides approval queue for human review of pending actions.

## Classes

- `ApprovalWorkflow`

## Key Methods

- `create_action()`
- `get_permission_tier()`
- `get_pending_actions()`
- `approve_action()`
- `reject_action()`
- `auto_approve_safe_actions()`
- `get_action_statistics()`
- `batch_approve()`
- `batch_reject()`

---
*Grace 3.1*
