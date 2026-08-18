# HullQ — Versioning and Change Control

**Status:** ACCEPTED baseline

## Contract versions

Schemas, taxonomies, formula methodologies, canonical API contracts and other persisted/public semantics are explicit versions.

During initial development, `0.x` versions are expected. A move to `1.0.0` indicates the relevant public contract is intentionally stable.

## Semantic versioning

For stable released contracts use Semantic Versioning 2.0.0:

- MAJOR — incompatible contract/behavior change;
- MINOR — backward-compatible addition;
- PATCH — backward-compatible correction.

Pre-1.0 contract changes still require explicit version increments and migration consideration; `0.x` is not permission to silently mutate persisted meaning.

## Immutable releases

Once a schema/spec version is used for persisted production data or exposed to consumers, do not rewrite its semantics in place. Create a new version.

## Commit convention

Use Conventional Commits 1.0.0 during active coding:

```text
feat(search): add unknown-data candidate state
fix(research): preserve raw unit on normalization conflict
spec(identity): define generation boundary
chore(ci): add schema validation gate
```

Breaking changes use the specification's breaking-change notation and MUST be accompanied by the corresponding contract/version change.

## Changelog

`CHANGELOG.md` records meaningful project-level changes. Do not fill it with every internal refactor. Prioritize:

- normative behavior changes;
- schema/taxonomy/formula versions;
- architecture decisions;
- migration-impacting changes;
- major research/data strategy changes;
- release milestones.
