# DevOps, Docker & Deployment Guide

## Docker

### Dockerfile Best Practices
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose
```yaml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    depends_on:
      qdrant: { condition: service_healthy }
    environment:
      - DATABASE_TYPE=sqlite
      - QDRANT_HOST=qdrant
      - OLLAMA_URL=http://ollama:11434
  
  frontend:
    build: ./frontend
    ports: ["80:80"]
  
  qdrant:
    image: qdrant/qdrant:latest
    ports: ["6333:6333"]
    volumes: ["qdrant-data:/qdrant/storage"]
  
  ollama:
    image: ollama/ollama:latest
    ports: ["11434:11434"]
    volumes: ["ollama-data:/root/.ollama"]
```

## CI/CD Pipelines

### Pipeline Stages
1. **Checkout**: Get source code
2. **Install**: Install dependencies
3. **Lint**: Check code quality (ruff, eslint)
4. **Test**: Run test suites
5. **Build**: Create deployable artifacts
6. **Security**: Scan for vulnerabilities
7. **Deploy**: Push to environment

### GitHub Actions
```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -r requirements.txt
      - run: pytest --tb=short -q
```

## System Administration

### Process Management
- **systemd**: Linux service management
- **supervisor**: Process control system
- **PM2**: Node.js process manager

### Monitoring
- Health checks: `/health` endpoint every 30s
- Metrics: Prometheus + Grafana
- Logs: Structured JSON logging
- Alerts: Threshold-based notifications

### Backup Strategy
- Database: Daily automated backups
- Vector DB: Qdrant snapshots
- Knowledge base: Git-tracked files
- Config: Version-controlled settings
