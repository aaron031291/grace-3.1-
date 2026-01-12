# GRACE Security Checklist

## Pre-Deployment Security Checklist

### Critical (Must Do Before Production)

- [ ] **Set `PRODUCTION_MODE=true`** in `.env`
- [ ] **Configure CORS origins** - Replace localhost URLs with your actual domains:
  ```
  CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
  ```
- [ ] **Enable HTTPS** - Deploy behind a reverse proxy (nginx) with TLS 1.3
- [ ] **Set `SESSION_COOKIE_SECURE=true`** - Requires HTTPS
- [ ] **Set strong database password** - Never use empty or default passwords
- [ ] **Review rate limits** - Adjust based on expected traffic

### Important (Strongly Recommended)

- [ ] **Enable security logging** - `LOG_SECURITY_EVENTS=true`
- [ ] **Set up log monitoring** - Monitor for security events
- [ ] **Use environment-specific .env files** - Don't share between dev/staging/prod
- [ ] **Rotate API keys regularly** - Qdrant, database, etc.
- [ ] **Enable database encryption at rest** - Use cloud provider features

### Optional (Production Hardening)

- [ ] **Configure WAF** - Use Cloudflare, AWS WAF, or similar
- [ ] **Set up intrusion detection** - Monitor for suspicious patterns
- [ ] **Enable HSTS preload** - After confirming HTTPS works
- [ ] **Review CSP headers** - Tighten based on your frontend needs
- [ ] **Set up Redis** - Replace in-memory rate limiting/sessions

---

## Security Features Implemented

### 1. CORS Protection
- **File**: `security/config.py`
- Restricted to specific origins (no more `allow_origins=["*"]`)
- Configurable via `CORS_ALLOWED_ORIGINS` environment variable

### 2. Rate Limiting
- **File**: `security/middleware.py`
- Per-IP rate limiting with sliding window
- Different limits for different endpoint types:
  - Auth endpoints: 10/minute (stricter)
  - AI/LLM endpoints: 30/minute
  - File uploads: 20/minute
  - General endpoints: 100/minute

### 3. Security Headers
- **File**: `security/middleware.py`
- Content-Security-Policy (CSP)
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- X-XSS-Protection: 1; mode=block
- Referrer-Policy: strict-origin-when-cross-origin
- Strict-Transport-Security (HSTS) - in production

### 4. Input Validation
- **File**: `security/validators.py`
- XSS pattern detection
- SQL injection pattern detection
- Path traversal prevention
- Command injection prevention
- File extension validation

### 5. Session Security
- **File**: `security/auth.py`
- Cryptographically secure session IDs
- Server-side session validation
- Secure cookie settings (httponly, samesite, secure)
- Reduced session/cookie expiration times

### 6. Security Logging
- **File**: `security/logging.py`
- Authentication attempts (success/failure)
- Rate limit violations
- Suspicious requests
- Input validation failures
- Access denied events

---

## Environment Variables Reference

```bash
# Security Mode
PRODUCTION_MODE=true              # Enable strict security

# CORS
CORS_ALLOWED_ORIGINS=https://...  # Allowed origins

# Rate Limiting
RATE_LIMIT_ENABLED=true           # Enable rate limiting
RATE_LIMIT_DEFAULT=100/minute     # Default limit
RATE_LIMIT_AUTH=10/minute         # Auth endpoints
RATE_LIMIT_AI=30/minute           # AI endpoints

# Session Security
SESSION_COOKIE_SECURE=true        # HTTPS-only cookies

# Logging
LOG_SECURITY_EVENTS=true          # Enable security logs
```

---

## Architecture Overview

```
Request Flow:

    [Client]
        |
        v
    [CORS Middleware] ──> Validates origin
        |
        v
    [Request Validation Middleware] ──> Checks for attacks
        |
        v
    [Rate Limit Middleware] ──> Enforces rate limits
        |
        v
    [Security Headers Middleware] ──> Adds security headers
        |
        v
    [Genesis Key Middleware] ──> Tracks requests
        |
        v
    [API Endpoint] ──> Processes request
        |
        v
    [Response with Security Headers]
```

---

## Incident Response

### Rate Limit Exceeded
- Check logs for `RATE_LIMIT_EXCEEDED` events
- Identify source IP/user
- Consider temporary IP block if malicious

### Suspicious Request Detected
- Check logs for `SUSPICIOUS_REQUEST` events
- Review the pattern that triggered detection
- Update validation rules if false positive

### Authentication Failures
- Check logs for `AUTH_ATTEMPT` events with `success: false`
- Look for patterns indicating brute force
- Consider IP blocking or CAPTCHA

---

## Support

For security concerns, create an issue at:
https://github.com/aaron031291/grace-3.1-/issues
