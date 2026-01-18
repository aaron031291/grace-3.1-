#!/usr/bin/env bash
# =============================================================================
# GRACE Enterprise Build Script (Linux/Mac)
# =============================================================================
# Usage:
#   ./scripts/build.sh              - Show help
#   ./scripts/build.sh install      - Install dependencies
#   ./scripts/build.sh dev          - Start development server
#   ./scripts/build.sh build        - Build for production
#   ./scripts/build.sh docker       - Build Docker containers
#   ./scripts/build.sh test         - Run all tests
# =============================================================================

set -e

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "\n${BLUE}$1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

show_help() {
    echo ""
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║               GRACE Enterprise Build System                  ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${GREEN}Installation:${NC}"
    echo "  ./build.sh install         Install production dependencies"
    echo "  ./build.sh install-dev     Install development dependencies"
    echo "  ./build.sh install-all     Install all dependencies"
    echo ""
    echo -e "${GREEN}Development:${NC}"
    echo "  ./build.sh dev             Start development server"
    echo "  ./build.sh run             Start production server"
    echo ""
    echo -e "${GREEN}Testing:${NC}"
    echo "  ./build.sh test            Run all tests"
    echo "  ./build.sh test-unit       Run unit tests only"
    echo "  ./build.sh test-coverage   Run tests with coverage"
    echo ""
    echo -e "${GREEN}Code Quality:${NC}"
    echo "  ./build.sh lint            Run linters"
    echo "  ./build.sh format          Format code"
    echo "  ./build.sh security        Run security scans"
    echo "  ./build.sh quality         Run all quality checks"
    echo ""
    echo -e "${GREEN}Build & Deploy:${NC}"
    echo "  ./build.sh build           Build Python package"
    echo "  ./build.sh docker          Build Docker containers"
    echo "  ./build.sh docker-up       Start Docker services"
    echo "  ./build.sh docker-down     Stop Docker services"
    echo ""
    echo -e "${GREEN}Maintenance:${NC}"
    echo "  ./build.sh clean           Clean build artifacts"
    echo "  ./build.sh update          Update dependencies"
    echo ""
}

do_install() {
    print_header "Installing Grace dependencies..."
    python -m pip install --upgrade pip setuptools wheel
    python -m pip install -e .
    print_success "Installation complete"
}

do_install_dev() {
    print_header "Installing Grace with development dependencies..."
    python -m pip install --upgrade pip setuptools wheel
    python -m pip install -e ".[dev]"
    pre-commit install || true
    print_success "Development installation complete"
}

do_install_all() {
    print_header "Installing Grace with all dependencies..."
    python -m pip install --upgrade pip setuptools wheel
    python -m pip install -e ".[all]"
    pre-commit install || true
    print_success "Full installation complete"
}

do_dev() {
    print_header "Starting Grace development server..."
    python -m launcher.launcher
}

do_run() {
    print_header "Starting Grace production server..."
    cd backend && uvicorn app:app --host 0.0.0.0 --port 8000
}

do_test() {
    print_header "Running all tests..."
    python -m pytest tests/ -v --tb=short
    print_success "All tests complete"
}

do_test_unit() {
    print_header "Running unit tests..."
    python -m pytest tests/ -v -m unit --tb=short
}

do_test_coverage() {
    print_header "Running tests with coverage..."
    python -m pytest tests/ -v --cov=backend --cov=launcher --cov-report=html --cov-report=term-missing
    print_success "Coverage report generated in htmlcov/"
}

do_lint() {
    print_header "Running linters..."
    python -m ruff check backend/ launcher/ --fix || true
    print_success "Linting complete"
}

do_format() {
    print_header "Formatting code..."
    python -m black backend/ launcher/ tests/
    python -m isort backend/ launcher/ tests/
    print_success "Formatting complete"
}

do_security() {
    print_header "Running security scans..."
    python -m bandit -r backend/ launcher/ -ll -f txt || true
    python -m safety check || true
    print_success "Security scan complete"
}

do_quality() {
    do_lint
    do_security
    print_success "All quality checks complete"
}

do_build() {
    print_header "Building Grace package..."
    python -m build
    print_success "Build complete - artifacts in dist/"
}

do_docker() {
    print_header "Building Docker containers..."
    docker-compose build
    print_success "Docker build complete"
}

do_docker_up() {
    print_header "Starting Docker services..."
    docker-compose up -d
    print_success "Services started"
    echo "  Backend: http://localhost:8000"
    echo "  Frontend: http://localhost:80"
}

do_docker_down() {
    print_header "Stopping Docker services..."
    docker-compose down
    print_success "Services stopped"
}

do_docker_logs() {
    docker-compose logs -f
}

do_clean() {
    print_header "Cleaning build artifacts..."
    rm -rf build/ dist/ *.egg-info/ .eggs/
    rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/
    rm -rf htmlcov/ .coverage coverage.xml
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    print_success "Clean complete"
}

do_update() {
    print_header "Updating dependencies..."
    python -m pip install --upgrade pip setuptools wheel
    python -m pip install --upgrade -e ".[all]"
    print_success "Dependencies updated"
}

# Main
case "${1:-help}" in
    help)           show_help ;;
    install)        do_install ;;
    install-dev)    do_install_dev ;;
    install-all)    do_install_all ;;
    dev)            do_dev ;;
    run)            do_run ;;
    test)           do_test ;;
    test-unit)      do_test_unit ;;
    test-coverage)  do_test_coverage ;;
    lint)           do_lint ;;
    format)         do_format ;;
    security)       do_security ;;
    quality)        do_quality ;;
    build)          do_build ;;
    docker)         do_docker ;;
    docker-up)      do_docker_up ;;
    docker-down)    do_docker_down ;;
    docker-logs)    do_docker_logs ;;
    clean)          do_clean ;;
    update)         do_update ;;
    *)              show_help ;;
esac
