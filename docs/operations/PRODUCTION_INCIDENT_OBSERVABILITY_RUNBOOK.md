# Production Incident / Observability Runbook — SLICE-0079

**Status:** operational runbook, required output of SLICE-0079.
**Controlling gate:** `docs/governance/PRODUCTION_READINESS_GATE.md` §3 (observability/alerting) and §5 (secrets/privileged access).
**DSGVO/incident-response context:** `docs/ARCHITECTURE_REBASELINE_2026-09-02.md` §27 (detect → contain → preserve evidence → assess → risk-assess → notify → remediate → postmortem). This runbook covers the operational detection/alerting half; the full incident-response policy for real personal-data incidents is that section, read together with this file.

## 1. Structured logging

Every request is logged as one JSON line to stdout by
`src/hullq/observability/logging_config.py` (`hullq.access` logger), with
`request_id`/`method`/`path`/`status_code`/`duration_ms`. Every unhandled
exception is additionally logged with a full traceback under
`unhandled_exception` before the client receives a generic, detail-free
500 response carrying the same `request_id` for correlation
(`src/hullq/api/app.py`'s `_structured_access_logging` middleware and
`_handle_unexpected_exception` handler).

**No file-based log state is written** — this preserves the stateless/
replaceable application-host assumption. In production, the container
runtime's own log driver (Docker's default `json-file` driver, or
whatever the VPS's log-shipping agent reads from `docker compose logs`)
is the retention mechanism. If/when log volume or retention needs exceed
what `docker compose logs` can practically serve an operator, the next
step is a log-shipping agent (e.g. Vector, Promtail) forwarding the same
stdout JSON lines to a retained destination — not a code change, since
the JSON-lines format is already shipping-agent-friendly.

## 2. Health/readiness

```text
GET /healthz   — liveness only, never touches the database
GET /readyz    — PostgreSQL reachability (SELECT 1)
```

See `src/hullq/api/app.py`'s docstrings on `get_liveness`/`get_readiness`
for why they are deliberately split (a database outage must not look like
"the application process itself needs restarting").

## 3. Actionable alerting

`src/hullq/observability/alerting.py`'s `send_alert` POSTs an `AlertEvent`
to `HULLQ_ALERT_WEBHOOK_URL` — a Slack incoming-webhook or Discord webhook
URL (the payload carries both `text` and `content` keys so either works
unmodified). `scripts/ops/health_monitor.py` is the operator-facing
trigger: run it from cron (architecture §26: "scheduler/cron where
appropriate" — no always-on monitoring daemon is justified at this scale).

```cron
# Every 5 minutes
*/5 * * * * cd /opt/hullq-ops && uv run python scripts/ops/health_monitor.py --base-url https://hullq.com >> /var/log/hullq-health-monitor.log 2>&1
```

Exit codes: `0` healthy, `1` unhealthy (alert delivered or no webhook
configured), `2` unhealthy **and** the alert itself failed to deliver —
cron's own failure handling (a cron MTA, or simply checking the log file)
is the backstop for exit code `2`, so a webhook outage can never become a
second silent failure on top of the first.

**No silent critical failure mode**: an application crash shows as
`/healthz` failing; a database outage shows as `/readyz` failing; either
triggers an alert within one cron interval (5 minutes). An exception
inside a single request is always structured-logged with a traceback
(§1) even when it does not fail the aggregate health checks.

## 4. Secrets / privileged access

- No secret is committed to the repository (verified: `docs/operations/production.env.example` contains only variable *names*; `.gitignore` already excludes `.env`/`.env.*`).
- Deployment credentials: a GHCR personal access token scoped `read:packages` only on the VPS (pull-only — the VPS never needs to *push* images); GitHub Actions uses the repository's own ambient `secrets.GITHUB_TOKEN` (scoped `packages: write` only in the `push_to_ghcr` job) to push.
- Database credentials: the application role (`HULLQ_DATABASE_URL`) and the backup mechanism's object-storage credentials (`HULLQ_BACKUP_R2_*`) are deliberately separate from each other and from the media object-storage credentials (`HULLQ_R2_*`) — `docs/ARCHITECTURE_REBASELINE_2026-09-02.md` §21/§22.
- Auth0 credentials: stored only in the VPS `.env` and (for CI, if ever needed) GitHub Actions secrets; never in the repository.
- Privileged operational actions (deploy, rollback, migration, restore) are all explicit, named CLI invocations with their own JSON output (never a routine manual `psql`/`docker exec` edit) — each run's stdout/exit-code is the audit trail; redirect to a dated log file per the cron examples above for durable retention.
- Rotation: any credential above can be rotated by generating a new value at the provider, updating the VPS `.env` (or the GitHub Environment secret), and restarting the affected container(s) — no code change is required for any of them, since every one is read from the environment at process start, never hardcoded.

## 5. Executable proof performed for this slice (2026-10-03)

```text
tests/unit/test_observability_logging_config.py       — 9 tests, JSON formatter
  correctness, idempotent handler attachment, extra-field promotion, exception
  traceback capture
tests/unit/test_observability_alerting.py              — 8 tests, webhook payload
  shape, unconfigured-webhook no-op, successful/failing delivery, transport-error
  handling
tests/persistence/test_production_readiness_health_api.py — 7 tests against the
  real FastAPI app + real PostgreSQL: /healthz and /readyz both independent of
  each other's failure mode, per-request X-Request-Id correlation, and a real
  unhandled exception (monkeypatched to actually raise) producing the generic
  structured 500 response with no exception detail in the HTTP body
```

All pass locally (`uv run pytest` for the unit tests;
`scripts/workflow/claude_diag.py run-local-test-db-compact` for the
PostgreSQL-backed ones). **Residual**: real delivery to an actual Slack/
Discord webhook has not been exercised (no real webhook URL available in
this sandbox) — `send_alert`'s HTTP-POST mechanism is proven with a fake
transport in the unit tests; the first real delivery is an operational
task for whoever configures `HULLQ_ALERT_WEBHOOK_URL` for the first time.
