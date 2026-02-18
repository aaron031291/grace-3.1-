#!/bin/bash
# ============================================================================
# Grace 3.1 Bootstrap Script
# ============================================================================
# Starts all required services and seeds the system.
#
# Usage:
#   ./bootstrap.sh          # Full start (Qdrant + Backend + Frontend)
#   ./bootstrap.sh backend  # Backend only
#   ./bootstrap.sh check    # Check if services are running
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[GRACE]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err() { echo -e "${RED}[ERROR]${NC} $1"; }

# ============================================================================
# CHECK MODE
# ============================================================================
if [ "$1" = "check" ]; then
    echo "=== Grace System Health Check ==="
    
    # Check Qdrant
    if curl -sf http://localhost:6333/health > /dev/null 2>&1; then
        log "Qdrant: RUNNING"
    else
        err "Qdrant: NOT RUNNING (start with: docker run -d -p 6333:6333 qdrant/qdrant)"
    fi
    
    # Check Ollama
    if curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
        MODELS=$(curl -sf http://localhost:11434/api/tags | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('models',[])))" 2>/dev/null || echo "0")
        log "Ollama: RUNNING ($MODELS models)"
    else
        err "Ollama: NOT RUNNING (start with: ollama serve)"
    fi
    
    # Check Backend
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        log "Backend: RUNNING"
    else
        err "Backend: NOT RUNNING"
    fi
    
    # Check Frontend
    if curl -sf http://localhost:5173 > /dev/null 2>&1 || curl -sf http://localhost:80 > /dev/null 2>&1; then
        log "Frontend: RUNNING"
    else
        err "Frontend: NOT RUNNING"
    fi
    
    exit 0
fi

# ============================================================================
# STEP 1: Check prerequisites
# ============================================================================
log "Grace 3.1 Bootstrap Starting..."
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    err "Python 3 not found. Please install Python 3.10+"
    exit 1
fi
log "Python: $(python3 --version)"

# Check Docker (optional, for Qdrant)
if command -v docker &> /dev/null; then
    log "Docker: Available"
else
    warn "Docker not found. You'll need to run Qdrant manually."
fi

# ============================================================================
# STEP 2: Start Qdrant (Vector Database)
# ============================================================================
echo ""
log "--- Starting Qdrant Vector Database ---"

if curl -sf http://localhost:6333/health > /dev/null 2>&1; then
    log "Qdrant already running on port 6333"
else
    if command -v docker &> /dev/null; then
        log "Starting Qdrant via Docker..."
        docker run -d --name grace-qdrant -p 6333:6333 -p 6334:6334 \
            -v grace-qdrant-data:/qdrant/storage \
            qdrant/qdrant:latest 2>/dev/null || \
        docker start grace-qdrant 2>/dev/null || true
        
        # Wait for Qdrant to be ready
        for i in $(seq 1 30); do
            if curl -sf http://localhost:6333/health > /dev/null 2>&1; then
                log "Qdrant started successfully"
                break
            fi
            sleep 1
        done
    else
        warn "Please start Qdrant manually: docker run -d -p 6333:6333 qdrant/qdrant"
    fi
fi

# ============================================================================
# STEP 3: Check/Install Ollama
# ============================================================================
echo ""
log "--- Checking Ollama LLM Service ---"

if curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
    MODELS=$(curl -sf http://localhost:11434/api/tags | python3 -c "import sys,json; d=json.load(sys.stdin); print(', '.join(m['name'] for m in d.get('models',[])))" 2>/dev/null || echo "unknown")
    log "Ollama running with models: $MODELS"
else
    warn "Ollama not running."
    warn "To start: ollama serve"
    warn "To pull a model: ollama pull mistral:7b"
    warn "The system will work without Ollama but chat/reasoning won't function."
fi

# ============================================================================
# STEP 4: Install Backend Dependencies
# ============================================================================
echo ""
log "--- Installing Backend Dependencies ---"

cd "$BACKEND_DIR"

if [ -f requirements.txt ]; then
    pip3 install -q -r requirements.txt 2>/dev/null || \
    pip3 install -q fastapi uvicorn sqlalchemy pydantic numpy qdrant-client watchdog psutil dulwich filelock edge-tts 2>/dev/null
    log "Backend dependencies installed"
else
    pip3 install -q fastapi uvicorn sqlalchemy pydantic numpy qdrant-client watchdog psutil dulwich filelock 2>/dev/null
    log "Core dependencies installed"
fi

# ============================================================================
# STEP 5: Start Backend
# ============================================================================
echo ""
log "--- Starting Grace Backend ---"

if [ "$1" = "backend" ] || [ "$1" = "" ]; then
    cd "$BACKEND_DIR"
    
    # Create data directories
    mkdir -p data/magma
    mkdir -p "$SCRIPT_DIR/knowledge_base"
    
    log "Starting FastAPI server on port 8000..."
    log "Backend will auto-initialize:"
    log "  - Database tables"
    log "  - Embedding model"
    log "  - Component registry (200+ modules)"
    log "  - Handshake protocol"
    log "  - Unified intelligence daemon"
    log "  - Self-* closed-loop ecosystem"
    log "  - TimeSense governance"
    log "  - 24/7 learning pipeline"
    echo ""
    
    if [ "$1" = "backend" ]; then
        # Foreground mode
        python3 -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
    else
        # Background mode
        nohup python3 -m uvicorn app:app --host 0.0.0.0 --port 8000 > /tmp/grace-backend.log 2>&1 &
        BACKEND_PID=$!
        log "Backend started (PID: $BACKEND_PID, log: /tmp/grace-backend.log)"
        
        # Wait for backend to be ready
        for i in $(seq 1 60); do
            if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
                log "Backend is healthy!"
                break
            fi
            sleep 1
        done
    fi
fi

# ============================================================================
# STEP 6: Start Frontend (if not backend-only)
# ============================================================================
if [ "$1" = "" ]; then
    echo ""
    log "--- Starting Grace Frontend ---"
    
    cd "$FRONTEND_DIR"
    
    if [ ! -d "node_modules" ]; then
        log "Installing frontend dependencies..."
        npm install --silent 2>/dev/null || warn "npm install failed — frontend may not start"
    fi
    
    log "Starting Vite dev server on port 5173..."
    nohup npm run dev -- --host 0.0.0.0 > /tmp/grace-frontend.log 2>&1 &
    FRONTEND_PID=$!
    log "Frontend started (PID: $FRONTEND_PID, log: /tmp/grace-frontend.log)"
fi

# ============================================================================
# DONE
# ============================================================================
echo ""
echo "============================================================================"
log "Grace 3.1 Bootstrap Complete!"
echo "============================================================================"
echo ""
echo "  Backend:  http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo "  Frontend: http://localhost:5173"
echo "  Qdrant:   http://localhost:6333/dashboard"
echo ""
echo "  Check status: ./bootstrap.sh check"
echo ""
echo "  The system will auto-seed the knowledge base from files in knowledge_base/"
echo "  10 background daemons are now running autonomously."
echo "============================================================================"
