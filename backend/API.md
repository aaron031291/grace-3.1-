# Grace API

FastAPI-based REST API for Ollama model inference and embeddings.

## Features

- 🤖 Chat endpoint with multi-turn conversation support
- 🏥 Health check endpoint
- 📚 Auto-generated API documentation (Swagger UI & ReDoc)
- 🔧 Configurable model parameters
- ✅ Type-safe request/response validation with Pydantic

## Endpoints

### GET `/` 
Root endpoint with API information.

**Response:**
```json
{
  "name": "Grace API",
  "version": "0.1.0",
  "description": "API for Ollama-based chat and embeddings",
  "docs": "/docs",
  "health": "/health"
}
```

### GET `/health`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "ollama_running": true,
  "models_available": 1
}
```

### POST `/chat`
Chat endpoint for generating responses using Ollama models.

**Request Body:**
```json
{
  "messages": [
    {
      "role": "system",
      "content": "You are a helpful assistant."
    },
    {
      "role": "user",
      "content": "What is Python?"
    }
  ],
  "model": "mistral:7b",
  "temperature": 0.7,
  "top_p": 0.9,
  "top_k": 40,
  "num_predict": 100
}
```

**Parameters:**
- `messages` (required): Array of message objects with `role` and `content`
  - Roles: `"user"`, `"assistant"`, `"system"`
- `model` (optional): Model name (defaults to `OLLAMA_LLM_DEFAULT` from settings)
- `temperature` (optional, 0.0-2.0): Controls randomness, default 0.7
- `top_p` (optional, 0.0-1.0): Nucleus sampling, default 0.9
- `top_k` (optional): Top-k sampling, default 40
- `num_predict` (optional): Max tokens to generate

**Response:**
```json
{
  "message": "Python is a high-level programming language...",
  "model": "mistral:7b",
  "generation_time": 2.34,
  "prompt_tokens": null,
  "response_tokens": null
}
```

### GET `/docs`
Swagger UI documentation (interactive API explorer).

### GET `/redoc`
ReDoc documentation (alternative API documentation).

## Running the API

### Start the server
```bash
cd backend
source venv/bin/activate
python app.py
```

The API will be available at `http://localhost:8000`

### With Uvicorn directly
```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

## Requirements

- Ollama running and accessible at `http://localhost:11434`
- Python packages: FastAPI, Uvicorn, Pydantic, ollama-client

All dependencies are in `requirements.txt`

## Configuration

Model defaults can be configured via environment variables in `.env`:

```env
OLLAMA_URL=http://localhost:11434
OLLAMA_LLM_DEFAULT=mistral:7b
```

## Testing

Run the test suite:
```bash
source venv/bin/activate
pytest tests/test_app.py -v
```

## Example Usage

### Using curl
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "What is machine learning?"}
    ]
  }'
```

### Using Python
```python
import requests

response = requests.post(
    "http://localhost:8000/chat",
    json={
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Explain quantum computing"}
        ],
        "temperature": 0.8
    }
)

print(response.json())
```

### Using JavaScript/TypeScript
```javascript
const response = await fetch('http://localhost:8000/chat', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    messages: [
      { role: 'user', content: 'Hello!' }
    ],
    temperature: 0.7
  })
});

const data = await response.json();
console.log(data.message);
```

## Error Handling

- `400`: Bad request (invalid model, validation error)
- `503`: Service unavailable (Ollama not running)
- `500`: Server error

All errors include a descriptive message in the response.

## Future Enhancements

- [ ] Embedding generation endpoint
- [ ] Streaming responses
- [ ] RAG (Retrieval-Augmented Generation) pipeline
- [ ] Vector similarity search
- [ ] Authentication/Authorization
- [ ] Rate limiting
- [ ] Request/response logging
