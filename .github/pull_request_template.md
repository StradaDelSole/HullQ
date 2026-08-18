# HullQ change checklist

## Slice / controlling artifacts

- Slice ID: <!-- e.g. SLICE-0003 -->
- Requirement IDs: <!-- e.g. REQ-DATA-001 -->
- Specification / ADR: <!-- paths -->
- Open question checked: `docs/governance/OPEN_QUESTIONS.md`

## Change

- [ ] This PR stays inside the assigned slice scope.
- [ ] This change follows `spec/decision → tests → implementation → verification`.
- [ ] No unresolved semantic decision was made only in code.
- [ ] Persisted/public contract changes are versioned and migration impact is documented.
- [ ] Source-rights/provenance consequences were evaluated when data acquisition or retention changes.
- [ ] Search/SEO consequences were evaluated when public routing, filtering, rendering or indexable content changes.
- [ ] The next slice was not started automatically.

## Verification

- [ ] Every checked slice acceptance criterion has actually been verified.
- [ ] Repository/schema validation passes or is not applicable.
- [ ] Ruff format and lint pass or are not applicable.
- [ ] mypy strict passes for `src/` or is not applicable.
- [ ] pytest and branch-coverage gate pass or are not applicable.
- [ ] Relevant golden/property/regression fixtures were added or updated where required.
- [ ] Documentation, slice status and `PROJECT_STATE.md` were updated when project state or behavior changed.

## Slice completion report

### Slice

- Recommended slice state: `REVIEW` / `BLOCKED`
- Scope completed: `YES` / `NO`

### Changes

- Changed files:
- Requirements implemented/researched:
- Tests/fixtures added or updated:

### Validation

- Local validation: `PASS` / `FAIL` / `PARTIAL` / `NOT APPLICABLE`
- Commands run:
- Results:

### External verification

- Remote CI: `PASS` / `FAIL` / `NOT VERIFIED` / `NOT APPLICABLE`
- Other external gates: `PASS` / `FAIL` / `NOT VERIFIED` / `NOT APPLICABLE`

### Findings

- Unresolved findings:
- Spec/ADR ambiguities:
- Scope deviations:

### Follow-up

- Recommended next action:

### Agent declaration

- [ ] No work outside the assigned slice was started.
- [ ] No unverified acceptance criterion was marked as passed.
- [ ] The next slice was not started automatically.
- [ ] The implementation/research agent has NOT marked this slice `DONE`.

## Independent review / acceptance

These items are completed after the implementation/research agent hands the slice off.

- [ ] Required remote/external checks have actually been verified.
- [ ] Independent spec/architecture review completed.
- [ ] User/project-owner acceptance received.
- [ ] Slice may now be moved from `REVIEW` to `DONE`.

## Notes

<!-- Explain non-obvious tradeoffs, migrations, blockers, acceptance evidence, or intentionally deferred work. -->
