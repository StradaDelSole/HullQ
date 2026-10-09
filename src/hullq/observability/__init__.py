"""Production observability boundary — SLICE-0079.

See `hullq.observability.logging_config` (structured JSON application logs
and the global unhandled-exception capture path) and
`hullq.observability.alerting` (actionable operator alert delivery), which
together satisfy `docs/governance/PRODUCTION_READINESS_GATE.md` §3.
"""

from __future__ import annotations
