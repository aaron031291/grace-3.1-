#!/bin/bash
# =============================================================================
# GRACE Backend Setup (Unix/Mac/WSL)
# =============================================================================
# Creates venv, installs deps, copies .env, runs migrations
# Usage: ./setup_backend.sh
# =============================================================================

set -e
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo -e "${CYAN}===============================================================================${NC}"
echo -e "${CYAN}   GRACE Backend Setup                                                        ${NC}"
echo -e "${CYAN}===============================================================================${NC}"
echo ""

cd "$BACKEND_DIR"
[ -f "requirements.txt" ] || { echo -e "${RED}Error: backend/requirements.txt not found.${NC}"; exit 1; }

# 1. Virtual environment
echo -e "${GREEN}[1/4] Virtual environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv || python -m venv venv
    echo "  Created venv"
else
    echo "  venv already exists"
fi
source venv/bin/activate

# 2. Dependencies
echo ""
echo -e "${GREEN}[2/4] Installing dependencies...${NC}"
pip install -r requirements.txt

# 3. Environment file
echo ""
echo -e "${GREEN}[3/4] Environment config...${NC}"
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "  Created .env from .env.example"
    else
        echo -e "  ${YELLOW}Warning: .env.example not found. Create .env manually.${NC}"
    fi
else
    echo "  .env already exists"
fi

# 4. Migrations
echo ""
echo -e "${GREEN}[4/4] Database migrations...${NC}"
python run_all_migrations.py

echo ""
echo -e "${CYAN}===============================================================================${NC}"
echo -e "${GREEN}   Backend setup complete. Run: ./start.sh backend  (or ./start.sh for both)${NC}"
echo -e "${CYAN}===============================================================================${NC}"
echo ""
exit 0
