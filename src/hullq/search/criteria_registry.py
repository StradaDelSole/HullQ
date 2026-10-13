"""Static whitelisted public multi-criterion Search registry — SLICE-0085.

Implements the slice's "Shared foundation" constraint 1: a small, explicitly
whitelisted, code-based registry of every criterion HullQ's native Buyer
Search and broker Search-fit preview accept, naming each one's stable public
parameter key(s), unit/allowed-token vocabulary (where bounded) and the
canonical ordering `hullq.application.search_read.build_canonical_search_path`
and its broker-preview counterpart must use. This module carries no
behavior of its own -- parsing, FieldResolution qualification and concrete
claim classification stay in each criterion's own bridge module
(`hullq.search.draft_max_design_bridge`, `keel_design_bridge`,
`loa_design_bridge`, `rudder_design_bridge`) and application funnel
(`hullq.application.native_inventory_query`); this is a single reusable
*lookup table* so every HTTP-boundary module agrees on the same whitelist
rather than hand-maintaining its own frozenset/ordering (SLICE-0056
independent-review Finding 2's "key order is itself an observable
non-canonicalization defect" concern, generalized to five keys).

A registry entry is never a database field scan, a raw JSON field pointer, a
user-controlled path, or a dynamically-registered plugin: every entry below
is a fixed, reviewed, compile-time constant exactly like the two originally
accepted SLICE-0051/0055 criteria were before this slice existed.
"""

from __future__ import annotations

from typing import Final

__all__ = [
    "CANONICAL_PARAM_KEY_ORDER",
    "DRAFT_MAX_PARAM_KEY",
    "KEEL_CONFIGURATION_PARAM_KEY",
    "LOA_MAX_PARAM_KEY",
    "LOA_MIN_PARAM_KEY",
    "RUDDER_CONFIGURATION_PARAM_KEY",
    "SUPPORTED_PARAM_KEYS",
]

#: Stable public query-parameter keys. These are the exact strings used in
#: public canonical Search URLs, the private broker Search-fit scenario and
#: the typed FastAPI/TS boundary -- never renamed without an accepted
#: canonical-URL migration decision.
DRAFT_MAX_PARAM_KEY: Final = "draft_max"
KEEL_CONFIGURATION_PARAM_KEY: Final = "keel_configuration"
LOA_MIN_PARAM_KEY: Final = "loa_min"
LOA_MAX_PARAM_KEY: Final = "loa_max"
RUDDER_CONFIGURATION_PARAM_KEY: Final = "rudder_configuration"

#: The complete bounded whitelist. Any query-parameter key outside this set
#: is INVALID, never silently ignored (the accepted zero-non-semantic-
#: allowlist policy, `docs/OQ_018_SEARCH_NONSEMANTIC_ALLOWLIST_DECISION_2026-09-11.md`,
#: extended to every criterion this slice adds).
SUPPORTED_PARAM_KEYS: Final[frozenset[str]] = frozenset(
    {
        DRAFT_MAX_PARAM_KEY,
        KEEL_CONFIGURATION_PARAM_KEY,
        LOA_MIN_PARAM_KEY,
        LOA_MAX_PARAM_KEY,
        RUDDER_CONFIGURATION_PARAM_KEY,
    }
)

#: The one accepted canonical key ordering (slice normative LOA semantics:
#: "Public canonical key order is the accepted lexicographic policy, not UI
#: display order"). Plain lexicographic sort of `SUPPORTED_PARAM_KEYS` --
#: asserted below so this constant can never silently drift from that rule.
CANONICAL_PARAM_KEY_ORDER: Final[tuple[str, ...]] = (
    DRAFT_MAX_PARAM_KEY,
    KEEL_CONFIGURATION_PARAM_KEY,
    LOA_MAX_PARAM_KEY,
    LOA_MIN_PARAM_KEY,
    RUDDER_CONFIGURATION_PARAM_KEY,
)

assert tuple(sorted(SUPPORTED_PARAM_KEYS)) == CANONICAL_PARAM_KEY_ORDER, (
    "CANONICAL_PARAM_KEY_ORDER must stay exactly the lexicographic sort of "
    "SUPPORTED_PARAM_KEYS -- see this module's docstring"
)
