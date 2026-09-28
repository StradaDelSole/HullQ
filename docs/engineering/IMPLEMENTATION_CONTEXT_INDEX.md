# HullQ — Implementation Context Index

**Status:** ACTIVE routing index — non-normative  
**Purpose:** give implementation/review agents one compact entry point to the stable current engineering boundaries without requiring broad project-history reads.

## Authority

This file is an index, not a second source of product/domain truth.

If this file conflicts with a normative spec, accepted ADR, architecture contract, governance record, accepted slice/closure, or current production implementation, the higher-authority/current artifact wins and this index must be corrected.

Do not use this file to bypass slice-specific reconciliation.

## Stable current engineering boundaries

### Application stack

- FastAPI is HullQ's sole application/domain API boundary.
- PostgreSQL 18 is the production database target.
- Astro is the primary web framework; React is used only for justified interactive islands.
- Application hosts remain stateless/replaceable.
- Auth0 is authentication-only; HullQ owns Account/Organization/Membership/roles/authorization truth in PostgreSQL.
- Privileged broker publishing uses the accepted MFA/step-up boundary.
- Deployment remains immutable container images through GHCR/versioned Docker Compose.
- Marketplace media bytes use an S3-compatible object-storage boundary; Cloudflare R2 Standard is the initial provider.

Read the exact architecture documents only when the assigned slice changes one of these boundaries.

### Marketplace identity/truth

Keep runtime/domain identities distinct:

```text
BoatDesignRef
!= PhysicalBoatId
!= MarketEpisodeId
!= NativeListingId
!= ExternalMarketObservationId
```

Pre-market draft identities are also distinct from marketplace identities.

Hard truth boundary:

```text
DESIGN / CONFIGURATION TRUTH
!=
PHYSICAL BOAT / LISTING TRUTH
```

Do not use this index as the detailed identity contract; follow the slice-named marketplace specs/code when identity is in scope.

### Professional workspace

Current accepted professional flow is:

```text
authenticated Account
→ selected MarketplaceOrganization
→ current ACTIVE membership
→ required role/MFA
→ Organization-owned professional draft
→ atomic promotion to NativeListing DRAFT
→ Organization-controlled media
→ publication/current-public path
```

Authorization remains server-side and Organization-scoped. Foreign/unknown resource handling remains non-enumerating where accepted.

### Search

Accepted hard technical native-inventory Search criteria count is currently:

```text
2
```

Accepted criteria:

1. `draft_max`
2. `keel_configuration`

Commercial consideration must not affect organic eligibility, match classification, or organic ordering.

Any criterion #3+ remains subject to the accepted abstraction guard.

### Workflow/gates

- `origin/main` is canonical repository truth.
- Readiness is independently reviewed and merged before implementation.
- `START_SLICE.bat` is the only initial implementation-prompt source.
- Claude implements on the assigned slice branch/worktree.
- Independent exact-head implementation review is mandatory.
- Material findings are amended on the same slice branch.
- Explicit Project Owner acceptance is required before implementation merge.
- Acceptance closure must merge before `FINISH_SLICE.bat`.
- The next slice is never auto-started.

Current gate values must be read from their canonical governance files when relevant; this index deliberately does not duplicate mutable gate markers.

## Token-efficient routing

For an implementation slice, normally read in this order:

1. `CLAUDE.md` — repository-wide operating rules, usually preloaded.
2. Assigned primary `docs/slices/SLICE-XXXX-*.md`.
3. The slice's normative spec(s).
4. Only the exact production modules/tests named by the slice or needed for the concrete implementation.
5. This index only when a stable cross-cutting boundary needs a compact reminder.
6. Broader governance/history only when the slice explicitly cites it or a real conflict/blocker requires it.

Do not preload `PROJECT_STATE.md`, full requirements, roadmap, slice history, acceptance closures, or old chats merely for orientation.

## Review routing

Independent implementation review should be delta-first:

1. establish readiness base and exact implementation HEAD;
2. inspect changed files/diff first;
3. map changed surfaces to the review matrix below;
4. open unchanged surrounding code only where the delta depends on it;
5. broaden to repository/history only if a material boundary conflict is plausible.

Review matrix:

```text
scope
authorization / tenant isolation
identity / truth
persistence / migration
transactionality / concurrency
failure / retry
privacy / secrets / media exposure
API / UI authoritative-state behavior
public/Search regression
governance / trigger gates
```

A full-repository reread is not a default review step.

## Amendment routing

For a same-slice amendment:

- base review on `previous reviewed HEAD → new HEAD`;
- inspect only changed files plus directly affected invariants/tests;
- do not repeat the whole readiness review;
- require a fresh full-suite run only at the final candidate handoff or when the amendment can affect broad regression risk;
- focused tests + repository validator/lint/type checks are normally sufficient during intermediate amendment iterations unless the slice contract requires otherwise.

## Completion-report routing

The exact completion-report schema remains in `docs/slices/SLICE_TEMPLATE.md`.

Reports should communicate evidence, not restate implementation history. The normal target is approximately one screen/page, with longer prose only for blockers, deviations, or unverified acceptance criteria.
