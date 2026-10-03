#!/usr/bin/env bash
# SLICE-0079 production rollback script — run on the application VPS.
#
# Redeploys the last recorded known-good image tag (written by deploy.sh on
# its own success). See docs/operations/PRODUCTION_DEPLOY_ROLLBACK_RUNBOOK.md.
set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_FILE="$DEPLOY_DIR/.last-good-tag"

if [ ! -s "$STATE_FILE" ]; then
  echo "No recorded known-good tag in $STATE_FILE; cannot roll back automatically." >&2
  exit 2
fi

TARGET_TAG="$(cat "$STATE_FILE")"
echo "Rolling back to recorded known-good tag: $TARGET_TAG"

export HULLQ_IMAGE_TAG="$TARGET_TAG"
docker compose -f "$DEPLOY_DIR/docker-compose.prod.yml" pull
docker compose -f "$DEPLOY_DIR/docker-compose.prod.yml" up -d

for _ in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:8000/healthz >/dev/null 2>&1 \
     && curl -fsS http://127.0.0.1:8000/readyz >/dev/null 2>&1; then
    echo "Rollback succeeded: $TARGET_TAG is live."
    exit 0
  fi
  sleep 2
done

echo "Rollback health check failed after 60s. Manual operator intervention required." >&2
exit 1
