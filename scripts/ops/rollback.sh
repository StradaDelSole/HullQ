#!/usr/bin/env bash
# SLICE-0079 production rollback script.
#
# This exact file is copied to the STABLE path $HULLQ_ROOT/rollback.sh by
# every successful run of deploy.sh (from that release's own release
# directory) — so the operator always invokes the one fixed path below,
# regardless of which release is currently live. The copy that still sits
# inside releases/<sha>/rollback.sh is retained only for per-commit audit
# (so you can inspect exactly what rollback logic existed at that commit);
# it is never executed in place. See
# docs/operations/PRODUCTION_DEPLOY_ROLLBACK_RUNBOOK.md §1/§4.
#
# A rollback is simply re-running the previous release's OWN deploy.sh —
# that script's own current/previous bookkeeping (see deploy.sh's header)
# is what correctly swaps current/previous back, so this script contains
# no state-writing logic of its own.
set -euo pipefail

HULLQ_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_DIR="$HULLQ_ROOT/state"
PREVIOUS_FILE="$STATE_DIR/previous-release"

if [ ! -s "$PREVIOUS_FILE" ]; then
  echo "No recorded previous release in $PREVIOUS_FILE; cannot roll back automatically." >&2
  exit 2
fi

PREVIOUS_SHA="$(cat "$PREVIOUS_FILE")"
PREVIOUS_DEPLOY_SCRIPT="$HULLQ_ROOT/releases/$PREVIOUS_SHA/deploy.sh"

if [ ! -x "$PREVIOUS_DEPLOY_SCRIPT" ]; then
  echo "Previous release directory for $PREVIOUS_SHA is missing its deploy.sh ($PREVIOUS_DEPLOY_SCRIPT); cannot roll back." >&2
  exit 2
fi

echo "Rolling back to previous release: $PREVIOUS_SHA"
exec "$PREVIOUS_DEPLOY_SCRIPT"
