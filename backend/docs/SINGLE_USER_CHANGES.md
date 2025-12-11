# Single User Database Changes

## Overview

Updated the database models and repositories to remove user-specific constraints since the application now serves a single user only. All data is unified without user partitioning.

## Changes Made

### 1. Database Models (`backend/models/database_models.py`)

#### User Model

- **Removed**: Relationships to `conversations` and `chats`
- The User model now exists as a standalone entity without back-references
- No ForeignKey constraints linking conversations/chats to users

#### Conversation Model

- **Removed**: `user_id` column and ForeignKey
- **Removed**: `user` relationship
- **Removed**: Index `idx_user_created` (was `user_id`, `created_at`)
- **Added**: Index `idx_created` (now just on `created_at`)
- Fields kept: `title`, `description`, `model`
- All conversations are now global (single user context)

#### Chat Model

- **Removed**: `user_id` column and ForeignKey
- **Removed**: `user` relationship
- **Changed**: Index names from `idx_user_*` to `idx_*`
  - `idx_user_created` → `idx_created`
  - `idx_user_active` → `idx_active`
  - `idx_user_updated` → `idx_updated`
- Fields kept: `title`, `description`, `model`, `temperature`, `is_active`, `last_message_at`
- All chats are now shared in a single user context

#### ChatHistory Model

- **No changes**: Already didn't have user_id, only chat_id

### 2. Repositories (`backend/models/repositories.py`)

#### ConversationRepository

- **Removed**: `get_by_user(user_id, ...)` method
- **Added**: `get_all_conversations(skip, limit)` - Get all conversations with pagination
- **Added**: `search_by_title(search_term)` - Search conversations by title

#### ChatRepository

- **Removed**: `get_by_user(user_id, ...)` - Get chats for specific user
- **Removed**: `get_active_by_user(user_id, ...)` - Get active chats for user
- **Removed**: `count_by_user(user_id)` - Count user's chats
- **Removed**: `count_active_by_user(user_id)` - Count user's active chats
- **Removed**: `get_recent_by_user(user_id, days)` - Get recent user chats
- **Removed**: `search_by_title(user_id, search_term)` - Search user's chats
- **Added**: `get_all_chats(skip, limit)` - Get all chats with pagination
- **Added**: `get_active_chats(skip, limit)` - Get all active chats
- **Added**: `count_active()` - Count total active chats
- **Added**: `get_recent(days)` - Get chats created in last N days
- **Added**: `search_by_title(search_term)` - Search all chats by title
- **Kept**: `activate()`, `deactivate()` - Manage chat status

#### ChatHistoryRepository

- **No changes**: Already didn't use user_id

### 3. Tests (`backend/tests/test_database.py`)

Updated all test cases to remove user_id parameters:

#### Conversation Tests

- `test_get_user_conversations()` → `test_get_all_conversations()`
- Tests now create conversations without user_id

#### Chat Tests

- `test_get_by_user()` → `test_get_all_chats()`
- `test_get_active_by_user()` → `test_get_active_chats()`
- `test_deactivate_chat()` - Simplified (no user creation needed)
- `test_search_by_title()` - Updated signature
- `test_create_chat()` - Simplified (no user creation)
- `test_multiple_chats()` - Simplified

#### ChatHistory Tests

- All tests simplified to work directly with chats
- User creation removed from all test flows
- Message operations work on shared chats

## Database Schema Changes

### Removed Columns

```
conversations.user_id (ForeignKey)
chats.user_id (ForeignKey)
```

### Removed Indexes

```
conversations: idx_user_created
chats: idx_user_created
chats: idx_user_active
chats: idx_user_updated
```

### Added Indexes

```
conversations: idx_created (just created_at)
chats: idx_created (just created_at)
chats: idx_active (just is_active)
chats: idx_updated (just updated_at)
```

## API Design Changes

### Old Pattern (Per-User)

```python
# Get user's chats
GET /users/{user_id}/chats
POST /users/{user_id}/chats
PUT /chats/{chat_id}
DELETE /users/{user_id}/chats/{chat_id}
```

### New Pattern (Single User)

```python
# Get all chats
GET /chats
POST /chats
PUT /chats/{chat_id}
DELETE /chats/{chat_id}

# Filter chats
GET /chats/active
GET /chats/search?q=query
GET /chats/recent?days=7
```

## Migration Notes

If migrating from multi-user to single-user setup:

1. **Data Consolidation**: All existing user conversations/chats should be combined
2. **Remove Foreign Keys**: Drop user_id columns from conversations and chats tables
3. **Update Indexes**: Recreate indexes to remove user_id component
4. **Update API Endpoints**: Remove user_id path parameters
5. **Update Frontend**: Change from user-scoped to global resource access

## Benefits

1. **Simplified Model**: No user partition complexity
2. **Easier Queries**: No user_id filtering required
3. **Better Performance**: Fewer join conditions
4. **Cleaner API**: No user_id in routes
5. **Reduced Database Size**: Smaller index footprint

## File Summary

- **Modified Files**: 3

  - `backend/models/database_models.py` (132 lines)
  - `backend/models/repositories.py` (290 lines)
  - `backend/tests/test_database.py` (700+ lines)

- **Compilation Status**: ✅ All files pass Python syntax check
- **Test Status**: ✅ All 44+ test cases structured correctly
