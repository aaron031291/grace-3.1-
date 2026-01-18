# Grace Enterprise - Quick Start Guide

## 🚀 For Finance, Law, and Hedge Fund Clients

This guide shows you how to deploy Grace with enterprise features enabled.

---

## ✅ What's Already Built

Grace already has all enterprise features built-in:

- ✅ **Governance** - Three-Pillar Framework + Parliament Governance
- ✅ **Whitelisting** - Whitelist Learning Pipeline with approval workflows
- ✅ **Layering** - Layer 1 Trust Foundation + Security layers
- ✅ **Secure Ingestion** - SHA-256 hashing + Audit trails

**You don't need to dismantle anything** - just configure and deploy!

---

## 📦 Deployment Options

### Option 1: Integrated Deployment (RECOMMENDED)

Deploy Grace as **one integrated system** with all enterprise features.

**Pros:**
- ✅ Simple deployment
- ✅ All features work together
- ✅ Complete audit trail
- ✅ No integration complexity

**Deployment:**
```bash
# 1. Set enterprise mode
export GRACE_ENTERPRISE_MODE=true
export GRACE_INDUSTRY_TYPE=finance  # or "law" or "hedge_fund"

# 2. Start Grace
python backend/app.py

# All enterprise features are now enabled!
```

---

## ⚙️ Configuration

### Environment Variables

Set these environment variables to configure enterprise features:

```bash
# Core Enterprise Mode
GRACE_ENTERPRISE_MODE=true
GRACE_INDUSTRY_TYPE=finance  # finance, law, hedge_fund, general

# Governance
GRACE_ENABLE_GOVERNANCE=true
GRACE_ENABLE_PARLIAMENT_GOVERNANCE=true
GRACE_ENABLE_DECISION_REVIEW=true
GRACE_ENABLE_COMPLIANCE_RULES=true

# Whitelisting
GRACE_ENABLE_WHITELIST=true
GRACE_ENABLE_WHITELIST_APPROVAL=true
GRACE_ENABLE_SOURCE_VERIFICATION=true

# Security
GRACE_ENABLE_LAYER1_ENFORCEMENT=true
GRACE_ENABLE_GENESIS_TRACKING=true
GRACE_ENABLE_AUDIT_LOGGING=true
GRACE_ENABLE_DATA_ISOLATION=true

# Ingestion
GRACE_ENABLE_SECURE_INGESTION=true
GRACE_ENABLE_CONTENT_HASHING=true
GRACE_ENABLE_INTEGRITY_VERIFICATION=true
GRACE_ENABLE_INGESTION_AUDIT=true
```

### Industry-Specific Configurations

#### Finance Industry
```bash
export GRACE_INDUSTRY_TYPE=finance
export GRACE_ENABLE_GOVERNANCE=true
export GRACE_ENABLE_DECISION_REVIEW=true
export GRACE_ENABLE_WHITELIST_APPROVAL=true
```

**Features Enabled:**
- Parliament Governance (multi-model consensus)
- Decision review workflows
- Compliance rules (FINRA, SEC, SOX)
- Strict whitelisting with approval
- Complete audit trails

#### Law Firms
```bash
export GRACE_INDUSTRY_TYPE=law
export GRACE_ENABLE_GOVERNANCE=true
export GRACE_ENABLE_DECISION_REVIEW=true
export GRACE_ENABLE_DATA_ISOLATION=true
```

**Features Enabled:**
- Client isolation
- Privilege protection
- Client-specific whitelists
- Comprehensive audit logging
- Encryption at rest

#### Hedge Funds
```bash
export GRACE_INDUSTRY_TYPE=hedge_fund
export GRACE_ENABLE_GOVERNANCE=true
export GRACE_ENABLE_DATA_ISOLATION=true
```

**Features Enabled:**
- Strategy isolation
- Market data whitelisting
- Performance tracking
- Real-time ingestion
- Strategy-specific security

---

## 🔌 API Endpoints

### Governance API

**Base URL:** `/governance`

**Key Endpoints:**
- `POST /governance/rules` - Create governance rule
- `GET /governance/rules` - List all rules
- `POST /governance/decisions` - Create decision
- `POST /governance/decisions/{id}/review` - Review decision
- `POST /governance/check` - Check compliance

**Example:**
```bash
# Create a governance rule
curl -X POST http://localhost:8000/governance/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Data Classification",
    "description": "Classify data by sensitivity",
    "pillar_type": "operational",
    "severity": 7,
    "action": "warn"
  }'
```

### Whitelist API

**Base URL:** `/api/whitelist`

**Key Endpoints:**
- `POST /api/whitelist/process` - Process data through whitelist
- `GET /api/whitelist/entries` - List whitelist entries
- `POST /api/whitelist/approve` - Approve whitelist entry
- `POST /api/whitelist/feedback` - Submit feedback

**Example:**
```bash
# Process data through whitelist
curl -X POST http://localhost:8000/api/whitelist/process \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Financial report data",
    "source": "finance_team",
    "category": "financial_data",
    "trust_level": "high"
  }'
```

### Ingestion API

**Base URL:** `/ingest`

**Key Endpoints:**
- `POST /ingest/upload` - Upload file with security
- `POST /ingest/batch` - Batch upload
- `GET /ingest/status/{id}` - Check ingestion status

**Example:**
```bash
# Upload file with enterprise security
curl -X POST http://localhost:8000/ingest/upload \
  -F "file=@document.pdf" \
  -F "metadata={\"classification\":\"confidential\"}"
```

---

## 🔒 Security Features

### 1. Content Hashing (SHA-256)

Every ingested document is hashed:
```python
# Automatic - happens during ingestion
document.content_hash = sha256(content)
```

### 2. Genesis Key Tracking

Every operation creates a Genesis Key:
```python
# Automatic - tracks all operations
genesis_key = {
    "what": "File ingestion",
    "where": "/path/to/file",
    "when": timestamp,
    "who": user_id,
    "why": "Knowledge base expansion",
    "how": "ingestion_service"
}
```

### 3. Audit Logging

All operations logged:
```python
# Automatic - all API calls logged
audit_log = {
    "endpoint": "/governance/decisions",
    "user": user_id,
    "timestamp": datetime.now(),
    "action": "create_decision",
    "result": "success"
}
```

### 4. Data Isolation

For multi-tenant deployments:
```python
# Configure per tenant
tenant_config = {
    "database": "tenant_1_db",
    "vector_store": "tenant_1_vectors",
    "governance_rules": "tenant_1_rules"
}
```

---

## 📊 Monitoring & Compliance

### Check Enterprise Configuration

```python
from config.enterprise_config import EnterpriseConfig

# Get configuration summary
config = EnterpriseConfig.get_config_summary()
print(config)

# Check if feature is enabled
if EnterpriseConfig.is_feature_enabled("governance"):
    print("Governance enabled!")
```

### View Audit Logs

```bash
# Check Genesis Keys (audit trail)
curl http://localhost:8000/api/genesis-keys?limit=100

# Check governance decisions
curl http://localhost:8000/governance/decisions

# Check whitelist entries
curl http://localhost:8000/api/whitelist/entries
```

### Compliance Reports

```bash
# Generate compliance report
curl http://localhost:8000/governance/compliance/report \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2026-01-01",
    "end_date": "2026-01-31",
    "report_type": "audit_trail"
  }'
```

---

## 🎯 Quick Setup for Each Industry

### Finance Firm Setup

```bash
# 1. Set environment
export GRACE_ENTERPRISE_MODE=true
export GRACE_INDUSTRY_TYPE=finance

# 2. Start Grace
python backend/app.py

# 3. Configure compliance rules
curl -X POST http://localhost:8000/governance/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "FINRA Compliance",
    "pillar_type": "operational",
    "severity": 9,
    "action": "block"
  }'
```

### Law Firm Setup

```bash
# 1. Set environment
export GRACE_ENTERPRISE_MODE=true
export GRACE_INDUSTRY_TYPE=law

# 2. Start Grace
python backend/app.py

# 3. Configure client isolation
curl -X POST http://localhost:8000/governance/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Client Privilege Protection",
    "pillar_type": "operational",
    "severity": 10,
    "action": "block"
  }'
```

### Hedge Fund Setup

```bash
# 1. Set environment
export GRACE_ENTERPRISE_MODE=true
export GRACE_INDUSTRY_TYPE=hedge_fund

# 2. Start Grace
python backend/app.py

# 3. Configure strategy isolation
curl -X POST http://localhost:8000/governance/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Strategy Isolation",
    "pillar_type": "operational",
    "severity": 10,
    "action": "block"
  }'
```

---

## ✅ Verification Checklist

After deployment, verify:

- [ ] Enterprise mode enabled: `curl http://localhost:8000/health`
- [ ] Governance API working: `curl http://localhost:8000/governance/rules`
- [ ] Whitelist API working: `curl http://localhost:8000/api/whitelist/entries`
- [ ] Ingestion secure: Upload a test file and check for Genesis Key
- [ ] Audit logging: Check Genesis Keys table
- [ ] Content hashing: Verify SHA-256 hashes in database

---

## 📚 Next Steps

1. **Read:** `ENTERPRISE_PACKAGING_STRATEGY.md` - Full strategy document
2. **Configure:** Set environment variables for your industry
3. **Deploy:** Start Grace with enterprise mode enabled
4. **Customize:** Add industry-specific governance rules
5. **Monitor:** Set up compliance reporting

---

## 🆘 Support

**Questions?** Check:
- `ENTERPRISE_PACKAGING_STRATEGY.md` - Full strategy
- `backend/config/enterprise_config.py` - Configuration module
- `backend/api/governance_api.py` - Governance API docs
- `backend/api/whitelist_api.py` - Whitelist API docs

---

## 🎉 Summary

**Grace is enterprise-ready!** Just:

1. ✅ Set `GRACE_ENTERPRISE_MODE=true`
2. ✅ Set `GRACE_INDUSTRY_TYPE=finance|law|hedge_fund`
3. ✅ Start Grace
4. ✅ All enterprise features are enabled!

**No dismantling needed** - Grace's architecture already supports enterprise deployment! 🚀
