#!/bin/bash
# =============================================================================
# GRACE External Services Starter (Unix/Mac/WSL)
# =============================================================================
# Starts Qdrant (required for RAG). Ollama: run manually (ollama serve)
# Usage: ./start_services.sh [qdrant|all]
# =============================================================================

set -e
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE="${1:-qdrant}"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo -e "${CYAN}===============================================================================${NC}"
echo -e "${CYAN}   GRACE External Services (Qdrant + optional Ollama)                        ${NC}"
echo -e "${CYAN}===============================================================================${NC}"
echo ""

start_qdrant() {
    echo -e "${GREEN}Starting Qdrant (vector DB on ports 6333, 6334)...${NC}"
    if docker ps --filter "name=qdrant" --format "{{.Names}}" 2>/dev/null | grep -q .; then
        echo "  Qdrant container already running."
    else
        docker run -d -p 6333:6333 -p 6334:6334 --name qdrant qdrant/qdrant:latest 2>/dev/null || docker start qdrant 2>/dev/null || true
    fi
    sleep 2
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:6333/health 2>/dev/null | grep -q 200; then
        echo "  Qdrant is ready at http://localhost:6333"
    else
        echo "  Wait a few seconds and check: curl http://localhost:6333/health"
    fi
}

case "$MODE" in
    qdrant)
        start_qdrant
        ;;
    all)
        start_qdrant
        echo ""
        echo -e "${YELLOW}Ollama (LLM) - start manually: ollama serve && ollama pull mistral:7b${NC}"
        ;;
    *)
        echo "Usage: ./start_services.sh [qdrant|all]"
        exit 1
        ;;
esac
echo ""
exit 0
