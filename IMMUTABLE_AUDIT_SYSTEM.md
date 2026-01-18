# GRACE Immutable Audit System

## Overview

The GRACE Immutable Audit System ensures **data cannot disappear** by providing:

- **Write-once, append-only storage** - Records cannot be modified or deleted
- **Cryptographic chain linking** - Each record links to the previous via SHA-256 hash
- **Tamper detection** - Chain verification detects any unauthorized modifications
- **Dual storage** - Database + append-only backup files for redundancy
- **Complete traceability** - Every action links back to its source

## What Gets Stored Immutably

### 1. User Interactions
- All user input messages
- User authentication events  
- User session data
- User actions and commands

### 2. AI Decisions
- All AI decisions with reasoning
- AI code generation requests and outputs
- AI responses to user queries
- Self-healing decisions and actions

### 3. Code Changes
- All code modifications (before AND after state)
- File creation and deletion
- Rollback operations
- Code analysis results

### 4. Data Operations
- All database writes
- Data access logs
- Data exports
- Configuration changes

### 5. Knowledge Base
- Document ingestion
- Knowledge retrieval queries
- Knowledge base updates
- Learning examples created

### 6. API Activity
- All API requests with metadata
- API responses
- External API calls
- Rate limiting events

### 7. Security Events
- Authentication attempts
- Authorization failures
- Security alerts
- Permission changes

### 8. Genesis Keys
- All Genesis Key creation
- Fix suggestions created
- Fixes applied
- Rollback operations

### 9. System Operations
- System startup and shutdown
- Error occurrences
- Health check results
- Background job executions

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    IMMUTABLE AUDIT STORAGE                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   Record 1   │───▶│   Record 2   │───▶│   Record 3   │───▶   │
│  │  hash: abc   │    │  prev: abc   │    │  prev: def   │       │
│  │              │    │  hash: def   │    │  hash: ghi   │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│         │                   │                   │                │
│         ▼                   ▼                   ▼                │
│  ╔══════════════════════════════════════════════════════════╗   │
│  ║                    DATABASE (Primary)                     ║   │
│  ║  • All records with full metadata                        ║   │
│  ║  • Indexed for fast queries                              ║   │
│  ║  • Chain verification on demand                          ║   │
│  ╚══════════════════════════════════════════════════════════╝   │
│         │                   │                   │                │
│         ▼                   ▼                   ▼                │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              APPEND-ONLY FILES (Backup)                   │   │
│  │  • audit_2026-01-18.jsonl                                │   │
│  │  • audit_2026-01-17.jsonl                                │   │
│  │  • Compressed archives (.json.gz)                        │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Chain Integrity

Each audit record contains:
- `record_id`: Unique identifier
- `record_hash`: SHA-256 hash of record content
- `previous_hash`: Hash of the previous record

This creates an unbroken chain where:
1. Any modification to a record changes its hash
2. This breaks the chain link to the next record
3. Chain verification immediately detects tampering

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/immutable-audit/trail` | GET | Get audit trail with filters |
| `/immutable-audit/record/{record_id}` | GET | Get specific record |
| `/immutable-audit/record/{record_id}/related` | GET | Get related records |
| `/immutable-audit/genesis/{genesis_key_id}` | GET | Get Genesis Key audit trail |
| `/immutable-audit/statistics` | GET | Get audit statistics |
| `/immutable-audit/verify-chain` | GET | Verify chain integrity |
| `/immutable-audit/types` | GET | Get available audit types |
| `/immutable-audit/export` | POST | Export verified audit trail |

## Usage Examples

### Record a User Input
```python
from genesis.immutable_audit_storage import audit_user_input

audit_user_input(
    session=session,
    user_id="user-123",
    input_content="Show me the code for authentication",
    context={"source": "chat", "session_id": "sess-456"}
)
```

### Record a Code Change
```python
from genesis.immutable_audit_storage import audit_code_change

audit_code_change(
    session=session,
    actor_id="grace-ai",
    actor_type="ai",
    file_path="backend/auth/login.py",
    code_before="old_code...",
    code_after="new_code...",
    reason="Fixed security vulnerability",
    genesis_key_id="GK-abc123"
)
```

### Record an AI Decision
```python
from genesis.immutable_audit_storage import audit_ai_decision

audit_ai_decision(
    session=session,
    decision="Apply automatic fix for syntax error",
    reasoning="High confidence fix (0.95), low risk, user approved auto-fix",
    confidence=0.95
)
```

### Verify Chain Integrity
```python
from genesis.immutable_audit_storage import get_immutable_audit_storage

storage = get_immutable_audit_storage(session)
is_valid, issues = storage.verify_chain_integrity()

if is_valid:
    print("All records verified - no tampering detected")
else:
    print(f"Chain integrity issues: {issues}")
```

### Query Audit Trail
```python
# Get all code changes for a file
records = storage.get_audit_trail(
    audit_type=ImmutableAuditType.CODE_CHANGE,
    file_path="backend/auth/login.py",
    limit=100
)

# Get all actions by an actor
records = storage.get_audit_trail(
    actor_id="grace-ai",
    start_time=datetime(2026, 1, 1),
    end_time=datetime.now()
)
```

## Guarantees

| Property | Guarantee |
|----------|-----------|
| **Immutability** | No UPDATE or DELETE operations on audit records |
| **Integrity** | SHA-256 hash chain detects any tampering |
| **Completeness** | All critical operations automatically captured |
| **Traceability** | Every record links to its source and parent operations |
| **Durability** | Dual storage (DB + files) prevents data loss |
| **Auditability** | Full queryable history for compliance |

## Integration Points

The immutable audit system integrates with:

1. **Genesis Keys** - All Genesis Key operations are audited
2. **Self-Healing** - All healing decisions and actions are audited
3. **Coding Agent** - All code changes are audited
4. **API Layer** - All API requests/responses are audited
5. **Knowledge Base** - All knowledge operations are audited

## File Locations

- **Database Records**: `backend/database/grace.db` (immutable_audit_records table)
- **Backup Files**: `backend/data/immutable_audit/audit_YYYY-MM-DD.jsonl`
- **Compressed Archives**: `backend/data/immutable_audit/audit_export_*.json.gz`
- **Configuration**: `.immutable_audit_config.json`

## Compliance

This system supports:
- **SOC 2** - Complete audit trail of all data access
- **GDPR** - Full data lineage and provenance
- **HIPAA** - Access logging for sensitive data
- **ISO 27001** - Security event logging

## Startup Verification

On every system startup:
1. Immutable audit storage initializes
2. Chain integrity is verified
3. Startup event is recorded in immutable audit
4. Any issues are logged with warnings

Check startup logs for:
```
[OK] Immutable Audit Storage initialized
[OK] Audit Middleware initialized  
[OK] Audit integrated with Genesis Keys
[OK] System startup recorded in immutable audit trail
[OK] Immutable audit chain integrity verified
```
