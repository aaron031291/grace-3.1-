# =============================================================================
# GRACE Enterprise Makefile
# =============================================================================
# Usage:
#   make help          - Show available commands
#   make install       - Install dependencies
#   make dev           - Start development server
#   make build         - Build for production
#   make docker        - Build Docker containers
#   make test          - Run all tests
# =============================================================================

.PHONY: help install dev build test lint format security docker clean

# Default target
.DEFAULT_GOAL := help

# Variables
PYTHON := python
PIP := pip
DOCKER_COMPOSE := docker-compose
PROJECT_NAME := grace

# Colors for terminal output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

# =============================================================================
# Help
# =============================================================================
help:
	@echo ""
	@echo "$(BLUE)╔══════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(BLUE)║               GRACE Enterprise Build System                  ║$(NC)"
	@echo "$(BLUE)╚══════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(GREEN)Installation:$(NC)"
	@echo "  make install         Install production dependencies"
	@echo "  make install-dev     Install development dependencies"
	@echo "  make install-all     Install all dependencies (dev + security + docs)"
	@echo ""
	@echo "$(GREEN)Development:$(NC)"
	@echo "  make dev             Start development server with auto-reload"
	@echo "  make run             Start production server"
	@echo "  make shell           Open Python shell with Grace context"
	@echo ""
	@echo "$(GREEN)Testing:$(NC)"
	@echo "  make test            Run all tests"
	@echo "  make test-unit       Run unit tests only"
	@echo "  make test-integration Run integration tests"
	@echo "  make test-e2e        Run end-to-end tests"
	@echo "  make test-coverage   Run tests with coverage report"
	@echo ""
	@echo "$(GREEN)Code Quality:$(NC)"
	@echo "  make lint            Run all linters"
	@echo "  make format          Format code with black and isort"
	@echo "  make typecheck       Run mypy type checker"
	@echo "  make security        Run security scans (bandit, safety)"
	@echo "  make quality         Run all quality checks"
	@echo ""
	@echo "$(GREEN)Build & Deploy:$(NC)"
	@echo "  make build           Build Python package"
	@echo "  make docker          Build Docker containers"
	@echo "  make docker-up       Start all Docker services"
	@echo "  make docker-down     Stop all Docker services"
	@echo "  make docker-logs     View Docker logs"
	@echo "  make docker-clean    Remove Docker containers and volumes"
	@echo ""
	@echo "$(GREEN)Maintenance:$(NC)"
	@echo "  make clean           Clean build artifacts"
	@echo "  make clean-all       Clean everything (including venv)"
	@echo "  make update          Update all dependencies"
	@echo ""

# =============================================================================
# Installation
# =============================================================================
install:
	@echo "$(BLUE)Installing Grace dependencies...$(NC)"
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -e .
	@echo "$(GREEN)✓ Installation complete$(NC)"

install-dev:
	@echo "$(BLUE)Installing Grace with development dependencies...$(NC)"
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -e ".[dev]"
	pre-commit install || true
	@echo "$(GREEN)✓ Development installation complete$(NC)"

install-all:
	@echo "$(BLUE)Installing Grace with all dependencies...$(NC)"
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -e ".[all]"
	pre-commit install || true
	@echo "$(GREEN)✓ Full installation complete$(NC)"

# =============================================================================
# Development
# =============================================================================
dev:
	@echo "$(BLUE)Starting Grace development server...$(NC)"
	$(PYTHON) -m launcher.launcher

run:
	@echo "$(BLUE)Starting Grace production server...$(NC)"
	cd backend && uvicorn app:app --host 0.0.0.0 --port 8000

shell:
	@echo "$(BLUE)Opening Grace Python shell...$(NC)"
	$(PYTHON) -c "import backend; import launcher; print('Grace modules loaded')" && ipython

# =============================================================================
# Testing
# =============================================================================
test:
	@echo "$(BLUE)Running all tests...$(NC)"
	$(PYTHON) -m pytest tests/ -v --tb=short
	@echo "$(GREEN)✓ All tests complete$(NC)"

test-unit:
	@echo "$(BLUE)Running unit tests...$(NC)"
	$(PYTHON) -m pytest tests/ -v -m unit --tb=short

test-integration:
	@echo "$(BLUE)Running integration tests...$(NC)"
	$(PYTHON) -m pytest tests/ -v -m integration --tb=short

test-e2e:
	@echo "$(BLUE)Running end-to-end tests...$(NC)"
	$(PYTHON) -m pytest tests/ -v -m e2e --tb=short

test-coverage:
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	$(PYTHON) -m pytest tests/ -v --cov=backend --cov=launcher --cov-report=html --cov-report=term-missing
	@echo "$(GREEN)✓ Coverage report generated in htmlcov/$(NC)"

# =============================================================================
# Code Quality
# =============================================================================
lint:
	@echo "$(BLUE)Running linters...$(NC)"
	$(PYTHON) -m ruff check backend/ launcher/ --fix
	$(PYTHON) -m ruff check backend/ launcher/
	@echo "$(GREEN)✓ Linting complete$(NC)"

format:
	@echo "$(BLUE)Formatting code...$(NC)"
	$(PYTHON) -m black backend/ launcher/ tests/
	$(PYTHON) -m isort backend/ launcher/ tests/
	@echo "$(GREEN)✓ Formatting complete$(NC)"

typecheck:
	@echo "$(BLUE)Running type checker...$(NC)"
	$(PYTHON) -m mypy backend/ launcher/ --ignore-missing-imports
	@echo "$(GREEN)✓ Type checking complete$(NC)"

security:
	@echo "$(BLUE)Running security scans...$(NC)"
	$(PYTHON) -m bandit -r backend/ launcher/ -ll -f txt || true
	$(PYTHON) -m safety check || true
	@echo "$(GREEN)✓ Security scan complete$(NC)"

quality: lint typecheck security
	@echo "$(GREEN)✓ All quality checks complete$(NC)"

# =============================================================================
# Build & Deploy
# =============================================================================
build:
	@echo "$(BLUE)Building Grace package...$(NC)"
	$(PYTHON) -m build
	@echo "$(GREEN)✓ Build complete - artifacts in dist/$(NC)"

docker:
	@echo "$(BLUE)Building Docker containers...$(NC)"
	$(DOCKER_COMPOSE) build
	@echo "$(GREEN)✓ Docker build complete$(NC)"

docker-up:
	@echo "$(BLUE)Starting Docker services...$(NC)"
	$(DOCKER_COMPOSE) up -d
	@echo "$(GREEN)✓ Services started$(NC)"
	@echo "  Backend: http://localhost:8000"
	@echo "  Frontend: http://localhost:80"

docker-down:
	@echo "$(BLUE)Stopping Docker services...$(NC)"
	$(DOCKER_COMPOSE) down
	@echo "$(GREEN)✓ Services stopped$(NC)"

docker-logs:
	$(DOCKER_COMPOSE) logs -f

docker-clean:
	@echo "$(YELLOW)Removing Docker containers and volumes...$(NC)"
	$(DOCKER_COMPOSE) down -v --rmi local
	@echo "$(GREEN)✓ Docker cleanup complete$(NC)"

# =============================================================================
# Maintenance
# =============================================================================
clean:
	@echo "$(BLUE)Cleaning build artifacts...$(NC)"
	rm -rf build/ dist/ *.egg-info/ .eggs/
	rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/
	rm -rf htmlcov/ .coverage coverage.xml
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "$(GREEN)✓ Clean complete$(NC)"

clean-all: clean
	@echo "$(YELLOW)Removing virtual environment...$(NC)"
	rm -rf .venv/ venv/
	@echo "$(GREEN)✓ Full clean complete$(NC)"

update:
	@echo "$(BLUE)Updating dependencies...$(NC)"
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install --upgrade -e ".[all]"
	@echo "$(GREEN)✓ Dependencies updated$(NC)"
