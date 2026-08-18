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

- [ ] Slice acceptance criteria pass.
- [ ] Repository/schema validation passes.
- [ ] Ruff format and lint pass.
- [ ] mypy strict passes for `src/`.
- [ ] pytest and branch-coverage gate pass.
- [ ] Relevant golden/property/regression fixtures were added or updated.
- [ ] Documentation, slice status and `PROJECT_STATE.md` were updated when project state or behavior changed.

## Notes

<!-- Explain non-obvious tradeoffs, migrations, blockers, or intentionally deferred work. -->
