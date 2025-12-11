# Grace API - Chat Endpoints Documentation

## Overview

The Grace API now provides a complete suite of endpoints for managing chats, messages, and AI-generated responses. All endpoints support full CRUD operations for chat sessions and messages, with integrated Ollama LLM support.

## Base URL

```
http://localhost:8000
```

## Authentication

Currently, there is no authentication. All endpoints are publicly accessible (for single-user setup).

---

## Chat Management Endpoints

### Create a New Chat

**Endpoint:** `POST /chats`

**Description:** Create a new chat session

**Request Body:**

```json
{
  "title": "Python Help",
  "description": "Discussing Python programming",
  "model": "mistral:7b",
  "temperature": 0.7
}
```

**Response (201):**

```json
{
  "id": 1,
  "title": "Python Help",
  "description": "Discussing Python programming",
  "model": "mistral:7b",
  "temperature": 0.7,
  "is_active": true,
  "created_at": "2024-12-11T10:30:00",
  "updated_at": "2024-12-11T10:30:00",
  "last_message_at": null
}
```

**Query Parameters:** None

**Status Codes:**

- `201 Created` - Chat created successfully
- `400 Bad Request` - Model not found
- `500 Internal Server Error` - Server error

---

### List All Chats

**Endpoint:** `GET /chats`

**Description:** Get all chats with pagination and filtering

**Query Parameters:**

- `skip` (int, default: 0) - Number of chats to skip
- `limit` (int, default: 50) - Maximum number of chats to return
- `active_only` (bool, default: false) - Only return active chats

**Example:**

```
GET /chats?skip=0&limit=10&active_only=false
```

**Response (200):**

```json
{
  "chats": [
    {
      "id": 1,
      "title": "Python Help",
      "description": "Discussing Python programming",
      "model": "mistral:7b",
      "temperature": 0.7,
      "is_active": true,
      "created_at": "2024-12-11T10:30:00",
      "updated_at": "2024-12-11T10:30:00",
      "last_message_at": "2024-12-11T10:45:00"
    }
  ],
  "total": 5,
  "skip": 0,
  "limit": 10
}
```

**Status Codes:**

- `200 OK` - Chats retrieved successfully
- `500 Internal Server Error` - Server error

---

### Get a Specific Chat

**Endpoint:** `GET /chats/{chat_id}`

**Description:** Get details of a specific chat

**Path Parameters:**

- `chat_id` (int) - ID of the chat

**Response (200):**

```json
{
  "id": 1,
  "title": "Python Help",
  "description": "Discussing Python programming",
  "model": "mistral:7b",
  "temperature": 0.7,
  "is_active": true,
  "created_at": "2024-12-11T10:30:00",
  "updated_at": "2024-12-11T10:30:00",
  "last_message_at": "2024-12-11T10:45:00"
}
```

**Status Codes:**

- `200 OK` - Chat retrieved successfully
- `404 Not Found` - Chat not found
- `500 Internal Server Error` - Server error

---

### Update a Chat

**Endpoint:** `PUT /chats/{chat_id}`

**Description:** Update chat settings (title, description, model, temperature)

**Path Parameters:**

- `chat_id` (int) - ID of the chat

**Request Body:**

```json
{
  "title": "Advanced Python",
  "description": "Updated description",
  "model": "mistral:7b",
  "temperature": 0.8
}
```

**Response (200):**

```json
{
  "id": 1,
  "title": "Advanced Python",
  "description": "Updated description",
  "model": "mistral:7b",
  "temperature": 0.8,
  "is_active": true,
  "created_at": "2024-12-11T10:30:00",
  "updated_at": "2024-12-11T10:35:00",
  "last_message_at": "2024-12-11T10:45:00"
}
```

**Status Codes:**

- `200 OK` - Chat updated successfully
- `404 Not Found` - Chat not found
- `400 Bad Request` - Model not found
- `500 Internal Server Error` - Server error

---

### Delete a Chat

**Endpoint:** `DELETE /chats/{chat_id}`

**Description:** Delete a chat and all associated messages

**Path Parameters:**

- `chat_id` (int) - ID of the chat

**Response (200):**

```json
{
  "message": "Chat 1 deleted successfully"
}
```

**Status Codes:**

- `200 OK` - Chat deleted successfully
- `404 Not Found` - Chat not found
- `500 Internal Server Error` - Server error

---

## Message Management Endpoints

### Add a Message to Chat

**Endpoint:** `POST /chats/{chat_id}/messages`

**Description:** Manually add a message to a chat (for message storage)

**Path Parameters:**

- `chat_id` (int) - ID of the chat

**Request Body:**

```json
{
  "content": "What is Python?",
  "role": "user"
}
```

**Response (201):**

```json
{
  "id": 1,
  "chat_id": 1,
  "role": "user",
  "content": "What is Python?",
  "tokens": null,
  "is_edited": false,
  "created_at": "2024-12-11T10:31:00",
  "edited_at": null
}
```

**Status Codes:**

- `201 Created` - Message created successfully
- `404 Not Found` - Chat not found
- `500 Internal Server Error` - Server error

---

### Get Chat History

**Endpoint:** `GET /chats/{chat_id}/messages`

**Description:** Get all messages in a chat with pagination

**Path Parameters:**

- `chat_id` (int) - ID of the chat

**Query Parameters:**

- `skip` (int, default: 0) - Number of messages to skip
- `limit` (int, default: 100) - Maximum number of messages to return

**Example:**

```
GET /chats/1/messages?skip=0&limit=50
```

**Response (200):**

```json
{
  "messages": [
    {
      "id": 1,
      "chat_id": 1,
      "role": "user",
      "content": "What is Python?",
      "tokens": 4,
      "is_edited": false,
      "created_at": "2024-12-11T10:31:00",
      "edited_at": null
    },
    {
      "id": 2,
      "chat_id": 1,
      "role": "assistant",
      "content": "Python is a high-level programming language...",
      "tokens": 50,
      "is_edited": false,
      "created_at": "2024-12-11T10:31:05",
      "edited_at": null
    }
  ],
  "total": 2,
  "model": "mistral:7b",
  "created_at": "2024-12-11T10:30:00"
}
```

**Status Codes:**

- `200 OK` - Messages retrieved successfully
- `404 Not Found` - Chat not found
- `500 Internal Server Error` - Server error

---

### Edit a Message

**Endpoint:** `PUT /chats/{chat_id}/messages/{message_id}`

**Description:** Edit an existing message in a chat

**Path Parameters:**

- `chat_id` (int) - ID of the chat
- `message_id` (int) - ID of the message to edit

**Request Body:**

```json
{
  "content": "What is Python? (updated)",
  "role": "user"
}
```

**Response (200):**

```json
{
  "id": 1,
  "chat_id": 1,
  "role": "user",
  "content": "What is Python? (updated)",
  "tokens": 4,
  "is_edited": true,
  "created_at": "2024-12-11T10:31:00",
  "edited_at": "2024-12-11T10:32:00"
}
```

**Note:** Original content is preserved in the database for audit purposes.

**Status Codes:**

- `200 OK` - Message edited successfully
- `404 Not Found` - Chat or message not found
- `500 Internal Server Error` - Server error

---

### Delete a Message

**Endpoint:** `DELETE /chats/{chat_id}/messages/{message_id}`

**Description:** Delete a message from a chat

**Path Parameters:**

- `chat_id` (int) - ID of the chat
- `message_id` (int) - ID of the message to delete

**Response (200):**

```json
{
  "message": "Message 1 deleted successfully"
}
```

**Status Codes:**

- `200 OK` - Message deleted successfully
- `404 Not Found` - Chat or message not found
- `500 Internal Server Error` - Server error

---

## Chat Prompt/LLM Endpoints

### Send a Prompt (Generate Response)

**Endpoint:** `POST /chats/{chat_id}/prompt`

**Description:** Send a message/prompt to a chat and get an AI-generated response

This is the main endpoint for chatting with the LLM. It:

1. Adds the user message to chat history
2. Retrieves chat history for context
3. Generates a response using Ollama
4. Stores the response in chat history
5. Returns the response with metadata

**Path Parameters:**

- `chat_id` (int) - ID of the chat

**Request Body:**

```json
{
  "content": "What are the main features of Python?",
  "temperature": 0.7,
  "top_p": 0.9,
  "top_k": 40
}
```

**Response (200):**

```json
{
  "chat_id": 1,
  "user_message_id": 3,
  "assistant_message_id": 4,
  "message": "Python has several main features:\n1. Simple and readable syntax\n2. Dynamic typing\n3. Extensive standard library...",
  "model": "mistral:7b",
  "generation_time": 2.345,
  "tokens_used": 150,
  "total_tokens_in_chat": 250
}
```

**Query Parameters:** None

**Status Codes:**

- `200 OK` - Response generated successfully
- `404 Not Found` - Chat not found
- `503 Service Unavailable` - Ollama not running
- `500 Internal Server Error` - Server error

**Parameters Explanation:**

- `content` - The user message/prompt
- `temperature` (optional) - Controls randomness (0.0-2.0). Default: use chat's setting
- `top_p` (optional) - Nucleus sampling (0.0-1.0). Default: 0.9
- `top_k` (optional) - Top-k sampling. Default: 40

---

## Usage Example - Complete Chat Flow

```bash
# 1. Create a new chat
curl -X POST http://localhost:8000/chats \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Programming Help",
    "description": "Get help with programming",
    "model": "mistral:7b",
    "temperature": 0.7
  }'

# Response: {"id": 1, ...}

# 2. Send a prompt (user message + get AI response)
curl -X POST http://localhost:8000/chats/1/prompt \
  -H "Content-Type: application/json" \
  -d '{
    "content": "How do I create a function in Python?"
  }'

# 3. Get chat history
curl http://localhost:8000/chats/1/messages

# 4. Send another prompt (continues conversation)
curl -X POST http://localhost:8000/chats/1/prompt \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Can you show me an example?"
  }'

# 5. Edit a message
curl -X PUT http://localhost:8000/chats/1/messages/1 \
  -H "Content-Type: application/json" \
  -d '{
    "content": "How do I create a function in Python? (corrected)"
  }'

# 6. List all chats
curl http://localhost:8000/chats

# 7. Delete the chat
curl -X DELETE http://localhost:8000/chats/1
```

---

## Error Handling

All endpoints return appropriate HTTP status codes:

- **200 OK** - Successful GET/PUT/DELETE
- **201 Created** - Successful POST
- **400 Bad Request** - Invalid input or model not found
- **404 Not Found** - Resource not found
- **503 Service Unavailable** - Ollama not running
- **500 Internal Server Error** - Server error

Error responses include a detail message:

```json
{
  "detail": "Error description here"
}
```

---

## Data Models

### Chat Response Model

```json
{
  "id": 1,
  "title": "string",
  "description": "string or null",
  "model": "string",
  "temperature": 0.7,
  "is_active": true,
  "created_at": "ISO datetime",
  "updated_at": "ISO datetime",
  "last_message_at": "ISO datetime or null"
}
```

### Message Response Model

```json
{
  "id": 1,
  "chat_id": 1,
  "role": "user|assistant|system",
  "content": "string",
  "tokens": 10,
  "is_edited": false,
  "created_at": "ISO datetime",
  "edited_at": "ISO datetime or null"
}
```

### Prompt Response Model

```json
{
  "chat_id": 1,
  "user_message_id": 1,
  "assistant_message_id": 2,
  "message": "string",
  "model": "string",
  "generation_time": 2.5,
  "tokens_used": null,
  "total_tokens_in_chat": 250
}
```

---

## Notes

1. **Single User**: All endpoints work with a single global user context
2. **Ollama Integration**: Requires Ollama to be running for prompt generation
3. **Model Validation**: All model selections are validated against available Ollama models
4. **Chat History**: Full conversation history is maintained and sent to the LLM for context
5. **Edit Tracking**: Original message content is preserved when messages are edited
6. **Cascading Deletes**: Deleting a chat automatically deletes all associated messages

---

## OpenAPI Documentation

Full interactive API documentation is available at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
