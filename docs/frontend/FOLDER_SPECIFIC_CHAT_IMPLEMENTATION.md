# Folder-Specific Chat Implementation

## Overview

This implementation adds folder-specific chat history to the Grace application. Each chat is now associated with a folder path, ensuring that chats from one folder cannot interfere with chats from another folder. This allows users to maintain separate conversations for different document folders.

## Changes Made

### 1. Backend Database Model Updates

**File:** `backend/models/database_models.py`

- Added `folder_path` column to the `Chat` model
  - Type: `String(512)`, nullable with default empty string
  - Indexed for efficient queries
  - Stores the folder path associated with each chat session

```python
folder_path = Column(String(512), nullable=True, default="", index=True)
```

### 2. Backend API Endpoint Updates

**File:** `backend/app.py`

#### a. Model Updates

- Updated `ChatCreateRequest` to include optional `folder_path` field
- Updated `ChatResponse` to include `folder_path` in responses

#### b. Endpoint Changes

**POST /chats** - Create Chat

- Now accepts `folder_path` in request body
- Creates chats with folder context
- If no folder specified, defaults to empty string

**GET /chats** - List Chats

- Added `folder_path` query parameter for filtering
- Returns only chats matching the specified folder
- Backward compatible (no filter = all chats)

**GET /chats/{chat_id}** - Get Chat Details

- Returns `folder_path` in response

**PUT /chats/{chat_id}** - Update Chat

- Can now update `folder_path` if provided

### 3. Frontend ChatTab Component Updates

**File:** `frontend/src/components/ChatTab.jsx`

- Added state for `selectedFolder` to track the current folder context
- Updated `fetchChats()` to filter by selected folder
- Pass `folder_path` when creating new chats
- Refresh chat list when folder selection changes
- Pass `folderPath` prop to ChatWindow component

### 4. Frontend ChatList Component Updates

**File:** `frontend/src/components/ChatList.jsx`

**New Features:**

- Folder filter section with UI controls
- "Select Folder" button to set folder filter
- Display active folder filter with ability to clear
- Input field for entering folder path
- Show folder badge on each chat item

**UI Elements:**

- `.set-folder-btn` - Button to activate folder filter
- `.folder-filter-active` - Display active folder selection
- `.clear-filter-btn` - Clear folder filter
- `.folder-input-group` - Input controls for folder selection
- `.chat-folder-badge` - Badge showing folder path on each chat

**Functionality:**

- Users can type a folder path and apply it as a filter
- Only chats from the selected folder are displayed
- Clear button resets to showing all chats
- Chats display their associated folder in a badge

### 5. Frontend ChatWindow Component Updates

**File:** `frontend/src/components/ChatWindow.jsx`

- Added `folderPath` prop to track the folder context
- Updated chat header to display folder information
- New element: `chat-header-top` div with title and folder context
- Folder context badge displayed next to chat title

### 6. CSS Updates

**File:** `frontend/src/components/ChatList.css`

Added comprehensive styling for:

- Folder filter section (`.folder-filter-section`)
- Folder selection controls (`.set-folder-btn`, `.apply-folder-btn`, `.cancel-folder-btn`)
- Active folder display (`.folder-filter-active`, `.folder-icon`, `.folder-path`)
- Clear button styling (`.clear-filter-btn`)
- Folder input styling (`.folder-input`, `.folder-input-group`)
- Chat folder badges (`.chat-folder-badge`)
- Updated `.chat-item-content` to support multi-line display with folder info

**File:** `frontend/src/components/ChatWindow.css`

Updated for:

- `.chat-header` - Now uses flex-direction: column with gap
- `.chat-header-top` - New container for title and folder badge
- `.folder-context-badge` - Styling for folder path display with ellipsis support

### 7. Database Migration Script

**File:** `backend/migrate_add_folder_path.py`

Migration script that:

- Checks if `folder_path` column exists
- Adds column if missing
- Creates index on `folder_path` for efficient queries
- Supports PostgreSQL, MySQL, and SQLite
- Handles errors gracefully

## Usage

### For Users

1. **Setting a Folder Context:**

   - Click "📁 Select Folder" button in the Chat list
   - Enter a folder path (e.g., `/documents/projects/my-project`)
   - Click "Apply"

2. **Creating Chats in a Folder:**

   - Select a folder first
   - Click the "+" button to create a new chat
   - Chat is automatically associated with the selected folder

3. **Viewing Folder-Specific Chats:**

   - Selected folder shows in highlighted blue badge
   - Only chats from that folder are displayed
   - Folder path shown on each chat

4. **Switching Folders:**

   - Click the folder filter to change the selected folder
   - Chat list updates to show chats from the new folder

5. **Clearing Filter:**
   - Click the "✕" button on active folder filter
   - Shows all chats again

### For Developers

**Running Migration:**

```bash
cd backend
python migrate_add_folder_path.py
```

**API Examples:**

Create chat in folder:

```bash
curl -X POST http://localhost:8000/chats \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Project Chat",
    "folder_path": "/documents/projects/my-project"
  }'
```

List chats for folder:

```bash
curl "http://localhost:8000/chats?folder_path=%2Fdocuments%2Fprojects%2Fmy-project"
```

List all chats:

```bash
curl "http://localhost:8000/chats"
```

## Data Isolation

- **Storage:** Each chat stores its `folder_path` in the database
- **Retrieval:** Queries filter by `folder_path` when specified
- **Display:** Frontend shows folder context in UI
- **Creation:** New chats automatically get the current folder context
- **Isolation:** Messages are stored per chat, automatically isolated by folder context

## Benefits

1. **Organization:** Keep conversations organized by document folder
2. **Context:** Clear visual indication of which folder a chat belongs to
3. **Isolation:** Prevent accidental mixing of conversations across folders
4. **Flexibility:** Users can easily switch between folder contexts
5. **Filtering:** Quick filtering to see chats for specific folders
6. **Backward Compatibility:** Existing chats without folder context still work

## Database Schema

```sql
ALTER TABLE chats ADD COLUMN folder_path VARCHAR(512) DEFAULT '';
CREATE INDEX idx_folder_path ON chats(folder_path);
```

## Files Modified

1. `backend/models/database_models.py` - Added folder_path column
2. `backend/app.py` - Updated endpoints and models
3. `frontend/src/components/ChatTab.jsx` - Added folder state management
4. `frontend/src/components/ChatList.jsx` - Added folder UI controls
5. `frontend/src/components/ChatWindow.jsx` - Show folder context
6. `frontend/src/components/ChatList.css` - Folder filter styling
7. `frontend/src/components/ChatWindow.css` - Folder badge styling
8. `backend/migrate_add_folder_path.py` - New migration script

## Testing

1. Start the backend service
2. Run migration: `python migrate_add_folder_path.py`
3. Create chats with different folder paths
4. Use folder filter to verify isolation
5. Verify folder badge displays correctly
6. Test switching between folders
7. Verify chats only appear in their assigned folder
