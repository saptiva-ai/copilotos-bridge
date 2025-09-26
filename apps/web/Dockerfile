# =========================================
# MULTI-STAGE DOCKERFILE FOR NEXT.JS WEB
# =========================================
FROM node:20-alpine AS base

# Install pnpm
RUN corepack enable pnpm

WORKDIR /app

# Copy package files
COPY package.json pnpm-lock.yaml* pnpm-workspace.yaml* ./
COPY packages/ ./packages/
COPY apps/web/package.json ./apps/web/

# =========================================
# DEPENDENCIES STAGE
# =========================================
FROM base AS deps

# Install dependencies
RUN pnpm install --frozen-lockfile

# =========================================
# DEVELOPMENT STAGE
# =========================================
FROM base AS dev

ENV NODE_ENV=development

# Copy dependencies from deps stage
COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/packages ./packages

# Copy source code
COPY apps/web ./apps/web

# Set working directory for Next.js dev server
WORKDIR /app/apps/web

EXPOSE 3000

# Run development server with host binding for Docker
CMD ["pnpm", "dev", "--host", "0.0.0.0", "--port", "3000"]

# =========================================
# BUILDER STAGE
# =========================================
FROM base AS builder

# Build-time environment variables
ARG NEXT_PUBLIC_API_URL=http://localhost:8001
ARG NODE_ENV=production

# Set environment variables for build
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NODE_ENV=$NODE_ENV

# Copy dependencies
COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/packages ./packages

# Copy source code
COPY apps/web ./apps/web

# Build application
RUN pnpm --filter web build

# =========================================
# PRODUCTION STAGE
# =========================================
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production

# Install pnpm
RUN corepack enable pnpm

# Create non-root user
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy built application
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/.next/static ./apps/web/.next/static
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/public ./apps/web/public

USER nextjs

EXPOSE 3000

ENV PORT=3000 \
    HOSTNAME="0.0.0.0"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://127.0.0.1:3000 || exit 1

CMD ["node", "apps/web/server.js"]
