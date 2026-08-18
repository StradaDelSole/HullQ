# HullQ Architecture Decision Records

ADRs capture significant decisions and their rationale.

## Numbering

Use monotonically increasing four-digit identifiers:

```text
ADR-0001-single-repository.md
ADR-0002-docs-to-code.md
```

Never renumber accepted ADRs.

## Status

`PROPOSED | ACCEPTED | SUPERSEDED | REJECTED | DEPRECATED`

## Rule

One significant decision per ADR. If a decision changes, write a new ADR and mark the old one `SUPERSEDED BY ADR-NNNN`.

See `templates/ADR_TEMPLATE.md` and `docs/governance/OPEN_QUESTION_PROCESS.md`.

## Accepted decisions

- `ADR-0001` — Single repository
- `ADR-0002` — Docs-to-code
- `ADR-0003` — Broad coverage with progressive verification depth
- `ADR-0004` — BoatModel / BoatDesign generation / NamedVariant / DesignOption identity
- `ADR-0005` — Source rights / clearance
- `ADR-0006` — Field provenance ledger
- `ADR-0007` — Search Architecture and SEO are first-class product architecture
- `ADR-0008` — Derived metric methodology
- `ADR-0009` — Python research/data-pipeline toolchain
- `ADR-0010` — VPS-first application stack: Contabo + Cloudflare edge + Astro/TypeScript + selective React + FastAPI/Python + PostgreSQL; auth remains deferred
- `ADR-0011` — Brand/Marque and Builder/Manufacturer are distinct first-class identities; both are searchable and may have independent aliases and historical relationships
