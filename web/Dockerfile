# SLICE-0079 production web (Astro Node SSR) image —
# docs/governance/PRODUCTION_READINESS_GATE.md §1.
#
# Multi-stage build: the builder stage installs the full locked dependency
# set (dev included -- the Astro/TypeScript build needs it) and runs
# `astro build`; the runtime stage installs only the production dependency
# set and copies the built `dist/` output, so no build toolchain or dev
# dependency ships in the running image. Stateless: this image writes
# nothing to a local volume and reads all configuration (e.g. the FastAPI
# API's public base URL, if the Astro server needs it) from the
# environment at container start.

FROM node:24-slim AS builder

WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:24-slim AS runtime

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev
COPY --from=builder /build/dist ./dist

ENV HOST=0.0.0.0 \
    PORT=4321 \
    NODE_ENV=production

USER node

EXPOSE 4321

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["node", "-e", "fetch('http://127.0.0.1:4321/').then(r => process.exit(r.status < 500 ? 0 : 1)).catch(() => process.exit(1))"]

CMD ["node", "./dist/server/entry.mjs"]
