#!/bin/bash
# =============================================================================
# GRACE Verification Script (Unix/Mac/WSL)
# =============================================================================
# Checks backend health, Qdrant, and optionally frontend
# Usage: ./verify.sh
# =============================================================================

PASS=0
FAIL=0

GREEN='\033[0;32m'
RED='\033[0;31m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo -e "${CYAN}===============================================================================${NC}"
echo -e "${CYAN}   GRACE System Verification                                                    ${NC}"
echo -e "${CYAN}===============================================================================${NC}"
echo ""

# Backend
echo "[1/3] Backend API (http://localhost:8000/health)..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null | grep -q 200; then
    echo -e "  ${GREEN}OK${NC} Backend is running"
    ((PASS++))
else
    echo -e "  ${RED}FAIL${NC} Backend not responding. Start with: ./start.sh backend"
    ((FAIL++))
fi
echo ""

# Qdrant
echo "[2/3] Qdrant (http://localhost:6333/health)..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost:6333/health 2>/dev/null | grep -q 200; then
    echo -e "  ${GREEN}OK${NC} Qdrant is running"
    ((PASS++))
else
    echo -e "  ${RED}FAIL${NC} Qdrant not responding. Run: ./start_services.sh qdrant"
    ((FAIL++))
fi
echo ""

# Frontend
echo "[3/3] Frontend (http://localhost:5173)..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost:5173 2>/dev/null | grep -q 200; then
    echo -e "  ${GREEN}OK${NC} Frontend is running"
    ((PASS++))
else
    echo -e "  ${YELLOW}SKIP${NC} Frontend not running. Start with: ./start.sh frontend"
fi
echo ""

echo -e "${CYAN}===============================================================================${NC}"
if [ $FAIL -gt 0 ]; then
    echo -e "  ${RED}Result: $FAIL required check(s) failed.${NC}"
    echo "  Backend and Qdrant are required for RAG. Start services and run verify again."
else
    echo -e "  ${GREEN}Result: Core services OK. Backend: http://localhost:8000  Docs: http://localhost:8000/docs${NC}"
fi
echo -e "${CYAN}===============================================================================${NC}"
echo ""
exit 0
