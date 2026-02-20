# Auth

**File:** `security/auth.py`

## Overview

Authentication and Session Security for GRACE

Provides:
- Secure session management
- Authentication dependencies for FastAPI
- Session validation

## Classes

- `SessionManager`

## Key Methods

- `create_session()`
- `validate_session()`
- `invalidate_session()`
- `get_user_sessions()`
- `invalidate_all_user_sessions()`
- `cleanup_expired_sessions()`
- `get_session_manager()`
- `require_auth()`
- `generate_csrf_token()`
- `validate_csrf_token()`

---
*Grace 3.1*
