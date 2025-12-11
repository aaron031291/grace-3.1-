# Frontend & Backend Integration Guide

This document explains how the Grace frontend integrates with the backend API.

## Request/Response Flow

```
User Action (e.g., Send Message)
         ↓
Frontend React Component
         ↓
Fetch API Call (HTTP POST/GET)
         ↓
Backend FastAPI Endpoint
         ↓
Database Operations
         ↓
Ollama API Call (for chat)
         ↓
Response Back to Frontend
         ↓
UI Update (State, Re-render)
```

## API Communication

### Base URL

- **Development**: `http://localhost:8000`
- **Production**: Configure in environment variables

### Content-Type

All API calls use:

```
Content-Type: application/json
```

### Error Handling

Frontend checks HTTP status codes:

- **2xx**: Success
- **4xx**: Client error (show to user)
- **5xx**: Server error (show to user)

## Chat Management Flow

### Create Chat

```
POST /chats
├─ Request: { title, description, model, temperature }
├─ Backend: Creates new chat in database
└─ Response: { id, title, created_at, ... }
```

### Get Chat List

```
GET /chats?skip=0&limit=50
├─ Backend: Fetches chats from database
└─ Response: { chats: [...], total, skip, limit }
```

### Send Message & Get Response

```
POST /chats/{chat_id}/prompt
├─ Request: { content, temperature, top_p, top_k }
├─ Backend:
│   ├─ Save user message to database
│   ├─ Get chat history
│   ├─ Call Ollama API
│   ├─ Save assistant response to database
│   └─ Return response
└─ Response: { message, model, generation_time, ... }
```

## Frontend Component API Contracts

### ChatTab.jsx

**Props**: None
**State**:

- `chats`: Array of chat objects
- `selectedChatId`: Currently selected chat ID
- `loading`: Loading state

**Methods**:

- `fetchChats()`: GET /chats
- `createNewChat()`: POST /chats
- `deleteChat(id)`: DELETE /chats/{id}
- `updateChatTitle(id, title)`: PUT /chats/{id}

### ChatList.jsx

**Props**:

```javascript
{
  chats: Array,              // List of chat objects
  selectedChatId: Number,    // Currently selected chat ID
  onSelectChat: Function,    // Handler for chat selection
  onCreateChat: Function,    // Handler for creating new chat
  onDeleteChat: Function,    // Handler for deleting chat
  onUpdateTitle: Function,   // Handler for renaming chat
  loading: Boolean           // Loading state
}
```

### ChatWindow.jsx

**Props**:

```javascript
{
  chatId: Number,           // Current chat ID
  onChatCreated: Function   // Called after message is sent
}
```

**State**:

- `messages`: Array of message objects
- `input`: Current input text
- `loading`: Loading state
- `chatInfo`: Current chat metadata

**Methods**:

- `fetchChatHistory()`: GET /chats/{chatId}/messages
- `fetchChatInfo()`: GET /chats/{chatId}
- `sendMessage(e)`: POST /chats/{chatId}/prompt

## Data Models

### Chat Object

```javascript
{
  id: Number,
  title: String,
  description: String,
  model: String,
  temperature: Number,
  is_active: Boolean,
  created_at: DateTime,
  updated_at: DateTime,
  last_message_at: DateTime | null
}
```

### Message Object

```javascript
{
  id: Number,
  chat_id: Number,
  role: String,           // "user" | "assistant" | "system"
  content: String,
  tokens: Number | null,
  is_edited: Boolean,
  created_at: DateTime,
  edited_at: DateTime | null
}
```

### Health Status Object

```javascript
{
  status: String,        // "healthy" | "unhealthy"
  ollama_running: Boolean,
  models_available: Number
}
```

## API Response Examples

### Create Chat Response

```json
{
  "id": 1,
  "title": "New Chat",
  "description": "New conversation",
  "model": "mistral:7b",
  "temperature": 0.7,
  "is_active": true,
  "created_at": "2024-12-11T10:30:00",
  "updated_at": "2024-12-11T10:30:00",
  "last_message_at": null
}
```

### Send Prompt Response

```json
{
  "chat_id": 1,
  "user_message_id": 5,
  "assistant_message_id": 6,
  "message": "This is the AI response...",
  "model": "mistral:7b",
  "generation_time": 2.34,
  "tokens_used": null,
  "total_tokens_in_chat": 150
}
```

### Health Check Response

```json
{
  "status": "healthy",
  "ollama_running": true,
  "models_available": 1
}
```

## State Management Pattern

The frontend uses React hooks for state management:

```javascript
// Parent Component (ChatTab)
const [chats, setChats] = useState([])
const [selectedChatId, setSelectedChatId] = useState(null)

// Fetch data on mount
useEffect(() => {
  fetchChats()
}, [])

// Pass handlers to children
<ChatList
  chats={chats}
  onSelectChat={setSelectedChatId}
  onDeleteChat={deleteChat}
/>
```

This pattern ensures:

- Single source of truth for chat data
- Consistent state across components
- Easy debugging and testing

## Error Handling

### Frontend Error Handling

```javascript
try {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  const data = await response.json();
  // Use data...
} catch (error) {
  console.error("Failed to fetch:", error);
  alert("An error occurred. Please try again.");
}
```

### Backend Error Responses

```json
{
  "detail": "Error message describing what went wrong"
}
```

## CORS Configuration

The backend includes CORS middleware to allow frontend requests:

```python
# In app.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Performance Considerations

### Frontend Optimizations

1. **Message Pagination**: Load only last 100 messages
2. **Auto-scroll**: Only scroll on new messages
3. **Input Debouncing**: Could be added for search
4. **Lazy Loading**: Could load older messages on scroll

### Backend Optimizations

1. **Database Indexing**: Indexes on chat_id, user_id
2. **Connection Pooling**: Reuse database connections
3. **Caching**: Could cache chat list
4. **Streaming**: Could stream long responses

## Testing Integration

### Manual Testing Checklist

- [ ] Create a new chat
- [ ] Send a message and receive response
- [ ] List all chats
- [ ] Rename a chat
- [ ] Delete a chat
- [ ] Check health status
- [ ] Verify error handling
- [ ] Test message history loading
- [ ] Test with empty chat

### Automated Testing

```bash
# Frontend
npm run lint
npm run test

# Backend
python -m pytest
```

## Deployment Checklist

- [ ] Update API base URL in frontend
- [ ] Build frontend: `npm run build`
- [ ] Deploy to hosting service
- [ ] Configure backend environment
- [ ] Set up database
- [ ] Enable HTTPS
- [ ] Configure CORS for production domain
- [ ] Test all endpoints
- [ ] Monitor logs and errors

## Troubleshooting Integration Issues

### 404 Not Found

- Check endpoint URL spelling
- Verify backend is running on correct port
- Check routing configuration

### CORS Error

- Verify backend CORS configuration
- Check frontend API URL
- Ensure requests use correct HTTP method

### 500 Internal Server Error

- Check backend logs
- Verify database connection
- Check Ollama service status

### Timeout

- Check Ollama service responsiveness
- Verify network connectivity
- Consider increasing timeout values

## Future Enhancements

### Frontend

- WebSocket support for real-time updates
- Service Worker for offline support
- Progressive Web App (PWA) features
- Local caching with IndexedDB

### Backend

- WebSocket endpoints for streaming
- GraphQL API option
- API versioning
- Rate limiting middleware
- Authentication/Authorization

### Integration

- OAuth2 authentication
- API key management
- Webhook support
- Event streaming
