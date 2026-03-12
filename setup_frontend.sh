#!/bin/bash
# =============================================================================
# GRACE Frontend Setup (Unix/Mac/WSL)
# =============================================================================
# Installs npm dependencies
# Usage: ./setup_frontend.sh
# =============================================================================

set -e
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"

GREEN='\033[0;32m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo -e "${CYAN}===============================================================================${NC}"
echo -e "${CYAN}   GRACE Frontend Setup                                                        ${NC}"
echo -e "${CYAN}===============================================================================${NC}"
echo ""

cd "$FRONTEND_DIR"
[ -f "package.json" ] || { echo -e "${RED}Error: frontend/package.json not found.${NC}"; exit 1; }

echo -e "${GREEN}Installing dependencies (npm install)...${NC}"
npm install

echo ""
echo -e "${CYAN}===============================================================================${NC}"
echo -e "${GREEN}   Frontend setup complete. Run: ./start.sh frontend  (or ./start.sh for both)${NC}"
echo -e "${CYAN}===============================================================================${NC}"
echo ""
exit 0
