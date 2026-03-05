# =============================================================================
# GRACE Backend Dockerfile
# =============================================================================
# Multi-stage build for optimized production image
# Usage: docker build -t grace-backend .
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 0: MCP Builder - Build Node.js based MCP servers
# -----------------------------------------------------------------------------
FROM node:20-slim as mcp-builder

WORKDIR /app

# Build DesktopCommanderMCP
COPY mcp_repos/DesktopCommanderMCP ./mcp_repos/DesktopCommanderMCP
WORKDIR /app/mcp_repos/DesktopCommanderMCP
RUN npm install && npm run build

# Build MCP memory server
WORKDIR /app
COPY mcp_repos/mcp-servers/src/memory ./mcp_repos/mcp-servers/src/memory
COPY mcp_repos/mcp-servers/tsconfig.json ./mcp_repos/mcp-servers/tsconfig.json
WORKDIR /app/mcp_repos/mcp-servers/src/memory
RUN npm install && npm run build

# Build MCP filesystem server
WORKDIR /app
COPY mcp_repos/mcp-servers/src/filesystem ./mcp_repos/mcp-servers/src/filesystem
WORKDIR /app/mcp_repos/mcp-servers/src/filesystem
RUN npm install && npm run build

# Build MCP sequential-thinking server
WORKDIR /app
COPY mcp_repos/mcp-servers/src/sequentialthinking ./mcp_repos/mcp-servers/src/sequentialthinking
WORKDIR /app/mcp_repos/mcp-servers/src/sequentialthinking
RUN npm install && npm run build

# Stage 1: Builder - Install dependencies
# -----------------------------------------------------------------------------
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# -----------------------------------------------------------------------------
# Stage 2: Runtime - Final production image
# -----------------------------------------------------------------------------
FROM python:3.11-slim as runtime

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    curl \
    nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set Python environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Create non-root user for security
RUN groupadd -r grace && useradd -r -g grace grace

# Copy application code
COPY --chown=grace:grace . .

# Copy built MCP assets from Stage 0
COPY --from=mcp-builder --chown=grace:grace /app/mcp_repos/DesktopCommanderMCP/dist /app/mcp_repos/DesktopCommanderMCP/dist
COPY --from=mcp-builder --chown=grace:grace /app/mcp_repos/DesktopCommanderMCP/node_modules /app/mcp_repos/DesktopCommanderMCP/node_modules
COPY --from=mcp-builder --chown=grace:grace /app/mcp_repos/mcp-servers/src/memory/dist /app/mcp_repos/mcp-servers/src/memory/dist
COPY --from=mcp-builder --chown=grace:grace /app/mcp_repos/mcp-servers/src/memory/node_modules /app/mcp_repos/mcp-servers/src/memory/node_modules
COPY --from=mcp-builder --chown=grace:grace /app/mcp_repos/mcp-servers/src/filesystem/dist /app/mcp_repos/mcp-servers/src/filesystem/dist
COPY --from=mcp-builder --chown=grace:grace /app/mcp_repos/mcp-servers/src/filesystem/node_modules /app/mcp_repos/mcp-servers/src/filesystem/node_modules
COPY --from=mcp-builder --chown=grace:grace /app/mcp_repos/mcp-servers/src/sequentialthinking/dist /app/mcp_repos/mcp-servers/src/sequentialthinking/dist
COPY --from=mcp-builder --chown=grace:grace /app/mcp_repos/mcp-servers/src/sequentialthinking/node_modules /app/mcp_repos/mcp-servers/src/sequentialthinking/node_modules

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/knowledge_base && \
    chown -R grace:grace /app/data /app/logs /app/knowledge_base

# Switch to non-root user
USER grace

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
