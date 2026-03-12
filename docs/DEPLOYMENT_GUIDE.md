# GRACE Production Deployment Guide

Complete guide for deploying GRACE to production environments.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Quick Start (Docker)](#quick-start-docker)
3. [Manual Deployment](#manual-deployment)
4. [Configuration](#configuration)
5. [Security Hardening](#security-hardening)
6. [SSL/TLS Setup](#ssltls-setup)
7. [Reverse Proxy (Nginx)](#reverse-proxy-nginx)
8. [Database Setup](#database-setup)
9. [Monitoring](#monitoring)
10. [Backup & Recovery](#backup--recovery)
11. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Hardware Requirements
| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 4 cores | 8+ cores |
| RAM | 8 GB | 16+ GB |
| Storage | 50 GB SSD | 100+ GB NVMe |
| GPU (optional) | - | NVIDIA with 8GB+ VRAM |

### Software Requirements
- Docker 24.0+ and Docker Compose 2.20+
- OR Python 3.11+, Node.js 20+
- Git
- Nginx (for reverse proxy)
- Certbot (for SSL)

---

## Quick Start (Docker)

### 1. Clone and Configure
```bash
git clone <your-repo-url>   # e.g. clone this repo from your git host
cd grace

# Copy environment template
cp backend/.env.example backend/.env

# Edit configuration
nano backend/.env
```

### 2. Configure Environment
```bash
# backend/.env
PRODUCTION_MODE=true
DATABASE_TYPE=postgresql
DATABASE_HOST=postgres
DATABASE_USER=grace
DATABASE_PASSWORD=<strong-password>
OLLAMA_URL=http://ollama:11434
QDRANT_HOST=qdrant
```

### 3. Start Services
```bash
# Production with PostgreSQL
docker-compose --profile postgres up -d

# With Ollama (CPU)
docker-compose --profile postgres --profile with-ollama up -d

# With GPU support
docker-compose --profile postgres --profile gpu up -d
```

### 4. Verify Deployment
```bash
# Check service health
curl http://localhost:8000/health

# View logs
docker-compose logs -f backend
```

---

## Manual Deployment

### Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Run migrations
python -c "from database.migration import create_tables; create_tables()"

# Start with Gunicorn (production)
gunicorn app:app -w 4 -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --keep-alive 5 \
  --access-logfile - \
  --error-logfile -
```

### Frontend Setup
```bash
cd frontend

# Install dependencies
npm ci --production

# Build for production
npm run build

# Serve with nginx (see nginx section below)
```

---

## Configuration

### Environment Variables

| Variable | Description | Default | Production |
|----------|-------------|---------|------------|
| `PRODUCTION_MODE` | Enable production security | `false` | `true` |
| `DATABASE_TYPE` | Database type | `sqlite` | `postgresql` |
| `DATABASE_HOST` | Database host | `localhost` | DB server |
| `DATABASE_PASSWORD` | Database password | - | Required |
| `OLLAMA_URL` | Ollama service URL | `localhost:11434` | Service URL |
| `QDRANT_HOST` | Qdrant vector DB host | `localhost` | Service host |
| `CORS_ALLOWED_ORIGINS` | Allowed CORS origins | `*` | Your domain |
| `RATE_LIMIT_ENABLED` | Enable rate limiting | `true` | `true` |
| `LOG_LEVEL` | Logging level | `INFO` | `WARNING` |

### Secrets Management
```bash
# Use environment variables (not .env in production)
export DATABASE_PASSWORD=$(cat /run/secrets/db_password)
export QDRANT_API_KEY=$(cat /run/secrets/qdrant_key)

# Or use Docker secrets
docker secret create db_password ./secrets/db_password.txt
```

---

## Security Hardening

### 1. Network Security
```yaml
# docker-compose.override.yml
services:
  backend:
    networks:
      - internal
      - frontend
  postgres:
    networks:
      - internal  # Not exposed to frontend
  qdrant:
    networks:
      - internal

networks:
  internal:
    internal: true
  frontend:
```

### 2. Environment Hardening
```bash
# backend/.env
PRODUCTION_MODE=true
CORS_ALLOWED_ORIGINS=https://grace.yourdomain.com
RATE_LIMIT_ENABLED=true
RATE_LIMIT_DEFAULT=60/minute
RATE_LIMIT_AUTH=5/minute
SESSION_COOKIE_SECURE=true
```

### 3. File Permissions
```bash
# Restrict configuration files
chmod 600 backend/.env
chmod 700 backend/data

# Run as non-root
chown -R 1000:1000 backend/data
```

---

## SSL/TLS Setup

### Using Certbot (Let's Encrypt)
```bash
# Install certbot
apt install certbot python3-certbot-nginx

# Obtain certificate
certbot --nginx -d grace.yourdomain.com

# Auto-renewal (add to crontab)
0 0 * * * certbot renew --quiet
```

### Using Custom Certificates
```nginx
# /etc/nginx/sites-available/grace
server {
    listen 443 ssl http2;
    server_name grace.yourdomain.com;

    ssl_certificate /etc/ssl/certs/grace.crt;
    ssl_certificate_key /etc/ssl/private/grace.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;

    # HSTS
    add_header Strict-Transport-Security "max-age=63072000" always;
}
```

---

## Reverse Proxy (Nginx)

### Full Configuration
```nginx
# /etc/nginx/sites-available/grace

# Rate limiting
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=upload:10m rate=1r/s;

# Upstream servers
upstream grace_backend {
    server 127.0.0.1:8000;
    keepalive 32;
}

# HTTP -> HTTPS redirect
server {
    listen 80;
    server_name grace.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

# Main server block
server {
    listen 443 ssl http2;
    server_name grace.yourdomain.com;

    # SSL (managed by Certbot or custom)
    ssl_certificate /etc/letsencrypt/live/grace.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/grace.yourdomain.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';" always;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

    # Frontend (static files)
    location / {
        root /var/www/grace/dist;
        try_files $uri $uri/ /index.html;

        # Cache static assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # API proxy
    location /api/ {
        limit_req zone=api burst=20 nodelay;

        proxy_pass http://grace_backend/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 300s;

        # Buffering
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }

    # WebSocket
    location /ws/ {
        proxy_pass http://grace_backend/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }

    # SSE streaming
    location /stream/ {
        proxy_pass http://grace_backend/stream/;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400;
    }

    # File uploads
    location /api/file_management/upload {
        limit_req zone=upload burst=5 nodelay;
        client_max_body_size 100M;

        proxy_pass http://grace_backend/file_management/upload;
        proxy_http_version 1.1;
        proxy_request_buffering off;
    }

    # Health check (no rate limit)
    location /api/health {
        proxy_pass http://grace_backend/health;
    }
}
```

---

## Database Setup

### PostgreSQL
```bash
# Create database and user
sudo -u postgres psql

CREATE USER grace WITH PASSWORD 'your-secure-password';
CREATE DATABASE grace OWNER grace;
GRANT ALL PRIVILEGES ON DATABASE grace TO grace;

# Enable extensions
\c grace
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

### Backup Script
```bash
#!/bin/bash
# /opt/grace/backup.sh

BACKUP_DIR="/var/backups/grace"
DATE=$(date +%Y%m%d_%H%M%S)

# PostgreSQL backup
pg_dump -U grace -h localhost grace | gzip > "$BACKUP_DIR/db_$DATE.sql.gz"

# Qdrant backup (if using persistent storage)
tar -czf "$BACKUP_DIR/qdrant_$DATE.tar.gz" /var/lib/qdrant/storage

# Keep last 7 days
find "$BACKUP_DIR" -type f -mtime +7 -delete
```

---

## Monitoring

### Health Check Endpoint
```bash
# Comprehensive health check
curl -s http://localhost:8000/health | jq

# Response:
{
  "status": "healthy",
  "ollama_running": true,
  "models_available": 3,
  "database": "connected",
  "qdrant": "connected"
}
```

### Prometheus Metrics (if enabled)
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'grace'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

### Log Aggregation
```bash
# View logs
docker-compose logs -f --tail=100 backend

# Export to file
docker-compose logs backend > backend.log 2>&1
```

---

## Backup & Recovery

### Automated Backups
```bash
# Add to crontab
0 2 * * * /opt/grace/backup.sh
```

### Recovery Steps
```bash
# 1. Stop services
docker-compose down

# 2. Restore database
gunzip -c backup.sql.gz | psql -U grace -h localhost grace

# 3. Restore Qdrant data
tar -xzf qdrant_backup.tar.gz -C /var/lib/qdrant/

# 4. Restart services
docker-compose up -d
```

---

## Troubleshooting

### Common Issues

**Backend won't start**
```bash
# Check logs
docker-compose logs backend

# Verify database connection
docker-compose exec backend python -c "from database.connection import DatabaseConnection; print(DatabaseConnection().test_connection())"
```

**Ollama not responding**
```bash
# Check Ollama status
curl http://localhost:11434/api/tags

# Restart Ollama
docker-compose restart ollama
```

**High memory usage**
```bash
# Check container stats
docker stats

# Limit memory in docker-compose.yml
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 4G
```

**SSL certificate issues**
```bash
# Test certificate
openssl s_client -connect grace.yourdomain.com:443

# Renew certificate
certbot renew --force-renewal
```

---

## Quick Reference

### Commands
```bash
# Start production
docker-compose --profile postgres up -d

# View logs
docker-compose logs -f

# Restart service
docker-compose restart backend

# Scale workers
docker-compose up -d --scale backend=3

# Update deployment
git pull && docker-compose build && docker-compose up -d
```

### Ports
| Service | Internal | External |
|---------|----------|----------|
| Backend | 8000 | 8000 |
| Frontend | 80 | 80/443 |
| PostgreSQL | 5432 | - |
| Qdrant | 6333 | - |
| Ollama | 11434 | - |

---

*For additional support, see the [CONTRIBUTING.md](./CONTRIBUTING.md) or open an issue.*
