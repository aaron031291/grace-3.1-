# Documents Tab Chat History Implementation

## Overview

Added folder-specific chat history to the Documents tab (RAGTab). When users navigate between folders, the application automatically creates new chats and preserves previous chat history per folder.

## Features Implemented

### 1. **Folder-Specific Chat Management** (RAGTab.jsx)

- Tracks chat sessions for each folder using `folderChats` state (Map of folder_path → Chat object)
- Automatically creates a new chat when navigating to a folder that doesn't have a chat yet
- Retrieves existing chat when navigating to a folder that already has a chat
- Chat titles include folder path: `Documents Chat - {folder_path}`

### 2. **Chat History Persistence** (DirectoryChat.jsx)

- Loads chat history from database when chatId changes
- Saves user and assistant messages to the chat session using `/chats/{chatId}/messages` endpoint
- Messages are persisted across page reloads and folder navigations
- Loading state displayed while fetching chat history

### 3. **Layout Changes** (RAGTab.css)

- Changed Files tab layout from vertical to horizontal grid layout
- File browser on the left (1 fraction)
- Chat interface on the right (1.5 fractions)
- Proper spacing and styling for sidebar layout

### 4. **User Experience Improvements**

- Chat input is disabled until a chat is created for the folder
- Loading indicator shows "Creating chat for folder..." while initializing
- Messages include source information when available
- Error handling for missing documents or API failures

## Technical Implementation

### Modified Files

#### `/frontend/src/components/RAGTab.jsx`

**Changes:**

- Added `folderChats` state to track chats by folder path
- Added `selectedChatId` and `loadingChat` states
- Added `useEffect` hook to create/retrieve chat when `currentDirectory` changes
- Pass `chatId={selectedChatId}` to DirectoryChat component
- Show loading state while creating chat

**Key Logic:**

```javascript
// Check if chat exists for this folder
if (folderChats[currentDirectory]) {
  setSelectedChatId(folderChats[currentDirectory].id);
  return;
}

// Create new chat for this folder
const response = await fetch(`${API_BASE}/chats`, {
  method: "POST",
  body: JSON.stringify({
    title: `Documents Chat - ${currentDirectory || "Root"}`,
    folder_path: currentDirectory,
  }),
});
```

#### `/frontend/src/components/DirectoryChat.jsx`

**Changes:**

- Added `chatId` prop to accept chat session ID
- Added `loadingHistory` state for loading indicator
- Added `loadChatHistory()` function to fetch messages from `/chats/{chatId}/messages`
- Modified `handleSubmit()` to save messages to chat session via `/chats/{chatId}/messages`
- Added loading state UI while fetching history
- Disabled input when `chatId` is not available

**Key Logic:**

```javascript
// Load messages when chatId changes
useEffect(() => {
  if (chatId) {
    loadChatHistory();
  }
}, [chatId]);

// Save messages when submitting
await fetch(`${API_BASE}/chats/${chatId}/messages`, {
  method: "POST",
  body: JSON.stringify({
    role: "user",
    content: userMessage,
  }),
});
```

#### `/frontend/src/components/RAGTab.css`

**Changes:**

- Modified `.files-content` to use CSS Grid instead of flexbox
- Layout: `grid-template-columns: 1fr 1.5fr` (file browser on left, chat on right)
- Updated `.file-browser-section` and `.directory-chat-section` styling for horizontal layout
- Added `.loading-chat` class for loading state
- Proper spacing with `gap: 1px` and background colors

**Key Styles:**

```css
.files-content {
  display: grid;
  grid-template-columns: 1fr 1.5fr;
  gap: 1px;
  height: 100%;
  overflow: hidden;
  background-color: #e5e7eb;
}
```

## API Endpoints Used

### Create Chat

- **POST** `/chats`
- Creates a new chat session with folder_path
- Request: `{ title, description, folder_path }`
- Response: `{ id, title, folder_path, ... }`

### Get Chat History

- **GET** `/chats/{chat_id}/messages`
- Retrieves all messages for a chat session
- Response: `{ messages: [{id, role, content, ...}], total, ... }`

### Add Message to Chat

- **POST** `/chats/{chat_id}/messages`
- Saves a message to a chat session
- Request: `{ role, content }`
- Response: `{ id, chat_id, role, content, ... }`

## Behavior

### When User Navigates to a New Folder

1. RAGTab detects `currentDirectory` change
2. Checks if `folderChats[currentDirectory]` exists
3. If not, creates new chat via POST `/chats` with `folder_path: currentDirectory`
4. Stores chat in `folderChats` state
5. Sets `selectedChatId` to trigger DirectoryChat to load
6. DirectoryChat loads messages for this chat (empty for new chats)

### When User Switches Back to Previous Folder

1. RAGTab detects `currentDirectory` change
2. Finds existing chat in `folderChats[currentDirectory]`
3. Sets `selectedChatId` immediately
4. DirectoryChat loads all previous messages for this folder
5. User sees complete conversation history

### When User Sends a Message

1. Message is added to local state immediately
2. Message is saved to database via POST `/chats/{chatId}/messages`
3. Prompt is sent to `/chat/directory-prompt` with `directory_path: currentPath`
4. Assistant response is saved to database
5. All messages persist across navigations

## Testing Checklist

- [ ] Navigate between folders in Documents tab
- [ ] Verify chat history loads when returning to previous folder
- [ ] Send messages in different folders
- [ ] Verify messages persist across folder changes
- [ ] Check that chat history on left shows messages from current folder
- [ ] Verify new folders get new empty chats
- [ ] Test error handling (network errors, missing documents)
- [ ] Verify chat titles match folder paths
- [ ] Check that input is disabled until chat is created

## Browser Console

- No errors should appear when navigating between folders
- API requests should complete successfully
- Messages should save and load without issues

## Database Schema

The Chat model includes:

- `id`: Primary key
- `title`: Chat title
- `folder_path`: Path of folder this chat belongs to (String 512)
- `created_at`, `updated_at`: Timestamps
- Relationship to ChatHistory messages

The folder_path column enables folder-specific filtering and isolation.
