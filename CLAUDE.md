# HullQ — Instructions for Coding / Research Agents

HullQ uses bounded docs-to-code slices with strict single-writer ownership and independent acceptance.

## Token-efficient reading order

Do **not** preload the whole repository for orientation.

For an assigned slice:

1. read this file (normally loaded automatically);
2. read the assigned primary `docs/slices/SLICE-XXXX-*.md` contract first;
3. read only the controlling specs, ADRs, protocols and implementation files explicitly named by that slice or required to answer a concrete implementation question;
4. consult broader project documents (`PROJECT_STATE`, `OPEN_QUESTIONS`, `REQUIREMENTS`, slice `INDEX`, roadmap/history) only when the slice references them or a real conflict/blocker requires them.

For SLICE-0039 and later, `docs/PRODUCT_EXECUTION_PLAN.md` is a controlling execution-policy document and must be read when named by the primary slice (the normal post-0038 template names it explicitly).

For work after the 2026-09-14 owner-direct marketplace pivot, `docs/OWNER_DIRECT_LISTING_PRODUCT_DIRECTION_2026-09-14.md`, `specs/OWNER_DIRECT_LISTING_REQUIREMENTS.v0.1.md` and `docs/PRODUCT_EXECUTION_PLAN_OWNER_DIRECT_RECONCILIATION_2026-09-14.md` control any slice that touches listing/supply, private-seller identity/verification, representation conflict, seller-to-broker referral, marketplace monetization or Search commercial independence.

When only one section/symbol of a large file is needed, prefer targeted search/narrow reads over loading the entire file.

Use the synchronized local checkout for ordinary repository reads. Do not repeatedly fetch local files through GitHub/API tooling when the local checkout already contains canonical synchronized content.

Operational token rules are in `docs/engineering/AI_TOKEN_EFFICIENCY.md`.

## Authority

When artifacts conflict, authority is:

1. normative `specs/`;
2. accepted ADRs in `architecture/decisions/`;
3. architecture contracts in `architecture/`;
4. operational `research/` protocols;
5. governance/engineering standards;
6. `PROJECT_CONTEXT.md` / strategy docs;
7. `reference/`.

Later explicit Project Owner decisions/reconciliations supersede older current-direction statements within the same authority class. In particular, the 2026-09-14 owner-direct direction supersedes the older broker-only/private-FSBO-out-of-scope supply policy while preserving its decision history.

Slices are operational work contracts and do not override this order. Never turn DRAFT/PROPOSED/BLOCKED material into production semantics without an explicit decision.

## Slice execution

- Work only on the explicitly assigned slice.
- Do not broaden scope because adjacent work looks convenient.
- `DESIGN_RESEARCH` does not authorize domain implementation unless explicitly stated.
- `IMPLEMENTATION` implements only accepted semantics identified by its controlling artifacts.
- If required semantics are unresolved or controlling artifacts materially conflict, stop and report `BLOCKED` rather than inventing policy.
- Do not automatically begin another slice after `REVIEW` or `BLOCKED`.
- Prefer small coherent edits and focused tests while iterating; run the full validation required by the slice at handoff.

The operational queue is `docs/slices/INDEX.md`; read it only when queue/status context is actually needed.

## Repository and branch ownership

`origin/main` is accepted canonical repository truth.

For an active implementation/research slice:

- Claude owns exactly the assigned `slice/...` branch/worktree;
- never push directly to `main`;
- never write another agent's branch/worktree;
- the project master/reviewer does not write Claude's active slice branch;
- review findings return to Claude, who fixes the same slice branch;
- force-push is forbidden unless the project owner explicitly authorizes recovery.

Use `START_SLICE.bat` and `FINISH_SLICE.bat` for the normal lifecycle. Never carry an old slice worktree forward as the next slice base.

### Shell / permission discipline

- Run shell commands directly from the current slice worktree. Do not prepend routine Bash/PowerShell commands with `cd <worktree> &&` / `cd <worktree>;` wrappers; the operator opens Claude Code in the correct worktree.
- Do not append synthetic exit-code wrappers such as `; echo "---EXIT $LASTEXITCODE---"` unless diagnosing a real shell/tool failure. Use Claude Code's tool result/exit status.
- Prefer one standalone command per tool call. This keeps commands compatible with the repository's shared `.claude/settings.json` allow/ask rules and avoids unnecessary approval prompts.
- For ad-hoc Python snippets, syntax/AST checks, and short repository inspection commands, use `uv run python ...` (for example `uv run python -c "..."`) rather than direct `python`, `python3`, or `py` invocations. `uv` is the shared approved execution path and avoids avoidable permission prompts.
- For routine multi-file checks, do not wrap commands in shell loops or compound expressions such as `for ...; do ...; done`, `&&`, or `;`. Run one standalone permitted command per tool call. For file-to-file comparisons, prefer `git diff --no-index <file-a> <file-b>` rather than direct `diff`/`cmp`, repeating as separate calls when several files must be compared.
- For read-only repository inspection/search, prefer Claude Code's `Read`, `Grep`, and `Glob` tools instead of spawning Bash/PowerShell commands such as `grep`, `find`, shell loops, or ad-hoc text-processing pipelines. Use shell only when the task genuinely requires process execution rather than file inspection.
- For web dependency installation, use the standalone repository-safe command `npm ci --prefix web` rather than `cd web && npm ci`, and do not append output-redirection/pipeline wrappers such as `2>&1 | tail ...`. The shared permissions allow `npm ci *` for this routine install path.
- **HARD APPROVAL-AUTONOMY RULE:** routine diagnostics, inspection, validation setup, and test preparation MUST NOT use shell composition that defeats static permission matching. Do not use shell variables/assignment, command substitution (`$(...)` or backticks), pipes (`|`), output redirection (`>`, `2>&1`), compound separators (`;`, `&&`, `||`), subshells, or shell loops for routine work. Split the task into separate tool calls instead. Use `Read`/`Grep`/`Glob` for file inspection and one standalone approved process command for execution. If a routine command would trigger an approval prompt because of its spelling/composition, rewrite it into approval-free standalone calls rather than asking the operator.
- Never print secret-bearing environment-variable values (for example database URLs, tokens, passwords or API keys) during diagnostics. Check only presence/status (`SET`/`UNSET`) or perform the required connection/probe without echoing credentials. Prefer a standalone `uv run python ...` probe when that avoids shell composition.
- Routine allowed commands may run autonomously; commands matched by the shared `ask` rules remain operator-gated. Never work around an approval boundary by spelling the same risky operation differently.

While Claude is actively implementing, unrelated changes should not be merged to `main`; blocker-resolution is a deliberate separate workflow.

See `docs/engineering/AI_SLICE_WORKFLOW.md` when workflow details are needed.

## Status and acceptance

Claude may move the assigned slice among:

```text
READY → IN_PROGRESS → REVIEW
                 ↘ BLOCKED
```

Claude MUST NOT mark a slice `DONE`.

`DONE` requires all of:

1. required acceptance criteria actually verified;
2. required remote/external checks actually observed and passed (or explicitly not applicable);
3. independent review complete;
4. explicit project-owner acceptance;
5. closure completed through the project workflow.

Never treat local green tests as proof of remote CI. If an external gate cannot be observed, report `NOT VERIFIED`.

At handoff, use the structure in `docs/slices/SLICE_TEMPLATE.md`. Keep it concise: summarize commands/results; do not paste full logs/diffs or repeat the entire slice contract unless needed to explain a failure/blocker. Include the exact final branch HEAD SHA.

## Core product guardrail

HullQ strengthens:

```text
FIND DESIGN → FIND BOAT FOR SALE → COMPARE / SAVE → ALERT
```

Do not broaden it into a generic boating super-app without an accepted scope decision.

## Marketplace supply model after 2026-09-14

HullQ is **broker-first mixed supply**, not broker-only.

Accepted direction:

```text
professional broker/dealer inventory
+
bounded owner-direct/private seller inventory
```

Private sellers may ultimately choose owner-direct listing or voluntarily opt into a broker-referral path. Existing implementation through accepted SLICE-0053 remains professional-only on the write side; do not fake a private seller as a broker/Organization to bypass that implementation boundary.

Hard invariants for relevant work:

```text
commercial consideration MUST NOT affect
- organic Search eligibility
- organic match classification
- organic ordering

payment may buy a verification service
payment NEVER buys a truth result or organic position
```

Seller trust scopes remain separate:

```text
PHONE VERIFIED
IDENTITY VERIFIED
RIGHT-TO-LIST ATTESTED
SALE AUTHORITY VERIFIED
```

They do not promote concrete-yacht technical fields. `Sale Authority Verified` is about authority to offer the vessel, not necessarily sole ownership.

Normal future owner-direct publication baseline is intentionally proportionate:

```text
HullQ account
+ verified phone reachability
+ explicit right-to-list attestation
+ baseline anti-abuse checks
```

Strong ID verification, vessel documents and physical boat challenges are not universal prerequisites; stronger evidence may be required on risk escalation/dispute.

Professional/owner-direct representation conflict must eventually be modeled through the existing `PhysicalBoat -> MarketEpisode` identity boundary plus explicit representation/sale-authority semantics; do not introduce a naïve global one-listing-per-PhysicalBoat shortcut.

Read the exact owner-direct product direction/spec before touching these domains.

## Product execution policy (post-SLICE-0038)

`docs/PRODUCT_EXECUTION_PLAN.md` governs product sequencing from SLICE-0039 onward, as reconciled by later owner-accepted execution records including the 2026-09-14 owner-direct reconciliation.

The execution principle is:

> **Strict truth. Fast product. Test the business before building the business.**

Every post-0038 primary slice must enter READY with all three explicit checks set to PASS:

```text
ONE-CAPABILITY CHECK
VISIBLE-RESULT CHECK
PRODUCT EXECUTION PLAN ALIGNMENT
```

`START_SLICE` enforces these markers mechanically for SLICE-0039 and later.

Agents must preserve the intent behind those checks during implementation:

- one user-visible capability OR one business-critical hypothesis per ordinary slice;
- the Project Owner can personally execute, observe or inspect the result;
- no generic framework or infrastructure widening without an active consumer/blocker;
- no second market adapter immediately after SLICE-0038 merely because it is the next obvious technical task;
- strict truth/provenance/fail-closed behavior remains non-negotiable while process scope is reduced for speed.

If implementation reveals that the slice no longer satisfies its PASS checks, stop and report the scope problem rather than silently widening the slice.

## Core data/identity/provenance guardrails

- Never invent missing boat data.
- Missing/unknown is not evidence that a characteristic is absent.
- No accepted production value without provenance.
- Preserve input identity separately from verified canonical identity.
- Preserve raw source representation when normalization occurs.
- Do not silently resolve conflicting authoritative evidence.
- Keel, rudder and skeg are independent dimensions.
- Monohulls, catamarans and trimarans are first-class.
- Canonical physical storage uses SI where practical.
- Derived metrics require the accepted versioned methodology and lineage.
- Do not force ambiguous model/generation/variant identities into one canonical identity.
- Brand and builder/manufacturer Organization are distinct identity concepts when evidence requires it.
- The SailboatData reference scrape is never an invisible production-data fallback.
- Build for broad design-universe coverage with progressive verification depth; sparse valid records are allowed when unknowns/provenance remain explicit.
- Source access and source reuse rights are separate; production/bulk/automation use fails closed unless cleared by accepted source-rights policy.

Read the exact controlling identity/provenance/source-rights/metric specs when the slice touches those domains.

## Research behavior

Use real source evidence rather than imagined source formats. Prefer authoritative/primary sources according to `research/RESEARCH_WORKFLOW.md` when the assigned research requires external verification.

Appropriately licensed/open structured data may bootstrap common facts when provenance is explicit. Use `null`, `unknown`, `needs_review` or `conflict` when evidence is insufficient.

Read `docs/DATABASE_COVERAGE_STRATEGY.md` before changing ingestion/coverage/search semantics.

## Application architecture guardrail

Application/backend/persistence/frontend/deployment work is authorized only by the relevant slice.

Accepted baseline is defined by:

- `architecture/decisions/ADR-0010-vps-first-application-stack.md`;
- `docs/engineering/APPLICATION_STACK_BASELINE.v0.1.md`;
- `architecture/SYSTEM_ARCHITECTURE.md`.

Read these only when the assigned slice touches that architecture.

Key baseline: CPython/FastAPI backend, PostgreSQL production persistence, Astro + TypeScript web with selective React islands, simple portable Linux VPS deployment, responsive web/PWA first and later Flutter consuming the same API. Do not introduce a second business-logic stack, client-only SPA, dedicated search engine or distributed infrastructure without an accepted decision.

Open decisions remain open: do not silently choose alert cadence (OQ-006), public API/versioning (OQ-015), or detailed public SEO surface mechanics (OQ-018). Auth/session is no longer broadly open where SLICE-0053 has accepted a concrete broker boundary; read current state/closure before treating an old OQ as authoritative.

## Search / SEO / internationalization

Search Architecture and SEO are first-class product architecture (ADR-0007). Before changing public routing, indexable page types, filters/facets, canonicalization, rendering, metadata, sitemap behavior or structured data, read:

- `architecture/SEARCH_AND_SEO_ARCHITECTURE.md`;
- `docs/PRODUCT_LED_SEO_STRATEGY.md`;
- OQ-018 and any slice-specific SEO contract.

Do not turn arbitrary faceted search states into an uncontrolled indexable URL universe.

The owner-direct pivot adds a permanent Search-commercial-independence rule: broker/private-seller payments, subscription tier, verification fees, referral economics, affiliate value and advertising relationships may not affect organic eligibility, match classification or organic ordering.

HullQ's required public languages are English, German, French, Portuguese and Spanish. Canonical data/identity/query semantics remain language-neutral; localization rules are governed by `docs/PRODUCT_LANGUAGE_AND_I18N_REQUIREMENT.md` and future OQ-018 implementation decisions.

## Market integrations

Keep each external marketplace behind its own adapter. Verify permitted API/feed/partner/access terms before implementation. Historical price/listing retention is governed separately by source rights and OQ-017.

Native owner-direct supply is not an external marketplace adapter and must use HullQ's accepted first-party marketplace identities/truth/authorization boundaries.

## Docs-to-code / engineering behavior

- Do not implement behavior that lacks an accepted requirement/spec when one is required.
- Do not silently resolve an `OQ-*` blocker.
- Significant architecture decisions require an ADR.
- Behavioral requirements must be traceable to tests.
- Update spec + tests + code atomically when semantics change.
- Keep first-party HullQ assets in this repository.
- Prefer small, testable changes and existing helpers/contracts.
- Keep raw imports immutable.
- Do not couple public filters to arbitrary raw-source fields.
- Do not encode multiple technical concepts into one legacy field.

## Context / session discipline

- One Claude session normally equals one slice.
- Start each new slice in a fresh conversation; if reusing the Claude Code UI, `/clear` before the new START_SLICE prompt.
- Use `/context` when context growth is unclear.
- Use `/compact` during a long same-slice task before context becomes excessive; preserve controlling contract, decisions, changed files, validation state and unresolved blockers, not exploratory history/logs.
- Do not carry previous slice reports/discussion into a new slice unless explicitly required.
- After final handoff, stop; the next slice starts fresh.

Full operational guidance: `docs/engineering/AI_TOKEN_EFFICIENCY.md`.
