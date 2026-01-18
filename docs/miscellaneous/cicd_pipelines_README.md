# Genesis CI/CD Pipelines

Self-hosted CI/CD pipeline system powered by Genesis Keys.

## Overview

GRACE includes a fully autonomous CI/CD system that doesn't rely on external services like GitHub Actions. All pipeline executions are tracked using Genesis Keys for complete auditability.

## Available Pipelines

### 1. GRACE CI Pipeline (`grace-ci`)
Main continuous integration pipeline that runs on every push and pull request.

**Stages:**
- Checkout
- Install Backend & Frontend Dependencies
- Lint (Python flake8, JS ESLint)
- Test (pytest, Jest)
- Security Scan (bandit, safety)
- Build Frontend

**Triggers:** `push`, `pull_request`
**Branches:** `main`, `develop`, `feature/*`, `fix/*`

### 2. GRACE Quick Check (`grace-quick`)
Fast validation pipeline for immediate feedback.

**Stages:**
- Quick Lint (syntax check)
- Quick Test (import check)

**Triggers:** `push`
**Branches:** `*` (all)

### 3. GRACE Deployment (`grace-deploy`)
Production deployment pipeline.

**Stages:**
- Pre-deployment Validation
- Run Critical Tests
- Build Docker Images
- Push to Registry
- Deploy with Docker Compose
- Health Check

**Triggers:** `manual` only
**Branches:** `main` only

## API Endpoints

### Trigger a Pipeline
```bash
curl -X POST http://localhost:8000/api/cicd/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "pipeline_id": "grace-ci",
    "branch": "main"
  }'
```

### List Pipeline Runs
```bash
curl http://localhost:8000/api/cicd/runs
```

### Get Run Details
```bash
curl http://localhost:8000/api/cicd/runs/{run_id}
```

### View Run Logs
```bash
curl http://localhost:8000/api/cicd/runs/{run_id}/logs
```

### Cancel a Run
```bash
curl -X POST http://localhost:8000/api/cicd/runs/{run_id}/cancel
```

### Webhook Endpoint
```bash
# Configure your Git server to POST to:
http://localhost:8000/api/cicd/webhook
```

## Genesis Key Tracking

Every CI/CD operation generates a Genesis Key for tracking:

| Action | Key Format |
|--------|------------|
| Pipeline Trigger | `gk-cicd-{hash}` |
| Stage Execution | `gk-cicd-{hash}` |
| Pipeline Complete | `gk-cicd-{hash}` |
| Webhook Received | `gk-cicd-{hash}` |

View all keys:
```bash
curl http://localhost:8000/api/cicd/genesis-keys
```

## Autonomous Actions

Pipelines can be triggered autonomously:

1. **Webhook Integration** - Configure your Git server to send webhooks
2. **Scheduled Runs** - Use the proactive learning system to schedule
3. **Event-Based** - Trigger based on file changes or system events
4. **Manual** - Trigger from the UI or API

## Creating Custom Pipelines

```yaml
id: my-custom-pipeline
name: My Custom Pipeline
description: Custom pipeline description

triggers:
  - push
  - manual

branches:
  - main
  - develop

stages:
  - name: my-stage
    type: custom
    commands:
      - echo "Running custom commands"
      - ./my-script.sh
    timeout_seconds: 300
    depends_on: []
```

Register via API:
```bash
curl -X POST http://localhost:8000/api/cicd/pipelines \
  -H "Content-Type: application/json" \
  -d @my-pipeline.json
```
