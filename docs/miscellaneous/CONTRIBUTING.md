# Contributing to GRACE

Thank you for your interest in contributing to GRACE! This document provides guidelines and information for contributors.

## Table of Contents
- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Submitting Changes](#submitting-changes)
- [Style Guidelines](#style-guidelines)
- [Testing](#testing)

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for everyone.

## Getting Started

1. Fork the repository
2. Clone your fork locally
3. Set up the development environment
4. Create a new branch for your changes

## Development Setup

### Prerequisites
- Python 3.11+
- Node.js 20+
- Docker (optional)
- Git

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Frontend Setup
```bash
cd frontend
npm install
```

### Running Locally
```bash
# Terminal 1 - Backend
cd backend
uvicorn app:app --reload --port 8000

# Terminal 2 - Frontend
cd frontend
npm run dev
```

Or use Docker:
```bash
docker-compose up -d
```

## Making Changes

### Branch Naming
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation changes
- `refactor/` - Code refactoring
- `test/` - Test additions/changes

Example: `feature/add-voice-recognition`

### Commit Messages
Follow conventional commits:
```
type(scope): description

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Example:
```
feat(cognitive): add contradiction detection

Implement semantic contradiction detection using NLI model.
Supports detecting conflicts in ingested documents.

Closes #123
```

## Submitting Changes

1. Push your branch to your fork
2. Create a Pull Request against `main`
3. Fill out the PR template completely
4. Wait for CI checks to pass
5. Address any review feedback

## Style Guidelines

### Python (Backend)
- Follow PEP 8
- Use type hints
- Maximum line length: 120 characters
- Use Black for formatting
- Use isort for import sorting

```bash
black .
isort .
flake8 .
mypy .
```

### JavaScript/React (Frontend)
- Use ESLint configuration
- Use functional components with hooks
- Use meaningful component names

```bash
npm run lint
```

## Testing

### Backend Tests
```bash
cd backend
pytest tests/ -v --cov=.
```

### Frontend Tests
```bash
cd frontend
npm test
```

### Running All Tests
```bash
# From root directory
./run_tests.sh
```

## Questions?

If you have questions, please:
1. Check existing issues
2. Open a new issue with the question label
3. Join discussions in existing PRs

Thank you for contributing!
