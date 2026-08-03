# =============================================================================
# Dockerfile — TN Gov AI Scheme Assistant Frontend (Production)
# =============================================================================
#
# Multi-stage build:
#   Stage 1 (deps)    — install dependencies
#   Stage 2 (builder) — build Next.js standalone output
#   Stage 3 (runner)  — minimal production runtime image
#
# NEXT_PUBLIC_API_URL must be passed as a build argument:
#   docker build --build-arg NEXT_PUBLIC_API_URL=https://backend.railway.app .
#
# For Vercel deployment: set NEXT_PUBLIC_API_URL in Vercel project settings.
# Vercel will NOT use this Dockerfile — it uses its own build pipeline.
# This Dockerfile is provided for Railway / self-hosted deployments.
# =============================================================================

FROM node:22-slim AS deps

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --only=production --ignore-scripts

# ─── Stage 2: Build ─────────────────────────────────────────────
FROM node:22-slim AS builder

WORKDIR /app

# Accept backend URL at build time (required for Next.js NEXT_PUBLIC_ vars)
ARG NEXT_PUBLIC_API_URL=https://backend-production-0a73.up.railway.app
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts

COPY . .
RUN npm run build

# ─── Stage 3: Production Runtime ────────────────────────────────
FROM node:22-slim AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV PORT=3000

# Copy standalone output (next.config.ts output: 'standalone')
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000

# Re-expose NEXT_PUBLIC_API_URL for runtime (needed by client components)
ARG NEXT_PUBLIC_API_URL=https://backend-production-0a73.up.railway.app
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

CMD ["node", "server.js"]
