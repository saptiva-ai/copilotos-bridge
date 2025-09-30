# =========================================
# MULTI-STAGE DOCKERFILE FOR NEXT.JS WEB
# =========================================
FROM node:20-alpine AS base

# Build arguments for user configuration
ARG UID=1000
ARG GID=1000

# Install pnpm
RUN corepack enable pnpm

# Create app user and group with configurable IDs
RUN set -eux; \
    if grep -q ":${UID}:" /etc/passwd; then \
        existing_user="$(grep ":${UID}:" /etc/passwd | head -n1 | cut -d: -f1)"; \
        if [ "$existing_user" != "app" ]; then \
            deluser "$existing_user"; \
        fi; \
    fi; \
    if grep -q ":${GID}:" /etc/group; then \
        existing_group="$(grep ":${GID}:" /etc/group | head -n1 | cut -d: -f1)"; \
        if [ "$existing_group" != "appgroup" ]; then \
            delgroup "$existing_group"; \
        fi; \
    fi; \
    addgroup -S -g "${GID}" appgroup; \
    adduser -S -D -u "${UID}" -G appgroup app;

# Create app directory and set ownership
WORKDIR /app
RUN chown app:appgroup /app

# Copy package files with proper ownership
COPY --chown=app:appgroup package.json pnpm-lock.yaml* pnpm-workspace.yaml* ./
COPY --chown=app:appgroup packages/ ./packages/
COPY --chown=app:appgroup apps/web/package.json ./apps/web/

# =========================================
# DEPENDENCIES STAGE
# =========================================
FROM base AS deps

# Switch to app user for dependency installation
USER app

# Install dependencies
RUN pnpm install --frozen-lockfile

# =========================================
# DEVELOPMENT STAGE
# =========================================
FROM base AS dev

ENV NODE_ENV=development
ENV IN_DOCKER=1

# Copy dependencies from deps stage with proper ownership
COPY --from=deps --chown=app:appgroup /app/node_modules ./node_modules
COPY --from=deps --chown=app:appgroup /app/packages ./packages

# Copy source code with proper ownership
COPY --chown=app:appgroup apps/web ./apps/web

# Create .next directory with proper permissions for mounted volume
# This ensures the anonymous volume inherits correct permissions
RUN mkdir -p /app/apps/web/.next && chown -R app:appgroup /app/apps/web/.next

# Switch to app user
USER app

# Set working directory for Next.js dev server
WORKDIR /app/apps/web

EXPOSE 3000

# Run development server with hostname binding for Docker (Next.js 14+ syntax)
CMD ["pnpm", "dev", "--hostname", "0.0.0.0", "--port", "3000"]

# =========================================
# BUILDER STAGE
# =========================================
FROM base AS builder

# Build-time environment variables
ARG NEXT_PUBLIC_API_URL=http://localhost:8001
ARG NODE_ENV=production

# Set environment variables for build
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV IN_DOCKER=1

# Copy dependencies with proper ownership
COPY --from=deps --chown=app:appgroup /app/node_modules ./node_modules
COPY --from=deps --chown=app:appgroup /app/packages ./packages
# CRITICAL: Copy workspace-specific node_modules for pnpm workspace
COPY --from=deps --chown=app:appgroup /app/apps/web/node_modules ./apps/web/node_modules

# Copy source code with proper ownership
COPY --chown=app:appgroup apps/web ./apps/web

# Create build output directory with proper ownership
RUN mkdir -p /tmp/next-cache && chown app:appgroup /tmp/next-cache
RUN mkdir -p /app/apps/web/.next && chown app:appgroup /app/apps/web/.next

# Switch to app user for build
USER app

# Build application as non-root user
RUN pnpm --filter web build

# =========================================
# PRODUCTION STAGE
# =========================================
FROM node:20-alpine AS runner

# Use same UID/GID arguments from base stage
ARG UID=1000
ARG GID=1000

WORKDIR /app

ENV NODE_ENV=production

# Install pnpm
RUN corepack enable pnpm

# Create non-root user with same IDs as build stage
RUN set -eux; \
    if grep -q ":${UID}:" /etc/passwd; then \
        existing_user="$(grep ":${UID}:" /etc/passwd | head -n1 | cut -d: -f1)"; \
        if [ "$existing_user" != "app" ]; then \
            deluser "$existing_user"; \
        fi; \
    fi; \
    if grep -q ":${GID}:" /etc/group; then \
        existing_group="$(grep ":${GID}:" /etc/group | head -n1 | cut -d: -f1)"; \
        if [ "$existing_group" != "appgroup" ]; then \
            delgroup "$existing_group"; \
        fi; \
    fi; \
    addgroup -S -g "${GID}" appgroup; \
    adduser -S -D -u "${UID}" -G appgroup app;

# Set ownership of app directory
RUN chown app:appgroup /app

# Copy built application with proper ownership
COPY --from=builder --chown=app:appgroup /app/apps/web/.next/standalone ./
COPY --from=builder --chown=app:appgroup /app/apps/web/.next/static ./apps/web/.next/static
COPY --from=builder --chown=app:appgroup /app/apps/web/public ./apps/web/public

# Verify that the standalone output was created correctly
RUN test -f /app/apps/web/server.js || (echo "Standalone output is missing server.js" && ls -laR && exit 1)

USER app

EXPOSE 3000

ENV PORT=3000 \
    HOSTNAME="0.0.0.0"

# Set working directory to where server.js is located for standalone mode
WORKDIR /app/apps/web

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://127.0.0.1:3000 || exit 1

CMD ["node", "server.js"]
