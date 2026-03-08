#!/bin/bash
# =============================================================================
# GRACE Unified Start Script (Unix/Mac/WSL)
# =============================================================================
# Starts both backend (FastAPI) and frontend (Vite) servers
# Usage: ./start.sh [backend|frontend|all|full|staged|services]
#   all     - Backend + Frontend (3s between) [default]
#   full    - Same as all
#   staged  - 1st runtime (backend) 30s ahead, 2nd (frontend) merges 15s behind
#   services - Qdrant only
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
if [[ ! "$MODE" =~ ^(all|full|staged|services|backend|frontend)$ ]]; then
    echo -e "${RED}Invalid mode: $MODE${NC}"
    echo "Usage: ./start.sh [backend|frontend|all|full|staged|services]"
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

start_staged() {
    # 1st runtime 30s ahead, 2nd run merges 15s behind (preflight-friendly)
    echo -e "${YELLOW}Starting GRACE (staged: 1st runtime 30s ahead, 2nd merges 15s behind)...${NC}"
    echo ""

    echo -e "${GREEN}[1st runtime] Backend starting (30s head start)...${NC}"
    cd "$BACKEND_DIR"
    if [ -f "venv_gpu/bin/activate" ] || [ -f "venv_gpu/Scripts/activate" ]; then
        [ -f "venv_gpu/bin/activate" ] && source venv_gpu/bin/activate || source venv_gpu/Scripts/activate
    elif [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    elif [ -f "venv/Scripts/activate" ]; then
        source venv/Scripts/activate
    fi
    python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000 &
    BACKEND_PID=$!

    echo "  Waiting 30s so backend gets head start..."
    sleep 30

    echo -e "${GREEN}[2nd run] Frontend starting (merges 15s behind)...${NC}"
    cd "$FRONTEND_DIR"
    npm run dev &
    FRONTEND_PID=$!

    echo "  Waiting 15s for merge..."
    sleep 15

    echo ""
    echo -e "${CYAN}==============================================================================${NC}"
    echo -e "${GREEN}Merge complete. GRACE System Started!${NC}"
    echo -e "${CYAN}==============================================================================${NC}"
    echo ""
    echo "  Backend:  http://localhost:8000"
    echo "  Frontend: http://localhost:5173"
    echo ""
    echo -e "${YELLOW}Press Ctrl+C to stop all services.${NC}"
    echo ""

    wait
}

ensure_qdrant() {
    if [ -f "$BACKEND_DIR/.env" ] && grep -q "QDRANT_URL=https" "$BACKEND_DIR/.env" 2>/dev/null; then
        echo -e "${GREEN}[OK] Qdrant Cloud configured.${NC}"
        return 0
    fi
    if ! command -v docker &>/dev/null; then
        echo -e "${YELLOW}[WARN] Docker not running. Backend will use Qdrant Cloud if set.${NC}"
        return 0
    fi
    if docker ps --filter "name=qdrant" --format "{{.Names}}" 2>/dev/null | grep -q .; then
        echo -e "${GREEN}[OK] Qdrant already running.${NC}"
        return 0
    fi
    echo "Starting Qdrant (vector DB)..."
    docker run -d -p 6333:6333 -p 6334:6334 --name qdrant qdrant/qdrant:latest 2>/dev/null || docker start qdrant 2>/dev/null
    echo "Waiting for Qdrant (5s)..."
    sleep 5
}

start_services() {
    ensure_qdrant
}

# =============================================================================
# Main execution
# =============================================================================

case "$MODE" in
    all|full)
        ensure_qdrant
        start_all
        ;;
    staged)
        ensure_qdrant
        start_staged
        ;;
    services)
        start_services
        ;;
    backend)
        start_backend
        ;;
    frontend)
        start_frontend
        ;;
esac
