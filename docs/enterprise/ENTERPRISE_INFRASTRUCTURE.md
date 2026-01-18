# Grace Enterprise Infrastructure

## Overview

Grace includes a comprehensive enterprise infrastructure layer that handles:

- **Multi-Environment Management** - Dev/Staging/Production with auto-detection
- **Service Orchestration** - Dependency management, circuit breakers, service mesh
- **Disaster Recovery** - Automated backups, failover, recovery testing
- **Compliance Automation** - SOC2, HIPAA, GDPR, PCI-DSS checks
- **Chaos Engineering** - Resilience testing with controlled failures

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      LAUNCHER LAYER                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  Launcher   │──│  Service    │──│ Dependency  │             │
│  │             │  │  Manager    │  │  Resolver   │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                    ENTERPRISE LAYER                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ Environment │  │ Orchestration│  │  Disaster   │             │
│  │  Manager    │  │   Layer     │  │  Recovery   │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  Secret     │  │  Feature    │  │  Compliance │             │
│  │  Manager    │  │   Flags     │  │   Manager   │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Environment Manager
**Location:** `backend/enterprise/environment_manager.py`

Automatically detects and configures:

| Detection | Method |
|-----------|--------|
| **Deployment Stage** | `GRACE_STAGE` env var, K8s/AWS markers |
| **Runtime Environment** | Docker markers, cloud provider env vars |
| **Hardware Profile** | CPU count, RAM, GPU availability |

**Stages:**
- `development` - Debug logging, hot reload, no auth
- `staging` - Info logging, no auth
- `production` - Warning logging, auth required
- `testing` - Debug logging, no telemetry

**Runtimes:**
- `local` - Native processes
- `docker` - Single container
- `docker_compose` - Multi-container
- `kubernetes` - K8s orchestrated
- `aws_ecs`, `aws_lambda`, `gcp_run`, `azure_container`

### 2. Orchestration Layer
**Location:** `backend/enterprise/orchestration_layer.py`

#### Secret Management
```python
from enterprise.orchestration_layer import get_orchestration_layer

orch = get_orchestration_layer()
api_key = orch.get_secret("API_KEY")
```

Supports:
- Environment variables
- File-based secrets
- HashiCorp Vault
- AWS Secrets Manager
- Azure Key Vault
- GCP Secret Manager

#### Distributed Tracing
```python
with orch.trace("operation_name") as span:
    # Your code here
    span.attributes["key"] = "value"
```

#### Circuit Breakers
```python
circuit = orch.mesh.get_circuit("service-name")
with circuit.call():
    # Protected call
    response = requests.get(endpoint)
```

States: `CLOSED` → `OPEN` → `HALF_OPEN` → `CLOSED`

#### Feature Flags
```python
if orch.is_feature_enabled("new_feature", user_id="user123"):
    # New feature code
```

Supports:
- Global toggles
- Percentage rollout
- User/group targeting
- A/B testing

#### Auto-Scaling
```python
orch.scaler.record_metrics(cpu_percent, memory_percent)
action, target = orch.scaler.get_scaling_decision()
if action == "scale_up":
    orch.scaler.apply_scaling(target)
```

### 3. Disaster Recovery
**Location:** `backend/enterprise/disaster_recovery.py`

#### Backup Management
```python
from enterprise.disaster_recovery import get_disaster_recovery

dr = get_disaster_recovery()

# Create backup
backup = dr.create_backup(BackupType.FULL)

# List backups
backups = dr.backup_manager.list_backups()

# Restore
dr.backup_manager.restore_backup(backup_id)
```

Backup types:
- `FULL` - Complete backup
- `INCREMENTAL` - Changes since last backup
- `DIFFERENTIAL` - Changes since last full
- `SNAPSHOT` - Point-in-time snapshot

#### Failover
```python
# Register targets
dr.failover_manager.register_target(FailoverTarget(
    name="backup-dc",
    url="https://backup.example.com",
    priority=1
))

# Trigger failover
dr.trigger_failover(reason="primary_down")
```

#### Recovery Testing
```python
# Test DR procedures
results = dr.test_recovery()
print(f"RPO Met: {results['rpo_met']}")
print(f"RTO Estimate: {results['rto_estimated_minutes']}min")
```

### 4. Compliance Manager
**Location:** `backend/enterprise/disaster_recovery.py`

#### Run Compliance Checks
```python
# Run all checks
results = dr.compliance_manager.run_all_checks()

# Run framework-specific
results = dr.compliance_manager.run_all_checks(
    framework=ComplianceFramework.SOC2
)
```

#### Generate Reports
```python
report = dr.compliance_manager.get_compliance_report(
    framework=ComplianceFramework.HIPAA
)
print(f"Compliance Rate: {report['summary']['compliance_rate']}%")
```

Frameworks supported:
- SOC2
- HIPAA
- GDPR
- PCI-DSS
- ISO27001

### 5. Chaos Engineering
**Location:** `backend/enterprise/orchestration_layer.py`

```python
# Enable chaos testing
orch.chaos.enabled = True
orch.chaos.set_failure_rate(0.1)  # 10% failure rate
orch.chaos.set_latency(100)       # 100ms added latency

# Use in code
with orch.chaos.chaos_context(service="api"):
    # May randomly fail or be delayed
    response = call_api()
```

## API Endpoints

### Environment
- `GET /api/enterprise/environment` - Current environment config
- `GET /api/enterprise/orchestration/status` - Orchestration status
- `GET /api/enterprise/orchestration/features` - Feature flags

### Disaster Recovery
- `GET /api/enterprise/dr/status` - DR status
- `GET /api/enterprise/dr/backups` - List backups
- `POST /api/enterprise/dr/backup` - Create backup
- `POST /api/enterprise/dr/restore` - Restore from backup

### Compliance
- `GET /api/enterprise/compliance/report` - Compliance report
- `POST /api/enterprise/compliance/check` - Run compliance checks

## Configuration

### Environment Variables

```bash
# Deployment
GRACE_STAGE=production          # development, staging, production, testing
GRACE_RUNTIME=kubernetes        # local, docker, kubernetes, aws_ecs, etc.

# Service URLs
GRACE_BACKEND_URL=http://backend:8000
QDRANT_URL=http://qdrant:6333
OLLAMA_URL=http://ollama:11434

# Features
GRACE_ENABLE_GPU=true
GRACE_ENABLE_CACHING=true
GRACE_MAX_WORKERS=8

# Secrets (Vault)
VAULT_ADDR=https://vault.example.com
VAULT_TOKEN=hvs.xxx
VAULT_PATH=secret/data/grace

# AWS Secrets Manager
AWS_REGION=us-east-1
```

### Config File
**Location:** `backend/enterprise/multi_os_config.json`

```json
{
  "services": {
    "backend": {
      "enabled": true,
      "port": 8000,
      "auto_start": true,
      "required": true
    },
    "qdrant": {
      "enabled": true,
      "port": 6333,
      "auto_start": true,
      "use_docker": true
    }
  },
  "startup_order": ["qdrant", "database", "backend", "frontend"]
}
```

## Deployment Scenarios

### Local Development
```bash
# Uses defaults
python -m launcher.launcher
```

### Docker Compose
```bash
docker-compose up -d
```

### Kubernetes
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: grace-backend
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: grace
        image: grace:latest
        env:
        - name: GRACE_STAGE
          value: production
        - name: GRACE_RUNTIME
          value: kubernetes
```

### Production Checklist

- [ ] Set `GRACE_STAGE=production`
- [ ] Configure secret provider (Vault/AWS/Azure)
- [ ] Set up failover targets
- [ ] Configure backup schedule
- [ ] Run compliance checks
- [ ] Test disaster recovery
- [ ] Enable monitoring/alerting
- [ ] Configure auto-scaling policies
