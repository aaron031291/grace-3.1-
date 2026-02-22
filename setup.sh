#!/bin/bash
# =============================================================================
# GRACE Setup Script - From Clone to Running
# =============================================================================
# Usage: chmod +x setup.sh && ./setup.sh
# =============================================================================

set -e

echo "============================================"
echo "  GRACE System Setup"
echo "============================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo -e "${RED}[FAIL] Python not found. Install Python 3.10+${NC}"
    exit 1
fi

echo -e "${GREEN}[OK]${NC} Python: $($PYTHON --version)"

# Check Node
if command -v node &> /dev/null; then
    echo -e "${GREEN}[OK]${NC} Node: $(node --version)"
else
    echo -e "${RED}[FAIL] Node.js not found. Install Node 18+${NC}"
    exit 1
fi

# =============================================================================
# Backend Setup
# =============================================================================
echo ""
echo "--- Backend Setup ---"

cd backend

# Create virtual environment if not exists
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    $PYTHON -m venv venv
    echo -e "${GREEN}[OK]${NC} Virtual environment created"
fi

# Activate venv
source venv/bin/activate
echo -e "${GREEN}[OK]${NC} Virtual environment activated"

# Install dependencies
echo "Installing Python dependencies (this may take a few minutes)..."
pip install --upgrade pip setuptools wheel > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1
echo -e "${GREEN}[OK]${NC} Python dependencies installed"

# Create .env from example if not exists
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${GREEN}[OK]${NC} Created .env from .env.example"
    fi
fi

# Create data directories
mkdir -p data logs knowledge_base
echo -e "${GREEN}[OK]${NC} Data directories created"

# Verify critical imports
echo "Verifying backend imports..."
$PYTHON -c "
import sys
sys.path.insert(0, '.')
failures = []
for mod in ['fastapi', 'sqlalchemy', 'pydantic', 'uvicorn']:
    try:
        __import__(mod)
    except ImportError:
        failures.append(mod)
if failures:
    print(f'MISSING: {failures}')
    sys.exit(1)
print('All critical imports OK')
" || { echo -e "${RED}[FAIL] Backend dependencies incomplete${NC}"; exit 1; }
echo -e "${GREEN}[OK]${NC} Backend imports verified"

cd ..

# =============================================================================
# Frontend Setup
# =============================================================================
echo ""
echo "--- Frontend Setup ---"

cd frontend

# Install dependencies
echo "Installing frontend dependencies..."
npm install --legacy-peer-deps > /dev/null 2>&1
echo -e "${GREEN}[OK]${NC} Frontend dependencies installed"

# Create .env.local from example if not exists
if [ ! -f ".env.local" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env.local
        echo -e "${GREEN}[OK]${NC} Created .env.local from .env.example"
    fi
fi

# Verify build
echo "Verifying frontend build..."
npm run build > /dev/null 2>&1 && echo -e "${GREEN}[OK]${NC} Frontend builds successfully" || echo -e "${YELLOW}[WARN]${NC} Frontend build failed (may need backend running)"

cd ..

# =============================================================================
# Summary
# =============================================================================
echo ""
echo "============================================"
echo "  Setup Complete"
echo "============================================"
echo ""
echo "To start Grace:"
echo ""
echo "  1. Start Qdrant (vector DB):"
echo "     docker run -p 6333:6333 qdrant/qdrant:latest"
echo ""
echo "  2. Start Ollama (LLM):"
echo "     ollama serve"
echo "     ollama pull mistral:7b"
echo ""
echo "  3. Start Backend:"
echo "     cd backend && source venv/bin/activate"
echo "     python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload"
echo ""
echo "  4. Start Frontend:"
echo "     cd frontend && npm run dev"
echo ""
echo "  Or use Docker:"
echo "     docker-compose up -d"
echo ""
