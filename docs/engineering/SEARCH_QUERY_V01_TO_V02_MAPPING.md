# Search query-contract v0.1 -> v0.2 mapping — SLICE-0035

Engineering note explaining the serialized query-contract evolution
introduced by SLICE-0035. Not a spec: `specs/SEARCH_QUERY_SEMANTICS.v0.1.md`
remains the controlling truth-semantics document. This note only explains the
JSON wire-format relationship between `hullq.search.query` (v0.1, SLICE-0033)
and `hullq.search.query_mixed` (v0.2, SLICE-0035).

## Why a new version instead of extending v0.1 in place

`specs/SEARCH_QUERY_SEMANTICS.v0.1.md` §8 requires explicit boolean structure
and the SLICE-0035 slice contract requires that "Existing serialized query
version `0.1` MUST remain readable with identical meaning" and that v0.2
"SHOULD represent categorical leaves without adding silent optional keys to
v0.1." Silently adding an optional `"kind"` key (or an optional `"equals"`
key) to the existing v0.1 criterion shape would violate that: v0.1's
`hullq.search.query._criterion_from_json_dict` already fails closed on any
key outside its exact accepted set, so it cannot be extended without either
breaking that fail-closed guarantee or quietly changing what "v0.1" means
after the fact. A new explicit version is therefore the only compatible path.

## What changed

| | v0.1 (`hullq.search.query`) | v0.2 (`hullq.search.query_mixed`) |
|---|---|---|
| Query type | `AndQuery` | `MixedAndQuery` |
| Leaf kinds | numeric only | numeric or categorical, discriminated by an explicit `"kind"` key (`"NUMERIC"` \| `"CATEGORICAL"`) |
| Numeric leaf shape | `field`, `comparison`, `threshold_min`, `threshold_max`, `strength` | identical five keys, plus `"kind": "NUMERIC"` |
| Categorical leaf shape | not representable | `"kind": "CATEGORICAL"`, `field`, `equals`, `strength` |
| Top-level shape | `schema_version`, `type`, `criteria` | identical three keys |
| Unknown key/kind/version handling | rejected (`ValueError`) | rejected (`ValueError`) |

v0.1's own module, parser, accepted key sets and error messages are
byte-for-byte unchanged by this slice (verified by the SLICE-0033 test suite
passing unmodified — zero drift).

## Compatibility contract

`hullq.search.query_mixed.mixed_query_from_json_dict` is the single
recommended read path going forward:

- a payload with `"schema_version": "0.1"` is parsed by delegating directly
  to the unmodified `hullq.search.query.query_from_json_dict` — identical
  validation, identical error messages, identical accepted key set — and its
  resulting `NumericLeafCriterion` tuple is wrapped unchanged into a
  `MixedAndQuery`;
- a payload with `"schema_version": "0.2"` is parsed natively, dispatching
  each criterion on its `"kind"` discriminator;
- any other `schema_version` (including a missing value), unsupported
  `"type"`, unknown top-level key, unknown criterion key, or
  missing/unrecognized `"kind"` raises `ValueError` — fails closed, never
  silently discards or coerces.

`hullq.search.query_mixed.mixed_query_to_json_dict` always serializes to
`"0.2"`, even when every criterion happens to be numeric. A `MixedAndQuery`
is never silently downgraded to v0.1 on write, so a caller can never lose
track of which parser round-trips a given payload losslessly.

`hullq.search.query.query_to_json_dict`/`query_from_json_dict` remain the
correct pair for a caller that only ever needs numeric criteria and wants to
keep emitting the smaller v0.1 wire shape.

## What did not change

- Truth semantics: AND reduction (`hullq.search.query.and_reduce`), the
  numeric leaf's inclusive-boundary comparison, and the fail-closed
  qualification-to-reason-code mapping are reused unmodified by every v0.2
  numeric leaf. Categorical leaves reuse the identical fail-closed
  qualification pattern via `hullq.search.criteria.evaluate_categorical_leaf`.
- No persisted v0.1 query payload requires migration: it keeps parsing to the
  exact same criteria it always did.
