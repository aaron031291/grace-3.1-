# Chat Models - Quick Reference

## 📍 Location

- **Models**: `backend/models/database_models.py`
- **Repositories**: `backend/models/repositories.py`
- **Tests**: `backend/tests/test_database.py`

## 🎯 Models at a Glance

### Chat (Chat Session)

```python
Chat(
    user_id: int,           # Which user
    title: str,             # Chat title
    model: str,             # AI model
    temperature: float,     # Temperature (0-2)
    is_active: bool,        # Active status
)
```

### ChatHistory (Messages)

```python
ChatHistory(
    chat_id: int,           # Which chat
    role: str,              # "user", "assistant", "system"
    content: str,           # Message content
    tokens: int,            # Tokens used (optional)
    is_edited: bool,        # Was edited?
    edited_content: str,    # Original (if edited)
)
```

## 🚀 Quick Start

### FastAPI Endpoint - Create Chat

```python
from models.repositories import ChatRepository
from sqlalchemy.orm import Session
from fastapi import Depends

@app.post("/chats/")
async def create_chat(
    title: str,
    user_id: int,
    session: Session = Depends(get_session)
):
    repo = ChatRepository(session)
    chat = repo.create(user_id=user_id, title=title)
    return chat.to_dict()
```

### FastAPI Endpoint - Add Message

```python
from models.repositories import ChatHistoryRepository

@app.post("/chats/{chat_id}/message/")
async def add_message(
    chat_id: int,
    role: str,
    content: str,
    session: Session = Depends(get_session)
):
    repo = ChatHistoryRepository(session)
    message = repo.add_message(
        chat_id=chat_id,
        role=role,
        content=content
    )
    return message.to_dict()
```

### FastAPI Endpoint - Get Conversation

```python
@app.get("/chats/{chat_id}/messages/")
async def get_messages(
    chat_id: int,
    session: Session = Depends(get_session)
):
    repo = ChatHistoryRepository(session)
    messages = repo.get_by_chat(chat_id)
    return [msg.to_dict() for msg in messages]
```

### FastAPI Endpoint - Search Chats

```python
@app.get("/users/{user_id}/chats/search/")
async def search_chats(
    user_id: int,
    query: str,
    session: Session = Depends(get_session)
):
    repo = ChatRepository(session)
    results = repo.search_by_title(user_id, query)
    return [chat.to_dict() for chat in results]
```

## 💾 Repository Methods

### ChatRepository

| Method                                     | Purpose          |
| ------------------------------------------ | ---------------- |
| `create(**kwargs)`                         | Create new chat  |
| `get(id)`                                  | Get chat by ID   |
| `get_by_user(user_id, skip, limit)`        | Get user's chats |
| `get_active_by_user(user_id, skip, limit)` | Get active chats |
| `search_by_title(user_id, search_term)`    | Search by title  |
| `deactivate(chat_id)`                      | Deactivate chat  |
| `activate(chat_id)`                        | Activate chat    |
| `count_by_user(user_id)`                   | Count chats      |
| `update(id, **kwargs)`                     | Update chat      |
| `delete(id)`                               | Delete chat      |

### ChatHistoryRepository

| Method                                      | Purpose                     |
| ------------------------------------------- | --------------------------- |
| `add_message(chat_id, role, content, ...)`  | Add message                 |
| `get_by_chat(chat_id, skip, limit)`         | Get messages (oldest first) |
| `get_by_chat_reverse(chat_id, skip, limit)` | Get messages (newest first) |
| `get_by_role(chat_id, role)`                | Get messages by role        |
| `edit_message(message_id, new_content)`     | Edit message                |
| `count_by_chat(chat_id)`                    | Count messages              |
| `count_tokens_in_chat(chat_id)`             | Total tokens in chat        |
| `get_edited_messages(chat_id)`              | Get all edits               |

## 🧪 Testing

```bash
# All tests
pytest backend/tests/test_database.py -v

# Chat tests only
pytest backend/tests/test_database.py::TestChatRepository -v

# ChatHistory tests only
pytest backend/tests/test_database.py::TestChatHistoryRepository -v
```

## 📊 Database Schema

```sql
-- Chat table
CREATE TABLE chats (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    title VARCHAR(255),
    model VARCHAR(255) DEFAULT 'mistral:7b',
    temperature FLOAT DEFAULT 0.7,
    is_active BOOLEAN DEFAULT TRUE,
    last_message_at DATETIME,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

-- Chat History table
CREATE TABLE chat_history (
    id INTEGER PRIMARY KEY,
    chat_id INTEGER NOT NULL,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    tokens INTEGER,
    token_ids TEXT,
    completion_time FLOAT,
    is_edited BOOLEAN DEFAULT FALSE,
    edited_at DATETIME,
    edited_content TEXT,
    metadata TEXT,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY(chat_id) REFERENCES chats(id)
);
```

## 🔄 Complete Workflow Example

```python
from sqlalchemy.orm import Session
from models.repositories import ChatRepository, ChatHistoryRepository
from fastapi import FastAPI, Depends
from database.session import get_session

@app.post("/api/chats/")
async def create_new_chat(
    title: str,
    user_id: int,
    session: Session = Depends(get_session)
):
    chat_repo = ChatRepository(session)
    chat = chat_repo.create(user_id=user_id, title=title)
    return {"chat_id": chat.id, "title": chat.title}

@app.post("/api/chats/{chat_id}/chat/")
async def send_message(
    chat_id: int,
    user_message: str,
    session: Session = Depends(get_session)
):
    history_repo = ChatHistoryRepository(session)

    # 1. Add user message
    user_msg = history_repo.add_message(
        chat_id=chat_id,
        role="user",
        content=user_message,
        tokens=len(user_message.split())
    )

    # 2. Generate AI response (your code)
    ai_response = "This is AI response"  # Your AI logic here

    # 3. Add assistant message
    ai_msg = history_repo.add_message(
        chat_id=chat_id,
        role="assistant",
        content=ai_response,
        tokens=len(ai_response.split()),
        completion_time=0.25
    )

    return {
        "user": user_msg.to_dict(),
        "assistant": ai_msg.to_dict()
    }

@app.get("/api/chats/{chat_id}/messages/")
async def get_conversation(
    chat_id: int,
    session: Session = Depends(get_session)
):
    history_repo = ChatHistoryRepository(session)
    messages = history_repo.get_by_chat(chat_id)
    return [msg.to_dict() for msg in messages]

@app.put("/api/messages/{message_id}/")
async def edit_message(
    message_id: int,
    new_content: str,
    session: Session = Depends(get_session)
):
    history_repo = ChatHistoryRepository(session)
    edited = history_repo.edit_message(message_id, new_content)
    return edited.to_dict() if edited else None

@app.get("/api/users/{user_id}/chats/")
async def list_user_chats(
    user_id: int,
    skip: int = 0,
    limit: int = 20,
    session: Session = Depends(get_session)
):
    chat_repo = ChatRepository(session)
    chats = chat_repo.get_by_user(user_id, skip, limit)
    return [chat.to_dict() for chat in chats]
```

## 📝 Key Features

✅ **Full CRUD** - Create, read, update, delete  
✅ **Message Editing** - Edit with history preservation  
✅ **Token Tracking** - Count tokens per message and chat  
✅ **Search** - Search chats by title  
✅ **Pagination** - Efficient data loading  
✅ **Performance** - Indexes on all query paths  
✅ **Type Safe** - Full type hints  
✅ **Well Tested** - 19 test cases

## 🔗 Related Files

- Models: `backend/models/database_models.py`
- Repositories: `backend/models/repositories.py`
- Tests: `backend/tests/test_database.py`
- Full Summary: `CHAT_MODELS_SUMMARY.md`
- Database Guide: `backend/DATABASE_GUIDE.md`
