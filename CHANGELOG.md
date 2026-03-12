# Changelog

All notable changes to GRACE will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Prometheus metrics endpoint (`/metrics`)
- Grafana dashboard templates
- Structured JSON logging
- Kubernetes deployment manifests
- Service worker for offline support
- Zustand state management
- Redis caching layer

### Changed
- Improved error handling across all API endpoints
- Enhanced WebSocket connection management

### Fixed
- CI pipeline lint errors
- Missing imports in various modules

## [3.1.1] - 2026-03-12

### Added
- Created `USAGE.md` for client onboarding.

### Changed
- Migrated deprecated `datetime.utcnow()` to timezone-aware UTC timestamps system-wide.
- Hardened React 19 frontend by resolving all remaining linting warnings, dead code, and fast-refresh issues.

### Fixed
- Resolved SQLite `sa_savepoint_4` database errors within the Genesis tracking system.
- Fixed 500 Internal Server Errors in multi-tier RAG retrieval and chat endpoints.
- Patched Qwen Model Pool initialization parameters and permissions.
- Fixed test docstring syntax causing skips in pytest.

## [3.1.0] - 2026-01-14

### Added
- **P1 (Critical) Features**
  - Docker support (Dockerfiles for backend and frontend)
  - `docker-compose.yml` for full stack deployment
  - CI/CD pipelines (`.github/workflows/ci.yml`, `cd.yml`)
  - Security test suite (`test_security.py`, `test_rate_limiting.py`)
  - GitHub issue and PR templates
  - `CONTRIBUTING.md` guide
  - `.editorconfig` for consistent formatting

- **P2 (Important) Features**
  - SSE streaming chat responses (`api/streaming.py`)
  - WebSocket real-time updates (`api/websocket.py`)
  - React Error Boundaries
  - Toast notification system
  - Skeleton loading states
  - Comprehensive health checks (`api/health.py`)
  - Load/stress testing framework (`test_load.py`)
  - Production deployment guide (`DEPLOYMENT_GUIDE.md`)

### Security
- Added rate limiting middleware
- Implemented security headers
- Added input validation and sanitization
- SQL injection protection tests
- XSS protection tests

## [3.0.0] - 2026-01-01

### Added
- **Core Systems**
  - Cognitive layer with contradiction detection
  - Learning memory with pattern extraction
  - Agent framework for autonomous tasks
  - Three-pillar governance system
  - ML Intelligence module (neural trust, bandits, meta-learning)
  - Sandbox Lab for experimentation

- **API Endpoints**
  - 32 API modules with comprehensive endpoints
  - Voice API (STT/TTS integration)
  - Notion task management API
  - Codebase browser API
  - Knowledge base connectors
  - KPI dashboard API
  - Proactive learning API
  - Repository management API
  - Telemetry and monitoring API

- **Frontend Components**
  - 34 React components
  - File browser with upload/download
  - Chat interface with markdown support
  - Dashboard with real-time metrics
  - Settings and preferences management
  - Learning memory visualization

### Changed
- Upgraded to React 19
- Migrated to FastAPI from Flask
- Switched to Qdrant for vector storage
- Updated Ollama client for latest API

### Fixed
- Memory leaks in long-running processes
- Connection pooling issues
- File upload size limits

## [2.0.0] - 2025-06-01

### Added
- Initial RAG (Retrieval-Augmented Generation) pipeline
- Document ingestion system
- Basic chat interface
- PostgreSQL database integration
- Ollama LLM integration

### Changed
- Complete architecture redesign
- Moved to microservices approach

## [1.0.0] - 2025-01-01

### Added
- Initial release
- Basic chat functionality
- Simple document storage
- SQLite database

---

## Version History Summary

| Version | Date | Highlights |
|---------|------|------------|
| 3.1.1 | 2026-03-12 | Enterprise stabilization, Genesis fixes, Lint cleanup |
| 3.1.0 | 2026-01-14 | Production readiness (Docker, CI/CD, Security) |
| 3.0.0 | 2026-01-01 | Major feature expansion (Cognitive, Learning, Agent) |
| 2.0.0 | 2025-06-01 | RAG pipeline, Document ingestion |
| 1.0.0 | 2025-01-01 | Initial release |

## Upgrade Notes

### 3.0.x to 3.1.x

1. **Docker Migration**: If previously running without Docker, review `docker-compose.yml` for service configuration.

2. **Environment Variables**: New variables required:
   ```
   CORS_ALLOWED_ORIGINS=http://localhost:3000
   RATE_LIMIT_ENABLED=true
   JWT_SECRET=your-secret-key
   ```

3. **Database**: No schema changes, but run migrations:
   ```bash
   python -m alembic upgrade head
   ```

### 2.x to 3.x

1. **Breaking Changes**:
   - API endpoint paths changed from `/v2/` to `/api/`
   - Authentication now uses JWT instead of API keys
   - Vector DB migrated from Pinecone to Qdrant

2. **Data Migration**:
   ```bash
   python scripts/migrate_to_v3.py
   ```

3. **Configuration**:
   - Review `settings.py` for new configuration options
   - Update `.env` with new required variables

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:
- Reporting bugs
- Suggesting features
- Submitting pull requests
- Code style requirements

## Links

- [Documentation](docs/README.md)
- [API Reference](docs/API.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Deployment Guide](DEPLOYMENT_GUIDE.md)
