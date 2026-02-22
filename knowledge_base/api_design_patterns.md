# API Design Patterns & Best Practices

## RESTful API Design

### URL Structure
- Use nouns, not verbs: `/users` not `/getUsers`
- Use plural nouns: `/items` not `/item`
- Nest for relationships: `/users/{id}/orders`
- Use query params for filtering: `/items?status=active&sort=name`

### HTTP Methods
- GET: Retrieve resources (idempotent)
- POST: Create new resources
- PUT: Full update of a resource
- PATCH: Partial update
- DELETE: Remove a resource

### Status Codes
- 200: Success
- 201: Created
- 204: No Content (successful delete)
- 400: Bad Request (validation error)
- 401: Unauthorized (not authenticated)
- 403: Forbidden (not authorized)
- 404: Not Found
- 409: Conflict (duplicate resource)
- 422: Unprocessable Entity (semantic error)
- 429: Too Many Requests (rate limited)
- 500: Internal Server Error

### Pagination
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 100,
    "total_pages": 5
  }
}
```

### Error Responses
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid email format",
    "details": [
      {"field": "email", "message": "Must be a valid email address"}
    ]
  }
}
```

## Authentication Patterns

### JWT (JSON Web Tokens)
- Access token: Short-lived (15 min), sent in Authorization header
- Refresh token: Long-lived (7 days), stored securely
- Never store JWTs in localStorage — use httpOnly cookies

### OAuth 2.0 Flow
1. Client redirects user to authorization server
2. User authenticates and grants permission
3. Authorization server returns authorization code
4. Client exchanges code for access token
5. Client uses access token to access resources

### API Keys
- For server-to-server communication
- Send in header: `X-API-Key: your-key-here`
- Rate limit per key
- Rotate regularly

## Database Design

### Normalization
- 1NF: Each column has atomic values
- 2NF: No partial dependencies on composite keys
- 3NF: No transitive dependencies

### Indexing Strategy
- Index columns used in WHERE, JOIN, ORDER BY
- Composite indexes for multi-column queries
- Don't over-index — each index slows writes

### Connection Pooling
```python
from sqlalchemy import create_engine
engine = create_engine(
    "postgresql://user:pass@host/db",
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
)
```

## Microservices Patterns

### Circuit Breaker
Prevents cascading failures. After N failures, circuit opens and returns fallback response for a cooldown period before retrying.

### Retry with Exponential Backoff
```python
import time

def retry_with_backoff(func, max_retries=3, base_delay=1):
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt)
            time.sleep(delay)
```

### Event-Driven Architecture
- Producer publishes events to a message queue
- Consumers process events independently
- Enables loose coupling and scalability
- Use dead-letter queues for failed messages

## Security Best Practices

### Input Validation
- Validate all input on the server side
- Use parameterized queries (never string concatenation for SQL)
- Sanitize HTML output to prevent XSS
- Validate file uploads (type, size, content)

### CORS Configuration
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

### Rate Limiting
- Per-IP: 100 requests/minute for general endpoints
- Per-user: 30 requests/minute for AI/LLM endpoints
- Per-API-key: Custom limits based on tier
