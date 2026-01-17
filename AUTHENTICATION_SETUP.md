# Authentication Setup Guide

## 🔐 **Overview**

Grace now supports optional authentication middleware that can be enabled to protect API endpoints. Authentication is **disabled by default** to maintain backward compatibility.

---

## 🚀 **Quick Start**

### **Enable Authentication**

Set the environment variable:
```bash
export AUTH_REQUIRED=true
```

Or add to your `.env` file:
```
AUTH_REQUIRED=true
```

### **Disable Authentication** (Default)

```bash
export AUTH_REQUIRED=false
```

Or simply don't set the variable (defaults to `false`).

---

## 📋 **How It Works**

### **Authentication Flow**

1. **User logs in** at `/auth/login` → Gets Genesis ID and session cookie
2. **Subsequent requests** include Genesis ID cookie → Middleware validates
3. **Protected endpoints** require valid Genesis ID → Returns 401 if missing
4. **Public endpoints** remain accessible → Health checks, docs, auth endpoints

### **Public Endpoints** (Always Accessible)

These endpoints don't require authentication even when `AUTH_REQUIRED=true`:

- `/health` - Health check
- `/health/live` - Liveness probe
- `/health/ready` - Readiness probe
- `/docs` - API documentation
- `/openapi.json` - OpenAPI schema
- `/redoc` - ReDoc documentation
- `/` - Root endpoint
- `/version` - Version info
- `/auth/login` - Login endpoint
- `/auth/logout` - Logout endpoint
- `/auth/whoami` - Check current user

### **Protected Endpoints** (Require Authentication When Enabled)

All other endpoints require authentication when `AUTH_REQUIRED=true`:
- `/chat` - Chat endpoints
- `/ingest` - Ingestion endpoints
- `/retrieve` - Retrieval endpoints
- `/api/*` - All API endpoints
- And all other endpoints

---

## 🔧 **Configuration**

### **Environment Variables**

```bash
# Enable/disable authentication (default: false)
AUTH_REQUIRED=true

# Add custom public endpoints (comma-separated)
AUTH_PUBLIC_ENDPOINTS=/custom/public,/another/public
```

### **Configuration File**

Edit `backend/security/config.py`:

```python
AUTH_REQUIRED: bool = True  # Enable authentication
AUTH_PUBLIC_ENDPOINTS: List[str] = [
    "/health",
    "/docs",
    # Add your custom public endpoints here
]
```

---

## 💻 **Usage Examples**

### **1. Login (Get Genesis ID)**

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "myuser"}'
```

**Response:**
```json
{
  "genesis_id": "GU-abc123def456",
  "session_id": "SS-xyz789",
  "username": "myuser",
  "is_new_user": true,
  "message": "Welcome myuser! You've been assigned Genesis ID: GU-abc123def456"
}
```

### **2. Make Authenticated Request**

```bash
# Using cookie (automatic with browser)
curl http://localhost:8000/api/endpoint \
  --cookie "genesis_id=GU-abc123def456; session_id=SS-xyz789"

# Using header
curl http://localhost:8000/api/endpoint \
  -H "X-Genesis-ID: GU-abc123def456" \
  -H "Cookie: session_id=SS-xyz789"
```

### **3. Check Current User**

```bash
curl http://localhost:8000/auth/whoami \
  --cookie "genesis_id=GU-abc123def456"
```

### **4. Logout**

```bash
curl -X POST http://localhost:8000/auth/logout \
  --cookie "genesis_id=GU-abc123def456; session_id=SS-xyz789"
```

---

## 🛡️ **Security Features**

### **Session Management**

- **Session expiration**: 24 hours (configurable via `SESSION_MAX_AGE_HOURS`)
- **Genesis ID expiration**: 30 days (configurable via `GENESIS_ID_MAX_AGE_DAYS`)
- **Secure cookies**: HttpOnly, Secure, SameSite protection
- **Session validation**: Server-side session validation in production mode

### **Security Headers**

When authentication is enabled, additional security headers are added:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Content-Security-Policy` (configurable)
- `Strict-Transport-Security` (in production)

---

## 🔍 **Troubleshooting**

### **Issue: Getting 401 Unauthorized**

**Solution:**
1. Check if `AUTH_REQUIRED=true` is set
2. Login at `/auth/login` to get Genesis ID
3. Include Genesis ID in requests (cookie or header)

### **Issue: Session Expired**

**Solution:**
1. Sessions expire after 24 hours
2. Login again at `/auth/login`
3. Use existing Genesis ID to resume session

### **Issue: Can't Access Public Endpoints**

**Solution:**
1. Public endpoints should always be accessible
2. Check if endpoint is in `AUTH_PUBLIC_ENDPOINTS` list
3. Verify middleware is configured correctly

---

## 📝 **Using Authentication in Code**

### **Protect an Endpoint**

```python
from fastapi import Depends
from security.auth import get_current_user

@app.get("/protected-endpoint")
async def protected_endpoint(
    user: dict = Depends(get_current_user)
):
    """This endpoint requires authentication."""
    return {
        "message": f"Hello {user['genesis_id']}!",
        "authenticated": True
    }
```

### **Optional Authentication**

```python
from security.auth import get_optional_user

@app.get("/optional-endpoint")
async def optional_endpoint(
    user: dict = Depends(get_optional_user)
):
    """This endpoint works with or without authentication."""
    if user:
        return {"message": f"Hello {user['genesis_id']}!"}
    else:
        return {"message": "Hello anonymous user!"}
```

### **Using Request State**

```python
from fastapi import Request

@app.get("/endpoint")
async def endpoint(request: Request):
    """Access authentication from middleware."""
    genesis_id = getattr(request.state, 'genesis_id', None)
    if genesis_id:
        return {"authenticated": True, "genesis_id": genesis_id}
    else:
        return {"authenticated": False}
```

---

## 🎯 **Best Practices**

1. **Development**: Keep `AUTH_REQUIRED=false` for easier testing
2. **Production**: Always set `AUTH_REQUIRED=true`
3. **Session Management**: Use secure cookies in production
4. **Error Handling**: Provide clear error messages for auth failures
5. **Logging**: Monitor authentication events via security logger

---

## 📚 **Related Documentation**

- `backend/security/auth.py` - Authentication dependencies
- `backend/security/auth_middleware.py` - Authentication middleware
- `backend/security/config.py` - Security configuration
- `backend/api/auth.py` - Authentication API endpoints

---

**Last Updated:** Current Session  
**Status:** Authentication middleware ready to use - enable via `AUTH_REQUIRED=true`
