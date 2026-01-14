# =============================================================================
# GRACE Frontend Dockerfile
# =============================================================================
# Multi-stage build for optimized production image
# Usage: docker build -t grace-frontend .
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder - Build the application
# -----------------------------------------------------------------------------
FROM node:20-alpine as builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --legacy-peer-deps

# Copy source code
COPY . .

# Build the application
RUN npm run build

# -----------------------------------------------------------------------------
# Stage 2: Runtime - Serve with nginx
# -----------------------------------------------------------------------------
FROM nginx:alpine as runtime

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Create non-root user
RUN addgroup -g 1001 -S grace && \
    adduser -u 1001 -S grace -G grace && \
    chown -R grace:grace /usr/share/nginx/html && \
    chown -R grace:grace /var/cache/nginx && \
    chown -R grace:grace /var/log/nginx && \
    touch /var/run/nginx.pid && \
    chown -R grace:grace /var/run/nginx.pid

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:80/ || exit 1

# Run as non-root user
USER grace

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
