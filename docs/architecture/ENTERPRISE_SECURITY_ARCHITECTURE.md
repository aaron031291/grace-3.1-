# GRACE Enterprise Security Architecture

## Overview

GRACE implements a comprehensive enterprise-grade security architecture designed for **high-stakes, trust, and auditability environments**. This document outlines the security capabilities built into GRACE.

---

## Security Modules

### 1. Role-Based Access Control (RBAC)
**Location:** `backend/security/rbac/`

| Component | Purpose |
|-----------|---------|
| `models.py` | SQLAlchemy models for roles, permissions, user assignments |
| `roles.py` | 9 built-in roles with hierarchy (SUPER_ADMIN → GUEST) |
| `permissions.py` | Resource types + actions (e.g., `code:healing:approve`) |
| `enforcer.py` | Deny-by-default policy enforcement with decorators |
| `middleware.py` | FastAPI middleware for automatic permission injection |
| `api.py` | Admin endpoints for role/permission management |

**Built-in Roles:**
- `SUPER_ADMIN` - Full system access
- `ADMIN` - Administrative functions
- `OPERATOR` - Operational tasks
- `DEVELOPER` - Development access
- `ANALYST` - Read and analyze
- `AUDITOR` - Audit trail access
- `READONLY` - View only
- `SERVICE_ACCOUNT` - Automated processes
- `GUEST` - Minimal access

---

### 2. Secrets Management
**Location:** `backend/security/secrets/`

| Component | Purpose |
|-----------|---------|
| `vault.py` | Multi-backend vault (Local, HashiCorp, AWS, Azure) |
| `encryption.py` | AES-256-GCM, Argon2, envelope encryption, HSM support |
| `rotation.py` | Automatic secret rotation with policies |
| `config.py` | Secrets configuration management |

**Features:**
- **Multi-backend support** with automatic failover
- **Secret versioning** with rollback capability
- **Automatic rotation** by secret type (API keys: 90 days, certificates: 365 days)
- **HSM integration** for hardware-backed key storage
- **Field-level encryption** for database columns
- **Audit logging** of all secret access (name only, never value)

---

### 3. Zero-Trust Security Framework
**Location:** `backend/security/zero_trust/`

| Component | Purpose |
|-----------|---------|
| `identity.py` | Continuous authentication, device fingerprinting |
| `context.py` | Request context enrichment, risk scoring |
| `policy_engine.py` | Policy-as-code conditional access |
| `mfa.py` | TOTP, WebAuthn, backup codes, adaptive MFA |
| `threat_detection.py` | Real-time threat detection |
| `network.py` | IP filtering, geo-blocking, mTLS |

**Threat Detection Types:**
- Brute force attacks
- Credential stuffing
- Session hijacking
- Impossible travel
- API abuse patterns
- Injection attempts
- Data exfiltration

**Self-Healing Responses:**
- Automatic IP blocking
- Session termination
- Step-up authentication
- Rate limiting
- Alert escalation

---

### 4. Cryptographic Security
**Location:** `backend/security/crypto/`

| Component | Purpose |
|-----------|---------|
| `keys.py` | RSA/ECDSA key generation, storage, rotation |
| `encryption.py` | AES-256-GCM, RSA-OAEP, searchable encryption |
| `signing.py` | Document/code signing, multi-party signatures |
| `hashing.py` | Argon2id passwords, SHA-256/SHA-3, HMAC |
| `certificates.py` | Certificate lifecycle management |
| `integrity.py` | Merkle trees, tamper detection |
| `random.py` | Cryptographically secure random generation |

---

### 5. API Security
**Location:** `backend/security/api_security/`

| Component | Purpose |
|-----------|---------|
| `api_keys.py` | API key generation, scoping, rotation |
| `oauth.py` | OAuth2/OIDC provider with PKCE |
| `rate_limiting.py` | Tiered sliding window rate limiting |
| `request_validation.py` | Request signing, replay prevention, injection blocking |
| `response_security.py` | Response signing, PII redaction |
| `gateway.py` | Circuit breaker, request routing |
| `middleware.py` | Composed security middleware with levels |

**Security Levels:**
- `MINIMAL` - Basic validation
- `STANDARD` - Rate limiting + headers
- `HIGH` - Signing + MFA triggers
- `MAXIMUM` - All checks + strict policies

---

### 6. Compliance Management
**Location:** `backend/security/compliance/`

| Component | Purpose |
|-----------|---------|
| `frameworks.py` | SOC 2, HIPAA, GDPR, ISO 27001, FedRAMP, PCI-DSS controls |
| `evidence.py` | Automated evidence collection, tamper-evident packaging |
| `data_governance.py` | Data classification, lineage, retention, erasure |
| `continuous_monitoring.py` | Real-time violation detection, drift detection |
| `api.py` | REST API for compliance operations |

**Supported Frameworks:**
| Framework | Controls | Use Case |
|-----------|----------|----------|
| SOC 2 Type II | 5 | General security |
| HIPAA | 5 | Healthcare/PHI |
| GDPR | 6 | Privacy/EU |
| ISO 27001 | 3 | International |
| FedRAMP | - | Government |
| PCI-DSS | - | Financial/payments |

**Data Classification Levels:**
- `PUBLIC` - Open information
- `INTERNAL` - Business internal
- `CONFIDENTIAL` - Sensitive business data
- `RESTRICTED` - PII, PHI, PCI data
- `TOP_SECRET` - Credentials, keys

---

## Immutable Audit System

All security events are logged to GRACE's immutable audit system:

- **Cryptographic chain linking** (SHA-256)
- **Tamper detection** via chain verification
- **Dual storage** (Database + append-only files)
- **7-year retention** for compliance
- **Complete traceability** to source

### Audited Events:
- Authentication attempts (success/failure)
- Authorization decisions (allow/deny)
- Secret access (name only)
- Threat detections
- Compliance violations
- Data access and modifications
- Code changes and deployments

---

## GRACE-Aligned Self-Healing

Security components integrate with GRACE's self-healing architecture:

| Threat | Automatic Response |
|--------|-------------------|
| Brute force (5 failures) | Block IP for 1 hour |
| Credential stuffing | Block IP for 24 hours |
| Session hijack | Terminate session + require MFA |
| Impossible travel | Step-up authentication |
| API abuse (100+ req/min) | Rate limit, then block |
| Injection attempt | Block IP for 7 days |
| Compliance drift | Auto-remediation where possible |

---

## API Endpoints

### RBAC API
```
GET/POST   /rbac/roles           - List/create roles
GET/PUT/DEL /rbac/roles/{id}     - Manage role
POST       /rbac/users/{id}/roles - Assign role
GET        /rbac/check           - Check permission
```

### Secrets API
```
GET/POST   /secrets              - List/create secrets
GET        /secrets/{name}       - Get secret
POST       /secrets/{name}/rotate - Rotate secret
```

### Compliance API
```
GET        /compliance/frameworks - List frameworks
GET        /compliance/controls   - List controls
GET        /compliance/summary    - Compliance score
POST       /compliance/evidence/collect - Collect evidence
GET        /compliance/violations - Active violations
POST       /compliance/dsar      - Create DSAR request
GET        /compliance/monitoring/status - Monitor status
```

---

## Deployment Recommendations

### Production Checklist

- [ ] Enable `AUTH_REQUIRED=true`
- [ ] Configure HashiCorp Vault or AWS Secrets Manager
- [ ] Enable MFA for all admin accounts
- [ ] Set up geo-blocking for allowed countries
- [ ] Configure TLS 1.2+ for all connections
- [ ] Enable continuous compliance monitoring
- [ ] Set up alert handlers (Slack, PagerDuty, email)
- [ ] Review and customize RBAC roles
- [ ] Configure evidence retention policies
- [ ] Enable audit log backup to external storage

### Environment Variables

```bash
# Authentication
AUTH_REQUIRED=true
SESSION_MAX_AGE_HOURS=24
GENESIS_ID_MAX_AGE_DAYS=30

# Secrets
VAULT_ADDR=https://vault.example.com
VAULT_TOKEN=<token>
# or
AWS_REGION=us-east-1

# Security
FORCE_HTTPS=true
ALLOWED_COUNTRIES=US,CA,GB,DE
BLOCKED_IPS=<cidr ranges>

# Compliance
COMPLIANCE_MONITOR_ENABLED=true
EVIDENCE_RETENTION_DAYS=2555  # 7 years
```

---

## Integration Points

### Existing GRACE Systems

| System | Security Integration |
|--------|---------------------|
| Genesis Keys | All operations audited |
| Self-Healing | Healing actions require approval at RESTRICTED+ |
| Coding Agent | Code changes audited with before/after |
| Knowledge Base | Data classification enforced |
| API Layer | Full request/response audit |

---

## Security Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           GRACE SECURITY LAYERS                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                    NETWORK LAYER                                    │ │
│  │  IP Filter → Geo Filter → Rate Limiter → mTLS → Request Signing   │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                    ↓                                     │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                    AUTHENTICATION LAYER                             │ │
│  │  Genesis ID → Session → MFA → Device Fingerprint → Risk Score     │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                    ↓                                     │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                    AUTHORIZATION LAYER                              │ │
│  │  RBAC → Policy Engine → Context-Aware → Attribute-Based           │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                    ↓                                     │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                    DATA PROTECTION LAYER                            │ │
│  │  Classification → Encryption → Lineage → Retention → Erasure      │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                    ↓                                     │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                    AUDIT & COMPLIANCE LAYER                         │ │
│  │  Immutable Logs → Evidence → Monitoring → Reporting → Self-Heal   │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Certifications Supported

With proper implementation and documentation, GRACE supports achieving:

- **SOC 2 Type II** - Security, Availability, Confidentiality
- **HIPAA** - Protected Health Information
- **GDPR** - EU Privacy Regulation
- **ISO 27001** - Information Security Management
- **FedRAMP** - US Government Cloud
- **PCI-DSS** - Payment Card Industry

---

*Last Updated: January 2026*
*Architecture Version: 3.1*
