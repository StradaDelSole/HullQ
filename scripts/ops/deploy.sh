#!/usr/bin/env bash
# SLICE-0079 production deploy script — part of one immutable release
# directory (/opt/hullq/releases/<git-commit-sha>/, copied there from the
# exact checked-out commit by .github/workflows/deploy.yml's `deploy` job
# before this script ever runs — see
# docs/operations/PRODUCTION_DEPLOY_ROLLBACK_RUNBOOK.md §1/§2). Never run a
# copy of this script from outside its own release directory: it derives
# the image tag it deploys from its own directory name, which is exactly
# how image and deployment configuration are kept from drifting apart
# (independent review Finding B, 2026-10-XX amendment).
#
# Usage: deploy.sh   (no arguments — everything is derived from $PWD/path)
#
# State machine (independent review Finding C): two small files under
# $HULLQ_ROOT/state/ record which release is current and which is the
# rollback target:
#
#   state/current-release    the SHA of the release this script last
#                             successfully brought up
#   state/previous-release   the SHA that was current immediately before
#                             that — i.e. the ONE valid rollback target
#
# Every successful run of this script shifts current -> previous and
# records its own SHA as the new current. A rollback is implemented
# (rollback.sh) as simply re-running the previous release's OWN copy of
# this exact script, which naturally swaps current/previous back — so
# repeated rollbacks correctly toggle rather than requiring unbounded
# history.
set -euo pipefail

RELEASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HULLQ_ROOT="$(cd "$RELEASE_DIR/../.." && pwd)"
STATE_DIR="$HULLQ_ROOT/state"
CURRENT_FILE="$STATE_DIR/current-release"
PREVIOUS_FILE="$STATE_DIR/previous-release"
COMPOSE_FILE="$RELEASE_DIR/docker-compose.prod.yml"

NEW_SHA="$(basename "$RELEASE_DIR")"
IMAGE_TAG="sha-$NEW_SHA"

# Overridable only for the retained local proof
# (scripts/ops/inspect_deploy_rollback_lifecycle.py); production always
# uses the defaults (up to 60s).
HEALTH_RETRIES="${HULLQ_DEPLOY_HEALTH_RETRIES:-30}"
HEALTH_INTERVAL_SECONDS="${HULLQ_DEPLOY_HEALTH_INTERVAL_SECONDS:-2}"

CURRENT_SHA="$(cat "$CURRENT_FILE" 2>/dev/null || echo "")"

echo "Deploying release $NEW_SHA (image tag $IMAGE_TAG); current before this deploy: ${CURRENT_SHA:-none}"

export HULLQ_IMAGE_TAG="$IMAGE_TAG"
docker compose -f "$COMPOSE_FILE" up -d

echo "Waiting for the API container to report healthy..."
ATTEMPT=0
until curl -fsS http://127.0.0.1:8000/healthz >/dev/null 2>&1 \
      && curl -fsS http://127.0.0.1:8000/readyz >/dev/null 2>&1; do
  ATTEMPT=$((ATTEMPT + 1))
  if [ "$ATTEMPT" -ge "$HEALTH_RETRIES" ]; then
    echo "Deploy health check failed for $NEW_SHA after $((HEALTH_RETRIES * HEALTH_INTERVAL_SECONDS))s." >&2
    if [ -n "$CURRENT_SHA" ] && [ "$CURRENT_SHA" != "$NEW_SHA" ]; then
      echo "Attempting automatic revert to previous release $CURRENT_SHA." >&2
      if "$HULLQ_ROOT/releases/$CURRENT_SHA/deploy.sh"; then
        echo "Automatic revert to $CURRENT_SHA succeeded. Deploy of $NEW_SHA FAILED (exit 1)." >&2
        exit 1
      else
        echo "Automatic revert to $CURRENT_SHA ALSO FAILED. Manual intervention required immediately (exit 3)." >&2
        exit 3
      fi
    fi
    echo "No different previous release recorded; cannot auto-revert. Manual intervention required (exit 1)." >&2
    exit 1
  fi
  sleep "$HEALTH_INTERVAL_SECONDS"
done

mkdir -p "$STATE_DIR"
if [ -n "$CURRENT_SHA" ] && [ "$CURRENT_SHA" != "$NEW_SHA" ]; then
  echo "$CURRENT_SHA" > "$PREVIOUS_FILE"
fi
echo "$NEW_SHA" > "$CURRENT_FILE"
# Refresh the stable rollback entrypoint from this exact release's own
# copy, so the operator never needs to know which release directory to
# look in (docs/operations/PRODUCTION_DEPLOY_ROLLBACK_RUNBOOK.md §4).
cp "$RELEASE_DIR/rollback.sh" "$HULLQ_ROOT/rollback.sh"
chmod +x "$HULLQ_ROOT/rollback.sh"

echo "Deploy succeeded: $NEW_SHA is now the current release."
