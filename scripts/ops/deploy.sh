#!/usr/bin/env bash
# SLICE-0079 production deploy script — run on the application VPS.
#
# Pulls the immutable GHCR image tagged $1, brings the versioned Compose
# stack (docker-compose.prod.yml, deployed alongside this script) up, and
# smoke-checks the two local-only health endpoints before recording the new
# tag as the rollback target. On a failed health check it automatically
# invokes rollback.sh. See docs/operations/PRODUCTION_DEPLOY_ROLLBACK_RUNBOOK.md
# for the full procedure.
set -euo pipefail

if [ $# -ne 1 ]; then
  echo "usage: deploy.sh <image-tag>" >&2
  exit 2
fi

NEW_TAG="$1"
DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_FILE="$DEPLOY_DIR/.last-good-tag"
PREVIOUS_TAG="$(cat "$STATE_FILE" 2>/dev/null || echo "")"

echo "Deploying image tag: $NEW_TAG (previous known-good: ${PREVIOUS_TAG:-none})"

export HULLQ_IMAGE_TAG="$NEW_TAG"
docker compose -f "$DEPLOY_DIR/docker-compose.prod.yml" pull
docker compose -f "$DEPLOY_DIR/docker-compose.prod.yml" up -d

echo "Waiting for the API container to report healthy..."
for _ in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:8000/healthz >/dev/null 2>&1 \
     && curl -fsS http://127.0.0.1:8000/readyz >/dev/null 2>&1; then
    echo "$NEW_TAG" > "$STATE_FILE"
    echo "Deploy succeeded: $NEW_TAG is now the recorded known-good tag."
    exit 0
  fi
  sleep 2
done

echo "Deploy health check failed after 60s." >&2
if [ -n "$PREVIOUS_TAG" ]; then
  echo "Rolling back to $PREVIOUS_TAG." >&2
  "$DEPLOY_DIR/rollback.sh"
  exit 1
fi
echo "No previous known-good tag recorded; cannot auto-rollback. Manual intervention required." >&2
exit 1
