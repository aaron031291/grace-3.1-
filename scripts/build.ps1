# =============================================================================
# GRACE Enterprise Build Script (Windows PowerShell)
# =============================================================================
# Usage:
#   .\scripts\build.ps1              - Show help
#   .\scripts\build.ps1 install      - Install dependencies
#   .\scripts\build.ps1 dev          - Start development server
#   .\scripts\build.ps1 build        - Build for production
#   .\scripts\build.ps1 docker       - Build Docker containers
#   .\scripts\build.ps1 test         - Run all tests
# =============================================================================

param(
    [Parameter(Position=0)]
    [string]$Command = "help"
)

$Blue = [ConsoleColor]::Cyan
$Green = [ConsoleColor]::Green
$Yellow = [ConsoleColor]::Yellow

switch ($Command) {
    "help" {
        Write-Host ""
        Write-Host "==============================================================" -ForegroundColor $Blue
        Write-Host "             GRACE Enterprise Build System                    " -ForegroundColor $Blue
        Write-Host "==============================================================" -ForegroundColor $Blue
        Write-Host ""
        Write-Host "Installation:" -ForegroundColor $Green
        Write-Host "  .\build.ps1 install         Install production dependencies"
        Write-Host "  .\build.ps1 install-dev     Install development dependencies"
        Write-Host ""
        Write-Host "Development:" -ForegroundColor $Green
        Write-Host "  .\build.ps1 dev             Start development server"
        Write-Host "  .\build.ps1 run             Start production server"
        Write-Host ""
        Write-Host "Testing:" -ForegroundColor $Green
        Write-Host "  .\build.ps1 test            Run all tests"
        Write-Host "  .\build.ps1 test-coverage   Run tests with coverage"
        Write-Host ""
        Write-Host "Code Quality:" -ForegroundColor $Green
        Write-Host "  .\build.ps1 lint            Run linters"
        Write-Host "  .\build.ps1 format          Format code"
        Write-Host "  .\build.ps1 security        Run security scans"
        Write-Host ""
        Write-Host "Build & Deploy:" -ForegroundColor $Green
        Write-Host "  .\build.ps1 build           Build Python package"
        Write-Host "  .\build.ps1 docker          Build Docker containers"
        Write-Host "  .\build.ps1 docker-up       Start Docker services"
        Write-Host "  .\build.ps1 docker-down     Stop Docker services"
        Write-Host ""
        Write-Host "Maintenance:" -ForegroundColor $Green
        Write-Host "  .\build.ps1 clean           Clean build artifacts"
        Write-Host "  .\build.ps1 update          Update dependencies"
        Write-Host ""
    }
    "install" {
        Write-Host "Installing Grace dependencies..." -ForegroundColor $Blue
        python -m pip install --upgrade pip setuptools wheel
        python -m pip install -e .
        Write-Host "Done!" -ForegroundColor $Green
    }
    "install-dev" {
        Write-Host "Installing Grace with development dependencies..." -ForegroundColor $Blue
        python -m pip install --upgrade pip setuptools wheel
        python -m pip install -e ".[dev]"
        Write-Host "Done!" -ForegroundColor $Green
    }
    "install-all" {
        Write-Host "Installing Grace with all dependencies..." -ForegroundColor $Blue
        python -m pip install --upgrade pip setuptools wheel
        python -m pip install -e ".[all]"
        Write-Host "Done!" -ForegroundColor $Green
    }
    "dev" {
        Write-Host "Starting Grace development server..." -ForegroundColor $Blue
        python -m launcher.launcher
    }
    "run" {
        Write-Host "Starting Grace production server..." -ForegroundColor $Blue
        Push-Location backend
        uvicorn app:app --host 0.0.0.0 --port 8000
        Pop-Location
    }
    "test" {
        Write-Host "Running all tests..." -ForegroundColor $Blue
        python -m pytest tests/ -v --tb=short
        Write-Host "Done!" -ForegroundColor $Green
    }
    "test-coverage" {
        Write-Host "Running tests with coverage..." -ForegroundColor $Blue
        python -m pytest tests/ -v --cov=backend --cov=launcher --cov-report=html --cov-report=term-missing
        Write-Host "Coverage report in htmlcov/" -ForegroundColor $Green
    }
    "lint" {
        Write-Host "Running linters..." -ForegroundColor $Blue
        python -m ruff check backend/ launcher/ --fix
        Write-Host "Done!" -ForegroundColor $Green
    }
    "format" {
        Write-Host "Formatting code..." -ForegroundColor $Blue
        python -m black backend/ launcher/ tests/
        python -m isort backend/ launcher/ tests/
        Write-Host "Done!" -ForegroundColor $Green
    }
    "security" {
        Write-Host "Running security scans..." -ForegroundColor $Blue
        python -m bandit -r backend/ launcher/ -ll -f txt
        python -m safety check
        Write-Host "Done!" -ForegroundColor $Green
    }
    "build" {
        Write-Host "Building Grace package..." -ForegroundColor $Blue
        python -m build
        Write-Host "Build complete - artifacts in dist/" -ForegroundColor $Green
    }
    "docker" {
        Write-Host "Building Docker containers..." -ForegroundColor $Blue
        docker-compose build
        Write-Host "Done!" -ForegroundColor $Green
    }
    "docker-up" {
        Write-Host "Starting Docker services..." -ForegroundColor $Blue
        docker-compose up -d
        Write-Host "Services started at http://localhost:8000" -ForegroundColor $Green
    }
    "docker-down" {
        Write-Host "Stopping Docker services..." -ForegroundColor $Blue
        docker-compose down
        Write-Host "Done!" -ForegroundColor $Green
    }
    "docker-logs" {
        docker-compose logs -f
    }
    "clean" {
        Write-Host "Cleaning build artifacts..." -ForegroundColor $Blue
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue build, dist, *.egg-info, .eggs
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue .pytest_cache, .mypy_cache, .ruff_cache
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue htmlcov, .coverage, coverage.xml
        Get-ChildItem -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "Done!" -ForegroundColor $Green
    }
    "update" {
        Write-Host "Updating dependencies..." -ForegroundColor $Blue
        python -m pip install --upgrade pip setuptools wheel
        python -m pip install --upgrade -e ".[all]"
        Write-Host "Done!" -ForegroundColor $Green
    }
    default {
        Write-Host "Unknown command: $Command" -ForegroundColor $Yellow
        Write-Host "Run '.\build.ps1 help' for usage information."
    }
}
