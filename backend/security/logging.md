# Logging

**File:** `security/logging.py`

## Overview

Security Event Logging for GRACE

Provides centralized logging for security-related events:
- Authentication attempts
- Rate limit violations
- Suspicious requests
- Input validation failures
- Access control events

## Classes

- `SecurityLogger`

## Key Methods

- `log_auth_attempt()`
- `log_rate_limit()`
- `log_suspicious_request()`
- `log_validation_failure()`
- `log_access_denied()`
- `log_security_event()`
- `get_security_logger()`
- `log_security_event()`

---
*Grace 3.1*
