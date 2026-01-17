#!/bin/bash
# =============================================================================
# GRACE Unified Start Script (Unix/Mac/WSL)
# =============================================================================
# Starts both backend (FastAPI) and frontend (Vite) servers
# Usage: ./start.sh [backend|frontend|all]
# Default: all (starts both)
# =============================================================================

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
MODE="${1:-all}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}==============================================================================${NC}"
echo -e "${CYAN}                         GRACE System Startup                                ${NC}"
echo -e "${CYAN}==============================================================================${NC}"
echo ""

# Validate mode
if [[ ! "$MODE" =~ ^(all|backend|frontend)$ ]]; then
    echo -e "${RED}Invalid mode: $MODE${NC}"
    echo "Usage: ./start.sh [backend|frontend|all]"
    exit 1
fi

# Cleanup function to kill background processes on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down GRACE services...${NC}"
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    echo -e "${GREEN}GRACE services stopped.${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# =============================================================================
# Start functions
# =============================================================================

start_backend() {
    echo -e "${GREEN}Starting Backend (FastAPI)...${NC}"
    cd "$BACKEND_DIR"

    # Activate virtual environment
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    elif [ -f "venv/Scripts/activate" ]; then
        source venv/Scripts/activate
    else
        echo -e "${YELLOW}Warning: Virtual environment not found. Using system Python.${NC}"
    fi

    echo -e "${CYAN}Backend server starting on http://localhost:8000${NC}"
    python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
}

start_frontend() {
    echo -e "${GREEN}Starting Frontend (Vite)...${NC}"
    cd "$FRONTEND_DIR"
    echo -e "${CYAN}Frontend server starting on http://localhost:5173${NC}"
    npm run dev
}

start_all() {
    echo -e "${YELLOW}Starting GRACE in full-stack mode...${NC}"
    echo ""

    # Start backend in background
    echo -e "${GREEN}[1/2] Starting Backend (FastAPI)...${NC}"
    cd "$BACKEND_DIR"

    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    elif [ -f "venv/Scripts/activate" ]; then
        source venv/Scripts/activate
    fi

    python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000 &
    BACKEND_PID=$!

    # Wait for backend to start
    sleep 3

    # Start frontend in background
    echo -e "${GREEN}[2/2] Starting Frontend (Vite)...${NC}"
    cd "$FRONTEND_DIR"
    npm run dev &
    FRONTEND_PID=$!

    echo ""
    echo -e "${CYAN}==============================================================================${NC}"
    echo -e "${GREEN}GRACE System Started Successfully!${NC}"
    echo -e "${CYAN}==============================================================================${NC}"
    echo ""
    echo "  Backend API:  http://localhost:8000"
    echo "  Frontend UI:  http://localhost:5173"
    echo "  API Docs:     http://localhost:8000/docs"
    echo ""
    echo -e "${YELLOW}Press Ctrl+C to stop all services.${NC}"
    echo ""

    # Wait for both processes
    wait
}

# =============================================================================
# Main execution
# =============================================================================

case "$MODE" in
    all)
        start_all
        ;;
    backend)
        start_backend
        ;;
    frontend)
        start_frontend
        ;;
esac
