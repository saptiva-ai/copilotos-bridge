FROM node:18-alpine AS base

# Allow configuring API endpoints at build time so Next.js rewrites point to the
# correct services when the app runs inside Docker.
ARG API_BASE_URL=http://api:8001
ARG NEXT_PUBLIC_API_URL=http://localhost:8001
ENV API_BASE_URL=${API_BASE_URL}
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

# Install pnpm
RUN npm install -g pnpm

# Set working directory
WORKDIR /app

# Copy package files
COPY package.json pnpm-lock.yaml* pnpm-workspace.yaml* ./


# Copy shared package files if they exist
COPY packages/ ./packages/
COPY apps/ ./apps/

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy source code
COPY . .

# Build the application
FROM base AS builder
ARG API_BASE_URL
ARG NEXT_PUBLIC_API_URL
ENV API_BASE_URL=${API_BASE_URL}
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
RUN pnpm build

# Production image
FROM node:18-alpine AS runner
WORKDIR /app

# Propagate API configuration to the runtime container (can be overridden at
# docker-compose level if required).
ARG API_BASE_URL=http://api:8001
ARG NEXT_PUBLIC_API_URL=http://localhost:8001
ENV API_BASE_URL=${API_BASE_URL}
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

# Install pnpm
RUN npm install -g pnpm

ENV NODE_ENV production

# Create non-root user
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy built application artifacts generated inside apps/web to the locations
# expected by the standalone server (which changes to /app/apps/web).
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/.next/static ./apps/web/.next/static
COPY --from=builder /app/apps/web/public ./apps/web/public

WORKDIR /app

USER nextjs

EXPOSE 3000

ENV PORT 3000
ENV HOSTNAME "0.0.0.0"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://127.0.0.1:3000 || exit 1

# Entry point runs the standalone server generated under apps/web
CMD ["node", "apps/web/server.js"]
