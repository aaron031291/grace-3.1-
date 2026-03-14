#!/bin/bash
#
# Grace Startup Script — One command to start everything
#
# Usage:
#   ./start_grace.sh          # Normal start
#   ./start_grace.sh --setup  # First-time setup (pulls models, creates DB)
#   ./start_grace.sh --test   # Start + run smoke test
#
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

echo "=========================================="
echo "  Grace Autonomous AI System"
echo "=========================================="
echo ""

# ── Check prerequisites ──────────────────────────────────────────────

echo "[1/8] Checking prerequisites..."

# Python
if ! command -v python3 &> /dev/null; then
    echo "  ❌ Python3 not found. Install Python 3.11+"
    exit 1
fi
echo "  ✅ Python: $(python3 --version)"

# Node
if ! command -v node &> /dev/null; then
    echo "  ⚠️ Node.js not found — frontend won't build"
else
    echo "  ✅ Node: $(node --version)"
fi

# Ollama
if ! command -v ollama &> /dev/null; then
    echo "  ⚠️ Ollama not found — local models won't work"
    echo "     Install: curl -fsSL https://ollama.com/install.sh | sh"
else
    echo "  ✅ Ollama: $(ollama --version 2>/dev/null || echo 'installed')"
fi

# GPU
if command -v nvidia-smi &> /dev/null; then
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)
    GPU_MEM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader 2>/dev/null | head -1)
    echo "  ✅ GPU: $GPU_NAME ($GPU_MEM)"
else
    echo "  ⚠️ No GPU detected — will use CPU (slower)"
fi

# ── Setup mode ────────────────────────────────────────────────────────

if [ "$1" == "--setup" ]; then
    echo ""
    echo "[SETUP] First-time setup..."
    echo ""

    # Python venv
    if [ ! -d "$BACKEND_DIR/venv" ]; then
        echo "  Creating Python virtual environment..."
        python3 -m venv "$BACKEND_DIR/venv"
    fi
    source "$BACKEND_DIR/venv/bin/activate"

    # Install dependencies
    echo "  Installing Python dependencies..."
    pip install -q -r "$BACKEND_DIR/requirements.txt" 2>/dev/null

    # Pull Ollama models
    if command -v ollama &> /dev/null; then
        echo ""
        echo "  Pulling local models (this takes a while first time)..."

        # Detect VRAM and choose appropriate model sizes
        VRAM_MB=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null | head -1)
        VRAM_MB=${VRAM_MB:-0}

        if [ "$VRAM_MB" -gt 60000 ]; then
            echo "  Detected ${VRAM_MB}MB VRAM — pulling large models"
            ollama pull qwen2.5-coder:32b
            ollama pull deepseek-r1:32b
            ollama pull qwen2.5:14b
            sed -i 's/OLLAMA_MODEL_CODE=.*/OLLAMA_MODEL_CODE=qwen2.5-coder:32b/' "$BACKEND_DIR/.env"
            sed -i 's/OLLAMA_MODEL_REASON=.*/OLLAMA_MODEL_REASON=deepseek-r1:32b/' "$BACKEND_DIR/.env"
            sed -i 's/OLLAMA_MODEL_FAST=.*/OLLAMA_MODEL_FAST=qwen2.5:14b/' "$BACKEND_DIR/.env"
        elif [ "$VRAM_MB" -gt 12000 ]; then
            echo "  Detected ${VRAM_MB}MB VRAM — pulling 16GB-class models"
            ollama pull qwen2.5-coder:14b
            ollama pull deepseek-r1:14b
            ollama pull qwen2.5:7b
            sed -i 's/OLLAMA_MODEL_CODE=.*/OLLAMA_MODEL_CODE=qwen2.5-coder:14b/' "$BACKEND_DIR/.env"
            sed -i 's/OLLAMA_MODEL_REASON=.*/OLLAMA_MODEL_REASON=deepseek-r1:14b/' "$BACKEND_DIR/.env"
            sed -i 's/OLLAMA_MODEL_FAST=.*/OLLAMA_MODEL_FAST=qwen2.5:7b/' "$BACKEND_DIR/.env"
        elif [ "$VRAM_MB" -gt 6000 ]; then
            echo "  Detected ${VRAM_MB}MB VRAM — pulling 7B models"
            ollama pull qwen2.5-coder:7b
            ollama pull deepseek-r1:7b
            ollama pull qwen2.5:7b
        else
            echo "  Limited VRAM — pulling small models"
            ollama pull qwen2.5-coder:1.5b
            ollama pull qwen2.5:1.5b
            sed -i 's/OLLAMA_MODEL_CODE=.*/OLLAMA_MODEL_CODE=qwen2.5-coder:1.5b/' "$BACKEND_DIR/.env"
            sed -i 's/OLLAMA_MODEL_FAST=.*/OLLAMA_MODEL_FAST=qwen2.5:1.5b/' "$BACKEND_DIR/.env"
        fi

        ollama pull nomic-embed-text
        echo "  ✅ Models pulled"
    fi

    # Qdrant
    if command -v docker &> /dev/null; then
        if ! docker ps | grep -q qdrant; then
            echo "  Starting Qdrant vector database..."
            docker run -d --name qdrant -p 6333:6333 \
                -v "$HOME/.grace/qdrant:/qdrant/storage" \
                qdrant/qdrant 2>/dev/null || echo "  Qdrant already exists"
        fi
        echo "  ✅ Qdrant running"
    else
        echo "  ⚠️ Docker not found — Qdrant won't start (RAG search disabled)"
    fi

    # Frontend
    if command -v node &> /dev/null; then
        echo "  Building frontend..."
        cd "$FRONTEND_DIR" && npm install -q 2>/dev/null && npm run build 2>/dev/null
        echo "  ✅ Frontend built"
        cd "$SCRIPT_DIR"
    fi

    # Database init
    echo "  Initialising database..."
    cd "$BACKEND_DIR"
    python3 -c "
from database.session import initialize_session_factory
from database.migration import create_tables
initialize_session_factory()
create_tables()
print('  ✅ Database initialised')
" 2>/dev/null || echo "  ⚠️ Database init skipped (will auto-create on first run)"

    # Ingest training corpus
    echo "  Ingesting training corpus..."
    python3 -c "
from cognitive.training_ingest import ingest_training_corpus
r = ingest_training_corpus()
print(f'  ✅ Training corpus: {r.get(\"ingested\", 0)} files ingested')
" 2>/dev/null || echo "  ⚠️ Training ingest skipped"

    echo ""
    echo "  ✅ Setup complete! Run './start_grace.sh' to start Grace."
    exit 0
fi

# ── Normal start ──────────────────────────────────────────────────────

echo ""
echo "[2/8] Loading environment..."
cd "$BACKEND_DIR"
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | grep '=' | xargs) 2>/dev/null
    echo "  ✅ Environment loaded"
else
    echo "  ⚠️ No .env file — using defaults"
fi

# Activate venv if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "  ✅ Virtual environment activated"
fi

echo ""
echo "[3/8] Checking Ollama..."
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    MODEL_COUNT=$(curl -s http://localhost:11434/api/tags | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('models',[])))" 2>/dev/null || echo "?")
    echo "  ✅ Ollama running — $MODEL_COUNT models available"
else
    echo "  ⚠️ Ollama not running — starting..."
    ollama serve &> /dev/null &
    sleep 2
fi

echo ""
echo "[4/8] Checking Qdrant..."
if curl -s http://localhost:6333/collections > /dev/null 2>&1; then
    echo "  ✅ Qdrant running"
else
    echo "  ⚠️ Qdrant not running — RAG search will be limited"
fi

echo ""
echo "[5/8] Checking cloud models..."
# Kimi
if [ -n "$KIMI_API_KEY" ]; then
    echo "  ✅ Kimi K2.5 configured"
else
    echo "  ⚠️ Kimi not configured (set KIMI_API_KEY in .env)"
fi
# Opus
if [ -n "$OPUS_API_KEY" ]; then
    echo "  ✅ Opus 4.6 configured"
else
    echo "  ⚠️ Opus not configured (set OPUS_API_KEY in .env)"
fi

echo ""
echo "[6/8] Running startup diagnostic..."
python3 -c "
import os
os.environ.setdefault('SKIP_EMBEDDING_LOAD', 'true')
from cognitive.test_framework import smoke_test
r = smoke_test()
print(f'  {r[\"summary\"]}')
" 2>/dev/null || echo "  ⚠️ Diagnostic skipped"

echo ""
echo "[7/8] Ingesting training corpus..."
python3 -c "
from cognitive.training_ingest import ingest_training_corpus
r = ingest_training_corpus()
if r.get('ingested', 0) > 0:
    print(f'  ✅ Ingested {r[\"ingested\"]} new training files')
else:
    print(f'  ✅ Training corpus up to date ({r.get(\"skipped\", 0)} already ingested)')
" 2>/dev/null || echo "  ⚠️ Training ingest skipped"

echo ""
echo "[8/8] Starting Grace..."
echo ""
echo "=========================================="
echo "  Grace is starting on http://localhost:8000"
echo "  Frontend: http://localhost:5173 (dev) or http://localhost:8000 (built)"
echo ""
echo "  Models:"
echo "    Local:  $OLLAMA_MODEL_CODE (code), $OLLAMA_MODEL_REASON (reason)"
echo "    Cloud:  Kimi K2.5 + Opus 4.6"
echo ""
echo "  Quick commands:"
echo "    Smoke test:  curl http://localhost:8000/api/audit/test/smoke"
echo "    Logic test:  curl http://localhost:8000/api/audit/test/logic"
echo "    Daily report: curl http://localhost:8000/api/audit/diagnostics/daily"
echo "=========================================="
echo ""

# Test mode
if [ "$1" == "--test" ]; then
    python3 -c "
from cognitive.deep_test_engine import get_deep_test_engine
r = get_deep_test_engine().run_logic_tests()
print(f'Logic tests: {r[\"passed\"]}/{r[\"total\"]} passed ({r[\"pass_rate\"]}%)')
print(f'Status: {r[\"status\"]}')
" 2>/dev/null
fi

# Start the server
exec uvicorn app:app --host 0.0.0.0 --port 8000 --reload
